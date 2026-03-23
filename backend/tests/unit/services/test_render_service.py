import pytest
from unittest.mock import MagicMock, patch, AsyncMock, call
import os
from backend.services.render_service import RenderService
from backend.models.video import VideoModel, ChapterModel, SubChapterModel, SceneModel, VideoStatus

@pytest.fixture
def render_service():
    return RenderService()

@pytest.fixture
def mock_video():
    scene = SceneModel(
        id=1, order=1, narrative="Scene 1", narration_content="Content",
        image_prompt="Prompt", video_prompt="Video Prompt",
        audio_url="audios/1.mp3", original_image_url="images/1.jpg"
    )
    sub = SubChapterModel(id=1, order=1, title="Sub 1", description="Sub Desc", scenes=[scene])
    chapter = ChapterModel(id=1, order=1, title="Chapter 1", estimated_duration_minutes=1.0, description="Chap Desc", subchapters=[sub])
    video = VideoModel(id=100, prompt="Test", status="pending", target_duration_minutes=1, chapters=[chapter])
    return video

def test_get_binary_path_found(render_service):
    with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
        path = render_service._get_binary_path("ffmpeg")
        assert path == "/usr/bin/ffmpeg"

def test_get_binary_path_fallback(render_service):
    with patch("shutil.which", return_value=None), \
         patch("os.path.exists", return_value=False):
        path = render_service._get_binary_path("ffmpeg")
        assert path == "ffmpeg"

def test_resolve_path(render_service):
    assert render_service._resolve_path("images/test.jpg") == "storage/images/test.jpg"
    assert render_service._resolve_path("/api/storage/videos/1.mp4") == "storage/videos/1.mp4"
    assert render_service._resolve_path("storage/already/path.ext") == "storage/already/path.ext"
    assert render_service._resolve_path("") == ""

@pytest.mark.asyncio
async def test_render_video_success(render_service, mock_video):
    # Mock Repos/Dependencies
    with patch("backend.services.render_service.video_repository") as mock_repo, \
         patch.object(render_service, "_create_scene_clip", new_callable=AsyncMock) as mock_create_clip, \
         patch.object(render_service, "_concatenate_clips", return_value=True) as mock_concat, \
         patch.object(render_service, "_get_media_duration", return_value=5.0), \
         patch("backend.services.render_service.music_repository") as mock_music_repo:
        
        # Setup Mocks
        mock_create_clip.return_value = "storage/temp/clip_1.mp4"
        mock_repo.get.return_value = mock_video # For refreshing inside
        
        # Execute
        result = await render_service.render_video(mock_video)
        
        # Verify
        assert result == f"videos/{mock_video.id}/final_horizontal.mp4"
        # Status update happens in VideoService, NOT RenderService! 
        # RenderService is a utility that marks internal status for its own tracking.
        mock_create_clip.assert_called()
        mock_concat.assert_called()

@pytest.mark.asyncio
async def test_render_video_validation_failure(render_service, mock_video):
    # Remove audio from scene to trigger validation error
    mock_video.chapters[0].subchapters[0].scenes[0].audio_url = None
    
    with patch("backend.services.render_service.video_repository") as mock_repo:
        result = await render_service.render_video(mock_video)
        
        assert result is None
        assert mock_video.status == VideoStatus.ERROR
        assert "incompleta" in mock_video.error_message



def test_concatenate_clips(render_service):
    clips = ["1.mp4", "2.mp4"]
    output = "final.mp4"
    
    with patch("backend.services.render_service.VideoFileClip") as MockVideoClip, \
         patch("backend.services.render_service.concatenate_videoclips") as mock_concat:
         
         mock_concat_instance = mock_concat.return_value
         
         # Execute
         success = render_service._concatenate_clips(clips, output)
         
         # Verify
         assert success is True
         mock_concat_instance.write_videofile.assert_called_with(
             output, fps=30, codec='libx264', audio_codec='aac', 
             preset='ultrafast', ffmpeg_params=['-pix_fmt', 'yuv420p'], threads=4
         )

def test_add_padding_to_audio_ffmpeg(render_service):
    with patch("subprocess.check_call") as mock_call, \
         patch("os.path.exists", return_value=True), \
         patch("os.remove") as mock_remove:
         
         result = render_service._add_padding_to_audio_ffmpeg("input.wav", 0.5, 100, 1)
         
         assert "padded_audio_100_1.wav" in result
         mock_call.assert_called()
