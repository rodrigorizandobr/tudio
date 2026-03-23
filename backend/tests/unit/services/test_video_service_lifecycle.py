
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from backend.models.video import VideoModel, VideoStatus, ChapterModel
from backend.services.video_service import VideoService

@pytest.fixture
def video_service():
    repo = MagicMock()
    # Mocking all services to avoid real I/O
    service = VideoService(
        repo=repo,
        render_svc=MagicMock(),
        audio_svc=MagicMock(),
        openai_svc=MagicMock(),
        unsplash_svc=MagicMock(),
        serpapi_svc=MagicMock(),
        storage_svc=MagicMock(),
        agent_svc=MagicMock()
    )
    return service

@pytest.mark.asyncio
async def test_process_video_background_exits_on_status_change(video_service):
    # Setup
    video_id = 123
    video = VideoModel(
        id=video_id,
        prompt="Topic",
        target_duration_minutes=2,
        status=VideoStatus.PROCESSING,
        openai_thread_id="thread_123",
        script_content=None # Ensure standard mode
    )
    
    reset_video = VideoModel(
        id=video_id, 
        prompt="Topic", 
        target_duration_minutes=2, 
        status=VideoStatus.PENDING # Reset detected!
    )

    # 1. self.get (initial at start)
    # 2. _save_video_merged.get (line 654)
    # 3. self.get (before lock at 733)
    # 4. self.get (after lock at 743)
    # 5. self.get (NEW check before Step 0 at 754) -> Here it should exit!
    video_service.video_repository.get.side_effect = [
        video, # 1
        video, # 2
        video, # 3
        video, # 4
        reset_video, # 5 (Reset Detected)
        reset_video, # safety
        reset_video  # safety
    ]
    
    # Mock OpenAI to not actually call
    video_service.openai_service.get_or_create_assistant = AsyncMock(return_value="asst_123")
    
    # Mock _get_video_context
    video_service._get_video_context = AsyncMock(return_value={})
    
    # Execute
    await video_service.process_video_background(video_id)
    
    # Assert
    # It should have called get 5 times and then stopped before Step 0's OpenAI call
    assert video_service.video_repository.get.call_count == 5
    
    # It should NOT have called Step 0 send_message_and_wait because it exited at the lifecycle check before Step 0
    assert video_service.openai_service.send_message_and_wait.call_count == 0

@pytest.mark.asyncio
async def test_process_video_background_sets_early_progress(video_service):
    # Setup
    video_id = 456
    video = VideoModel(
        id=video_id,
        prompt="Topic",
        target_duration_minutes=2,
        status=VideoStatus.PROCESSING,
        openai_thread_id="thread_456",
        script_content=None
    )
    
    # Mocking successful path to reach Step 1 start
    video_service.video_repository.get.return_value = video
    video_service.video_repository.save.side_effect = lambda x: x
    video_service.openai_service.get_or_create_assistant = AsyncMock(return_value="asst_456")
    video_service.openai_service.send_message_and_wait = AsyncMock(return_value='{"visual_style": "C", "characters": []}')
    video_service._get_video_context = AsyncMock(return_value={})
    
    # We want to check if progress was set to 1.0 at some point.
    # Since we can't easily check intermediate states with a simple lambda, 
    # let's check the calls to save.
    
    # Execute
    try:
        await video_service.process_video_background(video_id)
    except:
        pass # We only care about the early calls
        
    # Assert
    # Check if any save call had progress = 1.0
    progress_updates = [call.args[0].progress for call in video_service.video_repository.save.call_args_list]
    assert 1.0 in progress_updates
