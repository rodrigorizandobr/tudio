import pytest
import os
from unittest.mock import MagicMock, patch
from backend.models.video import VideoModel, SceneModel
from backend.services.caption_service import CaptionService

@pytest.mark.asyncio
async def test_caption_service_uses_persisted_config():
    """
    Verify that generate_captions_for_scene uses the style and options
    persisted in the VideoModel.
    """
    service = CaptionService()
    
    # Mock Video with specific caption config
    video = VideoModel(
        id=123,
        prompt="test",
        target_duration_minutes=1,
        status="completed",
        caption_style="bounce",  # Custom style
        caption_options={"position": "top", "words_per_line": 3}  # Custom options
    )
    
    scene = SceneModel(
        id=1,
        order=1,
        narration_content="Hello world",
        image_prompt="test img",
        video_prompt="test vid",
        generated_video_url="storage/videos/test.mp4"
    )
    
    # Mock dependencies to avoid real processing
    with patch.object(service, 'get_word_timestamps', return_value=[{"word": "Hello", "start": 0, "end": 1}]), \
         patch.object(service, '_resolve_video_path', return_value="/tmp/test.mp4"), \
         patch("os.path.exists", return_value=True), \
         patch("os.makedirs"), \
         patch("tempfile.mkstemp", return_value=(99, "/tmp/fake.ass")), \
         patch("os.fdopen", MagicMock()), \
         patch("os.remove", MagicMock()), \
         patch("backend.services.caption_service.video_repository.save") as mock_save, \
         patch.object(service, 'burn_captions_into_video', return_value=True) as mock_burn:
        
        # We also need to mock generate_ass_content to see what's being passed
        with patch("backend.services.caption_service.generate_ass_content", return_value="fake_ass") as mock_gen_ass:
            
            await service.generate_captions_for_scene(video, scene)
            
            # Check if generate_ass_content was called with video's persisted config
            mock_gen_ass.assert_called_once()
            args, kwargs = mock_gen_ass.call_args
            
            assert kwargs["style"] == "bounce"
            assert kwargs["options"]["position"] == "top"
            assert kwargs["options"]["words_per_line"] == 3
            
            # Verify status update
            assert scene.caption_status == "done"
            assert scene.captioned_video_url is not None
            mock_save.assert_called()

@pytest.mark.asyncio
async def test_caption_one_scene_defaults_if_not_set():
    """
    Verify default values if no style/options are set in the video.
    """
    service = CaptionService()
    video = VideoModel(id=456, prompt="test", target_duration_minutes=1, status="completed")
    scene = SceneModel(id=1, order=1, narration_content="test", image_prompt="test", video_prompt="test", generated_video_url="test.mp4")
    
    # By default in the router/service, it uses "karaoke" if not specified
    # but _caption_one_scene receives style/options as arguments from generate_captions_for_scene
    
    with patch.object(service, 'get_word_timestamps', return_value=[{"word": "test", "start": 0, "end": 1}]), \
         patch.object(service, '_resolve_video_path', return_value="/tmp/test.mp4"), \
         patch("os.path.exists", return_value=True), \
         patch("os.makedirs"), \
         patch("tempfile.mkstemp", return_value=(99, "/tmp/fake.ass")), \
         patch("os.fdopen", MagicMock()), \
         patch("os.remove", MagicMock()), \
         patch.object(service, 'burn_captions_into_video', return_value=True), \
         patch("backend.services.caption_service.generate_ass_content", return_value="fake_ass") as mock_gen_ass:
        
        # In generate_captions_for_scene: style = video.caption_style or "karaoke"
        await service.generate_captions_for_scene(video, scene)
        
        args, kwargs = mock_gen_ass.call_args
        assert kwargs["style"] == "karaoke"
        assert kwargs["options"] == {}
