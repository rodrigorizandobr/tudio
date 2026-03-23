
import asyncio
import json
import time
import os
from typing import Optional, List, Dict, Any
from openai import AsyncOpenAI
from openai.types.beta.threads import Run
from backend.core.configs import settings
from backend.core.logger import log
from backend.services.serpapi_service import serpapi_service

class OpenAIService:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model_name = settings.OPENAI_MODEL
        # Semaphore to limit concurrent API calls (e.g., max 3 at once to avoid quota spikes)
        self._semaphore = asyncio.Semaphore(3)
        # Minimum delay between calls to stay within RPM limits (adjustable)
        self._rate_limit_delay = 1.5 

        if self.api_key:
            self.client = AsyncOpenAI(api_key=self.api_key)
        else:
            self.client = None
            log.warning("OpenAI API Key missing. OpenAIService disabled.")

    async def create_thread(self) -> Optional[str]:
        """Creates a new Thread and returns its ID."""
        if not self.client: return None
        try:
            thread = await self.client.beta.threads.create()
            log.info(f"Created new OpenAI Thread: {thread.id}")
            return thread.id
        except Exception as e:
            log.error(f"Failed to create OpenAI Thread: {e}")
            raise e
    
    async def reset_thread(self, old_thread_id: str) -> str:
        """
        Creates a new thread to replace a corrupted one.
        This is useful when a thread's context becomes corrupted and starts
        returning conversational responses instead of following instructions.
        
        Args:
            old_thread_id: The corrupted thread ID to replace
            
        Returns:
            New thread ID
        """
        if not self.client:
            raise ValueError("OpenAI Client not initialized")
        
        new_thread_id = await self.create_thread()
        log.warning(f"Reset corrupted thread {old_thread_id} → new thread {new_thread_id}")
        return new_thread_id

    async def get_or_create_assistant(self, name: str, instructions: str) -> str:
        """
        Retrieves an assistant by name (simple cache/search logic could be added) or creates one.
        For now, we'll create/update a specific one or rely on ID if stored. 
        Simplest approach for this refactor: Create/Update based on a fixed config or search list.
        To avoid cluttering, we can use a single ID if provided in env, else find by metadata/name.
        """
        if not self.client: raise ValueError("OpenAI Client not initialized")
        
        # Simple Strategy: List assistants, find by name. If not found, create.
        # Note: Listing is paginated, but usually few assistants.
        assistants = await self.client.beta.assistants.list(limit=20)
        for a in assistants.data:
            if a.name == name:
                # Update instructions/model if needed
                if a.model != self.model_name or a.instructions != instructions:
                    await self.client.beta.assistants.update(
                        a.id, 
                        instructions=instructions,
                        model=self.model_name
                    )
                return a.id
        
        # Create new
        response = await self.client.beta.assistants.create(
            name=name,
            instructions=instructions,
            model=self.model_name,
            tools=[{"type": "function", "function": {
                "name": "google_search",
                "description": "Searches Google for real-time technical data, specs, news. Use this to find accurate details.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"]
                }
            }}]
        )
        return response.id

    async def send_message_and_wait(self, thread_id: str, assistant_id: str, content: str) -> str:
        """
        Sends a message to the thread, starts a run, handles tool calls, and returns the final text response.
        """
        if not self.client: raise ValueError("OpenAI Client not initialized")

        # 1. Add Message
        log.info(f"Sending message to thread {thread_id[:8]}... (length: {len(content)} chars)")
        print(f"\n================ [OPENAI PROMPT START] ================\nTO THREAD: {thread_id}\n\n{content}\n\n================ [OPENAI PROMPT END] ================\n")
        
        # Check for potentially missing variables
        if "{agent_" in content:
            log.warning(f"⚠️ POTENTIAL MISSING AGENT VARIABLE detected in prompt: {content[:200]}...")

        await self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=content
        )

        # 2. Start Run
        run = await self.client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )

        # 3. Poll Loop
        while True:
            # Wait a bit
            await asyncio.sleep(1) # Polling interval
            
            run_status = await self.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            
            if run_status.status == 'completed':
                break
            elif run_status.status == 'requires_action':
                # Handle Tool Calls
                tool_outputs = []
                for tool_call in run_status.required_action.submit_tool_outputs.tool_calls:
                    if tool_call.function.name == "google_search":
                        output = await self._handle_google_search(tool_call)
                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": output
                        })
                
                # Submit outputs
                if tool_outputs:
                    await self.client.beta.threads.runs.submit_tool_outputs(
                        thread_id=thread_id,
                        run_id=run.id,
                        tool_outputs=tool_outputs
                    )
            elif run_status.status in ['failed', 'cancelled', 'expired']:
                log.error(f"Run failed with status: {run_status.status}. Last error: {run_status.last_error}")
                raise ValueError(f"OpenAI Run failed: {run_status.last_error}")

        # 4. Get Messages
        messages_page = await self.client.beta.threads.messages.list(
            thread_id=thread_id,
            limit=1,
            order="desc" # Newest first
        )
        
        if not messages_page.data:
            return ""
            
        last_msg = messages_page.data[0]
        if last_msg.role == "assistant":
            # Extract text
            full_text = ""
            for block in last_msg.content:
                if block.type == 'text':
                    full_text += block.text.value
            
            log.info(f"Received response from thread {thread_id[:8]}... (length: {len(full_text)} chars)")
            print(f"\n[OPENAI RESPONSE] <<< From {thread_id[:8]}:\n{full_text}\n----------------------------------------\n")
            return full_text
        
        return ""

    async def send_message_and_wait_json(self, thread_id: str, assistant_id: str, content: str) -> str:
        """
        Sends a message to the thread, starts a run, handles tool calls, and returns the final text response.
        FORCES JSON OUTPUT via response_format parameter.
        """
        if not self.client: raise ValueError("OpenAI Client not initialized")

        # 1. Add Message
        log.info(f"Sending JSON mode message to thread {thread_id[:8]}... (length: {len(content)} chars)")
        print(f"\n================ [OPENAI JSON PROMPT START] ================\nTO THREAD: {thread_id}\n\n{content}\n\n================ [OPENAI JSON PROMPT END] ================\n")

        # Check for potentially missing variables
        if "{agent_" in content:
            log.warning(f"⚠️ POTENTIAL MISSING AGENT VARIABLE detected in JSON prompt: {content[:200]}...")
        
        await self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=content
        )

        # 2. Start Run with JSON mode
        run = await self.client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,
            response_format={"type": "json_object"}  # CRITICAL: Force JSON
        )
        log.info(f"Started JSON mode run {run.id} on thread {thread_id[:8]}...")

        # 3. Poll Loop
        while True:
            # Wait a bit
            await asyncio.sleep(1) # Polling interval
            
            run_status = await self.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            
            if run_status.status == 'completed':
                break
            elif run_status.status == 'requires_action':
                # Handle Tool Calls
                tool_outputs = []
                for tool_call in run_status.required_action.submit_tool_outputs.tool_calls:
                    if tool_call.function.name == "google_search":
                        output = await self._handle_google_search(tool_call)
                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": output
                        })
                
                # Submit outputs
                if tool_outputs:
                    await self.client.beta.threads.runs.submit_tool_outputs(
                        thread_id=thread_id,
                        run_id=run.id,
                        tool_outputs=tool_outputs
                    )
            elif run_status.status in ['failed', 'cancelled', 'expired']:
                log.error(f"Run failed with status: {run_status.status}. Last error: {run_status.last_error}")
                raise ValueError(f"OpenAI Run failed: {run_status.last_error}")

        # 4. Get Messages
        messages_page = await self.client.beta.threads.messages.list(
            thread_id=thread_id,
            limit=1,
            order="desc" # Newest first
        )
        
        if not messages_page.data:
            return ""
            
        last_msg = messages_page.data[0]
        if last_msg.role == "assistant":
            # Extract text
            full_text = ""
            for block in last_msg.content:
                if block.type == 'text':
                    full_text += block.text.value
            
            log.info(f"Received JSON mode response from thread {thread_id[:8]}... (length: {len(full_text)} chars)")
            print(f"\n[OPENAI JSON RESPONSE] <<< From {thread_id[:8]}:\n{full_text}\n----------------------------------------\n")
            
            # Warn if response doesn't look like JSON
            if full_text.strip() and not full_text.strip().startswith(('{', '[')):
                log.warning(f"JSON mode response doesn't start with {{ or [: {full_text[:100]}...")
            
            return full_text
        
        return ""

    async def _handle_google_search(self, tool_call) -> str:
        try:
            args = json.loads(tool_call.function.arguments)
            query = args.get("query")
            log.info(f"Executing Tool 'google_search': {query}")
            
            search_results = await serpapi_service.search("serpapi", query, per_page=5)
            
            minified_results = []
            for r in search_results:
                minified_results.append({
                    "title": r.get('description'),
                    "link": r.get('author_url') or r.get('url'),
                    "source": r.get('author_name')
                })
            
            return json.dumps(minified_results, ensure_ascii=False)
        except Exception as e:
            log.error(f"Tool execution failed: {e}")
            return json.dumps({"error": str(e)})

    async def generate_tts(self, text: str, output_path: str, voice: str = "alloy", instructions: Optional[str] = None) -> str:
        """
        Generates Audio using GPT-4o Audio (preview) to allows instructions/acting control.
        If the voice is not supported by the preview model, it falls back to the standard TTS API.
        """
        if not self.client:
            raise ValueError("OpenAI Client not initialized")
            
        # Global Safety Net: Always force lowercase voice
        voice = voice.lower()
        
        # Voices supported by gpt-4o-mini-audio-preview / gpt-4o-audio-preview
        # Expansion: Added newest voices ash, ballad, coral, sage, verse, marin, cedar.
        audio_preview_supported_voices = {
            "alloy", "echo", "fable", "onyx", "nova", "shimmer",
            "ash", "ballad", "coral", "sage", "verse", "marin", "cedar"
        }
            
        async with self._semaphore:
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # Check if we should use Audio Preview (supports instructions) or Standard TTS
                if voice in audio_preview_supported_voices:
                    log.info(f"Generating Audio ({len(text)} chars) using GPT-4o Audio and voice '{voice}'")
                    target_model = "gpt-4o-mini-audio-preview"
                    
                    # Construct message
                    messages = []
                    system_content = instructions or "Você é um narrador profissional."
                    system_content += f"\n\nIMPORTANTE: Use um tom de voz consistente. A voz solicitada é '{voice}'."
                    messages.append({"role": "system", "content": system_content})
                    
                    conversation_content = f"Por favor, leia o seguinte texto em voz alta, seguindo as instruções de direção de voz acima:\n\n'{text}'"
                    messages.append({"role": "user", "content": conversation_content})
                    
                    log.info(f"Sending Audio Request to {target_model} | Voice: {voice} | Inst: {instructions[:50] if instructions else 'None'}...")
                    
                    completion = await self.client.chat.completions.create(
                        model=target_model,
                        modalities=["text", "audio"],
                        audio={"voice": voice, "format": "mp3"},
                        messages=messages
                    )
                    
                    if completion.choices[0].message.audio:
                        import base64
                        audio_data = base64.b64decode(completion.choices[0].message.audio.data)
                        with open(output_path, "wb") as f:
                            f.write(audio_data)
                        log.info(f"Audio generated successfully via GPT-4o Audio: {output_path}")
                        return output_path
                    else:
                        error_msg = "No audio returned from GPT-4o Audio model."
                        log.error(error_msg)
                        raise ValueError(error_msg)
                else:
                    # FALLBACK: Standard TTS API (tts-1-hd)
                    log.info(f"Generating Audio ({len(text)} chars) using Standard TTS Fallback (tts-1-hd) and voice '{voice}'")
                    
                    response = await self.client.audio.speech.create(
                        model="tts-1-hd",
                        voice=voice, # type: ignore
                        input=text
                    )
                    
                    # Modern way to save response content in OpenAI v1+
                    await response.awrite_to_file(output_path)
                    log.info(f"Audio generated successfully via Standard TTS Fallback: {output_path}")
                    return output_path
                
            except Exception as e:
                log.error(f"Failed to generate TTS: {e}")
                raise e

openai_service = OpenAIService()

# --- MOCK FOR TESTING ---
if settings.TESTING and os.getenv("USE_E2E_MOCKS") == "True":
    log.warning("⚠️ E2E MOCK MODE DETECTED: Mocking OpenAIService for E2E tests.")
    
    # Common Mock Data
    MOCK_FULL_RESPONSE = {
        "title": "Mock Video Title",
        "description": "Mock Video Description",
        "tags": "mock, test, video",
        "visual_style": "Cinematic",
        "music": "Happy",
        "characters": [
            {"name": "Narrator", "description": "Standard voice", "voice": "alloy"}
        ],
        "chapters": [
            {
                "id": 1,
                "order": 1,
                "title": "Mock Chapter 1",
                "estimated_duration_minutes": 1,
                "description": "Mock Description"
            }
        ],
        "subchapters": [
            {
                "id": 1,
                "order": 1,
                "title": "Mock Subchapter 1",
                "description": "Mock Subchapter Desc"
            }
        ],
        "scenes": [
            {
                "id": 1,
                "order": 1,
                "duration_seconds": 5,
                "narration_content": "This is a mock narration for scene 1.",
                "visual_description": "A mock visual description.",
                "image_prompt": "mock image prompt",
                "video_prompt": "mock video prompt",
                "image_search": "mock search",
                "video_search": "mock video search",
                "audio_search": "mock audio"
            },
            {
                "id": 2,
                "order": 2,
                "duration_seconds": 5,
                "narration_content": "This is a mock narration for scene 2.",
                "visual_description": "A mock visual description.",
                "image_prompt": "mock image prompt",
                "video_prompt": "mock video prompt",
                "image_search": "mock search",
                "video_search": "mock video search",
                "audio_search": "mock audio"
            }
        ]
    }

    # Mock create_thread
    async def mock_create_thread(self) -> str:
        return "thread_mock_123"
    
    OpenAIService.create_thread = mock_create_thread # type: ignore
    
    # Mock send_message_and_wait (Text/JSON)
    async def mock_send_message_and_wait(self, thread_id: str, assistant_id: str, content: str) -> str:
        # Steps 0 and 1 use this and expect JSON
        log.info("MOCK: Returning Full JSON for text request.")
        return json.dumps(MOCK_FULL_RESPONSE)
        
    OpenAIService.send_message_and_wait = mock_send_message_and_wait # type: ignore

    # Mock send_message_and_wait_json (The critical one for Video Generation)
    async def mock_send_message_and_wait_json(self, thread_id: str, assistant_id: str, content: str) -> str:
        # Steps 2 and 3 use this
        log.info("MOCK: Returning Full JSON for JSON request.")
        return json.dumps(MOCK_FULL_RESPONSE)

    OpenAIService.send_message_and_wait_json = mock_send_message_and_wait_json # type: ignore

    # Mock generate_tts
    async def mock_generate_tts(self, text: str, output_path: str, voice: str = "alloy", instructions: Optional[str] = None) -> str:
        # Generate a valid 1-second silent MP3 using FFmpeg
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # We use a simple FFmpeg command to generate silent audio
        import subprocess
        try:
            # -f lavfi -i anullsrc=r=44100:cl=stereo:d=1 -c:a libmp3lame
            cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo:d=1", "-c:a", "libmp3lame", output_path]
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            log.info(f"MOCK TTS Generated (silent MP3) at {output_path}")
        except Exception as e:
            log.warning(f"MOCK TTS FFmpeg failed ({e}), falling back to dummy bytes.")
            with open(output_path, "wb") as f:
                f.write(b'\xFF\xFB\x90\x44' * 1024)
                
        return output_path
        
    OpenAIService.generate_tts = mock_generate_tts # type: ignore
    import types
    openai_service.generate_tts = types.MethodType(mock_generate_tts, openai_service) # Bind to instance as well
