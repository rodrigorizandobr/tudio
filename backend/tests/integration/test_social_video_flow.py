import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.services.video_service import VideoService
from backend.models.video import VideoModel, VideoStatus, ChapterModel, SubChapterModel, SceneModel
from backend.schemas.video import VideoCreate
from backend.repositories.video_repository import video_repository

@pytest.mark.asyncio
async def test_create_vertical_video_flow():
    """
    Verifies that a video created with aspect_ratios=['9:16']
    triggers the correct orientation in image search.
    """
    # 1. Setup Data
    video_in = VideoCreate(
        prompt="Test Vertical Video",
        target_duration_minutes=1,
        aspect_ratios=["9:16"], # Plural correctly used here
        auto_image_source="unsplash",
        script_content="Chapter 1\nScene 1: A tall building."
    )
    
    # 2. Mock Services
    mock_unsplash = AsyncMock()
    mock_openai = AsyncMock()
    mock_storage = MagicMock()
    mock_repo = MagicMock()
    
    # Setup Unsplash Mock
    mock_unsplash.search_images.return_value = [{"url": "http://img.com/1.jpg"}]
    
    # Setup OpenAI Mock (Script Mode)
    mock_openai.create_thread.return_value = "thread_123"
    mock_openai.get_or_create_assistant.return_value = "asst_123"
    
    # Setup Storage Mock
    mock_storage.download_image = AsyncMock(return_value="storage/img.jpg")
    mock_storage.calculate_center_crop_coords.return_value = (0,0,100,100)
    mock_storage.crop_image.return_value = "storage/cropped.jpg"

    # 3. Execution (Using DI)
    service = VideoService(
        repo=mock_repo,
        unsplash_svc=mock_unsplash,
        openai_svc=mock_openai,
        storage_svc=mock_storage
    )
    
    # We mock repo.save to return the same object
    mock_repo.save.side_effect = lambda x: x
    
    video = service.create(video_in)
    video.id = 123 # Ensure ID is set for path generation logic
    
    # Explicitly call the method that uses aspect_ratio
    # We need to inject the video with chapters first (simulating the script gen step)
    scene = SceneModel(id=1, order=1, narration_content="Tall bldg", image_search="sky", duration_seconds=5, image_prompt="sky", video_prompt="sky")
    video.chapters = [
        ChapterModel(
            id=1, order=1, title="C1", estimated_duration_minutes=1, description="D",
            subchapters=[
                SubChapterModel(id=1, order=1, title="S1", description="D", scenes=[scene])
            ]
        )
    ]
    
    await service._auto_populate_images(video)
    
    # 4. Verification
    
    # Verify Unsplash was called with orientation="portrait"
    mock_unsplash.search_images.assert_called()
    call_args = mock_unsplash.search_images.call_args
    assert call_args.kwargs.get("orientation") == "portrait", \
        f"Expected orientation='portrait', got {call_args.kwargs.get('orientation')}"
        
    # Verify that original_image_url was assigned
    assert scene.original_image_url == "storage/img.jpg", "Scene original_image_url was not assigned"

    # Note: crop_image is now handled during final render phase in RenderService, 
    # not during auto_populate_images anymore.
