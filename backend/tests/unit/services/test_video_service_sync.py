
import pytest
from unittest.mock import MagicMock
from backend.models.video import VideoModel, VideoStatus, ChapterModel, SubChapterModel, SceneModel, CharacterModel
from backend.services.video_service import VideoService

@pytest.fixture
def video_service():
    repo = MagicMock()
    # Simple init without complex deps
    service = VideoService(repo=repo)
    return service

def test_save_video_merged_preserves_references(video_service):
    # Setup
    video_id = 999
    
    # Original Background Object (in memory)
    # Note: ChapterModel status now defaults to PENDING
    chapter_1 = ChapterModel(id=1, order=1, title="C1", description="D1", estimated_duration_minutes=1.0)
    bg_video = VideoModel(
        id=video_id,
        prompt="Topic",
        target_duration_minutes=2,
        status=VideoStatus.PROCESSING,
        chapters=[chapter_1]
    )
    
    # Mocking Repository (simulating DB state)
    latest_chapter = ChapterModel(id=1, order=1, title="C1", description="D1", estimated_duration_minutes=1.0)
    latest_video = VideoModel(
        id=video_id,
        prompt="Topic",
        target_duration_minutes=2,
        status=VideoStatus.PROCESSING,
        chapters=[latest_chapter]
    )
    
    video_service.video_repository.get.return_value = latest_video
    video_service.video_repository.save.side_effect = lambda x: x # Returns what was saved
    
    # 1. TEST: Reference Survival
    # Change status on bg_video's chapter
    chapter_1.status = VideoStatus.PROCESSING
    
    # Execute merge
    video_service._save_video_merged(video_id, bg_video)
    
    # ASSERT: The chapter object in bg_video is STILL the original chapter_1
    assert bg_video.chapters[0] is chapter_1
    assert chapter_1.status == VideoStatus.PROCESSING
    
    # 2. TEST: Deep Persistence (Subchapters)
    sub_1 = SubChapterModel(id=1, order=1, title="S1", description="D1")
    chapter_1.subchapters = [sub_1]
    
    # Mock next DB state (it will have the subchapters now because they were saved in previous call)
    latest_video.chapters[0].subchapters = [SubChapterModel(id=1, order=1, title="S1", description="D1")]
    
    # Execute next merge
    video_service._save_video_merged(video_id, bg_video)
    
    # ASSERT: References are still alive
    assert bg_video.chapters[0] is chapter_1
    assert chapter_1.subchapters[0] is sub_1
    
    # 3. TEST: User Edit Sync-Back & Protection
    # Simulate user changing the title in the database
    latest_video.chapters[0].title = "User Edited Title"
    latest_video.title = "User Video Title"
    
    # Execute merge
    video_service._save_video_merged(video_id, bg_video)
    
    # ASSERT: The edit from DB flowed back into our persistent memory object
    assert chapter_1.title == "User Edited Title"
    assert bg_video.title == "User Video Title"

def test_save_video_merged_initial_population(video_service):
    # Setup
    video_id = 111
    
    # DB state is mostly empty (Brand new video or after full reprocess)
    latest_video = VideoModel(
        id=video_id,
        prompt="Topic",
        target_duration_minutes=2,
        status=VideoStatus.PROCESSING,
        title="",
        description="",
        characters=[]
    )
    
    # Background just finished Step 0
    bg_video = VideoModel(
        id=video_id,
        prompt="Topic",
        target_duration_minutes=2,
        status=VideoStatus.PROCESSING,
        title="AI Generated Title",
        description="AI Generated Desc",
        characters=[CharacterModel(name="AI Char", physical_description="White hair", voice="alloy")]
    )
    
    video_service.video_repository.get.return_value = latest_video
    video_service.video_repository.save.side_effect = lambda x: x
    
    # Execute merge
    saved = video_service._save_video_merged(video_id, bg_video)
    
    # ASSERT: Empty DB fields were populated by BG results
    assert saved.title == "AI Generated Title"
    assert saved.description == "AI Generated Desc"
    assert len(saved.characters) == 1
    assert saved.characters[0].name == "AI Char"
    
    # Now verify PROTECTION: Subsequent merge with different BG data should NOT overwrite
    bg_video.title = "Stale BG Title"
    video_service._save_video_merged(video_id, bg_video)
    assert saved.title == "AI Generated Title" # Protected!
