
import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.services.video_service import VideoService
from backend.models.video import VideoModel

@pytest.mark.asyncio
async def test_get_batch_fallback_search_terms():
    # Setup Mocks
    mock_openai = AsyncMock()
    mock_openai.send_message_and_wait_json.return_value = '{"terms": ["term1", "term2", "term3"]}'
    mock_openai.create_thread.return_value = "thread_123"
    mock_openai.get_or_create_assistant.return_value = "assistant_123"
    
    # Mock settings (needs to be patched where used or injected if service allows, 
    # but VideoService uses global settings. We can patch specific attributes or use DI if refactored)
    # The current VideoService accesses settings globally. 
    # However, since standard DI is preferred, let's see if we can inject it or just patch it locally.
    # For now, we will stick to patching settings as it is likely a global config,
    # BUT we will inject the services.
    
    mock_agent_service = MagicMock()
    mock_agent_service.get.return_value = None 
    mock_agent_service.list_all.return_value = []
    
    mock_repo = MagicMock()

    # Instantiate Service with DI
    video_service = VideoService(
        repo=mock_repo,
        openai_svc=mock_openai,
        agent_svc=mock_agent_service
    )
    
    # Video Model
    video = VideoModel(
        id=1, 
        agent_id="agent_1",
        prompt="test prompt",
        target_duration_minutes=1,
        status="pending"
    )
    
    # Execute
    terms = await video_service._get_batch_fallback_search_terms(
        video=video,
        original_query="bad query",
        context="some context",
        failed_terms=["failed1"]
    )
    
    # Verify
    assert len(terms) == 3
    assert terms[0] == "term1"
    assert video.openai_thread_id == "thread_123"
    
    mock_openai.send_message_and_wait_json.assert_called_once()
    call_args = mock_openai.send_message_and_wait_json.call_args
    assert call_args.kwargs['thread_id'] == "thread_123"

@pytest.mark.asyncio
async def test_get_batch_fallback_search_terms_json_failure():
    # Test handling of invalid JSON response
    mock_openai = AsyncMock()
    mock_openai.send_message_and_wait_json.return_value = "Not JSON"
    mock_openai.create_thread.return_value = "th_1"
    mock_openai.get_or_create_assistant.return_value = "asst_1"

    mock_agent_service = MagicMock()
    mock_agent_service.get.return_value = None

    video_service = VideoService(
        openai_svc=mock_openai,
        agent_svc=mock_agent_service,
        repo=MagicMock()
    )
    
    video = VideoModel(
        id=1,
        prompt="test",
        target_duration_minutes=1,
        status="pending"
    )
    
    terms = await video_service._get_batch_fallback_search_terms(
        video=video, 
        original_query="query",
        context="ctx"
    )
    assert terms == []
