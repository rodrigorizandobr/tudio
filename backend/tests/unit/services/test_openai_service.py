
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, mock_open
from backend.services.openai_service import OpenAIService

class TestOpenAIService:
    @pytest.fixture
    def mock_client(self):
        with patch("backend.services.openai_service.AsyncOpenAI") as mock:
            client_instance = AsyncMock()
            mock.return_value = client_instance
            yield client_instance

    @pytest.fixture
    def service(self, mock_client):
        # We need to re-instantiate or patch the existing global service's client
        # Because the global one is instantiated at import time
        service = OpenAIService()
        service.client = mock_client
        return service

    @pytest.mark.asyncio
    async def test_create_thread_success(self, service, mock_client):
        mock_thread = MagicMock()
        mock_thread.id = "thread_123"
        mock_client.beta.threads.create.return_value = mock_thread

        thread_id = await service.create_thread()
        assert thread_id == "thread_123"
        mock_client.beta.threads.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_thread_failure(self, service, mock_client):
        mock_client.beta.threads.create.side_effect = Exception("API Error")
        
        with pytest.raises(Exception):
            await service.create_thread()

    @pytest.mark.asyncio
    async def test_reset_thread(self, service, mock_client):
        # Setup create_thread mock
        mock_thread = MagicMock()
        mock_thread.id = "new_thread_456"
        mock_client.beta.threads.create.return_value = mock_thread

        new_id = await service.reset_thread("old_thread")
        assert new_id == "new_thread_456"

    @pytest.mark.asyncio
    async def test_get_or_create_assistant_found(self, service, mock_client):
        # Update logic: list returns assistant with same name
        mock_assistant = MagicMock()
        mock_assistant.name = "Test Assistant"
        mock_assistant.id = "asst_123"
        mock_assistant.model = "gpt-4o"
        mock_assistant.instructions = "Old instructions"

        mock_client.beta.assistants.list.return_value.data = [mock_assistant]

        # Call with different instructions to trigger update
        assistant_id = await service.get_or_create_assistant("Test Assistant", "New instructions")
        
        assert assistant_id == "asst_123"
        # Verify update called
        mock_client.beta.assistants.update.assert_called_once_with(
            "asst_123", instructions="New instructions", model=service.model_name
        )

    @pytest.mark.asyncio
    async def test_get_or_create_assistant_not_found(self, service, mock_client):
        mock_client.beta.assistants.list.return_value.data = []
        
        mock_created = MagicMock()
        mock_created.id = "asst_new"
        mock_client.beta.assistants.create.return_value = mock_created

        assistant_id = await service.get_or_create_assistant("New Assistant", "Instructions")
        
        assert assistant_id == "asst_new"
        mock_client.beta.assistants.create.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_send_message_and_wait_success(self, service, mock_client):
        # 1. Message Create
        mock_client.beta.threads.messages.create.return_value = AsyncMock()
        
        # 2. Run Create
        mock_run = MagicMock()
        mock_run.id = "run_123"
        mock_client.beta.threads.runs.create.return_value = mock_run
        
        # 3. Poll Loop (Retrieve)
        # Sequence: in_progress -> completed
        mock_status_progress = MagicMock()
        mock_status_progress.status = "in_progress"
        
        mock_status_completed = MagicMock()
        mock_status_completed.status = "completed"
        
        mock_client.beta.threads.runs.retrieve.side_effect = [
            mock_status_progress,
            mock_status_completed
        ]
        
        # 4. Get Messages
        mock_msg = MagicMock()
        mock_msg.role = "assistant"
        mock_msg.content = [MagicMock(type='text', text=MagicMock(value="Hello World"))]
        
        mock_client.beta.threads.messages.list.return_value.data = [mock_msg]

        # Execute
        # We define a short sleep to speed up test
        service._rate_limit_delay = 0 
        with patch("asyncio.sleep", AsyncMock()): 
            response = await service.send_message_and_wait("thread_1", "asst_1", "Hello")
        
        assert response == "Hello World"

    @pytest.mark.asyncio
    async def test_send_message_and_wait_json_success(self, service, mock_client):
        # Setup similar to normal send_message but verify response_format
        mock_client.beta.threads.messages.create.return_value = AsyncMock()
        mock_run = MagicMock()
        mock_run.id = "run_json_1"
        mock_client.beta.threads.runs.create.return_value = mock_run
        
        mock_client.beta.threads.runs.retrieve.return_value.status = "completed"
        
        mock_msg = MagicMock()
        mock_msg.role = "assistant"
        mock_msg.content = [MagicMock(type='text', text=MagicMock(value='{"key": "value"}'))]
        mock_client.beta.threads.messages.list.return_value.data = [mock_msg]
        
        service._rate_limit_delay = 0
        with patch("asyncio.sleep", AsyncMock()):
            resp = await service.send_message_and_wait_json("t1", "a1", "proc")
            
        assert resp == '{"key": "value"}'
        # Verify JSON format enforcement
        mock_client.beta.threads.runs.create.assert_called_with(
            thread_id="t1",
            assistant_id="a1",
            response_format={"type": "json_object"}
        )

    @pytest.mark.asyncio
    async def test_generate_tts_success(self, service, mock_client):
        # Mock chat completion with audio
        mock_completion = MagicMock()
        mock_audio = MagicMock()
        # "SGVsbG8=" is "Hello" in base64
        mock_audio.data = "SGVsbG8=" 
        mock_completion.choices = [MagicMock(message=MagicMock(audio=mock_audio))]
        
        mock_client.chat.completions.create.return_value = mock_completion
        
        with patch("builtins.open", mock_open()) as m_open:
            path = await service.generate_tts("Hello", "/tmp/out.mp3", "alloy")
            
            assert path == "/tmp/out.mp3"
            m_open.assert_called_with("/tmp/out.mp3", "wb")
            handle = m_open()
            handle.write.assert_called_once_with(b"Hello")

