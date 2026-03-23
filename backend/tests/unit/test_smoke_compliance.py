
import pytest
from backend.services.unsplash_service import unsplash_service
from backend.services.serpapi_service import serpapi_service
from backend.services.video_search_service import video_search_service
from backend.services.image_storage_service import image_storage_service
from backend.services.video_service import video_service
from backend.models.video import VideoModel
from backend.repositories.video_repository import video_repository

def test_services_import():
    """Smoke test to ensure all refactored services import without syntax errors."""
    assert unsplash_service is not None
    assert serpapi_service is not None
    assert video_search_service is not None
    assert image_storage_service is not None
    
def test_video_model_has_soft_delete():
    """Verify Soft Delete field in VideoModel."""
    assert "deleted_at" in VideoModel.model_fields
    
def test_repository_soft_delete_stub():
    """Verify Repository has delete method."""
    assert hasattr(video_repository, "delete")
