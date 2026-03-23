import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from backend.models.video import VideoModel, VideoStatus, ChapterModel
from backend.services.video_service import VideoService

@pytest.fixture
def video_service():
    repo = MagicMock()
    # Simple init without complex deps
    service = VideoService(repo=repo)
    return service

@pytest.mark.asyncio
async def test_process_video_background_stops_on_cancel(video_service):
    # Setup
    video_id = 123
    
    # Initial Video (Pending)
    video = VideoModel(
        id=video_id,
        prompt="Topic",
        target_duration_minutes=1,
        status=VideoStatus.PENDING,
        language="pt-BR"
    )
    
    video_service.video_repository.get.side_effect = [
        video, # Initial get
        video, # Lock check
        video, # Lock check 2
        video, # Lock check 3
        VideoModel(id=video_id, status=VideoStatus.CANCELLED, prompt="Topic", target_duration_minutes=1) # THE STOP SIGNAL
    ]
    
    # Mock OpenAI Service to avoid real calls
    video_service.openai_service = AsyncMock()
    video_service.openai_service.create_thread.return_value = "thread_123"
    video_service.openai_service.get_or_create_assistant.return_value = "asst_123"
    
    # Mock the save method
    video_service.video_repository.save.side_effect = lambda x: x
    
    # Mock settings to pass validation
    with patch("backend.services.video_service.settings") as mock_settings:
        mock_settings.PROMPT_INIT_TEMPLATE = "Init"
        mock_settings.PROMPT_CHAPTER_TEMPLATE = "Chapters"
        
        # Execute background task
        await video_service.process_video_background(video_id)
        
        # ASSERT: openai_service.send_message_and_wait should NOT be called for Chapters (Step 1)
        # because the cancellation was detected after Step 0.
        # Step 0 (Metadata/Init) might run depending on where we simulate the stop.
        # In our side_effect, the 5th get() (Step 1) returns CANCELLED.
        
        # Check calls
        # 1. create_thread 
        # 2. get_or_create_assistant
        # 3. send_message_and_wait (Step 0)
        # 4. (Check for Step 1 should return)
        
        # Verify it stopped before Step 1
        assert video_service.openai_service.send_message_and_wait.call_count <= 1
        
@pytest.mark.asyncio
async def test_cancel_processing_sets_status(video_service):
    video_id = 456
    video = VideoModel(id=video_id, status=VideoStatus.PROCESSING, prompt="Topic", target_duration_minutes=1)
    video_service.video_repository.get.return_value = video
    
    with patch.object(video_service, "_save_video_merged") as mock_save:
        success = video_service.cancel_processing(video_id)
        
        assert success is True
        assert video.status == VideoStatus.CANCELLED
        mock_save.assert_called_once()
