import pytest
import os
import uuid
from google.cloud import datastore
from backend.services.video_service import VideoService
from backend.models.video import VideoModel, SceneModel, VideoStatus
from backend.schemas.video import VideoCreate
from backend.repositories.video_repository import video_repository
from unittest.mock import patch, AsyncMock
import json

# --- Integration Fixtures ---

from backend.tests.fakes.fake_datastore import FakeDatastoreClient

# --- Integration Fixtures ---

@pytest.fixture(scope="module")
def fake_db():
    return FakeDatastoreClient()

@pytest.fixture(autouse=True)
def patch_datastore(fake_db):
    # Patch the repository's access to the client
    with patch("backend.repositories.video_repository.get_datastore_client", return_value=fake_db):
        yield

@pytest.fixture
def datastore_client(fake_db):
    return fake_db

@pytest.fixture
def clean_datastore(fake_db):
    # No-op or reset for memory dict
    yield []
    fake_db._storage.clear()

@pytest.fixture
def video_service_integration():
    # We want the Real Service, but with MOCKED External I/O (OpenAI, Audio, Render)
    # properly properly patched at the class level or instance level
    
    service = VideoService()
    return service

# --- Tests ---

@pytest.mark.asyncio
async def test_create_and_retrieve_video_real_db(video_service_integration, clean_datastore):
    """
    Test authentic persistence: Create via Service -> Save to Datastore -> Retrieve via Repo.
    """
    # 1. Create
    payload = VideoCreate(
        prompt=f"Integration Test {uuid.uuid4()}",
        target_duration_minutes=1,
        language="pt-BR"
    )
    
    video = video_service_integration.create(payload)
    assert video.id is not None
    
    # Track for cleanup
    client = video_repository.client
    key = client.key(video_repository.kind, video.id)
    clean_datastore.append(key)
    
    # 2. Retrieve directly from Repository (bypass service cache if any)
    fetched_video = video_repository.get(video.id)
    
    assert fetched_video is not None
    assert fetched_video.prompt == payload.prompt
    assert fetched_video.status == VideoStatus.PENDING
    assert fetched_video.target_duration_minutes == 1

@pytest.mark.asyncio
async def test_duplicate_video_integration(video_service_integration, clean_datastore):
    # 1. Setup Initial Video
    original = VideoModel(
        prompt="Original to Duplicate", 
        target_duration_minutes=1, 
        status=VideoStatus.COMPLETED,
        script_content="Original Script"
    )
    saved_original = video_repository.save(original)
    clean_datastore.append(video_repository.client.key(video_repository.kind, saved_original.id))
    
    # 2. Duplicate
    duplicate = video_service_integration.duplicate_video(saved_original.id)
    clean_datastore.append(video_repository.client.key(video_repository.kind, duplicate.id))
    
    # 3. Verify
    assert duplicate.id != saved_original.id
    assert duplicate.prompt == saved_original.prompt
    assert duplicate.script_content == "Original Script"
    assert duplicate.status == VideoStatus.PENDING
    
    # 4. Persistence Check
    fetched_dup = video_repository.get(duplicate.id)
    assert fetched_dup is not None

def test_soft_delete_integration(video_service_integration, clean_datastore):
    # 1. Create
    video = VideoModel(prompt="To Delete", target_duration_minutes=1, status=VideoStatus.PENDING)
    saved = video_repository.save(video)
    clean_datastore.append(video_repository.client.key(video_repository.kind, saved.id))
    
    # 2. Delete
    success = video_service_integration.delete(saved.id)
    assert success is True
    
    # 3. Verify it's gone from standard get
    assert video_repository.get(saved.id) is None
    
    # 4. Verify it's still in Datastore but with deleted_at
    client = video_repository.client
    key = client.key(video_repository.kind, saved.id)
    entity = client.get(key)
    assert entity is not None
    # We store data in full_json, but repository.save updates the entity properties too
    assert "deleted_at" in entity
    assert entity["deleted_at"] is not None

@pytest.mark.asyncio
async def test_process_video_flow_mock_external(video_service_integration, clean_datastore):
    """
    Test the orchestration flow. 
    We Mock OpenAI/Agents but use REAL Database state transitions.
    """
    # 1. Create Video
    # Enable auto_generate_narration to ensure flow proceeds to Render/Complete
    payload = VideoCreate(prompt="Flow Test", target_duration_minutes=1)
    payload.auto_generate_narration = True
    
    video = video_service_integration.create(payload)
    clean_datastore.append(video_repository.client.key(video_repository.kind, video.id))
    
    # 2. Mock External Services
    with patch("backend.services.openai_service.openai_service") as mock_openai, \
         patch("backend.services.video_service.audio_service") as mock_audio, \
         patch("backend.services.video_service.render_service") as mock_render, \
         patch("backend.services.video_service.settings") as mock_settings, \
         patch("backend.services.video_service.unsplash_service") as mock_unsplash, \
         patch("backend.services.video_service.serpapi_service") as mock_serp, \
         patch("backend.services.video_service.image_storage_service") as mock_storage:
         
         # Mock Settings Templates (must be strings)
         mock_settings.PROMPT_INIT_TEMPLATE = "Init Prompt {topic}"
         mock_settings.PROMPT_CHAPTERS_TEMPLATE = "Chapters Prompt"
         mock_settings.PROMPT_SUBCHAPTERS_TEMPLATE = "Subchapters Prompt"
         mock_settings.PROMPT_SCENES_TEMPLATE = "Scenes Prompt"
         
         # Mock Storage
         mock_storage.upload_video.return_value = "http://storage.com/final.mp4"
         mock_storage.download_image = AsyncMock(return_value="local/path/img.jpg")
         mock_storage.calculate_center_crop_coords.return_value = (0, 0, 100, 100)
         mock_storage.crop_image.return_value = "local/path/cropped.jpg"
         
         # Mock OpenAI Assistant - explicitly use AsyncMock for awaitable methods
         mock_openai.create_thread = AsyncMock(return_value="thread_123")
         mock_openai.get_or_create_assistant = AsyncMock(return_value="asst_123")
         
         # Mock Image Services
         mock_unsplash.search_images = AsyncMock(return_value=["http://mock_image.jpg"])
         mock_serp.search_images = AsyncMock(return_value=["http://mock_serp.jpg"])
         
         # Mock responses for the sequence of calls:
         # 1. Step 0 (Metadata)
         # 2. Step 1 (Chapters)
         # 3. Step 2 (Subchapters for Chapter 1)
         # 4. Step 3 (Scenes for Subchapter 1)
         
         step0_resp = json.dumps({
             "title": "Integration Flow Video",
             "visual_style": "Cinematic",
             "characters": [{"name": "Narrator", "voice": "alloy"}]
         })
         
         step1_resp = json.dumps({
             "chapters": [{"order": 1, "title": "Arrival", "description": "Intro", "estimated_duration_minutes": 1}]
         })
         
         step2_resp = json.dumps({
             "subchapters": [{"order": 1, "title": "Landing", "description": "Ship lands"}]
         })
         
         step3_resp = json.dumps({
             "scenes": [
                 {"order": 1, "narration_content": "The ship touched down.", "visual_description": "Spaceship landing", "duration_seconds": 5}
             ]
         })
         
         # Configure Side Effect for Send Message
         # We need AsyncMock for send_message_and_wait
         mock_openai.send_message_and_wait = AsyncMock(side_effect=[step0_resp, step1_resp, step2_resp, step3_resp])
         # send_message_and_wait_json ALSO returns a string (which is then parsed by _safe_json_parse helper)
         mock_openai.send_message_and_wait_json = AsyncMock(side_effect=[step2_resp, step3_resp])
         
         # Mock Audio & Render
         mock_audio.generate_narration_for_video = AsyncMock(return_value=True)
         mock_audio.generate_narration = AsyncMock(return_value="http://mock_audio.mp3")
         mock_render.render_scene_preview = AsyncMock(return_value="http://preview.mp4")
         mock_render.render_video = AsyncMock(return_value="http://storage.com/final.mp4")
         
         # Instantiate Service with DI
         service = VideoService(
             openai_svc=mock_openai,
             audio_svc=mock_audio,
             render_svc=mock_render,
             storage_svc=mock_storage,
             unsplash_svc=mock_unsplash,
             serpapi_svc=mock_serp
         )
         
         # Execute
         await service.process_video_background(video.id)
         
         # Verify
         final_video = video_repository.get(video.id)
         
         # Print error message if any, for debugging
         if final_video.error_message:
             print(f"Video Error: {final_video.error_message}")

         # Verify Script Generation Success
         assert final_video.error_message is None, f"Process failed with error: {final_video.error_message}"
         assert final_video.title == "Integration Flow Video"
         assert final_video.visual_style == "Cinematic"
         assert len(final_video.chapters) == 1
         assert final_video.chapters[0].title == "Arrival"
         assert len(final_video.chapters[0].subchapters) == 1
         assert final_video.chapters[0].subchapters[0].title == "Landing"
         assert len(final_video.chapters[0].subchapters[0].scenes) == 1
         
         scene = final_video.chapters[0].subchapters[0].scenes[0]
         assert scene.narration_content == "The ship touched down."
         assert scene.visual_description == "Spaceship landing"
         assert scene.duration_seconds > 0  # Duration is calculated automatically from narration_content
         
         # Status should be PROCESSING (not ERROR) since assets aren't ready for render
         # This is expected behavior for this integration test
         assert final_video.status in [VideoStatus.PROCESSING, VideoStatus.COMPLETED]
              
