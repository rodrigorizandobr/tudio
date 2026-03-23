import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from backend.services.video_service import VideoService
from backend.models.video import VideoModel, VideoStatus, ChapterModel, SubChapterModel, SceneModel

# --- Async Tests ---
@pytest.mark.asyncio
class TestVideoServicePart2:
    
    async def test_reprocess_scene_audio_success(self):
        """Test reprocess_scene_audio success flow"""
        mock_repo = MagicMock()
        mock_audio = AsyncMock()
        
        service = VideoService(repo=mock_repo, audio_svc=mock_audio, use_lock=False)
        
        # Setup Hierarchy
        scene = SceneModel(id=1, order=1, narration_content="Hello", image_prompt="Img", video_prompt="Vid", character="Narrator", generated_video_url="old.mp4", captioned_video_url="old.mp4")
        sub = SubChapterModel(id=10, order=1, title="Sub", description="Desc", scenes=[scene])
        chapter = ChapterModel(id=100, order=1, title="Chap", description="Desc", estimated_duration_minutes=1, subchapters=[sub])
        video = VideoModel(id=1, prompt="Test", status="completed", target_duration_minutes=1, chapters=[chapter])
        
        mock_repo.get.return_value = video
        mock_repo.save.side_effect = lambda x: x
        
        mock_audio.generate_narration_for_single_scene.return_value = True
        
        with patch("asyncio.create_task") as mock_create_task:
            result = await service.reprocess_scene_audio(1, 100, 10, 0)
            
            assert result is True
            mock_create_task.assert_called()
            assert scene.generated_video_url is None
            assert scene.captioned_video_url is None
            
            # Run the background task
            coro = mock_create_task.call_args[0][0]
            await coro

            mock_audio.generate_narration_for_single_scene.assert_called_with(video, chapter, sub, scene, force=True)
            assert video.status == VideoStatus.COMPLETED

    async def test_trigger_render_force_missing_assets(self):
        """Test trigger_render with missing assets but forced"""
        mock_repo = MagicMock()
        service = VideoService(repo=mock_repo, use_lock=False)
        
        video = VideoModel(id=1, prompt="Test", status="completed", target_duration_minutes=1)
        mock_repo.get.return_value = video
        mock_repo.save.side_effect = lambda x: x
        
        with patch.object(service, '_is_ready_for_rendering', return_value=False):
            with patch.object(service, 'process_video_background', new_callable=AsyncMock) as mock_process:
                 with patch("asyncio.create_task") as mock_create_task:
                     result = await service.trigger_render(1, force=True)
                     assert result is True
                     mock_create_task.assert_called()

    async def test_reprocess_scene_audio_not_found(self):
        """Test reprocess_scene_audio with invalid IDs"""
        mock_repo = MagicMock()
        service = VideoService(repo=mock_repo, use_lock=False)
        
        video = VideoModel(id=1, prompt="Test", status="completed", target_duration_minutes=1)
        mock_repo.get.return_value = video
        
        result = await service.reprocess_scene_audio(1, 999, 999, 0)
        assert result is False

    async def test_trigger_render_success(self):
        """Test trigger_render success flow"""
        mock_repo = MagicMock()
        mock_render = AsyncMock()
        service = VideoService(repo=mock_repo, render_svc=mock_render, use_lock=False)
        
        video = VideoModel(id=1, prompt="Test", status="completed", target_duration_minutes=1)
        mock_repo.get.return_value = video
        mock_repo.save.side_effect = lambda x: x
        
        # trigger_render calls process_video_background, which might call render_video
        # Wait, trigger_render calls process_video_background(video_id, stop_after_scenes=False).
        # process_video_background checks _is_ready_for_rendering.
        # If ready, it calls render_service.render_video.
        # We need mock_repo.get inside process_video_background to work.
        
        # However, testing full flow is complex.
        # If trigger_render just dispatches task, verify task dispatch.
        # The previous test patched render_video inside trigger_render? 
        # Original: "with patch.object(render_service, 'render_video', ...)"
        
        # If we just want to verify trigger_render dispatches process_video_background:
        with patch.object(service, 'process_video_background', new_callable=AsyncMock) as mock_process:
            with patch("asyncio.create_task") as mock_create_task:
                result = await service.trigger_render(1, force=True)
                assert result is True
                mock_create_task.assert_called()

    async def test_trigger_render_already_processing(self):
        """Test trigger_render fails if already processing and not forced"""
        mock_repo = MagicMock()
        service = VideoService(repo=mock_repo, use_lock=False)
        
        video = VideoModel(id=1, prompt="Test", status=VideoStatus.PROCESSING, target_duration_minutes=1)
        mock_repo.get.return_value = video
        
        with pytest.raises(ValueError):
            await service.trigger_render(1, force=False)

    async def test_resume_interrupted_tasks(self):
        """Test resume_interrupted_tasks"""
        mock_repo = MagicMock()
        service = VideoService(repo=mock_repo, use_lock=False)
        
        video = VideoModel(id=1, prompt="Test", status=VideoStatus.PROCESSING, target_duration_minutes=1)
        mock_repo.get_by_status.return_value = [video]
        mock_repo.get.return_value = video 
        
        with patch.object(service, 'process_video_background', new_callable=AsyncMock) as mock_process:
             with patch("asyncio.create_task") as mock_create_task:
                 await service.resume_interrupted_tasks()
                 mock_create_task.assert_called()

    async def test_auto_populate_images_fallback(self):
        """Test auto_populate_images with search failure and fallback"""
        mock_repo = MagicMock()
        mock_unsplash = MagicMock() # Search is usually async? check usage. unsplash_service.search_images is async.
        mock_unsplash.search_images = AsyncMock()
        mock_openai = AsyncMock()
        mock_storage = MagicMock() # Sync methods mixed with async? check usage.
        # download_image is async or sync? usually async.
        mock_storage.download_image = AsyncMock(return_value="path/img.jpg")
        mock_storage.crop_image.return_value = "path/crop.jpg"
        mock_storage.calculate_center_crop_coords.return_value = (0,0,100,100)
        
        service = VideoService(
            repo=mock_repo, 
            unsplash_svc=mock_unsplash, 
            openai_svc=mock_openai, 
            storage_svc=mock_storage,
            use_lock=False
        )
        
        scene = SceneModel(id=1, order=1, narration_content="Hello", image_prompt="FailTerm", video_prompt="Vid", character="Narrator")
        sub = SubChapterModel(id=10, order=1, title="Sub", description="Desc", scenes=[scene])
        chapter = ChapterModel(id=100, order=1, title="Chap", description="Desc", estimated_duration_minutes=1, subchapters=[sub])
        video = VideoModel(id=1, prompt="Test", status="completed", target_duration_minutes=1, chapters=[chapter], auto_image_source="unsplash")
        
        mock_repo.get.return_value = video
        mock_repo.save.side_effect = lambda x: x
        
        # 1. Search fails first, then succeeds
        mock_unsplash.search_images.side_effect = [[], [{"url": "http://win.com"}]]
        
        # 2. Fallback Agent returns new term
        mock_openai.get_or_create_assistant.return_value = "asst_123"
        mock_openai.send_message_and_wait_json.return_value = '{"terms": ["NewTerm"]}'
        
        # EXECUTE
        await service._auto_populate_images(video)
        
        # VERIFY
        assert mock_unsplash.search_images.call_count == 2
        # Check args
        args1 = mock_unsplash.search_images.call_args_list[0]
        # args1[0] is tuple of pos args. (term, orientation, count)
        assert args1[0][0] == "FailTerm"
        args2 = mock_unsplash.search_images.call_args_list[1]
        assert args2[0][0] == "NewTerm"
        
        assert scene.original_image_url == "path/img.jpg"
        assert scene.image_search == "NewTerm"

    @patch("backend.services.video_service.settings")
    async def test_process_video_background_skip_step0(self, mock_settings):
        """Test skipping Step 0 if metadata exists"""
        mock_settings.PROMPT_INIT_TEMPLATE = "Template"
        mock_repo = MagicMock()
        mock_openai = AsyncMock()
        
        service = VideoService(repo=mock_repo, openai_svc=mock_openai, use_lock=False)
        
        from backend.models.video import CharacterModel
        char = CharacterModel(name="C", description="D", physical_description="P", voice="V")
        
        video = VideoModel(
            id=1, prompt="Test", status=VideoStatus.COMPLETED, 
            title="T", description="D", tags="tag", characters=[char], visual_style="S",
            openai_thread_id="th_1",
            target_duration_minutes=1
        )
        
        mock_repo.get.return_value = video
        mock_repo.save.side_effect = lambda x: x
        
        mock_openai.get_or_create_assistant.return_value = "asst_1"
        # Setup return for Step 1 only (since Step 0 is skipped)
        mock_openai.send_message_and_wait.return_value = '{"chapters": []}'
        mock_openai.send_message_and_wait_json.return_value = '{"chapters": []}'
        
        # Using stop_after_scenes logic indirectly or mocking _generate_scenes...
        # Let's mock _generate_scenes_from_script_mode just in case script matches
        # or mock _safe_json_parse to return empty dict for chapters to stop loop
        
        # If we use stop_after_scenes=True in call?
        # The method has `stop_after_scenes` argument.
        
        await service.process_video_background(1, stop_after_scenes=True)
         
        # Verify Step 0 prompt NOT sent
        for call in mock_openai.send_message_and_wait.call_args_list:
            assert "Step 0" not in str(call)
        for call in mock_openai.send_message_and_wait_json.call_args_list:
            assert "Step 0" not in str(call)

    @patch("backend.services.video_service.settings")
    async def test_process_video_background_cancellation(self, mock_settings):
        """Test cancellation detection"""
        mock_settings.PROMPT_INIT_TEMPLATE = "Template"
        mock_repo = MagicMock()
        mock_openai = AsyncMock() # Should not be called
        service = VideoService(repo=mock_repo, openai_svc=mock_openai, use_lock=False)
        
        v1 = VideoModel(id=1, prompt="Test", status=VideoStatus.PROCESSING, openai_thread_id="th_1", target_duration_minutes=1)
        v2 = VideoModel(id=1, prompt="Test", status=VideoStatus.CANCELLED, openai_thread_id="th_1", target_duration_minutes=1)
        
        mock_repo.get.side_effect = [v1, v1, v2, v2, v2]
        mock_repo.save.side_effect = lambda x: x
        
        await service.process_video_background(1)
        
        mock_openai.send_message_and_wait.assert_not_called()
        mock_openai.send_message_and_wait_json.assert_not_called()

    @patch("backend.services.video_service.settings")
    async def test_process_video_background_assistant_failure(self, mock_settings):
        """Test failure when creating assistant"""
        mock_settings.PROMPT_INIT_TEMPLATE = "Template"
        mock_repo = MagicMock()
        mock_openai = AsyncMock()
        service = VideoService(repo=mock_repo, openai_svc=mock_openai, use_lock=False)
        
        video = VideoModel(id=1, prompt="Test", status=VideoStatus.PROCESSING, openai_thread_id="th_1", target_duration_minutes=1)
        mock_repo.get.return_value = video
        mock_repo.save.side_effect = lambda x: x
        
        mock_openai.get_or_create_assistant.side_effect = Exception("OpenAI Error")
        
        await service.process_video_background(1)
        
        assert video.status == VideoStatus.ERROR
        assert "OpenAI Error" in video.error_message

    @patch("backend.services.video_service.settings")
    async def test_call_openai_retry_corruption_success(self, mock_settings):
        """Test automatic retry when thread is corrupted"""
        mock_repo = MagicMock()
        mock_openai = AsyncMock()
        
        service = VideoService(repo=mock_repo, openai_svc=mock_openai, use_lock=False)
        
        video = VideoModel(id=1, prompt="Test", openai_thread_id="th_old", status=VideoStatus.PROCESSING, target_duration_minutes=1)
        mock_repo.get.return_value = video
        mock_repo.save.side_effect = lambda x: x
        
        mock_openai.send_message_and_wait_json.side_effect = [
             ValueError("THREAD_CORRUPTED: Please create a new thread"), # Attempt 1
             '{"valid": "json"}' # Attempt 2
        ]
        
        # Mock reset_thread
        with patch.object(service, 'reset_thread_for_video', new_callable=AsyncMock) as mock_reset:
            async def reset_side_effect(vid):
                video.openai_thread_id = "th_new"
                return True
            mock_reset.side_effect = reset_side_effect
    
            # Execute CORRECTLY: No mock_openai passed
            result = await service._call_openai_with_retry(
                "th_old", "asst_1", "Prompt", "Context", 1, max_retries=1
            )
            
            assert result == '{"valid": "json"}'
            assert mock_openai.send_message_and_wait_json.call_count == 2
            mock_reset.assert_called_with(1)
            assert video.openai_thread_id == "th_new"
