import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from backend.models.video import VideoModel, VideoStatus
from backend.repositories.video_repository import VideoRepository

class MockEntity(dict):
    """
    Simulates google.cloud.datastore.Entity
    """
    def __init__(self, key=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.key = key

class TestVideoRepository:
    @pytest.fixture
    def repository(self):
        return VideoRepository()

    @pytest.fixture
    def mock_client(self):
        with patch("backend.repositories.video_repository.get_datastore_client") as mock:
            client = MagicMock()
            mock.return_value = client
            yield client

    def test_save_new_video(self, repository, mock_client):
        video = VideoModel(prompt="Test", status=VideoStatus.PENDING, target_duration_minutes=1)
        
        mock_key = MagicMock()
        mock_key.id = 123
        mock_client.key.return_value = mock_key
        
        result = repository.save(video)
        
        assert result.id == 123
        mock_client.put.assert_called_once()
        args, _ = mock_client.put.call_args
        entity = args[0]
        assert entity["prompt"] == "Test"
        assert "full_json" in entity

    def test_save_existing_video(self, repository, mock_client):
        video = VideoModel(id=123, prompt="Test", status=VideoStatus.PENDING, target_duration_minutes=1)
        
        mock_client.key.return_value = MagicMock()
        
        result = repository.save(video)
        
        assert result.id == 123
        mock_client.put.assert_called_once()

    def test_save_safeguard_prevents_loss(self, repository, mock_client):
        # Video with NO chapters but status is NOT pending
        video = VideoModel(id=123, prompt="Test", status=VideoStatus.COMPLETED, target_duration_minutes=1)
        video.chapters = []
        
        # Mock existing entity in DB that HAS chapters (using MockEntity)
        mock_key = MagicMock()
        mock_key.id = 123
        
        existing_ent = MockEntity(key=mock_key)
        existing_ent["full_json"] = '{"id": 123, "prompt": "Safe", "status": "completed", "target_duration_minutes": 1, "chapters": [{"id": 1, "order": 1, "title": "Ch1", "description": "D", "estimated_duration_minutes": 1.0, "subchapters": []}]}'
        
        mock_client.get.return_value = existing_ent
        mock_client.key.return_value = mock_key
        
        result = repository.save(video)
        
        # Should NOT have called put
        mock_client.put.assert_not_called()
        # Should return the reconstructed video with chapters
        assert len(result.chapters) == 1

    def test_get_video(self, repository, mock_client):
        mock_key = MagicMock()
        mock_key.id = 123
        
        ent = MockEntity(key=mock_key)
        ent["full_json"] = '{"id": 123, "prompt": "Found", "status": "pending", "target_duration_minutes": 1}'
        
        mock_client.get.return_value = ent
        
        result = repository.get(123)
        assert result.id == 123
        assert result.prompt == "Found"

    def test_get_video_not_found(self, repository, mock_client):
        mock_client.get.return_value = None
        assert repository.get(999) is None

    def test_get_video_soft_deleted(self, repository, mock_client):
        mock_key = MagicMock()
        mock_key.id = 123
        
        ent = MockEntity(key=mock_key)
        # JSON valid but marked as deleted
        ent["full_json"] = '{"id": 123, "prompt": "Del", "status": "pending", "target_duration_minutes": 1, "deleted_at": "2026-01-01T00:00:00"}'
        
        mock_client.get.return_value = ent
        
        assert repository.get(123) is None

    def test_list_all(self, repository, mock_client):
        mock_key = MagicMock()
        mock_key.id = 123
        
        ent = MockEntity(key=mock_key)
        ent["full_json"] = '{"id": 123, "prompt": "A", "status": "pending", "target_duration_minutes": 1, "created_at": "2026-02-16T00:00:00"}'
        
        mock_query = MagicMock()
        mock_client.query.return_value = mock_query
        mock_query.fetch.return_value = [ent]
        
        videos = repository.list_all()
        assert len(videos) == 1
        assert videos[0].prompt == "A"

    def test_delete_video(self, repository, mock_client):
        mock_key = MagicMock()
        mock_key.id = 123
        
        ent = MockEntity(key=mock_key)
        ent["full_json"] = '{"id": 123, "prompt": "To be deleted", "status": "pending", "target_duration_minutes": 1}'
        
        mock_client.get.return_value = ent
        mock_client.put.return_value = None
        
        result = repository.delete(123)
        
        assert result is True
        # Datastore soft delete: client.put() is called twice (once per attribute, once for full_json)
        assert mock_client.put.call_count >= 1
        # Verify deleted_at was set on the entity
        assert ent["deleted_at"] is not None

    def test_get_by_status(self, repository, mock_client):
        mock_key = MagicMock()
        mock_key.id = 123
        
        ent = MockEntity(key=mock_key)
        ent["full_json"] = '{"id": 123, "status": "processing", "prompt": "P", "target_duration_minutes": 1}'
        
        mock_query = MagicMock()
        mock_client.query.return_value = mock_query
        mock_query.fetch.return_value = [ent]
        
        videos = repository.get_by_status(["processing"])
        assert len(videos) == 1
        assert videos[0].status == "processing"
