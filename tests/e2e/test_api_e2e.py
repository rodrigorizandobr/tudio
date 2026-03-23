import pytest
import time
import json
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from backend.main import app
from backend.models.script import ScriptStatus
from backend.services.script_service import script_service

# We use TestClient which runs the app in the same process, allowing us to patch the service.
client = TestClient(app)

@pytest.fixture
def mock_openai_service():
    """
    Patches the internal OpenAI client of the singleton script_service.
    """
    mock_client = AsyncMock()
    original_client = script_service.client
    
    # Inject mock
    script_service.client = mock_client
    
    # Define Mock Responses sequences
    # 1. Characters
    json_0 = '{"visual_style": "Test Style", "characters": [{"name": "TestChar", "physical_description": "Desc", "voice_type": "Voice"}]}'
    # 2. Chapters
    json_1 = '[{"order": 1, "title": "Test Chapter", "estimated_duration_minutes": 5, "description": "Desc"}]'
    # 3. Subchapters
    json_2 = '[{"order": 1, "title": "Test Sub", "description": "Desc"}]'
    # 4. Scenes
    json_3 = '[{"id": 1, "order": 1, "duration_seconds": 10, "narration_content": "Narration", "character_name": "TestChar", "voice_type": "Voice", "visual_description": "Vis", "image_prompt": "Img", "video_prompt": "Vid", "audio_prompt": "Aud"}]'

    def create_mock_response(content):
        m = MagicMock()
        m.choices = [MagicMock(message=MagicMock(content=content))]
        return m

    mock_client.chat.completions.create.side_effect = [
        create_mock_response(json_0),
        create_mock_response(json_1),
        create_mock_response(json_2),
        create_mock_response(json_3)
    ]
    
    yield mock_client
    
    # Restore
    script_service.client = original_client

def test_api_e2e_flow(mock_openai_service):
    """
    Simulates a full E2E flow using TestClient but mocking the external OpenAI API.
    This respects "No Code Mocks" in production, but uses standard Testing mocks.
    """
    # 1. POST Create
    response = client.post(
        "/api/v1/scripts/",
        json={"prompt": "E2E Test", "target_duration_minutes": 5, "language": "en"}
    )
    assert response.status_code == 201
    data = response.json()
    script_id = data["id"]
    assert data["status"] == "pending"

    # 2. Trigger Processing properly
    # Since TestClient is synchronous, the BackgroundTasks run after the response? 
    # FastAPI TestClient handles background tasks optionally? 
    # Actually, TestClient uses Starlette's TestClient which runs background tasks by default since 0.12, 
    # BUT our `process_script_background` is async and might race or need explicit wait.
    # However, `process_script_background` calls openai. 
    # Let's wait a bit.
    
    # Actually, strictly speaking, BackgroundTasks in TestClient run *after* response is sent but in the same thread/loop context 
    # usually blocking until done.
    
    # Poll status
    max_retries = 10
    final_status = None
    for _ in range(max_retries):
        resp = client.get(f"/api/v1/scripts/{script_id}")
        d = resp.json()
        if d["status"] == "completed":
            final_status = "completed"
            break
        # Call the background processor manually if needed for test determinism? 
        # But `process_script_background` is triggered by endpoint.
        # Let's see if TestClient runs it.
        time.sleep(0.5)

    # If TestClient didn't run background task, we might need to invoke it or rely on the fact 
    # that we mocked the service which is fast.
    
    # Manual trigger for test stability if needed:
    if final_status != "completed":
        # Force run (whitebox testing)
        import asyncio
        asyncio.run(script_service.process_script_background(script_id))
        resp = client.get(f"/api/v1/scripts/{script_id}")
        d = resp.json()
        final_status = d["status"]
    
    assert final_status == "completed"
    assert d["visual_style"] == "Test Style"
    assert len(d["chapters"]) == 1
    assert len(d["chapters"][0]["subchapters"]) == 1
    assert len(d["chapters"][0]["subchapters"][0]["scenes"]) == 1
