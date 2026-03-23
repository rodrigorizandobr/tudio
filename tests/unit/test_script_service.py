import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch
from backend.services.script_service import ScriptService
from backend.schemas.script import ScriptCreate
from backend.models.script import ScriptStatus

@pytest.fixture
def mock_openai():
    # Return a fresh AsyncMock
    return AsyncMock()

def test_calculate_duration():
    service = ScriptService()
    # 0 words
    assert service._calculate_duration("") == 0
    # 1 word = 0.4s -> 0
    assert service._calculate_duration("Hello") == 0
    # 2 words = 0.8s -> 1
    assert service._calculate_duration("Hello world") == 1
    # 150 words = 60s
    text_150 = "word " * 150
    assert service._calculate_duration(text_150) == 60
    # 75 words = 30s
    text_75 = "word " * 75
    assert service._calculate_duration(text_75) == 30

@pytest.mark.asyncio
async def test_service_background_processing(mock_openai):
    # Instantiate service inside test to use the mocked AsyncOpenAI
    # We patch settings directly since it's already loaded
    with patch("backend.core.configs.settings.OPENAI_API_KEY", "test-key"):
        service = ScriptService() 
        service.client = mock_openai # Ensure our mock is used
    
    # Define Mock Responses in sequence of turns
    # 1. Characters & Style
    json_0 = '{"visual_style": "Dark Mode", "characters": [{"name": "Neo", "physical_description": "Tall", "voice_type": "Deep"}]}'
    # 2. Chapters
    json_1 = '[{"order": 1, "title": "C1", "estimated_duration_minutes": 5, "description": "D1"}]'
    # 3. Subchapters (for C1)
    json_2 = '[{"order": 1, "title": "Sub1", "description": "SubDesc"}]'
    # 4. Scenes (for Sub1)
    json_3 = '[{"id": 1, "order": 1, "duration_seconds": 10, "narration_content": "Wake up", "character_name": "Neo", "voice_type": "Deep", "visual_description": "Matrix", "image_prompt": "Code", "video_prompt": "Rain", "audio_prompt": "Thunder"}]'

    # Create mock response objects
    def create_mock_response(content):
        m = MagicMock()
        m.choices = [MagicMock(message=MagicMock(content=content))]
        return m

    # side_effect for the async call
    mock_openai.chat.completions.create.side_effect = [
        create_mock_response(json_0),
        create_mock_response(json_1),
        create_mock_response(json_2),
        create_mock_response(json_3)
    ]

    # Setup Script
    script_in = ScriptCreate(prompt="Unit Test Deep AI", target_duration_minutes=5, language="en")
    script = service.create(script_in)
    
    # Run Background Task (Await it)
    await service.process_script_background(script.id)
    
    # Assertions
    updated_script = service.get(script.id)
    assert updated_script.status == ScriptStatus.COMPLETED
    assert updated_script.progress == 100.0
    
    # Verify Hierarchy
    assert updated_script.visual_style == "Dark Mode"
    assert len(updated_script.characters) == 1
    assert updated_script.characters[0].name == "Neo"
    
    assert len(updated_script.chapters) == 1
    assert updated_script.chapters[0].title == "C1"
    
    assert len(updated_script.chapters[0].subchapters) == 1
    assert updated_script.chapters[0].subchapters[0].title == "Sub1"
    
    assert len(updated_script.chapters[0].subchapters[0].scenes) == 1
    scene = updated_script.chapters[0].subchapters[0].scenes[0]
    # "Wake up" = 2 words * 0.4 = 0.8 -> 1
    assert scene.narration_content == "Wake up"
    assert scene.duration_seconds == 1
    assert updated_script.chapters[0].estimated_duration_minutes == round(1/60, 2)
    assert scene.video_prompt == "Rain"

@pytest.mark.asyncio
async def test_service_api_error(mock_openai):
    with patch("backend.core.configs.settings.OPENAI_API_KEY", "test-key"):
        service = ScriptService()
        service.client = mock_openai

    # Simulate API Error
    mock_openai.chat.completions.create.side_effect = Exception("API Down")
    
    script_in = ScriptCreate(prompt="Error Test", target_duration_minutes=5)
    script = service.create(script_in)
    
    await service.process_script_background(script.id)
    
    updated = service.get(script.id)
    assert updated.status == ScriptStatus.ERROR
    assert "API Down" in updated.error_message
