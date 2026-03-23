import asyncio
import os
import json
import re
from typing import Optional
from datetime import datetime
# from openai import AsyncOpenAI (Removed)
from backend.core.configs import settings
from backend.models.video import (
    VideoModel, ChapterModel, SubChapterModel, SceneModel, 
    VideoStatus, CharacterModel
)
from backend.schemas.video import VideoCreate
from backend.repositories.video_repository import video_repository
from backend.core.logger import log
from backend.services.serpapi_service import serpapi_service
from backend.services.unsplash_service import unsplash_service
from backend.services.image_storage_service import image_storage_service
from backend.services.audio_service import audio_service
from backend.services.render_service import render_service
from backend.core.progress import update_video_progress



class VideoService:
    async def _get_video_context(self, video: VideoModel) -> dict:
        """
        Gather all available variables for prompt formatting.
        Uses specific prefixes (video_, chapter_, subchapter_) to avoid ambiguity.
        """
        context = {
            # Base variables (topic, duration, language, agent)
            "topic": video.prompt,
            "duration": f"{video.target_duration_minutes} minutes" if video.target_duration_minutes and video.target_duration_minutes > 0 else "Flexible/Automatic (Determine optimal length based on the topic)",
            "language": video.language,
            
            # Video metadata (renamed for clarity)
            "video_title": video.title or "",
            "video_description": video.description or "",
            "video_tags": video.tags or "",
            "video_visual_style": video.visual_style or "",
            "video_music": video.music or "",
            "video_characters": "",
            
            # Agent info
            "agent_name": "",
            "agent_description": "",
            "agent_icon": "",
            "agent_prompt_init": "",
            "agent_prompt_chapters": "",
            "agent_prompt_subchapters": "",
            "agent_prompt_scenes": ""
        }

        # Agent info
        if video.agent_id:
            agent = await self.agent_service.get(video.agent_id)
            if agent:
                context["agent_name"] = agent.name
                context["agent_description"] = agent.description
                context["agent_icon"] = agent.icon
                context["agent_prompt_init"] = agent.prompt_init or ""
                context["agent_prompt_chapters"] = agent.prompt_chapters or ""
                context["agent_prompt_subchapters"] = agent.prompt_subchapters or ""
                context["agent_prompt_scenes"] = agent.prompt_scenes or ""
                
                # DEBUG LOG for User
                log.info(f"Context Loaded Agent: '{agent.name}' (ID: {video.agent_id})")
                log.info(f"   - Init Instructions: {len(agent.prompt_init) if agent.prompt_init else 0} chars")
                log.info(f"   - Chapter Instructions: {len(agent.prompt_chapters) if agent.prompt_chapters else 0} chars")
            else:
                 log.warning(f"Video {video.id} has agent_id {video.agent_id} but Agent was NOT FOUND.")
        else:
             log.info(f"Video {video.id} has NO agent_id configured.")

        # Characters as JSON
        if video.characters:
            context["video_characters"] = json.dumps([
                {"name": c.name, "description": c.physical_description, "voice": c.voice}
                for c in video.characters
            ], ensure_ascii=False)

        return context

    def _format_prompt(self, template: str, **kwargs) -> str:
        """
        Robustly format string template, ignoring missing keys.
        """
        import string
        class SafeDict(dict):
            def __missing__(self, key):
                return '{' + key + '}'
        
        try:
            return string.Formatter().vformat(template, (), SafeDict(**kwargs))
        except Exception as e:
            log.error(f"Error formatting prompt template: {e}")
            return template

    def __init__(self, use_lock: bool = True, render_svc=None, audio_svc=None, openai_svc=None, 
                 unsplash_svc=None, serpapi_svc=None, storage_svc=None, repo=None, agent_svc=None):
        self._use_lock = use_lock
        self._locks = {} # Per-video locks
        
        # Dependency Injection for easier testing
        # Use module-level imports where available to respect patches
        
        # OpenAI Service is NOT imported at top level (avoid circular), so import here
        from backend.services.openai_service import openai_service as global_openai_service
        from backend.services.agent_service import agent_service as global_agent_service
        
        self.render_service = render_svc or render_service
        self.audio_service = audio_svc or audio_service
        self.openai_service = openai_svc or global_openai_service
        self.agent_service = agent_svc or global_agent_service
        self.unsplash_service = unsplash_svc or unsplash_service
        self.serpapi_service = serpapi_svc or serpapi_service
        self.image_storage_service = storage_svc or image_storage_service
        self.video_repository = repo or video_repository
    
    def _script_lock(self, video_id: int):
        """Returns or creates a lock for a specific video to ensure serialized script generation per video."""
        if not self._use_lock:
            # Return a dummy lock that never blocks (for tests)
            class DummyLock:
                async def __aenter__(self): return self
                async def __aexit__(self, *args): pass
            return DummyLock()
            
        if video_id not in self._locks:
            self._locks[video_id] = asyncio.Lock()
            
        return self._locks[video_id]

    async def create(self, video_in: VideoCreate) -> VideoModel:
        video = VideoModel(
            prompt=video_in.prompt,
            target_duration_minutes=video_in.target_duration_minutes,
            language=video_in.language,
            auto_image_source=video_in.auto_image_source,
            auto_generate_narration=video_in.auto_generate_narration,
            transition_type=video_in.transition_type,
            audio_transition_padding=video_in.audio_transition_padding or 0.5,
            aspect_ratios=video_in.aspect_ratios or ["16:9"], # Default
            agent_id=video_in.agent_id,
            script_content=video_in.script_content,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status=VideoStatus.PENDING,
            progress=0.0
        )
        return await self.video_repository.save(video)

    async def cancel_processing(self, video_id: int) -> bool:
        """
        Marks a video as CANCELLED or resets caption status to error.
        Background tasks must check this status periodically to stop execution.
        """
        video = await self.get(video_id)
        if not video:
            return False
        
        # Check active states
        is_processing = video.status in [VideoStatus.PENDING, VideoStatus.PROCESSING, VideoStatus.RENDERING, VideoStatus.RENDERING_SCENES]
        is_captioning = video.caption_status == "processing"

        if is_processing or is_captioning:
            # If ONLY captioning is active and video is already completed, don't cancel the whole video
            if is_captioning and video.status == VideoStatus.COMPLETED:
                log.info(f"Video {video_id}: resetting caption_status to 'error' (video is COMPLETED).")
                video.caption_status = "error"
            else:
                # Full cancellation
                video.status = VideoStatus.CANCELLED
                video.caption_status = "error"
                video.error_message = "Processamento cancelado pelo usuário."
                log.info(f"Video {video_id}: status set to CANCELLED.")

            await self._save_video_merged(video.id, video)
            return True
        
        return False

    async def duplicate_video(self, video_id: int) -> VideoModel:
        """
        Duplicates a video project, resetting its state and ID.
        Ensures OpenAI thread context is NOT copied.
        """
        original_video = await self.get(video_id)
        if not original_video:
            raise ValueError(f"Video {video_id} not found")

        # Create new video with same data but reset fields
        new_video = original_video.model_copy()
        new_video.id = None # Datastore will assign new ID
        new_video.created_at = datetime.now()
        new_video.updated_at = datetime.now()
        new_video.status = VideoStatus.PENDING
        new_video.progress = 0.0
        new_video.rendering_progress = 0.0
        new_video.error_message = None
        new_video.video_url = None
        new_video.social_publish_status = "draft"
        new_video.social_video_id = None
        new_video.timestamps_index = None
        
        # CRITICAL FIX: Reset OpenAI Thread to prevent context collision
        new_video.openai_thread_id = None 
        
        # Deep copy and reset assets
        new_video.characters = [c.model_copy() for c in original_video.characters]
        
        new_video.chapters = []
        for ch in original_video.chapters:
            new_ch = ch.model_copy()
            new_ch.status = VideoStatus.PENDING
            new_ch.error_message = None
            new_ch.subchapters = []
            for sub in ch.subchapters:
                new_sub = sub.model_copy()
                new_sub.scenes = []
                for sc in sub.scenes:
                     new_sc = sc.model_copy()
                     # Reset generated assets
                     new_sc.audio_url = None
                     new_sc.original_image_url = None
                     new_sc.cropped_image_url = None
                     new_sc.video_url = None
                     new_sc.generated_video_url = None
                     new_sub.scenes.append(new_sc)
                new_ch.subchapters.append(new_sub)
            new_video.chapters.append(new_ch)

        # Title adjustment
        new_video.title = f"{new_video.title} (Copy)"

        return await self.video_repository.save(new_video)

    async def get(self, video_id: int, include_deleted: bool = False) -> Optional[VideoModel]:
        return await self.video_repository.get(video_id, include_deleted=include_deleted)

    async def save(self, video: VideoModel) -> VideoModel:
        """
        Directly save/update a video model instance.
        """
        return await self.video_repository.save(video)

    async def _save_video_merged(self, video_id: int, bg_video: VideoModel) -> VideoModel:
        import asyncio
        """
        Atomic refresh and save strategy for background tasks.
        Fetches the latest video state from DB and merges background-controlled 
        fields while preserving user-controlled metadata.
        
        Deep Merge Logic:
        - If structure (chapter/scene count) changes, Background wins.
        - If structure is identical, preservation of user edits in scenes is performed.
        """
        try:
            latest = await self.video_repository.get(video_id)
            if not latest:
                log.warning(f"Video {video_id} not found in DB during merged save. Falling back to direct save.")
                return await self.video_repository.save(bg_video)

            # 1. Top-level Background fields (exclusive owner)
            bg_exclusive = [
                'status', 'progress', 'rendering_progress', 
                'error_message', 'openai_thread_id', 'total_duration_seconds',
                'timestamps_index', 'outputs', 'captioned_outputs',
                'caption_status', 'caption_progress', 'parallel_tasks'
            ]
            for field in bg_exclusive:
                bg_val = getattr(bg_video, field)
                db_val = getattr(latest, field)
                
                # SPECIAL CASE: dictionaries should be a MERGE, not an overwrite
                if field in ['parallel_tasks', 'outputs', 'captioned_outputs']:
                    if isinstance(bg_val, dict) and isinstance(db_val, dict):
                        merged = db_val.copy()
                        merged.update(bg_val)
                        setattr(latest, field, merged)
                        
                        # Special handling ONLY for parallel_tasks (rendering progress aggregation)
                        if field == 'parallel_tasks' and latest.aspect_ratios:
                            expected = len(latest.aspect_ratios)
                            if expected > 0:
                                total_acc = sum(merged.values())
                                avg_p = total_acc / expected
                                if latest.status == VideoStatus.RENDERING:
                                    latest.rendering_progress = avg_p
                                    latest.progress = avg_p
                                    log.info(f"Video {video_id}: Merged parallel_tasks={merged}. Expected={expected}. Aggregated progress={avg_p:.1f}%")
                    else:
                        setattr(latest, field, bg_val)
                    continue

                # PROTECTION: Never overwrite 'done' status with 'processing' (Anti-Ghost Process)
                if field == 'caption_status' and db_val == 'done' and bg_val == 'processing':
                    log.warning(f"Video {video_id}: Blocked status regression from 'done' to 'processing' for captions.")
                    continue

                if field == 'status' and db_val == 'completed' and bg_val in [VideoStatus.PROCESSING, VideoStatus.RENDERING]:
                    log.warning(f"Video {video_id}: Blocked overall status regression from 'completed' back to processing.")
                    continue

                # SPECIAL CASE: Never overwrite rendering_progress with 0 or None if DB has better value
                # Unless status is explicitly being reset to PENDING/PROCESSING
                if field == 'rendering_progress' and bg_val <= 0.0 and latest.rendering_progress > 0.0:
                    if bg_video.status not in [VideoStatus.PENDING, VideoStatus.PROCESSING]:
                         continue 

                # SPECIAL CASE: Never overwrite caption_progress with lower value
                if field == 'caption_progress' and (bg_val or 0) < (db_val or 0):
                    if bg_val != 0: # Allow reset to 0
                        continue

                setattr(latest, field, bg_val)

            # 2. Top-level User fields (background must NOT overwrite, but SYNC BACK)
            user_metadata = [
                'agent_id', 'language', 'title', 'description', 'tags',
                'visual_style', 'aspect_ratios', 'auto_image_source',
                'auto_generate_narration', 'audio_generation_instructions',
                'caption_style', 'music_id', 'characters'
            ]
            
            # INITIAL POPULATION: If a user field is empty in DB, take background value (Step 0)
            for field in user_metadata:
                db_val = getattr(latest, field)
                bg_val = getattr(bg_video, field)
                if not db_val: # If empty in DB (None, empty string, empty list)
                    setattr(latest, field, bg_val)

            # 3. Deep Merge Content (Chapters / Subchapters / Scenes)
            if not latest.chapters or len(latest.chapters) != len(bg_video.chapters):
                # Structural change (e.g. initial generation) -> BG wins
                latest.chapters = bg_video.chapters
                latest.script_content = bg_video.script_content
            else:
                # Merge existing structure
                for i, bg_chapter in enumerate(bg_video.chapters):
                    lat_chapter = latest.chapters[i]
                    
                    # SYNC Background Chapter fields to Latest
                    lat_chapter.status = bg_chapter.status
                    lat_chapter.error_message = bg_chapter.error_message
                    lat_chapter.estimated_duration_minutes = bg_chapter.estimated_duration_minutes
                    
                    # Merge subchapters if count matches
                    if not lat_chapter.subchapters or len(lat_chapter.subchapters) != len(bg_chapter.subchapters):
                        lat_chapter.subchapters = bg_chapter.subchapters
                    else:
                        for j, bg_sub in enumerate(bg_chapter.subchapters):
                            lat_sub = lat_chapter.subchapters[j]
                            
                            # Merge scenes if count matches
                            if not lat_sub.scenes or len(lat_sub.scenes) != len(bg_sub.scenes):
                                lat_sub.scenes = bg_sub.scenes
                            else:
                                for k, bg_scene in enumerate(bg_sub.scenes):
                                    lat_scene = lat_sub.scenes[k]
                                    # BG owns asset URLs and technical status
                                    asset_fields = [
                                        'original_image_url', 'generated_video_url', 
                                        'captioned_video_url', 'audio_url', 'duration_seconds',
                                        'generated_video_urls', 'captioned_video_urls'
                                    ]
                                    for f in asset_fields:
                                        bg_val = getattr(bg_scene, f)
                                        db_val = getattr(lat_scene, f)
                                        # Never overwrite a URL with null in merged save
                                        # (Prevents race conditions where progress saving clobbers URL saving)
                                        if bg_val is None and db_val is not None:
                                            continue
                                        setattr(lat_scene, f, bg_val)
                                    
                                    # User owns content prompts/text (Unless they are empty in DB)
                                    # We only overwrite if DB is empty to allow initial population
                                    content_fields = [
                                        'narration_content', 'visual_description', 
                                        'image_prompt', 'image_search', 'video_prompt',
                                        'video_search', 'audio_prompt', 'audio_search',
                                        'character', 'audio_effect_search'
                                    ]
                                    for f in content_fields:
                                        db_val = getattr(lat_scene, f)
                                        if not db_val: # If empty in DB, take BG value
                                            setattr(lat_scene, f, getattr(bg_scene, f))
                                        # else: preserve DB value (user edit)

            latest.updated_at = datetime.now()
            saved = await self.video_repository.save(latest)
            
            # 4. Sync EVERYTHING back to bg_video in memory (Maintaining Reference Integrity)
            # This ensures next AI/Processing step uses latest user-refined texts/prompts
            # while keeping the same objects that might be held by loops in process_video_background.
            for field in bg_exclusive:
                setattr(bg_video, field, getattr(saved, field))
            
            for field in user_metadata:
                setattr(bg_video, field, getattr(saved, field))
            
            bg_video.script_content = saved.script_content
            bg_video.updated_at = saved.updated_at

            # 5. In-Place Chapter/Scene Sync
            if not bg_video.chapters or len(bg_video.chapters) != len(saved.chapters):
                # Structural mismatch (e.g. initial generation) -> Replace list
                bg_video.chapters = saved.chapters
            else:
                # Same structure -> Sync fields into EXISTING objects to keep loop references alive
                for i, saved_chapter in enumerate(saved.chapters):
                    bg_chapter = bg_video.chapters[i]
                    bg_chapter.status = saved_chapter.status
                    bg_chapter.error_message = saved_chapter.error_message
                    bg_chapter.estimated_duration_minutes = saved_chapter.estimated_duration_minutes
                    bg_chapter.title = saved_chapter.title
                    bg_chapter.description = saved_chapter.description

                    # Subchapters
                    if not bg_chapter.subchapters or len(bg_chapter.subchapters) != len(saved_chapter.subchapters):
                        bg_chapter.subchapters = saved_chapter.subchapters
                    else:
                        for j, saved_sub in enumerate(saved_chapter.subchapters):
                            bg_sub = bg_chapter.subchapters[j]
                            bg_sub.title = saved_sub.title
                            bg_sub.description = saved_sub.description

                            # Scenes
                            if not bg_sub.scenes or len(bg_sub.scenes) != len(saved_sub.scenes):
                                # IMPORTANT: Never replace the list object during iteration/processing
                                # Update in-place to maintain reference integrity
                                bg_sub.scenes = saved_sub.scenes
                            else:
                                for k, saved_scene in enumerate(saved_sub.scenes):
                                    bg_scene = bg_sub.scenes[k]
                                    # Sync all scene fields back to background object
                                    # Using model_dump to get all fields safely
                                    for key, value in saved_scene.model_dump().items():
                                        setattr(bg_scene, key, value)
                
            return saved
        except Exception as e:
            log.error(f"CRITICAL: Failed deep merged save for video {video_id}: {e}", exc_info=True)
            return await self.video_repository.save(bg_video)

    async def list_all(
        self, 
        status: Optional[str] = None, 
        show_deleted: bool = False,
        search_query: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 50
    ) -> list[VideoModel]:
        return await self.video_repository.query_videos(
            status=status,
            show_deleted=show_deleted,
            search_query=search_query,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit
        )

    async def update(self, video_id: int, data: dict) -> VideoModel:
        """
        Update video with new data (e.g. scene image URLs).
        """
        existing_video = await self.video_repository.get(video_id)
        if not existing_video:
            raise ValueError(f"Video {video_id} not found")
        
        # DEBUG: Log incoming update for image URLs to verify payload
        try:
             # Deep inspection for debugging
             if 'chapters' in data:
                 for ch in data['chapters']:
                     for sub in ch.get('subchapters', []):
                         for sc in sub.get('scenes', []):
                             if 'original_image_url' in sc and sc['original_image_url']:
                                 log.info(f"Video {video_id} UPDATE: Received original_image_url for scene {sc.get('id')}: {sc['original_image_url']}")
        except Exception:
             pass

        # Robust Update: Merge existing data with new data and re-validate
        # This ensures nested dicts (chapters->scenes) are converted back to Models
        current_data = existing_video.model_dump()
        current_data.update(data)
        
        # Re-instantiate to enforce validation and type conversion
        updated_video = VideoModel(**current_data)
        
        # Preserve system fields that shouldn't be overridden by potential missing keys in partial updates (if any)
        # But here correct_data has everything.
        # Just ensure ID match
        if updated_video.id != video_id:
             updated_video.id = video_id
        
        updated_video.updated_at = datetime.now()
        return await self.video_repository.save(updated_video)

    async def update_scene_generated_url(self, video_id: int, chapter_id: int, subchapter_id: int, scene_idx: int, url: str):
        """
        Atomically updates ONLY the generated_video_url of a specific scene.
        Prevents full-model clobbering during long renders.
        """
        video = await self.video_repository.get(video_id)
        if not video:
            return False
            
        found = False
        for ch in video.chapters:
            if ch.id == chapter_id:
                for sub in ch.subchapters:
                    if sub.id == subchapter_id:
                        if len(sub.scenes) > scene_idx:
                            sub.scenes[scene_idx].generated_video_url = url
                            found = True
                            break
        
        if found:
            await self.video_repository.save(video)
            return True
        return False

    async def delete(self, video_id: int) -> bool:
        """
        Soft delete a video and cancel active processing.
        """
        # Cancel processing first to stop background task and log
        await self.cancel_processing(video_id)
        
        # Perform soft-delete and ensure status is CANCELLED (safeguard)
        return await self.video_repository.delete(video_id, status=VideoStatus.CANCELLED)
    
    async def restore(self, video_id: int) -> bool:
        """
        Restore a soft-deleted video.
        """
        return await self.video_repository.restore(video_id)
    
    
    async def reset_thread_for_video(self, video_id: int) -> bool:
        """
        Reset the OpenAI thread for a video. Useful when thread context is corrupted.
        
        Args:
            video_id: ID of the video
            
        Returns:
            True if successful, False if video not found
        """
        video = await self.get(video_id)
        if not video or not video.openai_thread_id:
            return False
        
        from backend.services.openai_service import openai_service
        
        old_thread_id = video.openai_thread_id
        new_thread_id = await self.openai_service.reset_thread(old_thread_id)
        
        video.openai_thread_id = new_thread_id
        await self._save_video_merged(video.id, video)
        
        log.info(f"Video {video_id}: Thread reset from {old_thread_id[:8]}... to {new_thread_id[:8]}...")
        return True
    
    async def _call_openai_with_retry(self, thread_id: str, assistant_id: str, 
                                      prompt: str, context: str, video_id: int, 
                                      use_json_mode: bool = True, max_retries: int = 1) -> str:
        """
        Call OpenAI with automatic retry on thread corruption.
        
        Args:
            thread_id: Current thread ID
            assistant_id: Assistant ID
            prompt: Prompt to send
            context: Context for logging (e.g., "Chapter 3")
            video_id: Video ID for thread reset
            use_json_mode: Whether to use JSON mode
            max_retries: Maximum number of retries (default: 1)
            
        Returns:
            OpenAI response content
            
        Raises:
            ValueError: If all retries fail
        """
        attempt = 0
        current_thread_id = thread_id
        
        while attempt <= max_retries:
            try:
                if use_json_mode:
                    content = await self.openai_service.send_message_and_wait_json(
                        current_thread_id, assistant_id, prompt
                    )
                else:
                    content = await self.openai_service.send_message_and_wait(
                        current_thread_id, assistant_id, prompt
                    )
                
                # Try to parse to trigger conversational detection
                self._safe_json_parse(content, context)
                return content
                
            except ValueError as e:
                error_msg = str(e)
                
                # Check if it's a thread corruption error
                if "THREAD_CORRUPTED" in error_msg and attempt < max_retries:
                    log.warning(f"{context}: Thread corrupted, resetting and retrying (attempt {attempt + 1}/{max_retries})")
                    
                    # Reset thread
                    await self.reset_thread_for_video(video_id)
                    
                    # Get new thread ID
                    video = await self.get(video_id)
                    current_thread_id = video.openai_thread_id
                    
                    # Update assistant with new thread (re-establish context)
                    # Note: We lose conversation history, but that's acceptable for corrupted threads
                    
                    attempt += 1
                    continue
                else:
                    # Not a thread corruption error, or out of retries
                    raise
        
        raise ValueError(f"{context}: Failed after {max_retries} retries")


    def _calculate_duration(self, text: str) -> int:
        """
        Calculates duration in seconds based on word count.
        Rule: 150 words per minute = 0.4 seconds per word.
        """
        if not text:
            return 0
        word_count = len(text.split())
        return round(word_count * 0.4)
    
    def _is_conversational_response(self, content: str) -> bool:
        """
        Detect if OpenAI response is conversational instead of the expected JSON.
        This happens when thread context becomes corrupted.
        
        Args:
            content: The response content to check
            
        Returns:
            True if content appears to be conversational, False otherwise
        """
        if not content or not content.strip():
            return False
            
        content_lower = content.lower().strip()
        
        # Common conversational patterns (multilingual)
        conversational_patterns = [
            "como posso ajudar",
            "how can i help",
            "what can i do for you",
            "posso ajudá-lo",
            "posso te ajudar",
            "em que posso ajudar",
            "how may i assist",
            "je peux vous aider",
            "cómo puedo ayudar"
        ]
        
        return any(pattern in content_lower for pattern in conversational_patterns)

    def _safe_json_parse(self, content: str, context: str = "") -> dict:
        """
        Safely parse JSON with error handling and recovery attempts.
        Args:
            content: JSON string to parse
            context: Context description for logging (e.g., "Step 0", "Chapter 1")
        Returns:
            Parsed JSON dict
        Raises:
            ValueError: If JSON cannot be parsed after recovery attempts
        """
        # Check for conversational response FIRST
        if self._is_conversational_response(content):
            log.error(f"OpenAI returned conversational response in {context}: {content[:100]}...")
            raise ValueError(
                f"THREAD_CORRUPTED:{context}:OpenAI returned conversational response instead of JSON. "
                f"This indicates the thread context is corrupted. Thread reset required."
            )
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            log.warning(f"JSON parse error in {context}: {str(e)}")
            log.warning(f"Problematic content (first 500 chars): {content[:500]}...")
            
            # Attempt 1: Try to fix common issues
            try:
                # Remove potential trailing commas
                cleaned = re.sub(r',\s*(}|])', r'\1', content)
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass
            
            # Attempt 2: Try to extract JSON from markdown code blocks
            try:
                json_match = re.search(r'```json\s*(.+?)```', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
            
            except json.JSONDecodeError:
                pass
            
            # Attempt 3: raw_decode (Best for "Extra data" errors)
            try:
                start_index = content.find('{')
                if start_index != -1:
                    decoder = json.JSONDecoder()
                    # raw_decode returns (obj, end_index)
                    # It parses specifically the first valid JSON object it finds
                    obj, _ = decoder.raw_decode(content[start_index:])
                    return obj
            except Exception:
                pass
            
            # Attempt 4: AST Literal Eval (for Single Quotes / Python Dicts)
            try:
               import ast
               # Only try this if it looks like a dict
               if content.strip().startswith('{'):
                   return ast.literal_eval(content)
            except Exception:
               pass
            
            # If all recovery attempts fail, log full content and raise
            log.error(f"Failed to parse JSON in {context}. Full content:\n{content}")
            raise ValueError(
                f"Invalid JSON in {context}: {str(e)}. "
                f"This usually means OpenAI returned malformed JSON. "
                f"Please try reprocessing the script."
            )

    def _is_ready_for_rendering(self, video: VideoModel) -> bool:
        """
        Check if all scenes have narration and visual assets.
        """
        # --- PERMISSIVE MODE FOR TESTING ---
        from backend.core.configs import settings
        if settings.TESTING and os.getenv("USE_E2E_MOCKS") == "True":
            log.warning(f"Video {video.id}: E2E MOCK mode active. Skipping strict asset validation.")
            return True

        for chapter in video.chapters:
            for subchapter in chapter.subchapters:
                for scene in subchapter.scenes:
                    if scene.deleted:
                        continue
                        
                    # Must have audio
                    if not scene.audio_url:
                        return False
                    # Must have original image OR video (Auto-crop happens at render)
                    if not scene.original_image_url and not scene.video_url:
                        return False
        return True

    async def process_video_background(self, video_id: int, stop_after_scenes: bool = False):
        log.info(f"Starting deep processing for video {video_id}")
        
        video = await self.get(video_id)
        if not video:
            return
            
        if video.deleted_at:
            log.warning(f"Video {video_id}: Attempted to process a deleted video. Stopping.")
            return

        try:
            video.status = VideoStatus.PROCESSING
            await self._save_video_merged(video.id, video)
            
            # VALIDATE PROMPTS EXIST BEFORE STARTING
            log.info(f"Video {video_id}: Validating prompts configuration...")
            if not settings.PROMPT_INIT_TEMPLATE or not settings.PROMPT_INIT_TEMPLATE.strip():
                log.error(f"Video {video_id}: PROMPT_INIT_TEMPLATE is empty. Cannot generate video.")
                video.status = VideoStatus.ERROR
                video.error_message = "Configure os prompts em Settings (.env) antes de gerar vídeos."
                await self._save_video_merged(video.id, video)
                return
                
            log.info(f"Video {video_id}: ✅ Prompts validated. INIT: {len(settings.PROMPT_INIT_TEMPLATE)} chars")
            
            # --- CONTEXT INITIALIZATION (THREADS) ---
            # removed local import to use self.openai_service
            
            # 1. Ensure Agent (Fallback)
            if not video.agent_id:
                log.warning(f"Video {video_id}: No Agent assigned. Attempting to assign Default Agent...")
                default_agent = await self.agent_service.get_default()
                if default_agent:
                    video.agent_id = default_agent.id
                    await self._save_video_merged(video.id, video)
                    log.info(f"Video {video_id}: ✅ Default Agent assigned: '{default_agent.name}' ({default_agent.id})")
                else:
                    log.error(f"Video {video_id}: ❌ No Default Agent found! Script generation might fail or use global defaults.")

            # 2. Ensure Thread
            if not video.openai_thread_id:
                log.info(f"Video {video_id}: Creating OpenAI thread...")
                try:
                    thread_id = await self.openai_service.create_thread()
                    video.openai_thread_id = thread_id
                    await self._save_video_merged(video.id, video)
                    log.info(f"Video {video_id}: ✅ Thread created successfully: {thread_id}")
                except Exception as e:
                    log.error(f"Video {video_id}: ❌ Failed to create OpenAI thread: {e}", exc_info=True)
                    video.status = VideoStatus.ERROR
                    video.error_message = f"Falha ao conectar com OpenAI: {str(e)}"
                    await self._save_video_merged(video.id, video)
                    return
            else:
                log.info(f"Video {video_id}: Resuming existing OpenAI Thread: {video.openai_thread_id}")

            # 2. Ensure Assistant
            log.info(f"Video {video_id}: Getting or creating OpenAI assistant...")
            # Use the 'system' prompt logic as Instructions
            system_instructions = (
                f"You are a professional video scriptwriter. Output always in {video.language}. "
                f"CRITICAL: Your responses MUST be ONLY valid JSON. No explanations, no conversational text, no markdown. "
                f"Just raw JSON starting with {{ and ending with }}. DO NOT write anything except the JSON object."
            )
            try:
                assistant_id = await self.openai_service.get_or_create_assistant("TudioScriptwriter", system_instructions)
                log.info(f"Video {video_id}: ✅ Assistant ready: {assistant_id}")
            except Exception as e:
                log.error(f"Video {video_id}: ❌ Failed to get/create assistant: {e}", exc_info=True)
                video.status = VideoStatus.ERROR
                video.error_message = f"Falha ao configurar assistente OpenAI: {str(e)}"
                await self._save_video_merged(video.id, video)
                return

            # --- STEP 0: Style & Characters ---
            log.info(f"Video {video_id}: Defining Characters & Style...")
            
            # Resolve Prompts - Start with settings (global baseline)
            prompt_init = settings.PROMPT_INIT_TEMPLATE
            prompt_chapters = settings.PROMPT_CHAPTERS_TEMPLATE
            prompt_subchapters = settings.PROMPT_SUBCHAPTERS_TEMPLATE
            prompt_scenes = settings.PROMPT_SCENES_TEMPLATE

            # Get base context
            context = await self._get_video_context(video)

            # --- LOCK: Serialize Script Generation ---
            # Ensure only one video generates script at a time to prevent context mixing (if using shared resources)
            # and to reduce load on OpenAI.
            
            # CHECK CANCELLATION BEFORE WAITING FOR LOCK
            video = await self.get(video_id) # Refresh status
            if not video:
                 log.info(f"Video {video_id}: Not found before acquiring lock. Stopping.")
                 return
            if video.status == VideoStatus.CANCELLED or video.deleted_at:
                 log.info(f"Video {video_id}: Detected CANCELLATION or DELETION before acquiring lock. Stopping.")
                 return

            async with self._script_lock(video_id):
                # CHECK CANCELLATION AFTER ACQUIRING LOCK
                video = await self.get(video_id) # Refresh status again
                if not video:
                     log.info(f"Video {video_id}: Not found inside lock. Stopping.")
                     return
                if video.status == VideoStatus.CANCELLED or video.deleted_at:
                     log.info(f"Video {video_id}: Detected CANCELLATION or DELETION inside lock. Stopping.")
                     return

                log.info(f"Video {video_id}: Acquired Script Generation Lock.")

                # CHECK STATUS: Did it get reset while we were waiting for the lock?
                check_video = await self.get(video_id)
                if not check_video or check_video.status != VideoStatus.PROCESSING or check_video.deleted_at:
                    log.info(f"Video {video_id}: Lifecycle check failed before Step 0. Stopping task.")
                    return

                # --- STEP 0: Execution ---
                    # --- STEP 0: Style & Characters ---
                # Also generates Metadata (Title, Description, Tags) - Sprint 62
                if video.visual_style and video.characters and video.title and video.description:
                     log.info(f"Video {video_id}: Step 0 (Style, Characters & Metadata) already done.")
                else:
                    log.info(f"Video {video_id}: Executing Step 0 (Metadata Backfill if needed)...")
                    
                    step0_prompt = self._format_prompt(prompt_init, **context)

                    content_0 = await self.openai_service.send_message_and_wait(
                        video.openai_thread_id, 
                        assistant_id, 
                        step0_prompt
                    )
                    data_0 = self._safe_json_parse(content_0, "Step 0 (Style & Characters)") or {}
                    
                    # Update Metadata (Prioritize filling empty fields)
                    if not video.title: video.title = data_0.get("title", "")
                    if not video.description: video.description = data_0.get("description", "")
                    if not video.tags: video.tags = data_0.get("tags", "")
                    if not video.music: video.music = data_0.get("music", "")
                    
                    # Update Style & Characters only if missing (Preserve consistency if already set)
                    if not video.visual_style:
                        video.visual_style = data_0.get("visual_style", "Cinematic")
                    
                    if not video.characters:
                        chars_data = data_0.get("characters", []) or []
                        # Transform OpenAI response format to CharacterModel format
                        video.characters = [
                            CharacterModel(
                                name=c.get("name", ""),
                                physical_description=c.get("physical_description") or c.get("description", ""),  # Prioritize physical_description
                                description=c.get("description") or c.get("physical_description", ""), # Fallback
                                voice=c.get("voice") or c.get("voice_type", "")  # Prioritize voice
                            )
                            for c in chars_data if c
                        ]
                        
                    await self._save_video_merged(video.id, video)
                    # Refresh context with new metadata
                    context = await self._get_video_context(video)

                # --- STEP 1: Script Generation Strategy ---
                if video.script_content:
                    log.info(f"Video {video_id}: 📜 Script Mode Detected. processing provided text...")
                    await self._generate_scenes_from_script_mode(video, assistant_id, context)
                else: 
                    # --- STEP 1: Chapters (Standard Mode) ---
                    log.info(f"Video {video_id}: Generating Chapters (Standard Mode)...")
                    
                    # EARLY FEEDBACK: Set progress to 1% so the UI shows the spinner immediately
                    video.progress = 1.0
                    await self._save_video_merged(video.id, video)

                    if video.chapters:
                         log.info(f"Video {video_id}: Step 1 already done.")
                    else:
                        # CHECK CANCELLATION before heavy OpenAI call
                        check_video = await self.get(video_id)
                        if not check_video or check_video.status == VideoStatus.CANCELLED or check_video.deleted_at:
                            log.info(f"Video {video_id}: Stopping due to CANCELLATION before Step 1.")
                            return

                        step1_prompt = self._format_prompt(prompt_chapters, **context)

                        content_1 = await self.openai_service.send_message_and_wait(
                            video.openai_thread_id, 
                            assistant_id, 
                            step1_prompt
                        )
                        chapters_data = self._safe_json_parse(content_1, "Step 1 (Chapters)")
                        if isinstance(chapters_data, dict):
                            chapters_data = chapters_data.get("chapters", [])
                        
                        video.chapters = []
                        for c_data in chapters_data:
                            video.chapters.append(ChapterModel(
                                id=c_data['order'],
                                order=c_data['order'],
                                title=c_data['title'],
                                estimated_duration_minutes=c_data.get('estimated_duration_minutes', 0),
                                description=c_data['description']
                            ))
                        # video.progress = 10.0 # DISABLED: Keep at 0 until chapters are actually processed
                        await self._save_video_merged(video.id, video)

                    # --- LOOP: Subchapters & Scenes ---
                    total_chapters = len(video.chapters)
                    
                    for i, chapter in enumerate(video.chapters):
                        # CHECK CANCELLATION
                        # Use a fresh variable to check status, DO NOT overwrite 'video' 
                        # because 'video' holds the in-memory chapters we just generated/modified.
                        check_video = await self.get(video_id)
                        if not check_video or check_video.status != VideoStatus.PROCESSING or check_video.deleted_at:
                            log.info(f"Video {video_id}: Lifecycle check failed during chapter loop. Stopping task.")
                            return

                        log.info(f"Processing Chapter {chapter.order}: {chapter.title}")
                        
                        if chapter.subchapters and len(chapter.subchapters) > 0:
                             log.info(f"   -> Chapter {chapter.order} already done.")
                             chapter.status = VideoStatus.COMPLETED
                             continue

                        chapter.status = VideoStatus.PROCESSING
                        await self._save_video_merged(video.id, video)

                        # CHECK CANCELLATION before each chapter's AI call
                        check_video = await self.get(video_id)
                        if not check_video or check_video.status == VideoStatus.CANCELLED or check_video.deleted_at:
                            log.info(f"Video {video_id}: Stopping due to CANCELLATION before Chapter {chapter.order}.")
                            return

                        try:
                            # Restore base context to ensure agent_prompts are available
                            chapter_context = context.copy()
                            chapter_context.update({
                                "chapter_order": chapter.order,
                                "chapter_title": chapter.title,
                                "chapter_description": chapter.description
                            })
                            
                            step2_prompt = self._format_prompt(prompt_subchapters, **chapter_context)
                            # Enforce JSON output
                            step2_prompt += "\n\nCRITICAL: Return ONLY the JSON object. No other text."
                            
                            # Use retry wrapper
                            content_2 = await self._call_openai_with_retry(
                                video.openai_thread_id,
                                assistant_id,
                                step2_prompt,
                                f"Step 2 (Chapter {chapter.order})",
                                video_id,
                                use_json_mode=True,
                                max_retries=1
                            )
                            subs_data = self._safe_json_parse(content_2, f"Step 2 (Chapter {chapter.order})")
                            if isinstance(subs_data, dict):
                                subs_data = subs_data.get("subchapters", [])
                            
                            chapter.subchapters = []
                            for sub_data in subs_data:
                                sub_obj = SubChapterModel(
                                    id=sub_data['order'],
                                    order=sub_data['order'],
                                    title=sub_data['title'],
                                    description=sub_data['description']
                                )
                                
                                # --- SCENES LOOP ---
                                # Context is already in the thread history.
                                # We use context.copy() to ensure agent prompt variables are available for substitution.
                                sub_context = context.copy()
                                sub_context.update({
                                    "subchapter_order": sub_obj.order,
                                    "subchapter_title": sub_obj.title,
                                    # "subchapter_description": sub_obj.description # Keep description available via context if needed, or rely on thread
                                })
                                
                                step3_prompt = self._format_prompt(prompt_scenes, **sub_context)
                                # Enforce JSON output
                                step3_prompt += "\n\nCRITICAL: Return ONLY the JSON object. No other text."
                                
                                # Use retry wrapper
                                content_3 = await self._call_openai_with_retry(
                                    video.openai_thread_id,
                                    assistant_id,
                                    step3_prompt,
                                    f"Step 3 (Subchapter {sub_obj.title})",
                                    video_id,
                                    use_json_mode=True,
                                    max_retries=1
                                )
                                scenes_raw = self._safe_json_parse(content_3, f"Step 3 (Subchapter {sub_obj.title})")
                                if isinstance(scenes_raw, dict):
                                    scenes_raw = scenes_raw.get("scenes", [])
                                
                                sub_obj.scenes = []
                                for idx, s in enumerate(scenes_raw):
                                    scene_id = s.get('id', idx + 1) # Use idx + 1 as fallback for id
                                    
                                    # Map auto_image_source to correct provider names for API
                                    provider_map = {
                                        'google': 'serpapi',
                                        'bing': 'bing',
                                        'unsplash': 'unsplash',
                                        'none': 'unsplash'  # Default fallback
                                    }
                                    scene_provider = provider_map.get(video.auto_image_source, 'unsplash')
                                    
                                    sub_obj.scenes.append(SceneModel(
                                        id=scene_id,
                                        order=s.get('order', idx + 1),
                                        duration_seconds=s.get('duration_seconds', 10), # Changed default from 0 to 10
                                        narration_content=s.get('narration_content', ''),
                                        visual_description=s.get('visual_description', ''), # Added new field
                                        image_prompt=s.get('image_prompt', ''),
                                        image_search=s.get('image_search', ''),
                                        image_search_provider=scene_provider, # Correctly mapped provider
                                        video_prompt=s.get('video_prompt', ''),
                                        video_search=s.get('video_search', ''),
                                        audio_prompt=s.get('audio_prompt', ''), # Added new field
                                        audio_search=s.get('audio_search', ''), 
                                        
                                        # New Narration Logic Mapping
                                        character=s.get('character', 'Narrator'), # Map JSON 'character' to model
                                        audio_effect_search=s.get('audio_effect_search', ''),
                                        audio_effect_seconds_start=s.get('audio_effect_seconds_start', 0),
                                        deleted=s.get('deleted', False)
                                    ))
                                chapter.subchapters.append(sub_obj)
                                
                                for scene in sub_obj.scenes:
                                    narration = scene.narration_content or ""
                                    scene.duration_seconds = self._calculate_duration(narration)

                            total_seconds = sum(
                                scene.duration_seconds 
                                for sub in chapter.subchapters 
                                for scene in sub.scenes
                            )
                            chapter.estimated_duration_minutes = round(total_seconds / 60, 2)
                            
                            video.progress = ((i + 1) / total_chapters * 50.0)
                        except Exception as e:
                            log.error(f"Error processing Chapter {chapter.order}: {str(e)}")
                            chapter.status = VideoStatus.ERROR
                            chapter.error_message = str(e)
                            await self._save_video_merged(video.id, video)
                            continue

                        chapter.status = VideoStatus.COMPLETED
                    await self._save_video_merged(video.id, video)
            
            log.info(f"Video {video_id}: Script Generation Layout Completed. Lock released.")

            # --- WRAP UP ---
            # ... (Existing logic for duration calcs, auto images, status) ... 
            # Need to ensure the rest of the method is kept in the replacement if checking EndLine.
            # I will check lines 459+ to see if I need to include them.
            # The tool call replaces up to line 514 (reprocess_chapter).
            # I must include the rest of process_video_background up to reprocess_chapter.
            
            # --- RECALCULATE VIDEO TOTAL DURATION ---
            grand_total_seconds = sum(
                scene.duration_seconds
                for chapter in video.chapters
                for sub in chapter.subchapters
                for scene in sub.scenes
            )
            video.total_duration_seconds = grand_total_seconds

            # --- SPRINT 64: AUTO-IMAGES ---
            video = await self.get(video_id) # Refresh state before next heavy steps
            if not video or video.deleted_at:
                log.info(f"Video {video_id}: Skipping Images/Audio/Render because video was deleted.")
                return

            if stop_after_scenes:
                log.info(f"Video {video_id}: 'stop_after_scenes' requested. Halting processing before Image Generation.")
                video.status = VideoStatus.COMPLETED
                video.progress = 100.0 # Or keep it at 75%? Let's say Completed as 'Script is done'
                await self._save_video_merged(video.id, video)
                return

            if hasattr(video, 'auto_image_source') and video.auto_image_source and video.auto_image_source != "none":
                try:
                    await self._auto_populate_images(video)
                except Exception as e:
                    # CRITICAL: If image generation fails (e.g. API limit), HALT the process.
                    # Do not proceed to Audio or Render.
                    log.error(f"Critical Image Generation Failure for Video {video_id}: {e}")
                    video.status = VideoStatus.ERROR
                    video.error_message = f"Falha na Geração de Imagens: {str(e)}"
                    await self._save_video_merged(video.id, video)
                    return False
            
            # --- SPRINT 65: AUTO-AUDIO (TTS HD) ---
            # Now respects manual/auto choice
            if getattr(video, 'auto_generate_narration', True):
                await self.audio_service.generate_narration_for_video(video)
            else:
                log.info(f"Video {video_id}: Auto-narration disabled. Waiting for manual trigger.")

            # --- SPRINT 66: FINAL RENDERING ---
            # NOW DISABLED: Manual trigger required (Step 6)
            # await self._perform_multi_format_render(video)

            # Mark as COMPLETED to indicate the automated phase is done
            video.status = VideoStatus.COMPLETED
            video.progress = 100.0
            await self._save_video_merged(video.id, video)
            log.info(f"Video {video_id}: Automated processing finished. Ready for manual Steps 4, 5, 6.")

        except Exception as e:
            log.error(f"Error processing video {video_id}: {str(e)}", exc_info=True)
            video.status = VideoStatus.ERROR
            video.error_message = str(e)
            await self._save_video_merged(video.id, video)

    async def reprocess_script(self, video_id: int) -> bool:
        """
        Deep Reset:
        1. Wipes all Chapters, Subchapters, Scenes.
        2. Resets Status to PENDING.
        3. Restarts processing with stop_after_scenes=True (Script Only).
        """
        video = await self.get(video_id)
        if not video:
            return False
            
        log.info(f"Video {video_id}: FULL SCRIPT RESET requested.")
        
        # 1. Wipe Data
        video.chapters = []
        video.script_content = ""
        video.visual_style = ""
        video.characters = []
        video.title = ""
        video.description = ""
        video.tags = ""
        video.music = ""
        video.music_id = None
        
        video.status = VideoStatus.PENDING
        video.progress = 0.0
        video.error_message = None
        video.rendering_progress = 0.0
        video.total_duration_seconds = 0.0
        
        # Clear output fields
        video.outputs = {}
        video.captioned_outputs = {}
        video.caption_status = "none"
        
        # Keep thread to maintain "Persona" context
        
        await self._save_video_merged(video.id, video)
        
        # 2. Trigger Background Task (Script Only)
        # The ROUTER must handle the background task adding.
        return True
    async def reprocess_chapter(self, video_id: int, chapter_id: int, stop_after_scenes: bool = True):
        video = await self.get(video_id)
        if not video:
            return False
            
        # Find chapter
        chapter = next((c for c in video.chapters if c.id == chapter_id), None)
        if not chapter:
            return False
            
        # Clear existing content
        chapter.subchapters = []
        chapter.status = VideoStatus.PENDING 
        chapter.error_message = None
        await self._save_video_merged(video.id, video)
        
        # Trigger background task
        asyncio.create_task(self.process_video_background(video_id, stop_after_scenes=stop_after_scenes))
        return True

    async def update_scene_video(self, video_id: int, chapter_id: int, sub_id: int, scene_idx: int, video_path: str) -> bool:
        """
        Update a specific scene's video URL after background download.
        """
        video = await self.get(video_id)
        if not video:
            log.warning(f"Video {video_id} not found for association")
            return False
        
        # Traverse to find scene
        # IDs passed are 'order' in this robust context
        found = False
        for chapter in video.chapters:
            if chapter.order == chapter_id:
                for sub in chapter.subchapters:
                    if sub.order == sub_id:
                        for scene in sub.scenes:
                            if scene.order == scene_idx:
                                scene.video_url = video_path
                                found = True
                                break
                        if found: break
                if found: break
        
        if found:
            await self._save_video_merged(video.id, video)
            log.info(f"Updated scene video URL for video {video_id}")
            return True
        else:
            log.warning(f"Scene {chapter_id}/{sub_id}/{scene_idx} not found in video {video_id}")
            return False

    async def reprocess_images(self, video_id: int, provider: str = "unsplash") -> bool:
        """
        Wipes all images from scenes and regenerates them using the specified provider.
        """
        video = await self.get(video_id)
        if not video:
            return False

        # Determine Orientation
        orientation = "landscape"
        if "9:16" in video.aspect_ratios:
            orientation = "portrait"

        log.info(f"Reprocessing images for Video {video.id} (Provider: {provider}, Orientation: {orientation})")
        
        # Reset progress
        video.status = VideoStatus.PROCESSING
        video.auto_image_source = provider
        video.progress = 0
        await self._save_video_merged(video.id, video)

        async def _run_image_gen():
            try:
                processed_count = 0
                total_scenes = sum(len(sub.scenes) for ch in video.chapters for sub in ch.subchapters)
                
                for chapter in video.chapters:
                    for sub in chapter.subchapters:
                        for scene in sub.scenes:
                            # CHECK CANCELLATION
                            loop_video = self.video_repository.get(video.id)
                            if loop_video.status == VideoStatus.CANCELLED:
                                 log.info(f"Video {loop_video.id}: Image processing cancelled.")
                                 return

                            processed_count += 1
                            
                            # Update Progress
                            if total_scenes > 0:
                                video.progress = round((processed_count / total_scenes) * 100, 1)
                                await self._save_video_merged(video.id, video)

                            # 1. Image Search
                            query = scene.image_search or scene.image_prompt or scene.visual_description or scene.narration_content or "scene"
                            if not query: continue

                            results = []
                            try:
                                if provider == "unsplash":
                                    results = await self.unsplash_service.search_images(query, per_page=10, orientation=orientation)
                                else:
                                    results = await self.serpapi_service.search(provider, query, per_page=10, orientation=orientation)
                            except Exception as e:
                                log.error(f"Search failed for scene {scene.id}: {e}")
                                continue

                            if not results:
                                continue

                            # 2. Pick first valid
                            for candidate in results:
                                image_url = candidate.get("url")
                                if not image_url: continue
                                
                                try:
                                    composite_scene_id = f"{chapter.order}-{sub.order}-{scene.order}"
                                    rel_path = await self.image_storage_service.download_image(image_url, video.id, composite_scene_id)
                                    if not rel_path: continue

                                    scene.original_image_url = rel_path
                                    scene.image_search_provider = provider
                                    break # Success
                                except Exception as e:
                                    log.error(f"Failed to process image {image_url}: {e}")
                                    continue
                
                video.status = VideoStatus.COMPLETED
                await self._save_video_merged(video.id, video)
                log.info(f"Video {video_id}: Image reprocessing completed.")

            except Exception as e:
                log.error(f"Error reprocessing images for {video_id}: {e}")
                video.status = VideoStatus.ERROR
                video.error_message = str(e)
                await self._save_video_merged(video.id, video)

        asyncio.create_task(_run_image_gen())
        return True

    async def reprocess_audio(self, video_id: int) -> bool:
        """
        Forces regeneration of narration for the video.
        """
        import os
        video = await self.get(video_id)
        if not video:
            return False

        log.info(f"Video {video_id}: Reprocessing audio...")
        
        # Clear existing audio states and files
        for chapter in video.chapters:
            for sub in chapter.subchapters:
                for scene in sub.scenes:
                    if scene.audio_url:
                        try:
                            # Attempt to delete physical file
                            rel_path = scene.audio_url
                            if rel_path.startswith("/api/"):
                                rel_path = rel_path[5:]
                            
                            # Strip cache-busting query string
                            if "?" in rel_path:
                                rel_path = rel_path.split("?")[0]
                                
                            if "storage/audios" in rel_path and os.path.exists(rel_path):
                                os.remove(rel_path)
                        except Exception as e:
                            log.warning(f"Could not delete old audio file for scene {scene.order}: {e}")
                    scene.audio_url = None
                    
        video.progress = 0.0
        video.rendering_progress = 0.0
        video.status = VideoStatus.PROCESSING
        await self._save_video_merged(video.id, video)

        async def _run_audio_gen():
            try:
                await self.audio_service.generate_narration_for_video(video, force=True, standalone=True)
                video.status = VideoStatus.COMPLETED
                video.progress = 100.0
                await self._save_video_merged(video.id, video)
                log.info(f"Video {video_id}: Audio reprocessing completed.")
            except Exception as e:
                log.error(f"Error reprocessing audio for {video_id}: {e}")
                video.status = VideoStatus.ERROR
                video.error_message = str(e)
                await self._save_video_merged(video.id, video)
        
        asyncio.create_task(_run_audio_gen())
        return True

    async def reprocess_scene_audio(self, video_id: int, chapter_id: int, subchapter_id: int, scene_idx: int) -> bool:
        """
        Forces regeneration of narration for a specific scene using hierarchical targeting.
        """
        video = await self.get(video_id)
        if not video:
            log.warning(f"Video {video_id} not found.")
            return False

        log.info(f"Video {video_id}: Reprocessing audio for Chapter {chapter_id} > Sub {subchapter_id} > Scene Index {scene_idx}...")
        
        # Traverse and find scene
        target = None
        target_chapter = None
        target_sub = None

        # Find Chapter
        for chapter in video.chapters:
            if chapter.id == chapter_id:
                target_chapter = chapter
                break
        
        if target_chapter:
            # Find Subchapter
            for sub in target_chapter.subchapters:
                if sub.id == subchapter_id:
                    target_sub = sub
                    break
        
        if target_sub:
            # Find Scene by Index
            if 0 <= scene_idx < len(target_sub.scenes):
                target_scene = target_sub.scenes[scene_idx]
                target = (target_chapter, target_sub, target_scene)
            else:
                 log.warning(f"Scene index {scene_idx} out of range for Subchapter {subchapter_id}")

        if not target:
            log.warning(f"Target scene not found: Ch {chapter_id} / Sub {subchapter_id} / Idx {scene_idx}")
            return False

        chapter, sub, scene = target
        
        # CRITICAL FIX: Synchronously clear audio_url so frontend polling sees it as "processing"
        # and doesn't immediately revert to the old audio URL.
        scene.audio_url = None
        
        # DOWNSTREAM INVALIDATION: Audio defines the timing base of the scene.
        # If audio changes, the generated clip and burned captions are now invalid.
        scene.generated_video_url = None
        scene.captioned_video_url = None
        
        # Save the updated state (cleared audio_url)
        await self._save_video_merged(video.id, video)

        async def _run_single_audio_gen():
            try:
                # VideoStatus.PROCESSING during generation for UI feedback
                video.status = VideoStatus.PROCESSING
                await self._save_video_merged(video.id, video)
                
                # Check for text content to log
                text_preview = scene.narration_content[:50] if scene.narration_content else "EMPTY"
                log.info(f"Async Gen Starting for Scene {scene.order}: '{text_preview}...'")

                success = await self.audio_service.generate_narration_for_single_scene(video, chapter, sub, scene, force=True)
                
                # Check if all assets are ready, but mostly just revert status
                video.status = VideoStatus.COMPLETED
                await self._save_video_merged(video.id, video)
                log.info(f"Video {video_id}: Scene {scene.order} audio reprocessing completed (Success: {success}).")
            except Exception as e:
                log.error(f"Error reprocessing scene audio for {video_id}: {e}")
                video.status = VideoStatus.ERROR
                video.error_message = str(e)
                await self._save_video_merged(video.id, video)
        
        asyncio.create_task(_run_single_audio_gen())
        return True

    async def resume_interrupted_tasks(self):
        """
        Called on startup to find videos stuck in PROCESSING or RENDERING
        and restart them.
        """
        log.info("Checking for interrupted video tasks...")
        stuck_videos = await self.video_repository.get_by_status([
            VideoStatus.PROCESSING, 
            VideoStatus.RENDERING
        ])
        
        if not stuck_videos:
            log.info("No interrupted tasks found.")
        log.warning(f"Found {len(stuck_videos)} interrupted videos. Resuming...")
        
        for video in stuck_videos:
            try:
                log.info(f"Resuming video {video.id} (Status: {video.status})")
                
                # Verify readiness before resuming
                if not self._is_ready_for_rendering(video):
                    log.warning(f"Video {video.id}: Not ready for rendering. Marking as ERROR to prevent loops.")
                    video.status = VideoStatus.ERROR
                    video.error_message = "Interrupted task found to be missing required assets on resume."
                    await self._save_video_merged(video.id, video)
                    continue

                # Force trigger to bypass "already processing" check
                await self.trigger_render(video.id, force=True)
            except Exception as e:
                log.error(f"Failed to resume video {video.id}: {e}")

    async def trigger_scene_render(self, video_id: int, force: bool = False) -> bool:
        """
        Triggers rendering of individual scenes (Step 4 of workflow).
        """
        video = await self.video_repository.get(video_id)
        log.info(f"VideoService: trigger_scene_render called for {video_id} with force={force} (Current Status: {video.status if video else 'None'})")
        if not video:
            return False
            
        if not force and video.status in [VideoStatus.PROCESSING, VideoStatus.RENDERING]:
             raise ValueError(f"Video is already in {video.status} state.")

        # Set status to RENDERING_SCENES 
        video.status = VideoStatus.RENDERING_SCENES
        video.rendering_progress = 1.0  # Visual feedback that something started
        
        # Clear existing scene video URLs to allow progress tracking from zero in UI
        # and ensure no stale captioned videos are used.
        for chapter in video.chapters:
            for sub in chapter.subchapters:
                for scene in sub.scenes:
                    scene.generated_video_url = None
                    scene.generated_video_urls = {}
                    scene.captioned_video_url = None
                    scene.captioned_video_urls = {}
        
        await self._save_video_merged(video.id, video)
        
        # Reset rendering progress for actual tracking
        video.rendering_progress = 0.0
        await self._save_video_merged(video.id, video)
        
        log.info(f"Video {video_id}: Triggering scenes-only render...")

        async def _run_scenes_render():
            try:
                success = await self._perform_scenes_only_render(video)
                if success:
                    log.info(f"Video {video_id}: Scenes-only render completed.")
                    # Return to standard PROCESSING or just leave it
                    video.status = VideoStatus.PROCESSING 
                    await self._save_video_merged(video.id, video)
                else:
                    log.error(f"Video {video_id}: Scenes-only render failed.")
                    video.status = VideoStatus.ERROR
                    await self._save_video_merged(video.id, video)
            except Exception as e:
                log.error(f"Error in scene render task for {video_id}: {e}")
                video.status = VideoStatus.ERROR
                video.error_message = str(e)
                await self._save_video_merged(video.id, video)

        asyncio.create_task(_run_scenes_render())
        return True

    async def render_single_scene(self, video_id: int, chapter_id: int, subchapter_id: int, scene_idx: int) -> bool:
        """
        Immediately renders a single scene clip.
        """
        video = await self.get(video_id)
        if not video:
            return False

        # Find Chapter
        target_chapter = next((c for c in video.chapters if c.id == chapter_id), None)
        if not target_chapter: return False

        # Find Subchapter
        target_sub = next((s for s in target_chapter.subchapters if s.id == subchapter_id), None)
        if not target_sub: return False

        # Find Scene
        if not (0 <= scene_idx < len(target_sub.scenes)): return False
        scene = target_sub.scenes[scene_idx]

        log.info(f"Video {video_id}: Explicitly rendering single scene {scene.order}...")

        # Clear existing URL to force update
        scene.generated_video_url = None
        
        # DOWNSTREAM INVALIDATION: The baseline visual has changed. 
        # Any previously burned captions are now out-of-sync/invalid against the new clip.
        scene.captioned_video_url = None
        
        await self._save_video_merged(video.id, video)

        async def _run_single_render(video_model, scene_obj, chapter_obj, sub_obj):
            try:
                video_id = video_model.id
                # We use the first aspect ratio for the preview
                ratios = getattr(video_model, 'aspect_ratios', ["16:9"])
                ratio = ratios[0] if ratios else "16:9"
                
                # Use scene order to avoid collisions with the global render counter
                scene_counter = 1000 + scene_obj.order
                
                # Render using RenderService
                from backend.services.render_service import render_service
                clip_path = await render_service._create_scene_clip(video_id, scene_obj, scene_counter, target_ratio=ratio)
                
                if clip_path and os.path.exists(clip_path):
                    # Store it permanently
                    format_name = "horizontal" if ratio == "16:9" else "vertical"
                    perm_filename = f"{chapter_obj.order}-{sub_obj.order}-{scene_obj.order}.mp4"
                    perm_path = os.path.join(render_service.storage_dir, "videos", str(video_id), "scenes", format_name, perm_filename)
                    os.makedirs(os.path.dirname(perm_path), exist_ok=True)
                    
                    import shutil
                    shutil.copy2(clip_path, perm_path)
                    
                    # Update model — re-fetch video to avoid overwriting concurrent changes
                    # CRITICAL FIX: Use hierarchical triple-key (chapter_id, subchapter_id, scene_idx)
                    # to locate the exact scene. Using sc.id alone is WRONG because scene.id is NOT
                    # globally unique — each subchapter has scenes with id=1,2,3.
                    fresh_video = await self.get(video_id)
                    if fresh_video:
                        scene_found = False
                        for c in fresh_video.chapters:
                            if int(c.id) == int(chapter_obj.id):
                                for s in c.subchapters:
                                    if int(s.id) == int(sub_obj.id):
                                        if 0 <= scene_idx < len(s.scenes):
                                            s.scenes[scene_idx].generated_video_url = f"videos/{video_id}/scenes/{format_name}/{perm_filename}"
                                            s.scenes[scene_idx].captioned_video_url = None  # Invalidate old captions
                                            scene_found = True
                                        break
                                break
                        if scene_found:
                            await self._save_video_merged(video_id, fresh_video)
                            log.info(f"Video {video_id}: Single scene {scene_obj.order} (Ch:{chapter_obj.id}/Sub:{sub_obj.id}/Idx:{scene_idx}) rendered successfully.")
                        else:
                            log.error(f"Video {video_id}: Scene not found via hierarchy: Ch:{chapter_obj.id}/Sub:{sub_obj.id}/Idx:{scene_idx}")
                    else:
                        log.error(f"Video {video_id}: Could not re-fetch video after scene render.")
                else:
                    log.error(f"Video {video_id}: Failed to generate clip for single scene {scene_obj.order}")
                    # Update scene status to error — also use hierarchical lookup
                    fresh_video = await self.get(video_id)
                    if fresh_video:
                        for c in fresh_video.chapters:
                            if c.id == chapter_obj.id:
                                for s in c.subchapters:
                                    if s.id == sub_obj.id:
                                        if 0 <= scene_idx < len(s.scenes):
                                            s.scenes[scene_idx].generated_video_url = None
                                        break
                                break
                        await self._save_video_merged(video_id, fresh_video)
            except Exception as e:
                log.error(f"Error in single scene render task: {e}")
                log.exception(e)

        asyncio.create_task(_run_single_render(video, scene, target_chapter, target_sub))
        return True

    async def _perform_scenes_only_render(self, video: VideoModel) -> bool:
        """
        Internal logic to render scenes only.
        """
        # Progress callback
        async def progress_cb(p):
            video.rendering_progress = p
            await self._save_video_merged(video.id, video)

        ratios = getattr(video, 'aspect_ratios', ["16:9"])
        if not ratios: ratios = ["16:9"]
        
        # We only render the first ratio for "Cenas" dashboard previews to save time
        # or we render all. Let's do all if the user has multiple requested.
        success_any = False
        for ratio in ratios:
            paths = await self.render_service.render_scenes_only(video, target_ratio=ratio, progress_callback=progress_cb)
            if paths:
                success_any = True
        
        return success_any

    async def trigger_render(self, video_id: int, force: bool = False) -> bool:
        """
        Manually triggers the final video rendering process.
        """
        video = await self.video_repository.get(video_id)
        if not video:
            return False
            
        # 1. Double Processing Check (Skip if forced)
        if not force and video.status in [VideoStatus.PROCESSING, VideoStatus.RENDERING]:
            log.warning(f"Video {video_id} is already processing/rendering (Status: {video.status}). Ignoring request.")
            raise ValueError(f"Video is already in {video.status} state.")

        # 2. Reset Status & Progress
        video.status = VideoStatus.RENDERING 
        video.rendering_progress = 1.0
        video.error_message = None
        await self._save_video_merged(video.id, video)
        
        log.info(f"Video {video_id}: Manually triggering render...")
        
        # Check assets first
        if not self._is_ready_for_rendering(video):
            # We can force IT or throw error. 
            # Let's try to proceed but log warning, as render_service might handle partials or fail gracefully.
            # actually render_service expects files. 
            log.warning(f"Video {video_id}: Assets might be missing, but user forced render.")

        video.rendering_progress = 0.0
        await self._save_video_merged(video.id, video)

        async def _run_render():
            try:
                success = await self._perform_multi_format_render(video)
                if success:
                    log.info(f"Video {video_id}: Manual render completed.")
                else:
                    log.error(f"Video {video_id}: Manual render failed.")
                    video.status = VideoStatus.ERROR
                    video.error_message = "Rendering failed (check logs for details)."
                    await self._save_video_merged(video.id, video)
            except Exception as e:
                log.error(f"Error in manual render task for {video_id}: {e}")
                video.status = VideoStatus.ERROR
                video.error_message = str(e)
                await self._save_video_merged(video.id, video)

        asyncio.create_task(_run_render())
        return True

    async def _perform_multi_format_render(self, video: VideoModel) -> bool:
        import asyncio
        """
        Unified logic to render all requested aspect ratios, update model, and save.
        Returns True if at least one format was successfully rendered.
        """
        video_id = video.id
        
        if not self._is_ready_for_rendering(video):
            log.warning(f"Video {video_id}: Missing assets. Render delayed/aborted.")
            return False

        try:
            # 1. Recalculate duration
            grand_total_seconds = sum(
                scene.duration_seconds
                for chapter in video.chapters
                for sub in chapter.subchapters
                for scene in sub.scenes
            )
            video.total_duration_seconds = grand_total_seconds

            # 2. Identify ratios
            ratios = getattr(video, 'aspect_ratios', ["16:9"])
            if not ratios:
                ratios = ["16:9"]
            
            # Reset to avoid stale data from previous/manual runs
            # We want current outputs to only match the current request
            video.video_url = None
            video.captioned_outputs = {}
            # Keep done status if it was already captioned (avoids 0% timeline regression)
            if video.caption_status != "done":
                video.caption_status = "pending"
            processed_outputs = {}
            
            # 3. Initialize progress for all formats to ensure accurate average from start
            for ratio in ratios:
                await update_video_progress(
                    video, 
                    task_id=ratio, 
                    progress=0.0, 
                    repository=self.video_repository, 
                    expected_tasks=ratios
                )

            # 4. Render each format IN PARALLEL
            async def render_format_task(r):
                try:
                    log.info(f"Video {video_id}: Rendering format {r} (Started)")
                    
                    async def progress_cb(p):
                        # Use the new centralized progress helper
                        await update_video_progress(video, task_id=r, progress=p, repository=self.video_repository, expected_tasks=ratios)
                        
                        # PERSIST PROGRESS via merged save to avoid clobbering final states
                        # Using background=True to avoid delaying render pipeline too much
                        await self._save_video_merged(video_id, video)

                        # CHECK CANCELLATION or COMPLETION inside render loop (via progress callback)
                        check_v = await self.video_repository.get(video_id)
                        if check_v and check_v.status in [VideoStatus.CANCELLED, VideoStatus.COMPLETED]:
                            if check_v.status == VideoStatus.COMPLETED:
                                log.info(f"Video {video_id}: Already COMPLETED. Stopping redundant render format {r}.")
                            raise Exception("RENDER_CANCELLED")
                        
                    final_url = await self.render_service.render_video(video, target_ratio=r, progress_callback=progress_cb)
                    return r, final_url
                except Exception as e:
                    log.error(f"Rendering task error for {r}: {e}")
                    return r, None

            tasks = [render_format_task(ratio) for ratio in ratios]
            results = await asyncio.gather(*tasks)
            
            for ratio, output_url in results:
                if output_url:
                    # REMOVED: Unstable timestamp injection that triggers re-downloads during polling.
                    # Frontend handles cache-busting for images; videos should stay stable.
                    processed_outputs[ratio] = output_url
                    # Update primary video_url: Priority to 16:9 or the first one rendered
                    if ratio == "16:9" or not video.video_url:
                        video.video_url = output_url
                else:
                    log.error(f"Video {video_id}: Rendering failed for format {ratio}")

            # 4. Save results
            video.outputs = processed_outputs
            
            if processed_outputs:
                video.status = VideoStatus.COMPLETED
                video.progress = 100.0
                video.rendering_progress = 100.0
                await self._save_video_merged(video.id, video)
                return True
            else:
                video.status = VideoStatus.ERROR
                video.error_message = "Falha ao renderizar formatos de vídeo."
                await self._save_video_merged(video.id, video)
                return False

        except Exception as e:
            log.error(f"Critical error in _perform_multi_format_render for {video_id}: {e}")
            video.status = VideoStatus.ERROR
            video.error_message = str(e)
            await self._save_video_merged(video.id, video)
            return False
        
    async def _get_batch_fallback_search_terms(self, video: VideoModel, original_query: str, context: str = "", failed_terms: list[str] = None) -> list[str]:
        """
        Asks LLM for a BATCH of better search terms when the original one fails.
        Uses the video's OpenAI Thread for context continuity.
        Returns a list of strings.
        """
        from backend.services.openai_service import openai_service
        from backend.services.agent_service import agent_service
        from backend.core.configs import settings
        import json
        
        # 0. Ensure Thread
        if not video.openai_thread_id:
            try:
                # Assuming openai_service can create threads
                video.openai_thread_id = await self.openai_service.create_thread()
                await self._save_video_merged(video.id, video)
            except Exception as e:
                log.error(f"Failed to create thread for video {video.id}: {e}")
                return []
        
        # Mypy check
        if not video.openai_thread_id:
             return []


        failed_terms_str = ", ".join(failed_terms) if failed_terms else "None"
        
        # 1. Fetch Agent Prompt
        prompt_template = settings.PROMPT_IMAGE_SEARCH_TEMPLATE
        
        target_agent = None
        if video.agent_id:
            target_agent = agent_service.get(video.agent_id)
        
        if not target_agent:
            agents = agent_service.list_all()
            target_agent = next((a for a in agents if a.is_default), None)
            
        if target_agent and target_agent.prompt_image_search:
            prompt_template = target_agent.prompt_image_search

        # Safe formatting
        try:
            prompt = prompt_template.replace("{original_query}", original_query)\
                                    .replace("{context}", context)\
                                    .replace("{failed_terms}", failed_terms_str)
        except Exception as e:
            log.error(f"Error formatting prompt: {e}. Using fallback.")
            prompt = f"No images found for: '{original_query}'. Context: {context}. Failed: {failed_terms_str}. Return JSON with 'terms' list."
        
        try:
            # We don't have a specific assistant for this, so we might need to pass an assistant ID or just use chat based?
            # The self.openai_service.send_message_and_wait_json requires an assistant_id.
            # If we don't have one, we might need to rely on a "Visual Researcher" assistant or standard chat if the service supported it.
            # Checking openai_service, it requires assistant_id.
            # Let's assume we can get/create a "Visual Researcher" assistant.
            
            assistant_id = await self.openai_service.get_or_create_assistant(
                name="Visual Researcher",
                instructions="You are an expert visual researcher helps finding stock photos. You always output JSON."
            )
            
            response_json_str = await self.openai_service.send_message_and_wait_json(
                thread_id=video.openai_thread_id,
                assistant_id=assistant_id,
                content=prompt
            )
            
            if not response_json_str:
                return []
                
            data = json.loads(response_json_str)
            terms = data.get("terms", [])
            
            # Clean terms
            cleaned_terms = [t.strip().replace('"', '').replace("'", "") for t in terms if isinstance(t, str)]
            return cleaned_terms
            
        except Exception as e:
            log.warning(f"Batch fallback term generation failed: {e}")
            return []

    async def _auto_populate_images(self, video: VideoModel, progress_start: float = 50.0, progress_end: float = 75.0):
        """
        Iterates over all scenes, searches for images, downloads, and crops them.
        """
        log.info(f"Auto-populating images for Video {video.id} using {video.auto_image_source}")
        
        provider = "unsplash"
        if video.auto_image_source == "google":
            provider = "serpapi"
        elif video.auto_image_source == "bing":
            provider = "bing"
        
        
        used_image_urls = set()
        
        # Calculate total scenes for progress tracking
        total_scenes = 0
        for chapter in video.chapters:
            for subchapter in chapter.subchapters:
                total_scenes += len(subchapter.scenes)
        
        processed_scenes = 0
        
        # Initial Progress Set
        video.progress = progress_start
        await self._save_video_merged(video.id, video)

        for chapter in video.chapters:
            for subchapter in chapter.subchapters:
                for scene in subchapter.scenes:
                    processed_scenes += 1
                    
                    # Update Progress: Map 0..1 (completion) to start..end
                    if total_scenes > 0:
                        fraction_complete = processed_scenes / total_scenes
                        range_span = progress_end - progress_start
                        new_progress = progress_start + (fraction_complete * range_span)
                        video.progress = min(progress_end, round(new_progress, 1))
                        
                        # Save progress
                        await self._save_video_merged(video.id, video)
                    
                    try:
                        # 1. Determine Initial Query
                        # PRIORITIZE image_search as requested by user
                        initial_query = scene.image_search or scene.image_prompt or scene.visual_description or scene.narration_content or "scene"
                        
                        current_search_term = initial_query
                        scene_success = False
                        failed_search_terms = []
                        
                        # Queue for batch processing
                        term_queue: list[str] = [] 
                        
                        # RETRY LOOP (Start + Fallbacks) - Limited to prevent infinite loops
                        retry_count = 0
                        max_loop_retries = 5
                        while retry_count < max_loop_retries:
                            retry_count += 1
                            if not current_search_term:
                                break
                                
                            # 2. Search
                            # Determine Orientation
                            orientation = "landscape"
                            if "9:16" in video.aspect_ratios:
                                orientation = "portrait"

                            results = []
                            if provider == "unsplash":
                                results = await self.unsplash_service.search_images(current_search_term, per_page=50, orientation=orientation) 
                            else:
                                results = await self.serpapi_service.search(provider, current_search_term, per_page=50, orientation=orientation)
                            
                            if results:
                                # 3. Try candidates
                                for candidate in results:
                                    try:
                                        image_url = candidate.get("url")
                                        if not image_url: continue
                                        if image_url in used_image_urls: continue
                                            
                                        # 4. Download & Crop
                                        if not video.id:
                                             log.warning(f"Video ID missing for scene {scene.id}")
                                             continue

                                        composite_scene_id = f"{chapter.order}-{subchapter.order}-{scene.order}"
                                        rel_path = await self.image_storage_service.download_image(image_url, video.id, composite_scene_id)
                                        
                                        # 6. Assign (Auto-crop is now handled during render phase)
                                        scene.original_image_url = rel_path
                                        used_image_urls.add(image_url)
                                        await self._save_video_merged(video.id, video)
                                        
                                        scene_success = True
                                        break 
                                    except Exception:
                                        continue
                            
                            if scene_success:
                                break 
                            
                            # Record failure
                            failed_search_terms.append(current_search_term)
                            
                            # QUEUE MANAGEMENT
                            # If queue is empty, fetch a new batch
                            if not term_queue:
                                log.warning(f"No valid images for '{current_search_term}' (Attempt {retry_count}). Requesting BATCH fallback...")
                                context = scene.visual_description or scene.narration_content or ""
                                new_batch = await self._get_batch_fallback_search_terms(
                                    video,
                                    current_search_term, # pass the one that just failed as context trigger
                                    context, 
                                    failed_terms=failed_search_terms
                                )
                                
                                # Filter duplicates
                                for t in new_batch:
                                    t_clean = t.lower().strip()
                                    if t_clean and t_clean not in [ft.lower().strip() for ft in failed_search_terms]:
                                        term_queue.append(t)
                            
                            # Pop from queue
                            if term_queue:
                                next_term = term_queue.pop(0)
                                log.info(f"Using next batch term: '{next_term}' (Queue left: {len(term_queue)})")
                                current_search_term = next_term
                                scene.image_search = next_term
                            else:
                                log.warning("Batch fallback returned no new valid terms. Stopping to prevent infinite loop.")
                                break

                        if not scene_success:
                            log.warning(f"All image attempts failed for scene {scene.id}")

                    except Exception as e:
                        log.error(f"Error processing scene {scene.id}: {e}")
                        if "Package has expired" in str(e) or "SerpApi Error" in str(e):
                             raise e 
                        continue
        
        return True

    async def _generate_scenes_from_script_mode(self, video: VideoModel, assistant_id: str, context: dict):
        """
        Handles the logic for "Script to Video" mode.
        1. Parses `video.script_content` into scenes (by line).
        2. Calls OpenAI "Director" to organize scenes into Chapters/Subchapters 
           and generate visual descriptions/search terms.
        """
        # 1. Parse Script to raw list for prompt
        raw_lines = video.script_content.split('\n')
        scenes_for_ai = []
        id_counter = 1
        
        for line in raw_lines:
            line = line.strip()
            if not line: continue
            
            scenes_for_ai.append({
                "id": id_counter,
                "narration_content": line
            })
            id_counter += 1
            
        if not scenes_for_ai:
             log.warning(f"Video {video.id}: Script content was empty or only whitespace.")
             return

        # 2. Call Director AI (Organize Hierarchy & Enrich Visuals)
        log.info(f"Video {video.id}: Calling Director AI to structure and enrich {len(scenes_for_ai)} scenes...")
        
        # Update context with the scenes JSON so AI knows what to organize
        script_context = context.copy()
        script_context["scenes_list"] = json.dumps(scenes_for_ai, ensure_ascii=False)
        
        director_prompt = self._format_prompt(settings.PROMPT_SCRIPT_TO_VIDEO_TEMPLATE, **script_context)
        director_prompt += "\n\nCRITICAL: Return ONLY the JSON object. No other text."

        try:
            content = await self._call_openai_with_retry(
                video.openai_thread_id,
                assistant_id,
                director_prompt,
                "Director Mode Organization",
                video.id,
                use_json_mode=True
            )
            
            structured_data = self._safe_json_parse(content, "Director Mode Structure")
            
            # 3. Build Video Hierarchy from AI response
            chapters_data = structured_data.get("chapters", [])
            if not chapters_data:
                log.error(f"Video {video.id}: Director AI returned no chapters. Falling back to simple mode.")
                raise ValueError("No chapters found in Director AI response")

            video.chapters = []
            
            provider_map = {
                'google': 'serpapi',
                'bing': 'bing',
                'unsplash': 'unsplash',
                'none': 'unsplash'
            }
            scene_provider = provider_map.get(video.auto_image_source, 'unsplash')
            
            # Default character from video.characters if available, else "Narrator"
            default_character = video.characters[0].name if video.characters else "Narrator"
            
            received_scene_ids = set()

            for ch_data in chapters_data:
                chapter = ChapterModel(
                    id=ch_data.get("id", 1),
                    order=ch_data.get("order", 1),
                    title=ch_data.get("title", "Capítulo"),
                    description=ch_data.get("description", ""),
                    estimated_duration_minutes=0.0
                )
                
                for sub_data in ch_data.get("subchapters", []):
                    subchapter = SubChapterModel(
                        id=sub_data.get("id", 1),
                        order=sub_data.get("order", 1),
                        title=sub_data.get("title", "Subcapítulo"),
                        description=sub_data.get("description", "")
                    )
                    
                    for s_data in sub_data.get("scenes", []):
                        orig_id = s_data.get("id")
                        received_scene_ids.add(orig_id)
                        
                        # Find original narration
                        original_text = next((s["narration_content"] for s in scenes_for_ai if s["id"] == orig_id), s_data.get("narration_content", ""))
                        
                        duration = self._calculate_duration(original_text)
                        
                        scene = SceneModel(
                            id=s_data.get("id", 1),
                            order=s_data.get("order", 1),
                            duration_seconds=duration,
                            narration_content=original_text,
                            visual_description=s_data.get("visual_description", ""),
                            image_prompt=s_data.get("image_prompt", ""),
                            video_prompt=s_data.get("video_prompt", ""),
                            image_search=s_data.get("image_search", ""),
                            video_search=s_data.get("video_search", ""),
                            audio_search=s_data.get("audio_search", ""),
                            image_search_provider=scene_provider,
                            character=default_character
                        )
                        subchapter.scenes.append(scene)
                        
                    chapter.subchapters.append(subchapter)
                
                video.chapters.append(chapter)

            # INTEGRITY CHECK: Did we lose any scenes?
            expected_scene_ids = set(s["id"] for s in scenes_for_ai)
            missing_ids = expected_scene_ids - received_scene_ids
            if missing_ids:
                log.error(f"Video {video.id}: INTEGRITY FAILURE! Director AI skipped {len(missing_ids)} scenes: {missing_ids}")
                for mid in missing_ids:
                    missing_text = next((s["narration_content"] for s in scenes_for_ai if s["id"] == mid), "Unknown")
                    log.error(f"Missing Scene {mid}: '{missing_text}'")
                # For now we log as error, but we could implement a recovery subchapter "Resto do Roteiro"
            
            video.status = VideoStatus.PROCESSING
            await self._save_video_merged(video.id, video)
            log.info(f"Video {video.id}: Director AI hierarchy and enrichment completed (Scenes: {len(received_scene_ids)}/{len(expected_scene_ids)}).")

            
        except Exception as e:
            log.error(f"Video {video.id}: Director AI failed or returned invalid structure: {e}")
            video.status = VideoStatus.ERROR
            video.error_message = f"Falha ao processar roteiro com IA: {str(e)}"
            await self._save_video_merged(video.id, video)

video_service = VideoService()

