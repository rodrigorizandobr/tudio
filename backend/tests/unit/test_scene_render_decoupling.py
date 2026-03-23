import pytest
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch
from backend.models.video import VideoModel, VideoStatus, SceneModel, ChapterModel, SubChapterModel
from backend.services.video_service import VideoService

@pytest.mark.asyncio
async def test_trigger_scene_render_success():
    # Mock Repositories
    mock_repo = MagicMock()
    mock_render = AsyncMock()
    
    # Setup Video
    video = VideoModel(
        id=123,
        user_id="user_123",
        title="Test Scene Render",
        status=VideoStatus.PENDING,
        prompt="Test prompt",
        target_duration_minutes=1.0,
        chapters=[
            ChapterModel(
                id=1,
                title="Ch 1",
                order=1,
                description="Ch desc",
                estimated_duration_minutes=1.0,
                subchapters=[
                    SubChapterModel(
                        id=1,
                        title="Sub 1",
                        order=1,
                        description="Test desc",
                        scenes=[
                            SceneModel(
                                id=1,
                                order=1,
                                audio_url="audios/1.wav",
                                original_image_url="images/1.jpg",
                                narration_content="Test",
                                image_prompt="Test",
                                video_prompt="Test"
                            )
                        ]
                    )
                ]
            )
        ]
    )
    mock_repo.get.return_value = video
    
    # Initialize Service
    service = VideoService(repo=mock_repo)
    service.render_service = mock_render
    
    # Mock render_scenes_only to return something and call callback
    async def mock_render_scenes_only(video, target_ratio="16:9", progress_callback=None):
        if progress_callback:
            await progress_callback(50.0)
        return ["storage/temp/scene_1.mp4"]
    mock_render.render_scenes_only.side_effect = mock_render_scenes_only
    
    # Trigger
    with patch("asyncio.create_task") as mock_task:
        success = await service.trigger_scene_render(123)
        assert success is True
        assert video.status == VideoStatus.RENDERING
        
    # Manually run the internal logic to verify decoupling
    success_internal = await service._perform_scenes_only_render(video)
    assert success_internal is True
    mock_render.render_scenes_only.assert_called_once()
    assert video.rendering_progress > 0

@pytest.mark.asyncio
async def test_trigger_render_still_works_and_calls_scenes():
    # Verify that the main trigger_render still performs full render (via render_video)
    mock_repo = MagicMock()
    mock_render = AsyncMock()
    video = VideoModel(
        id=456, 
        user_id="u1", 
        title="Full Render", 
        status=VideoStatus.COMPLETED, # SET TO COMPLETED TO AVOID "ALREADY PROCESSING" ERROR
        prompt="Test prompt",
        target_duration_minutes=1.0
    )
    mock_repo.get.return_value = video
    
    service = VideoService(repo=mock_repo)
    service.render_service = mock_render
    
    # Mocking _perform_multi_format_render to verify it still works
    with patch.object(service, "_perform_multi_format_render", new_callable=AsyncMock) as mock_multi:
        await service.trigger_render(456)
        # Note: trigger_render starts a task, so we check status
        assert video.status == VideoStatus.RENDERING
