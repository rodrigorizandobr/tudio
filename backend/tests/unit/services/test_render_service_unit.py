import pytest
from unittest.mock import MagicMock, patch, ANY, AsyncMock
from backend.services.render_service import RenderService
from backend.models.video import VideoModel, ChapterModel, SubChapterModel, SceneModel, VideoStatus

class TestRenderServiceUnit:

    @pytest.fixture
    def service(self):
        return RenderService()

    @pytest.fixture
    def mock_scene(self):
        return SceneModel(
            id=1, 
            order=1, 
            narration_content="Test Narration",
            image_prompt="Test Image Prompt",
            video_prompt="Test Video Prompt",
            audio_url="storage/audios/1.mp3", 
            original_image_url="storage/images/1.jpg",
            duration=5.0
        )

    def test_get_binary_path_custom(self, service):
        """Test finding binary in custom paths"""
        with patch("shutil.which", return_value=None), \
             patch("os.path.exists", side_effect=lambda x: x == "/opt/homebrew/bin/ffmpeg"):
            path = service._get_binary_path("ffmpeg")
            assert path == "/opt/homebrew/bin/ffmpeg"

    def test_resolve_path(self, service):
        assert service._resolve_path("https://api.com/api/storage/file.mp4") == "storage/file.mp4"
        assert service._resolve_path("temp/file.mp4") == "storage/temp/file.mp4"

    @patch("backend.services.render_service.subprocess.check_output")
    def test_get_media_duration(self, mock_subprocess, service):
        mock_subprocess.return_value = b"10.5\n"
        dur = service._get_media_duration("test.mp4")
        assert dur == 10.5
        mock_subprocess.assert_called()

    @patch("backend.services.render_service.AudioFileClip")
    @patch("backend.services.render_service.ImageClip")
    @patch("backend.services.render_service.CompositeVideoClip")
    @patch("backend.services.render_service.afx")
    @patch("backend.services.render_service.video_repository")
    def test_create_scene_clip_sync_image(self, mock_repo, mock_afx, mock_composite, mock_image_clip, mock_audio_clip, service, mock_scene):
        """Test creating a clip from a static image with zoom effect"""
        # Setup Mocks
        mock_audio_instance = mock_audio_clip.return_value
        mock_audio_instance.duration = 5.0
        # Mock subclip return (chaining)
        mock_audio_instance.subclip.return_value = mock_audio_instance 
        
        # Audio FX mocks
        mock_afx.audio_fadeout.return_value = mock_audio_instance
        mock_afx.audio_fadein.return_value = mock_audio_instance
        
        # Image Mock
        mock_img_instance = mock_image_clip.return_value
        mock_img_instance.size = (1920, 1080)
        mock_img_instance.set_duration.return_value = mock_img_instance
        mock_img_instance.resize.return_value = mock_img_instance
        
        # Composite Mock
        mock_final_clip = mock_composite.return_value
        mock_final_clip.set_audio.return_value = mock_final_clip
        
        # Mock OS/Shutil/Padding
        with patch("os.path.exists", return_value=True), \
             patch("os.makedirs"), \
             patch.object(service, "_add_padding_to_audio_ffmpeg", return_value="storage/temp/padded.wav"):
             
            output = service._create_scene_clip_sync(1, mock_scene, 1)
            
            assert "scene_1_horizontal_0001.mp4" in output
            mock_composite.assert_called()
            mock_final_clip.write_videofile.assert_called()

    @patch("backend.services.render_service.AudioFileClip")
    @patch("backend.services.render_service.VideoFileClip")
    @patch("backend.services.render_service.afx")
    @patch("backend.services.render_service.video_repository")
    def test_create_scene_clip_sync_video(self, mock_repo, mock_afx, mock_video_clip, mock_audio_clip, service, mock_scene):
        """Test creating a clip from a video source"""
        mock_scene.video_url = "storage/videos/input.mp4"
        
        # Audio Mock
        mock_audio_instance = mock_audio_clip.return_value
        mock_audio_instance.duration = 5.0
        mock_audio_instance.subclip.return_value = mock_audio_instance
        
        mock_afx.audio_fadeout.return_value = mock_audio_instance
        mock_afx.audio_fadein.return_value = mock_audio_instance

        # Video Mock
        mock_vid_instance = mock_video_clip.return_value
        mock_vid_instance.size = (1280, 720) # Input size
        mock_vid_instance.duration = 10.0
        
        # Resizing mocks
        mock_vid_instance.resize.return_value = mock_vid_instance
        mock_vid_instance.crop.return_value = mock_vid_instance
        mock_vid_instance.subclip.return_value = mock_vid_instance
        mock_vid_instance.set_audio.return_value = mock_vid_instance
        
        with patch("os.path.exists", return_value=True), \
             patch("os.makedirs"), \
             patch.object(service, "_add_padding_to_audio_ffmpeg", return_value="storage/temp/padded.wav"):
             
             output = service._create_scene_clip_sync(1, mock_scene, 2)
             
             assert "scene_1_horizontal_0002.mp4" in output
             mock_vid_instance.write_videofile.assert_called()

    def test_crop_to_aspect_ratio(self, service):
        mock_clip = MagicMock()
        mock_clip.size = (200, 200) # 1:1
        
        # Target 2:1 (wide) -> Should crop height
        # New height = width / ratio = 200 / 2 = 100
        service._crop_to_aspect_ratio(mock_clip, 200, 100)
        mock_clip.crop.assert_called_with(x1=0, y1=50, width=200, height=100)

    @patch("backend.services.render_service.RenderService._create_scene_clip", new_callable=AsyncMock)
    @patch("backend.services.render_service.RenderService._concatenate_clips")
    @patch("backend.services.render_service.video_repository")
    @pytest.mark.asyncio
    async def test_render_video_lifecycle(self, mock_repo, mock_concat, mock_create_clip, service):
        """Test the orchestration logic without running moviepy"""
        video = VideoModel(
            id=1,
            prompt="Test Video",
            target_duration_minutes=2,
            status=VideoStatus.PENDING,
            chapters=[
                ChapterModel(
                    id=1, order=1, title="C1", 
                    estimated_duration_minutes=1.0, description="Chap Desc",
                    subchapters=[
                        SubChapterModel(
                            id=1, order=1, title="S1", description="Sub Desc",
                            scenes=[
                                SceneModel(
                                    id=1, order=1, 
                                    narration_content="N1", image_prompt="P1", video_prompt="V1",
                                    audio_url="a.mp3", original_image_url="i.jpg"
                                )
                            ]
                        )
                    ]
                )
            ]
        )
        
        mock_repo.get.return_value = video
        mock_create_clip.return_value = "storage/temp/clip.mp4"
        mock_concat.return_value = True
        
        with patch("backend.services.render_service.RenderService._get_media_duration", return_value=5.0), \
             patch("shutil.copy2"), \
             patch("os.makedirs"), \
             patch("os.remove"), \
             patch("glob.glob", return_value=[]):
             
             res = await service.render_video(video)
             
             assert res == f"videos/1/final_horizontal.mp4"
             # Status check is redundant here as RenderService refreshes local object
             mock_create_clip.assert_called()
