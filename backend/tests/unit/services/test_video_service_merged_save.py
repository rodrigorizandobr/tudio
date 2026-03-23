
import pytest
from unittest.mock import MagicMock
from datetime import datetime
from backend.models.video import VideoModel, VideoStatus, ChapterModel, SubChapterModel

@pytest.fixture
def video_service():
    from backend.services.video_service import VideoService
    repo = MagicMock()
    service = VideoService(repo=repo)
    return service

def test_save_video_merged_syncs_chapter_status(video_service):
    # Setup
    video_id = 123
    
    # DB state (latest)
    latest_video = VideoModel(
        id=video_id,
        prompt="Topic",
        target_duration_minutes=2,
        status=VideoStatus.PROCESSING,
        chapters=[
            ChapterModel(
                id=1, order=1, title="Chapter 1", 
                estimated_duration_minutes=1.0, description="D 1",
                status=VideoStatus.PENDING
            )
        ]
    )
    
    # Background state (bg_video)
    bg_video = VideoModel(
        id=video_id,
        prompt="Topic",
        target_duration_minutes=2,
        status=VideoStatus.PROCESSING,
        chapters=[
            ChapterModel(
                id=1, order=1, title="Chapter 1", 
                estimated_duration_minutes=1.0, description="D 1",
                status=VideoStatus.COMPLETED
            )
        ]
    )
    
    video_service.video_repository.get.return_value = latest_video
    video_service.video_repository.save.side_effect = lambda x: x
    
    # Execute
    video_service._save_video_merged(video_id, bg_video)
    
    # Assert
    saved_video = video_service.video_repository.save.call_args[0][0]
    assert saved_video.chapters[0].status == VideoStatus.COMPLETED
    assert bg_video.chapters[0].status == VideoStatus.COMPLETED

def test_save_video_merged_preserves_subchapters(video_service):
    # Setup
    video_id = 123
    
    # DB state (latest) - chapters exist but no subchapters yet
    latest_video = VideoModel(
        id=video_id,
        prompt="Topic",
        target_duration_minutes=2,
        status=VideoStatus.PROCESSING,
        chapters=[
            ChapterModel(
                id=1, order=1, title="Chapter 1", 
                estimated_duration_minutes=1.0, description="D 1",
                status=VideoStatus.PROCESSING, subchapters=[]
            )
        ]
    )
    
    # Background state (bg_video) - has subchapters newly generated
    bg_video = VideoModel(
        id=video_id,
        prompt="Topic",
        target_duration_minutes=2,
        status=VideoStatus.PROCESSING,
        chapters=[
            ChapterModel(
                id=1, order=1, title="Chapter 1", 
                estimated_duration_minutes=1.0, description="D 1",
                status=VideoStatus.COMPLETED,
                subchapters=[
                    SubChapterModel(id=1, order=1, title="Sub 1", description="Desc")
                ]
            )
        ]
    )
    
    video_service.video_repository.get.return_value = latest_video
    video_service.video_repository.save.side_effect = lambda x: x
    
    # Execute
    video_service._save_video_merged(video_id, bg_video)
    
    # Assert
    saved_video = video_service.video_repository.save.call_args[0][0]
    assert len(saved_video.chapters[0].subchapters) == 1
    assert saved_video.chapters[0].subchapters[0].title == "Sub 1"
    assert len(bg_video.chapters[0].subchapters) == 1

def test_save_video_merged_sync_back_references(video_service):
    # Setup
    video_id = 123
    latest_video = VideoModel(
        id=video_id, prompt="Topic", target_duration_minutes=2, status=VideoStatus.PROCESSING,
        chapters=[ChapterModel(id=1, order=1, title="Chapter 1", estimated_duration_minutes=1.0, description="D 1")]
    )
    bg_video = VideoModel(
        id=video_id, prompt="Topic", target_duration_minutes=2, status=VideoStatus.PROCESSING,
        chapters=[ChapterModel(id=1, order=1, title="Chapter 1", estimated_duration_minutes=1.0, description="D 1")]
    )
    
    # Simulate DB save returning a DIFFERENT object
    saved_video = VideoModel(
        id=video_id, prompt="Topic", target_duration_minutes=2, status=VideoStatus.PROCESSING,
        chapters=[ChapterModel(id=1, order=1, title="Chapter 1", estimated_duration_minutes=1.0, description="D 1", status=VideoStatus.COMPLETED)]
    )
    
    video_service.video_repository.get.return_value = latest_video
    video_service.video_repository.save.return_value = saved_video
    
    # Execute
    video_service._save_video_merged(video_id, bg_video)
    
    # Assert
    assert bg_video.chapters[0].status == VideoStatus.COMPLETED
    assert bg_video.chapters == saved_video.chapters
