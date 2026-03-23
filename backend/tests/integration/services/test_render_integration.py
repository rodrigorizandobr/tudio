
import pytest
import os
import shutil
from unittest.mock import MagicMock, AsyncMock, patch
from backend.services.render_service import RenderService
from backend.models.video import VideoModel, ChapterModel, SubChapterModel, SceneModel, VideoStatus

@pytest.fixture
def mock_render_video():
    # Helper to generate dummy files
    base_dir = "storage/test_render"
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)
    os.makedirs(base_dir, exist_ok=True)
    os.makedirs(f"{base_dir}/audio", exist_ok=True)
    os.makedirs(f"{base_dir}/image", exist_ok=True)
    os.makedirs(f"{base_dir}/videos", exist_ok=True) # Output dir
    
    # Needs real files for MoviePy to load (unless fully mocked).
    # Since MoviePy is strict on inputs, we mock the heavy lifting 
    # to test logic flow, or use ffmpeg to gen small assets.
    # Let's mock the heavy MoviePy clip creation to speed up tests,
    # relying on the PoC script which proved the rendering works.
    
    return base_dir

@pytest.mark.asyncio
async def test_render_flow_mocked(mock_render_video):
    # Verify the orchestration logic
    service = RenderService()
    service.storage_dir = mock_render_video
    service.output_dir = f"{mock_render_video}/videos"
    
    # Mock Data
    video = VideoModel(
        id=999,
        prompt="Test Render",
        target_duration_minutes=1,
        status="pending",
        chapters=[
            ChapterModel(
                id=1,
                title="C1",
                order=1,
                estimated_duration_minutes=1.0,
                description="Chapter 1 description",
                subchapters=[
                    SubChapterModel(
                            id=1,
                            title="S1",
                            order=1,
                        description="Subchapter 1 description",
                        scenes=[
                            SceneModel(
                                id=1,
                                order=1,
                                narrative="Scene 1",
                                narration_content="Scene 1 content",
                                image_prompt="A beautiful scene",
                                video_prompt="A beautiful video",
                                audio_url="audios/1.mp3",
                                original_image_url="images/1.jpg"
                            ),
                            SceneModel(
                                id=2,
                                order=2,
                                narrative="Scene 2",
                                narration_content="Scene 2 content",
                                image_prompt="A beautiful scene 2",
                                video_prompt="A beautiful video 2",
                                audio_url="audios/2.mp3",
                                video_url="videos/2.mp4"
                            )
                        ]
                    )
                ]
            )
        ]
    )
    
    # Mock _resolve_path
    service._resolve_path = MagicMock(side_effect=lambda x: f"{mock_render_video}/{x}")
    
    # Mock _get_media_duration
    service._get_media_duration = MagicMock(return_value=5.0)

    # Mock _create_scene_clip
    # Return dummy paths
    service._create_scene_clip = AsyncMock(side_effect=[
        f"{mock_render_video}/temp/scene_999_0001.mp4",
        f"{mock_render_video}/temp/scene_999_0002.mp4"
    ])
    
    # Mock _concatenate_clips
    service._concatenate_clips = MagicMock(return_value=True)
    
    # Create dummy temp paths needed for "exist" checks inside
    os.makedirs(f"{mock_render_video}/temp", exist_ok=True)
    
    # Execute
    with patch("backend.services.render_service.video_repository") as mock_repo:
        output = await service.render_video(video)
        
        # Verify
        assert output == "videos/999/final_horizontal.mp4"
        
        # Verify calls
        assert service._create_scene_clip.call_count == 2
        service._concatenate_clips.assert_called_once()
