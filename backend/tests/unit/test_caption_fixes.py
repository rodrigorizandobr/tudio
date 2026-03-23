import pytest
import asyncio
import os
from unittest.mock import MagicMock, patch
from backend.services.caption_service import CaptionService
from backend.models.video import VideoModel, SceneModel, VideoStatus

@pytest.mark.asyncio
async def test_burn_captions_async_non_blocking():
    service = CaptionService()
    
    # Mock ffmpeg and capabilities
    service._has_ass_filter = True
    service._ffmpeg_path = "ffmpeg"
    
    # Create dummy files to pass exists() checks
    test_video = "/tmp/test.mp4"
    with open(test_video, "wb") as f:
        f.write(b"A"*200) # > 100 bytes
        
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        
        success = await service.burn_captions_into_video(
            video_path=test_video,
            ass_path="/tmp/test.ass",
            output_path="/tmp/out.mp4"
        )
        
        assert success is True
        assert mock_run.called
    
    # Cleanup
    if os.path.exists(test_video):
        os.remove(test_video)

@pytest.mark.asyncio
async def test_generate_scene_captions_isolation():
    service = CaptionService()
    video = VideoModel(
        id=1, 
        prompt="test", 
        target_duration_minutes=1, 
        status=VideoStatus.PENDING,
        chapters=[]
    )
    scene = SceneModel(
        id=10, 
        order=1,
        description="desc", 
        image_prompt="img", 
        video_prompt="vid", 
        narration_content="Hello"
    )
    
    with patch.object(service, "get_word_timestamps", return_value=[{"word": "Hello", "start": 0, "end": 1}]):
        with patch.object(service, "_caption_one_scene", return_value="url") as mock_caption:
            with patch("backend.repositories.video_repository.video_repository.save") as mock_save:
                words = await service.generate_captions_for_scene(video, scene)
                
                assert len(words) == 1
                assert scene.caption_status == "done"
                # Ensure only one scene was captioned
                mock_caption.assert_called_once_with(video, scene, "karaoke", {}, force_whisper=False)
