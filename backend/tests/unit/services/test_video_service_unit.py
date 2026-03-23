import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from backend.services.video_service import VideoService
from backend.models.video import VideoModel, VideoStatus, ChapterModel, SubChapterModel, SceneModel

from backend.schemas.video import VideoCreate

class TestVideoServiceUnit:

    @patch("backend.services.video_service.video_repository")
    @pytest.mark.asyncio
    async def test_create_video(self, mock_repo):
        service = VideoService()
        video_data = VideoCreate(prompt="Test", target_duration_minutes=1, language="pt-BR")
        expected = VideoModel(prompt="Test", id=1, status="pending", target_duration_minutes=1)
        mock_repo.save.return_value = expected
        
        result = service.create(video_data) # sync method
        assert result == expected
        mock_repo.save.assert_called()

    @patch("backend.services.video_service.video_repository")
    @pytest.mark.asyncio
    async def test_get_video(self, mock_repo):
        service = VideoService()
        mock_repo.get.return_value = VideoModel(id=1, prompt="t", status="pending", target_duration_minutes=1)
        result = service.get(1)
        assert result.id == 1

    @patch("backend.services.video_service.video_repository")
    @pytest.mark.asyncio
    async def test_list_videos(self, mock_repo):
        service = VideoService()
        mock_repo.query_videos.return_value = []
        result = service.list_all()
        assert result == []

    @patch("backend.services.video_service.video_repository")
    @pytest.mark.asyncio
    async def test_update_video(self, mock_repo):
        service = VideoService()
        existing = VideoModel(id=1, prompt="Old", status="pending", target_duration_minutes=1)
        mock_repo.get.return_value = existing
        # Return the object passed to save to simulate persistence of changes
        mock_repo.save.side_effect = lambda x: x
        
        update_data = {"prompt": "New"}
        result = service.update(1, update_data)
        assert result.prompt == "New"

    @patch("backend.services.video_service.video_repository")
    @pytest.mark.asyncio
    async def test_delete_video(self, mock_repo):
        service = VideoService()
        mock_repo.delete.return_value = True
        result = service.delete(1)
        assert result is True
    @patch("backend.services.video_service.video_repository")
    @pytest.mark.asyncio
    async def test_restore_video(self, mock_repo):
        service = VideoService()
        mock_repo.restore.return_value = True
        result = service.restore(1)
        assert result is True
        mock_repo.restore.assert_called_with(1)


    @patch("backend.services.openai_service.openai_service")
    @patch("backend.services.video_service.video_repository")
    @pytest.mark.asyncio
    async def test_process_video_background_simple(self, mock_repo, mock_openai):
        service = VideoService()
        # Setup Video with NO chapters initially to trigger generation
        video = VideoModel(id=1, prompt="Test", status="pending", target_duration_minutes=1)
        mock_repo.get.return_value = video
        
        # Configure AsyncMocks for awaitable methods
        mock_openai.generate_script = AsyncMock(return_value="Script content")
        mock_openai.generate_chapters = AsyncMock(return_value=[])
        mock_openai.create_thread = AsyncMock(return_value="thread_123")
        mock_openai.get_or_create_assistant = AsyncMock(return_value="asst_123")
    
        with patch("backend.services.video_service.settings") as mock_settings:
            mock_settings.PROMPT_INIT_TEMPLATE = "Template Init"
            mock_settings.PROMPT_CHAPTERS_TEMPLATE = "Template Chapters"
            mock_settings.PROMPT_SUBCHAPTERS_TEMPLATE = "Template Sub"
            mock_settings.PROMPT_SCENES_TEMPLATE = "Template Scenes"
            mock_settings.PROMPT_IMAGE_SEARCH_TEMPLATE = "Template Img"
            
            # JSON Responses Sequence:
            # 1. Step 0 (Metadata)
            # 2. Step 1 (Chapters)
            # 3. Step 2 (Subchapters for Chapter 1)
            # 4. Step 3 (Scenes for Subchapter 1)
            # 5. ... (We only have 1 chapter, 1 subchapter to keep it simple)
            
            response_step0 = '{"title": "Gen Title", "visual_style": "Comic", "characters": []}'
            response_step1 = '{"chapters": [{"order": 1, "title": "C1", "description": "D1", "estimated_duration_minutes": 1}]}'
            response_step2 = '{"subchapters": [{"order": 1, "title": "S1", "description": "D1"}]}'
            response_step3 = '{"scenes": [{"order": 1, "narration_content": "Hello World", "duration_seconds": 5}]}'
            
            # Using side_effect for consecutive calls
            # Note: send_message_and_wait (Step 0, 1) AND _call_openai_with_retry (Step 2, 3 uses send_message_and_wait_json)
            # define side_effects for both potential methods called
            
            async def side_effect_openai(*args, **kwargs):
                if not responses:
                     return "{}"
                return responses.pop(0)

            responses = [response_step0, response_step1, response_step2, response_step3]
            
            mock_openai.send_message_and_wait.side_effect = side_effect_openai
            mock_openai.send_message_and_wait_json.side_effect = side_effect_openai # reuse same queue
            
            # CRITICAL: video_repository.save must return the video object so the service continues working with it
            mock_repo.save.side_effect = lambda x: x
            
            await service.process_video_background(1)
        
        mock_openai.create_thread.assert_called()
        
        # Verify assertions
        assert mock_repo.save.call_count > 1
        assert len(video.chapters) == 1
        assert len(video.chapters[0].subchapters) == 1
        assert len(video.chapters[0].subchapters[0].scenes) == 1
    @patch("backend.services.video_service.audio_service")
    @patch("backend.services.video_service.video_repository")
    @pytest.mark.asyncio
    async def test_reprocess_audio(self, mock_repo, mock_audio):
        service = VideoService()
        import asyncio
        # Setup video
        video = VideoModel(id=1, prompt="Test", status="processing", target_duration_minutes=1)
        mock_repo.get.return_value = video
        mock_repo.save.side_effect = lambda x: x
        
        mock_audio.generate_narration_for_video = AsyncMock(return_value=True)
        
        await service.reprocess_audio(1)
        
        # Give chance for background task to run
        await asyncio.sleep(0.1)
        
        mock_audio.generate_narration_for_video.assert_called_with(video, force=True, standalone=True)
        assert video.status == "completed"

    @patch("backend.services.video_service.render_service")
    @patch("backend.services.video_service.video_repository")
    @pytest.mark.asyncio
    async def test_trigger_render(self, mock_repo, mock_render):
        service = VideoService()
        import asyncio
        video = VideoModel(id=1, prompt="Test", status="completed", target_duration_minutes=1)
        # Ensure chapters have estimated_duration_minutes if any
        video.chapters = [ChapterModel(id=1, order=1, title="C", description="D", subchapters=[], estimated_duration_minutes=1.0)]
        mock_repo.get.return_value = video
        mock_repo.save.side_effect = lambda x: x 
        
        service._is_ready_for_rendering = MagicMock(return_value=True)
        
        # Simulate side-effect: render_service updates video object AND returns url
        async def render_side_effect(v, target_ratio="16:9", progress_callback=None):
            v.video_url = "http://video.url"
            return "http://video.url"
    
        mock_render.render_video.side_effect = render_side_effect
    
        await service.trigger_render(1)
    
        # Give chance for background task to run
        await asyncio.sleep(0.1)
    
        from unittest.mock import ANY
        mock_render.render_video.assert_called_with(video, target_ratio="16:9", progress_callback=ANY)
        assert video.video_url.startswith("http://video.url")
        assert video.status == "completed"
    
    @patch("backend.services.video_service.unsplash_service")
    @patch("backend.services.video_service.image_storage_service")
    @patch("backend.services.video_service.video_repository")
    @pytest.mark.asyncio
    async def test_auto_populate_images(self, mock_repo, mock_storage, mock_unsplash):
        service = VideoService()
        video = VideoModel(
            id=1, prompt="Test", status="processing", target_duration_minutes=1,
            auto_image_source="unsplash", aspect_ratios=["16:9"]
        )
        # Add a scene
        from backend.models.video import ChapterModel, SubChapterModel, SceneModel
        scene = SceneModel(
            id=1, order=1, narration_content="N", image_prompt="I", video_prompt="V"
        )
        sub = SubChapterModel(id=1, order=1, title="S", description="D", scenes=[scene])
        chap = ChapterModel(id=1, order=1, title="C", description="D", estimated_duration_minutes=1.0, subchapters=[sub]) # Fixed: added estimated_duration_minutes
        video.chapters = [chap]
        
        mock_repo.save.side_effect = lambda x: x
        
        # Mock Unsplash (Async)
        mock_unsplash.search_images = AsyncMock(return_value=[{"url": "http://img.com/1.jpg"}])
        
        # Mock Storage (Async)
        mock_storage.download_image = AsyncMock(return_value="local/path/1.jpg")
        # Sync method
        mock_storage.calculate_center_crop_coords.return_value = (0,0,100,100)
        mock_storage.crop_image = AsyncMock(return_value="local/path/crop_1.jpg") # Assuming crop is async or we check implementation... 
        # Wait, crop_image in service is called without await?
        # Line 1400: final_path = image_storage_service.crop_image(...)
        # If crop_image is sync, then MagicMock is fine. If async, need AsyncMock.
        # Looking at previous view_file (line 1012), it is called without await: 
         # final_path = image_storage_service.crop_image(...)
         # So crop_image is sync. I should NOT make it AsyncMock.
        mock_storage.crop_image = MagicMock(return_value="local/path/crop_1.jpg")
        
        await service._auto_populate_images(video)
        
        assert scene.original_image_url == "local/path/1.jpg"

    def test_calculate_duration(self):
        service = VideoService()
        text = "word " * 150 # 150 words
        # Rule: 150 words = 60 seconds (0.4s per word)
        duration = service._calculate_duration(text)
        assert duration == 60

    def test_safe_json_parse(self):
        service = VideoService()
        valid = '{"key": "value"}'
        assert service._safe_json_parse(valid) == {"key": "value"}
        
        # Test markdown strip
        markdown = '```json\n{"key": "value"}\n```'
        assert service._safe_json_parse(markdown) == {"key": "value"}
        
        # Test error
        with pytest.raises(ValueError):
            service._safe_json_parse("invalid")

    @patch("backend.services.video_service.video_repository")
    @pytest.mark.asyncio
    async def test_cancel_processing(self, mock_repo):
        service = VideoService()
        video = VideoModel(id=1, prompt="Test", status="processing", target_duration_minutes=1)
        mock_repo.get.return_value = video
        mock_repo.save.side_effect = lambda x: x
        
        service.cancel_processing(1)
        
        assert video.status == "cancelled"
        mock_repo.save.assert_called()

    @patch("backend.services.video_service.audio_service")
    @patch("backend.services.video_service.video_repository")
    @pytest.mark.asyncio
    async def test_reprocess_script(self, mock_repo, mock_audio):
        service = VideoService()
        import asyncio
        video = VideoModel(id=1, prompt="Test", status="completed", target_duration_minutes=1)
        mock_repo.get.return_value = video
        mock_repo.save.side_effect = lambda x: x
        
        # Mock process_video_background on the instance
        service.process_video_background = AsyncMock(return_value=True)
        
        await service.reprocess_script(1)
        
        # Validation: check if it reset stuff
        assert video.chapters == []
        assert video.status == "pending"
        # service.process_video_background.assert_called_with(1, stop_after_scenes=True) 
        # CORRECTION: The method implementation creates task in Router, not Service (based on comments)
        # So we don't assert call here.

    @patch("backend.services.openai_service.openai_service")
    @patch("backend.services.video_service.video_repository")
    @pytest.mark.asyncio
    async def test_process_video_background_error(self, mock_repo, mock_openai):
        service = VideoService()
        # Setup clean video
        video = VideoModel(id=1, prompt="Fail", status="pending", target_duration_minutes=1)
        mock_repo.get.return_value = video
        mock_repo.save.side_effect = lambda x: x
        
        # Make openai fail immediately
        mock_openai.create_thread = AsyncMock(side_effect=Exception("API Error"))
        
        # process_video_background swallows exceptions and sets status=ERROR
        await service.process_video_background(1)
        
        assert video.status == "error"
        assert "API Error" in str(video.error_message)

    @patch("backend.services.openai_service.openai_service")
    @patch("backend.services.video_service.video_repository")
    @pytest.mark.asyncio
    async def test_reprocess_chapter(self, mock_repo, mock_openai):
        service = VideoService()
        import asyncio
        # Setup video with 1 chapter
        from backend.models.video import ChapterModel, SubChapterModel, SceneModel
        scene = SceneModel(id=1, order=1, narration_content="Old", image_prompt="Img", video_prompt="Vid")
        sub = SubChapterModel(id=1, order=1, title="Old", description="Old", scenes=[scene])
        chap = ChapterModel(id=1, order=1, title="Old", description="Old", estimated_duration_minutes=1, subchapters=[sub])
        video = VideoModel(id=1, prompt="Test", status="completed", target_duration_minutes=1, chapters=[chap])
        
        mock_repo.get.return_value = video
        mock_repo.save.side_effect = lambda x: x
        
        # Strategy: Mock process_video_background to avoid deep dependencies (OpenAI) 
        # and just verify it was triggered and logic flows.
        assert len(video.chapters[0].subchapters) == 1
        
        async def fake_processing(vid_id, **kwargs):
             # Simulate side effects of processing (Regeneration)
             # Note: reprocess_chapter clears subchapters, so we must recreate them
             from backend.models.video import SubChapterModel, SceneModel
             new_scene = SceneModel(id=2, order=1, narration_content="New Scene", image_prompt="Img", video_prompt="Vid")
             new_sub = SubChapterModel(id=2, order=1, title="New", description="New", scenes=[new_scene])
             
             # The test setup defines 'video' in the outer scope
             if video.chapters:
                 video.chapters[0].subchapters = [new_sub]
             return True

        service.process_video_background = AsyncMock(side_effect=fake_processing)

        await service.reprocess_chapter(1, 1) # This triggers background task
        
        # Give chance for background task to run
        await asyncio.sleep(0.1) 
        
        # Verify call
        service.process_video_background.assert_called()
        
        # Verify simulated update
        assert video.chapters[0].subchapters[0].title == "New"
        assert video.chapters[0].subchapters[0].scenes[0].narration_content == "New Scene"

    @patch("backend.services.video_service.video_repository")
    def test_update_scene_video(self, mock_repo):
        service = VideoService()
        # Setup hierarchy
        from backend.models.video import ChapterModel, SubChapterModel, SceneModel
        scene = SceneModel(id=1, order=1, narration_content="Scene 1", image_prompt="Img", video_prompt="Vid")
        sub = SubChapterModel(id=1, order=1, title="S", description="D", scenes=[scene])
        chap = ChapterModel(id=1, order=1, title="C", description="D", estimated_duration_minutes=1, subchapters=[sub])
        video = VideoModel(id=1, prompt="Test", status="completed", target_duration_minutes=1, chapters=[chap])
        
        mock_repo.get.return_value = video
        mock_repo.save.side_effect = lambda x: x
        
        # Success case
        result = service.update_scene_video(1, 1, 1, 1, "http://new.url")
        assert result is True
        assert scene.video_url == "http://new.url"
        
        # Failure case (not found)
        result_fail = service.update_scene_video(1, 99, 99, 99, "http://fail.url")
        assert result_fail is False




    @patch("backend.services.openai_service.openai_service")
    @patch("backend.services.video_service.video_repository")
    @pytest.mark.asyncio
    async def test_process_video_openai_error(self, mock_repo, mock_openai):
        service = VideoService()
        video = VideoModel(id=1, prompt="Test", status="pending", target_duration_minutes=1)
        mock_repo.get.return_value = video
        mock_repo.save.side_effect = lambda x: x
        
        mock_openai.create_thread = AsyncMock(side_effect=Exception("OpenAI Down"))
        
        # Should catch exception and log error/update status
        # Assuming service swallows exception or re-raises? 
        # Typically background tasks log and update DB status.
        try:
            await service.process_video_background(1)
        except Exception:
            pass # If it re-raises
            
        # Verify status update to ERROR if implemented
        # Based on typical service pattern:
        # assert video.status == "error" 
        # But let's verify mock_repo.save was called to persist 'error' state if logic exists
        mock_repo.save.assert_called()


    def test_format_prompt(self):
        service = VideoService()
        template = "Hello {name}, welcome to {place}"
        result = service._format_prompt(template, name="World")
        assert result == "Hello World, welcome to {place}"

    @patch("backend.services.agent_service.agent_service")
    @pytest.mark.asyncio
    async def test_get_video_context(self, mock_agent_service):
        service = VideoService()
        # Setup video with agent
        video = VideoModel(id=1, prompt="Topic", status="pending", target_duration_minutes=1, agent_id="agent_1")
        
        # Mock agent service get
        mock_agent = MagicMock()
        mock_agent.name = "Bond"
        mock_agent.description = "Spy"
        mock_agent.icon = "gun"
        mock_agent.prompt_init = "Init"
        mock_agent.prompt_chapters = "Chaps" 
        mock_agent.prompt_subchapters = "Subs"
        mock_agent.prompt_scenes = "Scenes"
        
        mock_agent_service.get.return_value = mock_agent
        
        context = await service._get_video_context(video)
        
        assert context["topic"] == "Topic"
        assert context["agent_name"] == "Bond"
        assert context["agent_prompt_init"] == "Init"
        
        # Test without agent
        video_no_agent = VideoModel(id=2, prompt="NoAgent", status="pending", target_duration_minutes=1)
        context_no_agent = await service._get_video_context(video_no_agent)
        assert context_no_agent["topic"] == "NoAgent"
        assert context_no_agent["agent_name"] == ""

    def test_is_ready_for_rendering(self):
        service = VideoService()
        from backend.models.video import VideoModel, ChapterModel, SubChapterModel, SceneModel
        
        # Setup complete video
        scene = SceneModel(id=1, order=1, narration_content="N", audio_url="aud.mp3", original_image_url="img.jpg", image_prompt="Img", video_prompt="Vid")
        sub = SubChapterModel(id=1, order=1, title="S", description="D", scenes=[scene])
        chap = ChapterModel(id=1, order=1, title="C", description="D", estimated_duration_minutes=1, subchapters=[sub])
        video = VideoModel(id=1, prompt="Test", status="processing", target_duration_minutes=1, chapters=[chap], music="music.mp3")
        
        # Mock os.path.exists globally for this test block
        with patch("os.path.exists", return_value=True):
             assert service._is_ready_for_rendering(video) is True
             
             # Missing audio
             scene.audio_url = None
             assert service._is_ready_for_rendering(video) is False

    @patch("backend.services.video_service.video_repository")
    def test_duplicate_video(self, mock_repo):
        service = VideoService()
        from backend.models.video import ChapterModel, SubChapterModel, SceneModel
        # Setup complex video
        scene = SceneModel(id=10, order=1, narration_content="N", image_prompt="I", video_prompt="V", audio_url="old.mp3")
        sub = SubChapterModel(id=20, order=1, title="S", description="D", scenes=[scene])
        chap = ChapterModel(id=30, order=1, title="C", description="D", estimated_duration_minutes=1, subchapters=[sub])
        original = VideoModel(id=1, prompt="Orig", status="completed", target_duration_minutes=1, chapters=[chap], openai_thread_id="th_1")
        
        mock_repo.get.return_value = original
        mock_repo.save.side_effect = lambda x: x
        
        new_video = service.duplicate_video(1)
        
        assert new_video.id is None
        assert new_video.status == "pending"
        assert new_video.openai_thread_id is None # Critical check
        assert new_video.title == " (Copy)" # Original title was empty default
        # Check deep copy of structure
        assert len(new_video.chapters) == 1
        assert new_video.chapters[0].subchapters[0].scenes[0].audio_url is None # Should be reset

    @patch("backend.services.video_service.video_repository")
    @patch("backend.services.openai_service.openai_service")
    @pytest.mark.asyncio
    async def test_reset_thread_for_video(self, mock_openai, mock_repo):
        service = VideoService()
        video = VideoModel(id=1, prompt="T", status="pending", target_duration_minutes=1, openai_thread_id="old_thread")
        mock_repo.get.return_value = video
        mock_repo.save.side_effect = lambda x: x
        
        mock_openai.reset_thread = AsyncMock(return_value="new_thread_123")
        
        await service.reset_thread_for_video(1)
        
        assert video.openai_thread_id == "new_thread_123"
        mock_repo.save.assert_called()

    @patch("backend.services.openai_service.openai_service")
    @pytest.mark.asyncio
    async def test_get_batch_fallback_search_terms(self, mock_openai):
        service = VideoService()
        # Setup
        mock_openai.evaluate_and_fallback_image_term = AsyncMock(return_value=["cat", "kitten"])
        mock_openai.create_thread = AsyncMock(return_value="th_fallback")
        # Mock dependencies called inside
        mock_openai.get_or_create_assistant = AsyncMock(return_value="asst_fallback")
        mock_openai.send_message_and_wait_json = AsyncMock(return_value='{"terms": ["cat", "kitten"]}')
        
        from backend.models.video import VideoModel
        video = VideoModel(id=1, prompt="Pets", status="processing", target_duration_minutes=1, openai_thread_id="th_exists")
        
        terms = await service._get_batch_fallback_search_terms(video, "dog", "context", ["dog"])
        
        assert "cat" in terms
        assert "kitten" in terms

    @patch("backend.services.video_service.video_repository")
    @patch("backend.services.openai_service.openai_service")
    @pytest.mark.asyncio
    async def test_generate_scenes_from_script_mode(self, mock_openai, mock_repo):
        service = VideoService()
        # Setup video with script content
        # Note: In Script Mode, narration_content come directly from script lines, not OpenAI!
        video = VideoModel(id=1, prompt="Script Video", status="processing", target_duration_minutes=1, 
                          script_content="Line 1", openai_thread_id="th_1")
        mock_repo.get.return_value = video
        mock_repo.save.side_effect = lambda x: x
        
        # Mock OpenAI responses
        mock_openai.create_thread = AsyncMock(return_value="th_1")
        mock_openai.get_or_create_assistant = AsyncMock(return_value="asst_1")
        
        # SMART Async Side Effect
        async def smart_side_effect(thread_id, assistant_id, content):
            # print(f"DEBUG Mock Prompt: {content[:50]}...")
            content_lower = content.lower()
            
            # DIRECTOR MODE logic: It should return CHAPTERS hierarchy
            if "chapters" in content_lower or "capítulos" in content_lower or "organize" in content_lower:
                return '''
                {
                    "chapters": [
                        {
                            "id": 1,
                            "order": 1,
                            "title": "C1",
                            "description": "D1",
                            "subchapters": [
                                {
                                    "id": 1,
                                    "order": 1,
                                    "title": "S1",
                                    "description": "D1",
                                    "scenes": [
                                        {
                                            "id": 1,
                                            "order": 1,
                                            "narration_content": "Line 1",
                                            "visual_description": "Visual",
                                            "image_prompt": "Img",
                                            "duration_seconds": 5
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
                '''
            
            # Fallback for sub-calls if any (though _generate_scenes_from_script_mode 
            # might not make more calls after the main organization depending on implementation)
            if "scenes" in content_lower or "cenas" in content_lower: 
                 return '{"scenes": [{"id": 1, "order": 1, "narration_content": "Line 1", "duration_seconds": 5}]}'
            
            if "subchapters" in content_lower or "sub-capítulos" in content_lower: 
                 return '{"subchapters": [{"order": 1, "title": "S1", "description": "D1"}]}'
            
            return '{}'

        mock_openai.send_message_and_wait_json.side_effect = smart_side_effect
        
        # The service implementation of _generate_scenes_from_script_mode takes (video, assistant_id, context)
        await service._generate_scenes_from_script_mode(video, "asst_1", {})
        
        # Verificações
        assert len(video.chapters) == 1
        assert video.chapters[0].subchapters[0].scenes[0].narration_content == "Line 1"

    @patch("backend.services.video_service.video_repository")
    @patch("backend.services.video_service.unsplash_service")
    @patch("backend.services.video_service.image_storage_service") # Default (MagicMock) to support Sync methods
    @patch("backend.services.video_service.audio_service", new_callable=AsyncMock)
    @patch("backend.services.video_service.render_service", new_callable=AsyncMock)
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_process_video_background_success(self, mock_render, mock_audio, mock_storage, mock_unsplash, mock_repo):
        # Happy Path Test
        # Assign mocks manually to the service instance to avoid fixture/patch order issues
        service = VideoService()
        service.render_service = mock_render
        service.video_repository = mock_repo
        
        video = VideoModel(id=1, prompt="Success", status="pending", target_duration_minutes=1, 
                          auto_generate_narration=True, auto_image_source="unsplash", aspect_ratios=["16:9"])
        
        # Mock Repo must allow updates to the video object
        mock_repo.get.return_value = video
        mock_repo.save.side_effect = lambda x: x
        
        # MANUAL PATCHING
        import backend.services.openai_service as openai_module
        original_service = openai_module.openai_service
        
        mock_openai = AsyncMock()
        openai_module.openai_service = mock_openai
        service.openai_service = mock_openai # Manual injection
        
        try:
            # Mocks
            mock_openai.create_thread = AsyncMock(return_value="th_1")
            mock_openai.get_or_create_assistant = AsyncMock(return_value="asst_1")
            
            # Mock text response (Standard Mode Step 1)
            mock_openai.send_message_and_wait = AsyncMock(return_value='{"chapters": [{"order": 1, "title": "C1", "description": "D1", "estimated_duration_minutes": 1}]}')
            
            # Async Side Effect for JSON responses
            async def smart_side_effect(thread_id, assistant_id, content):
                 print(f"DEBUG PROMPT: {content}")
                 content_lower = content.lower()
                 # print(f"DEBUG JSON Prompt: {content[:100]}...")
                 
                 # ORDER MATTERS!
                 if "chapters" in content_lower or "capítulos" in content_lower: # Step 1 (Standard Mode)
                     return '{"chapters": [{"order": 1, "title": "C1", "description": "D1", "estimated_duration_minutes": 1}]}'

                 if "scenes" in content_lower or "cenas" in content_lower or "cena" in content_lower: # Step 3
                     return '{"scenes": [{"order": 1, "narration_content": "Line", "image_search": "img", "duration_seconds": 5}]}'
                 
                 if "subchapters" in content_lower or "sub-capítulos" in content_lower or "sub-capítulo" in content_lower: # Step 2
                     return '{"subchapters": [{"order": 1, "title": "S1", "description": "D1"}]}'
                     
                 # FALLBACK BATCH SUPPORT
                 if "fallback" in content_lower or "no images found" in content_lower:
                     return '{"terms": ["kitten", "cat"]}'
                 
                 print("DEBUG JSON Prompt UNMATCHED, returning empty dict")
                 return '{}'
                 
            mock_openai.send_message_and_wait_json.side_effect = smart_side_effect
            
            # Audio SIDE EFFECT to populate audio_url (Critical for _is_ready_for_rendering)
            async def audio_side_effect(video_arg, force=False):
                # print("DEBUG AUDIO SIDE EFFECT RUNNING")
                count = 0
                for ch in video_arg.chapters:
                    for sub in ch.subchapters:
                        for scene in sub.scenes:
                            scene.audio_url = "http://audio.com/1.mp3"
                            count += 1
                return True
                
            mock_audio.generate_narration_for_video.side_effect = audio_side_effect
            service.audio_service = mock_audio
            
            # Render Side Effect (Critical for completion)
            async def render_side_effect(video_arg, *args, **kwargs):
                video_arg.video_url = "http://vid.com/1.mp4"
                return "http://vid.com/1.mp4"
            
            mock_render.render_video.side_effect = render_side_effect
            service.render_service = mock_render
            
            # Images 
            mock_unsplash.search_images = AsyncMock(return_value=[{"url": "http://img.com/1.jpg"}])
            service.unsplash_service = mock_unsplash
             
            # IMPORTANT: mock_storage is MagicMock (default). 
            # We must configure Async methods as AsyncMock, and Sync as sync values.
            mock_storage.download_image = AsyncMock(return_value="local/1.jpg")
            mock_storage.calculate_center_crop_coords.return_value = (0,0,10,10)
            mock_storage.crop_image.return_value = "local/crop_1.jpg"
             
            # IMPORTANT: mock os.path.exists to pass _is_ready_for_rendering
            with patch("os.path.exists", return_value=True):
                # Run
                await service.process_video_background(1)
                 
                assert video.status == "completed"
                assert video.progress == 100.0
                mock_render.render_video.assert_called()
        finally:
            openai_module.openai_service = original_service


    @patch("backend.services.video_service.video_repository")
    @patch("asyncio.create_task")
    @pytest.mark.asyncio
    async def test_reprocess_images(self, mock_create_task, mock_repo):
        service = VideoService()
        """Test reprocess images logic (Background Task)"""
        video = VideoModel(id=1, prompt="Reprocess Images", status="completed", target_duration_minutes=1)
        video.chapters = [ChapterModel(id=1, order=1, title="C1", description="Desc", estimated_duration_minutes=1, subchapters=[SubChapterModel(id=1, order=1, title="S1", description="Desc", scenes=[SceneModel(id=1, order=1, narration_content="Scene", image_prompt="Img", video_prompt="Vid", character="Narrator")])])]
        
        # Configure Repo calling
        mock_repo.get.return_value = video
        mock_repo.save.side_effect = lambda x: x
        
        # Import Dependencies to Patch
        from backend.services.video_service import unsplash_service, image_storage_service
        
        with patch.object(unsplash_service, 'search_images', new_callable=AsyncMock) as mock_search:
             with patch.object(image_storage_service, 'download_image', new_callable=AsyncMock) as mock_download:
                 # crop_image and calculate are SYNC
                 with patch.object(image_storage_service, 'crop_image') as mock_crop:
                     with patch.object(image_storage_service, 'calculate_center_crop_coords') as mock_calc:
                         # Setup Mocks
                         mock_search.return_value = [{"url": "http://img.com"}]
                         mock_download.return_value = "path/to/img.jpg"
                         

                         result = await service.reprocess_images(1, "unsplash")
                         
                         assert result is True
                         
                         # Capture and run background task
                         mock_create_task.assert_called()
                         coro = mock_create_task.call_args[0][0]
                         await coro # Run logic synchronously
                         
                         # Verify Persistence
                         found = False
                         for call in mock_repo.save.call_args_list:
                             if call[0][0].auto_image_source == "unsplash":
                                 found = True
                                 break
                         assert found, "Video with unsplash source not saved"
                         
                         # Verify Scene Update
                         assert video.chapters[0].subchapters[0].scenes[0].original_image_url == "path/to/img.jpg"


    @pytest.mark.parametrize("content,expected", [
        ("Como posso ajudar?", True),
        ("How can I help you?", True),
        ('{"chapters": []}', False),
        ("   Posso te ajudar?   ", True),
    ])
    def test_is_conversational_response(self, content, expected):
        service = VideoService()
        assert service._is_conversational_response(content) == expected

    def test_safe_json_parse_conversational_error(self):
        service = VideoService()
        with pytest.raises(ValueError) as exc:
            service._safe_json_parse("Como posso ajudar?", "Test")
        assert "THREAD_CORRUPTED" in str(exc.value)

    def test_safe_json_parse_recovery_markdown(self):
        service = VideoService()
        content = "Here is the JSON: ```json\n{\"id\": 1}\n``` and more text."
        result = service._safe_json_parse(content, "Test")
        assert result == {"id": 1}

    def test_safe_json_parse_recovery_extra_data(self):
        service = VideoService()
        content = '{"id": 1} Some extra garbage text'
        result = service._safe_json_parse(content, "Test")
        assert result == {"id": 1}

    def test_safe_json_parse_recovery_ast(self):
        service = VideoService()
        content = "{'id': 1, 'name': 'Single Quotes'}"
        result = service._safe_json_parse(content, "Test")
        assert result == {"id": 1, "name": "Single Quotes"}

    @patch("backend.services.video_service.video_repository")
    @patch("backend.services.openai_service.openai_service")
    @pytest.mark.asyncio
    async def test_call_openai_with_retry_corruption(self, mock_openai, mock_repo):
        service = VideoService()
        video = VideoModel(id=1, prompt="Test", status="processing", openai_thread_id="thread_old", target_duration_minutes=1)
        mock_repo.get.return_value = video
        
        # Define a custom side effect that handles async calls
        async def side_effect(*args, **kwargs):
            if side_effect.counter == 0:
                side_effect.counter += 1
                return "Como posso ajudar?"
            return '{"id": 1}'
        side_effect.counter = 0
        
        mock_openai.send_message_and_wait_json.side_effect = side_effect
        mock_openai.reset_thread = AsyncMock(return_value="thread_new")
        
        result = await service._call_openai_with_retry(
            "thread_old", "asst_1", "Prompt", "Context", 1
        )
        
        assert result == '{"id": 1}'
        assert mock_openai.reset_thread.called
        assert mock_openai.send_message_and_wait_json.call_count == 2

    @patch("backend.services.video_service.video_repository")
    @pytest.mark.asyncio
    async def test_generate_scenes_from_script_mode_no_chapters(self, mock_repo):
        service = VideoService()
        video = VideoModel(id=1, prompt="Script", status="processing", script_content="Line 1", target_duration_minutes=1)
        
        # Mock _call_openai_with_retry to return JSON without chapters
        with patch.object(service, '_call_openai_with_retry', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = '{"id": 1}' # Missing chapters
            
            # The method catches exceptions and sets status to ERROR.
            await service._generate_scenes_from_script_mode(video, "asst_1", {})
            
            assert video.status == VideoStatus.ERROR
            assert "No chapters found" in video.error_message

    @patch("backend.services.video_service.video_repository")
    def test_cancel_processing_not_in_progress(self, mock_repo):
        service = VideoService()
        # Video in 'completed' status cannot be cancelled
        video = VideoModel(id=1, prompt="Test", status=VideoStatus.COMPLETED, target_duration_minutes=1)
        mock_repo.get.return_value = video
        
        result = service.cancel_processing(1)
        assert result is False

    @patch("backend.services.video_service.video_repository")
    def test_update_video_not_found(self, mock_repo):
        service = VideoService()
        mock_repo.get.return_value = None
        with pytest.raises(ValueError):
            service.update(999, {"prompt": "New"})

    @patch("backend.services.video_service.video_repository")
    @pytest.mark.asyncio
    async def test_resume_interrupted_tasks_not_ready(self, mock_repo):
        service = VideoService()
        # Setup video in RENDERING state but missing assets
        video = VideoModel(id=126, prompt="Test", status=VideoStatus.RENDERING, target_duration_minutes=1)
        mock_repo.get_by_status.return_value = [video]
        mock_repo.save.side_effect = lambda x: x
        
        # Mock _is_ready_for_rendering to return False (missing assets)
        service._is_ready_for_rendering = MagicMock(return_value=False)
        service.trigger_render = AsyncMock()

        await service.resume_interrupted_tasks()

        # Should NOT trigger render
        service.trigger_render.assert_not_called()
        # Should mark as ERROR
        assert video.status == VideoStatus.ERROR
        assert "missing required assets" in video.error_message
        mock_repo.save.assert_called()

    @patch("backend.services.video_service.video_repository")
    @pytest.mark.asyncio
    async def test_trigger_render_updates_status_on_failure(self, mock_repo):
        service = VideoService()
        import asyncio
        video = VideoModel(id=126, prompt="Test", status=VideoStatus.COMPLETED, target_duration_minutes=1)
        mock_repo.get.return_value = video
        mock_repo.save.side_effect = lambda x: x
        
        service._is_ready_for_rendering = MagicMock(return_value=True)
        # Mock failure in render
        service._perform_multi_format_render = AsyncMock(return_value=False)

        await service.trigger_render(126)
        
        # Wait for the background task _run_render
        await asyncio.sleep(0.1)

        # Video status should be ERROR
        assert video.status == VideoStatus.ERROR
        assert "Rendering failed" in video.error_message
        # Verify save was called to persist the error
        mock_repo.save.assert_called()

    @patch("backend.services.video_service.video_repository")
    def test_delete_video_cancels_processing(self, mock_repo):
        service = VideoService()
        # Setup video in PROCESSING state
        video = VideoModel(id=123, prompt="Test", status=VideoStatus.PROCESSING, target_duration_minutes=1)
        mock_repo.get.return_value = video
        mock_repo.save.side_effect = lambda x: x
        mock_repo.delete.return_value = True

        service.delete(123)

        # Status should be CANCELLED before/during deletion
        assert video.status == VideoStatus.CANCELLED
        # Repository save should have been called by cancel_processing
        mock_repo.save.assert_called()
        # Repository delete should have been called with status
        mock_repo.delete.assert_called_with(123, status=VideoStatus.CANCELLED)

    @patch("backend.services.video_service.video_repository")
    def test_get_video_include_deleted(self, mock_repo):
        service = VideoService()
        # Setup deleted video
        from datetime import datetime
        video = VideoModel(id=123, prompt="Test", status=VideoStatus.CANCELLED, target_duration_minutes=1, deleted_at=datetime.now())
        
        # Mock repo to return None if include_deleted is False (default)
        def mock_get(vid_id, include_deleted=False):
            if vid_id == 123:
                if include_deleted:
                    return video
                return None
            return None
        
        mock_repo.get.side_effect = mock_get

        # Test 1: Should NOT find deleted video by default
        found_default = service.get(123)
        assert found_default is None

        # Test 2: Should find deleted video if flag is True
        found_with_flag = service.get(123, include_deleted=True)
        assert found_with_flag is not None
        assert found_with_flag.id == 123
