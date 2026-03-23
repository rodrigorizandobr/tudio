import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from backend.models.video import VideoModel, ChapterModel, SubChapterModel, SceneModel, VideoStatus
from backend.services.video_service import VideoService

@pytest.mark.asyncio
async def test_render_single_scene_success():
    mock_repo = MagicMock()
    mock_audio = MagicMock()
    video_service = VideoService(repo=mock_repo, audio_svc=mock_audio)
    
    # Create a dummy video structure
    scene = SceneModel(id=1, order=1, narration_content="Hello world", audio_url="audio.mp3", original_image_url="img.jpg", image_prompt="A prompt", video_prompt="A prompt")
    sub = SubChapterModel(id=10, order=1, title="Sub", description="Description", scenes=[scene])
    chapter = ChapterModel(id=100, order=1, title="Chapter", description="Description", estimated_duration_minutes=1.0, subchapters=[sub])
    video = VideoModel(id=500, prompt="Prompt", chapters=[chapter], language="en", total_duration_seconds=60, target_duration_minutes=1.0, status=VideoStatus.PENDING)
    
    # FIX: Ensure mock returns fresh copies and tracks saves
    saved_versions = []
    async def mock_save(v):
        saved_versions.append(VideoModel.model_validate(v.model_dump()))
        return v
        
    mock_repo.get = AsyncMock(side_effect=lambda *args, **kwargs: (saved_versions[-1] if saved_versions else VideoModel.model_validate(video.model_dump())))
    mock_repo.save = AsyncMock(side_effect=mock_save)
    
    # Mock RenderService
    with patch("backend.services.render_service.render_service._create_scene_clip", new_callable=AsyncMock) as mock_render:
        mock_render.return_value = "/tmp/fake_clip.mp4"
        
        # Mock os.path.exists and shutil.copy2
        with patch("os.path.exists", return_value=True), \
             patch("os.makedirs"), \
             patch("shutil.copy2"):
            
            tasks = []
            def mock_create_task(coro):
                t = asyncio.get_event_loop().create_task(coro)
                tasks.append(t)
                return t
                
            with patch("asyncio.create_task", side_effect=mock_create_task):
                success = await video_service.render_single_scene(video.id, chapter.id, sub.id, 0)
                assert success is True
                
                if tasks:
                    await asyncio.gather(*tasks)
                
                # Fetch video from repo to verify update
                saved_video = await video_service.get(video.id)
                saved_scene = saved_video.chapters[0].subchapters[0].scenes[0]
                
                assert saved_scene.generated_video_url is not None
                assert "1-1-1.mp4" in saved_scene.generated_video_url

@pytest.mark.asyncio
async def test_render_single_scene_hierarchical_lookup():
    mock_repo = MagicMock()
    mock_audio = MagicMock()
    video_service = VideoService(repo=mock_repo, audio_svc=mock_audio)
    
    # Create two subchapters with scenes having the same ID (1)
    scene1 = SceneModel(id=1, order=1, narration_content="Scene 1-1", audio_url="a1.mp3", original_image_url="i1.jpg", image_prompt="P", video_prompt="V")
    scene2 = SceneModel(id=1, order=1, narration_content="Scene 1-2", audio_url="a2.mp3", original_image_url="i2.jpg", image_prompt="P", video_prompt="V")
    
    sub1 = SubChapterModel(id=10, order=1, title="Sub 1", description="D1", scenes=[scene1])
    sub2 = SubChapterModel(id=20, order=2, title="Sub 2", description="D2", scenes=[scene2])
    
    chapter = ChapterModel(id=100, order=1, title="Chapter", description="D", estimated_duration_minutes=1.0, subchapters=[sub1, sub2])
    video = VideoModel(id=500, prompt="P", chapters=[chapter], language="en", total_duration_seconds=60, target_duration_minutes=1.0, status=VideoStatus.PENDING)
    
    # FIX: Ensure mock returns fresh copies and tracks saves
    saved_versions = []
    async def mock_save(v):
        saved_versions.append(VideoModel.model_validate(v.model_dump()))
        return v
        
    mock_repo.get = AsyncMock(side_effect=lambda *args, **kwargs: (saved_versions[-1] if saved_versions else VideoModel.model_validate(video.model_dump())))
    mock_repo.save = AsyncMock(side_effect=mock_save)
    
    # Mock RenderService
    with patch("backend.services.render_service.render_service._create_scene_clip", new_callable=AsyncMock) as mock_render:
        mock_render.return_value = "/tmp/fake_clip_2.mp4"
        
        with patch("os.path.exists", return_value=True), \
             patch("os.makedirs"), \
             patch("shutil.copy2"):
            
            tasks = []
            def mock_create_task(coro):
                t = asyncio.get_event_loop().create_task(coro)
                tasks.append(t)
                return t
                
            with patch("asyncio.create_task", side_effect=mock_create_task):
                # Target the scene in the SECOND subchapter (index 0 of sub2)
                success = await video_service.render_single_scene(video.id, chapter.id, sub2.id, 0)
                assert success is True
                
                if tasks:
                    await asyncio.gather(*tasks)
                
                # Fetch latest version
                final_video = await video_service.get(video.id)
                final_sub1 = final_video.chapters[0].subchapters[0]
                final_sub2 = final_video.chapters[0].subchapters[1]
                
                # Verify that scene in sub2 was updated, but NOT sub1
                assert final_sub2.scenes[0].generated_video_url is not None
                assert "1-2-1.mp4" in final_sub2.scenes[0].generated_video_url
                assert final_sub1.scenes[0].generated_video_url is None

@pytest.mark.asyncio
async def test_render_single_scene_not_found():
    mock_repo = MagicMock()
    video_service = VideoService(repo=mock_repo, audio_svc=MagicMock())
    mock_repo.get = AsyncMock(return_value=None)
    
    success = await video_service.render_single_scene(999, 1, 1, 0)
    assert success is False
