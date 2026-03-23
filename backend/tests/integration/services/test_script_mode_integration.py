import pytest
import json
from unittest.mock import AsyncMock, patch
from backend.services.video_service import video_service
from backend.schemas.video import VideoCreate
from backend.models.video import VideoStatus, VideoModel
from backend.repositories.video_repository import video_repository

@pytest.mark.asyncio
async def test_generate_scenes_from_script_mode_integration():
    """
    Tests the hierarchical generation logic in VideoService.
    Mocks OpenAI but verifies the model updates and structure parsing.
    """
    script_text = "Linha 1 do roteiro\nLinha 2 do roteiro"
    video_in = VideoCreate(
        prompt="Integração Roteiro",
        language="pt-br",
        target_duration_minutes=1,
        script_content=script_text
    )
    
    video = video_service.create(video_in)
    
    # Mock for OpenAI response following our hierarchical schema
    mock_response = {
        "chapters": [
            {
                "id": 1, "order": 1, "title": "Capítulo Único", "description": "Desc",
                "subchapters": [
                    {
                        "id": 1, "order": 1, "title": "Subcap 1", "description": "Desc sub",
                        "scenes": [
                            {
                                "id": 1, "order": 1, "narration_content": "Linha 1 do roteiro",
                                "visual_description": "Visual 1", "image_prompt": "Prompt 1"
                            },
                            {
                                "id": 2, "order": 2, "narration_content": "Linha 2 do roteiro",
                                "visual_description": "Visual 2", "image_prompt": "Prompt 2"
                            }
                        ]
                    }
                ]
            }
        ]
    }

    with patch.object(video_service, '_call_openai_with_retry', AsyncMock(return_value=json.dumps(mock_response))):
        # We also need to mock or ensure context initialization doesn't fail
        # This test focuses on the _generate_scenes_from_script_mode method
        await video_service._generate_scenes_from_script_mode(video, "mock_asst", {"topic": "test"})
        
    # Validation
    processed_video = video_repository.get(video.id)
    assert len(processed_video.chapters) == 1
    assert len(processed_video.chapters[0].subchapters) == 1
    assert len(processed_video.chapters[0].subchapters[0].scenes) == 2
    assert processed_video.chapters[0].subchapters[0].scenes[0].image_prompt == "Prompt 1"
    assert processed_video.status == VideoStatus.PROCESSING
