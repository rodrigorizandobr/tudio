
import pytest
from backend.services.render_service import RenderService
from backend.models.video import VideoModel

@pytest.mark.asyncio
async def test_auto_crop_logic():
    render_service = RenderService()
    
    # Mock data or use actual logic to test specific crop calculations
    # Since _create_scene_clip is a complex method involving file IO, 
    # we can test the internal dimensions logic if it were extracted, 
    # or perform a controlled integration test.
    
    # For now, let's verify if the RenderService can accept target_ratio
    # This is a smoke test to ensure the refactored method signature is correct.
    assert hasattr(render_service, '_create_scene_clip')
    
    # We could also test the aspect_ratio logic directly if we had a pure function
    # Let's verify the VideoModel migration validator
    
    old_video_data = {
        "id": 1,
        "title": "Old Video",
        "aspect_ratio": "16:9",
        "status": "completed",
        "prompt": "test",
        "chapters": [],
        "target_duration_minutes": 1.0
    }
    
    video = VideoModel(**old_video_data)
    # The validator should move aspect_ratio -> aspect_ratios
    assert video.aspect_ratios == ["16:9"]
    
    multi_video_data = {
        "id": 2,
        "title": "Multi Video",
        "aspect_ratios": ["16:9", "9:16"],
        "status": "pending",
        "prompt": "test",
        "chapters": [],
        "target_duration_minutes": 2.0,
        "outputs": {
            "16:9": "path/to/horiz.mp4",
            "9:16": "path/to/vert.mp4"
        }
    }
    
    video2 = VideoModel(**multi_video_data)
    assert video2.aspect_ratios == ["16:9", "9:16"]
    assert video2.outputs["16:9"] == "path/to/horiz.mp4"
    assert video2.outputs["9:16"] == "path/to/vert.mp4"

if __name__ == "__main__":
    pytest.main([__file__])
