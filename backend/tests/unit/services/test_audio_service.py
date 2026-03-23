
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, ANY
from backend.services.audio_service import AudioService
from backend.models.video import VideoModel, ChapterModel, SubChapterModel, SceneModel, CharacterModel

class TestAudioService:
    @pytest.fixture
    def service(self):
        return AudioService()

    @pytest.fixture
    def mock_video(self):
        # Create a complex video structure
        video = VideoModel(
            id=1, 
            duration=5.0,
            prompt="Test Video",
            target_duration_minutes=2,
            status="pending"
        )
        video.characters = [
            CharacterModel(name="Hero", voice="onyx", physical_description="Desc 1"),
            CharacterModel(name="Villain", voice="invalid_voice", physical_description="Desc 2")
        ]
        
        scene1 = SceneModel(id=1, order=1, narration_content="Scene 1", character="Hero", image_prompt="p1", video_prompt="v1")
        scene2 = SceneModel(id=2, order=2, narration_content="Scene 2", character="Villain", image_prompt="p2", video_prompt="v2")
        scene3 = SceneModel(id=3, order=3, narration_content="Scene 3", character=None, image_prompt="p3", video_prompt="v3")
        
        sub1 = SubChapterModel(id=1, order=1, title="S1", description="D1", scenes=[scene1, scene2])
        sub2 = SubChapterModel(id=2, order=2, title="S2", description="D2", scenes=[scene3])
        
        chap1 = ChapterModel(id=1, order=1, title="C1", estimated_duration_minutes=2.5, description="Chap 1", subchapters=[sub1])
        chap2 = ChapterModel(id=2, order=2, title="C2", estimated_duration_minutes=2.5, description="Chap 2", subchapters=[sub2])
        
        video.chapters = [chap1, chap2]
        return video

    @patch("backend.services.audio_service.openai_service.generate_tts", new_callable=AsyncMock)
    @patch("backend.services.audio_service.video_repository.save")
    @patch("backend.services.audio_service.video_repository.get")
    @patch("os.path.exists", return_value=False)
    @patch("os.makedirs")
    @pytest.mark.asyncio
    async def test_generate_narration_for_video_success(self, mock_mkdirs, mock_exists, mock_get, mock_save, mock_tts, service, mock_video):
        """Test full video iteration and progress updates"""
        mock_get.return_value = mock_video
        
        res = await service.generate_narration_for_video(mock_video, force=True)
        
        assert res is True
        # 3 scenes total
        assert mock_tts.call_count == 3
        
        # Verify Progress Updates
        # Total 3 scenes. 
        # 1/3 processed -> progress += ~6.66 -> 75 + 6.66 = 81.6
        # 2/3 processed -> progress += ~13.33 -> 75 + 13.33 = 88.3
        # 3/3 processed -> progress += 20 -> 95.0
        
        # Check final save call
        assert mock_save.call_count >= 3
        assert mock_video.progress == 95.0

    @patch("backend.services.audio_service.openai_service.generate_tts", new_callable=AsyncMock)
    @patch("backend.services.audio_service.video_repository.save")
    @patch("os.path.exists", return_value=False)
    @pytest.mark.asyncio
    async def test_voice_selection_logic(self, mock_exists, mock_save, mock_tts, service, mock_video):
        """Test voice selection based on character mapping"""
        
        chapter = mock_video.chapters[0]
        sub = chapter.subchapters[0]
        
        # Scene 1: Hero -> Onyx (Valid)
        scene1 = sub.scenes[0]
        await service.generate_narration_for_single_scene(mock_video, chapter, sub, scene1)
        mock_tts.assert_called_with(text=ANY, output_path=ANY, voice="onyx", instructions=ANY)
        
        # Scene 2: Villain -> invalid_voice -> Fallback to 'nova'
        scene2 = sub.scenes[1]
        await service.generate_narration_for_single_scene(mock_video, chapter, sub, scene2)
        mock_tts.assert_called_with(text=ANY, output_path=ANY, voice="nova", instructions=ANY)
        
        # Scene 3: No Character -> Default 'nova'
        chapter2 = mock_video.chapters[1]
        sub2 = chapter2.subchapters[0]
        scene3 = sub2.scenes[0]
        await service.generate_narration_for_single_scene(mock_video, chapter2, sub2, scene3)
        mock_tts.assert_called_with(text=ANY, output_path=ANY, voice="nova", instructions=ANY)

    @patch("backend.services.audio_service.openai_service.generate_tts", new_callable=AsyncMock)
    @patch("backend.services.audio_service.video_repository.save")
    @pytest.mark.asyncio
    async def test_skip_existing_no_force(self, mock_save, mock_tts, service, mock_video):
        """Test skipping generation if audio_url exists and force=False"""
        scene = mock_video.chapters[0].subchapters[0].scenes[0]
        # Simulate existing audio
        scene.audio_url = "/api/storage/audios/1/1-1-1_123.mp3"
        
        res = await service.generate_narration_for_single_scene(
            mock_video, mock_video.chapters[0], mock_video.chapters[0].subchapters[0], scene, force=False
        )
        
        assert res is True
        mock_tts.assert_not_called()
        assert scene.audio_url == "/api/storage/audios/1/1-1-1_123.mp3"

    @patch("backend.services.audio_service.openai_service.generate_tts", new_callable=AsyncMock)
    @patch("backend.services.audio_service.video_repository.save")
    @pytest.mark.asyncio
    async def test_openai_error_handling(self, mock_save, mock_tts, service, mock_video):
        """Test error handling when OpenAI fails"""
        mock_tts.side_effect = Exception("OpenAI Error")
        
        scene = mock_video.chapters[0].subchapters[0].scenes[0]
        
        with patch("os.path.exists", return_value=False):
            res = await service.generate_narration_for_single_scene(
                mock_video, mock_video.chapters[0], mock_video.chapters[0].subchapters[0], scene
            )
        
        assert res is False

