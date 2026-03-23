import pytest
from backend.services.video_service import VideoService
from backend.models.video import VideoModel, VideoStatus
from backend.repositories.video_repository import video_repository
from unittest.mock import patch

@pytest.fixture
def video_service():
    return VideoService()

def test_cancel_processing_during_main_processing(video_service):
    # Setup: Video in PROCESSING state
    video = VideoModel(
        prompt="Test Cancel",
        target_duration_minutes=1,
        status=VideoStatus.PROCESSING,
        caption_status="processing"
    )
    saved = video_repository.save(video)
    
    # Execute
    success = video_service.cancel_processing(saved.id)
    
    # Verify
    assert success is True
    updated = video_repository.get(saved.id)
    assert updated.status == VideoStatus.CANCELLED
    assert updated.caption_status == "error"

def test_cancel_captions_on_completed_video(video_service):
    # Setup: Video in COMPLETED state but captioning is active
    video = VideoModel(
        prompt="Test Cancel Captions Only",
        target_duration_minutes=1,
        status=VideoStatus.COMPLETED,
        caption_status="processing"
    )
    saved = video_repository.save(video)
    
    # Execute
    success = video_service.cancel_processing(saved.id)
    
    # Verify
    assert success is True
    updated = video_repository.get(saved.id)
    # Status should remain COMPLETED
    assert updated.status == VideoStatus.COMPLETED
    # Caption status should be reset to error
    assert updated.caption_status == "error"
