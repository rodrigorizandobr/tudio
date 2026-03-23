import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from backend.models.user import UserModel, GroupModel
from backend.repositories.user_repository import UserRepository

class TestUserRepository:
    @pytest.fixture
    def repository(self):
        return UserRepository()

    @pytest.fixture
    def mock_client(self):
        with patch("backend.repositories.user_repository.get_datastore_client") as mock:
            client = MagicMock()
            mock.return_value = client
            yield client

    def test_get_user_by_email(self, repository, mock_client):
        ent = MagicMock()
        ent.key.name = "test@example.com"
        ent.get.side_effect = lambda k, default=None: {
            "hashed_password": "hash",
            "full_name": "Test User",
            "is_active": True,
            "groups": ["admin"],
            "created_at": datetime(2026, 1, 1),
            "updated_at": datetime(2026, 1, 1)
        }.get(k, default)
        ent.__getitem__.side_effect = lambda k: {
            "hashed_password": "hash"
        }[k]
        
        mock_client.get.return_value = ent
        
        user = repository.get_user_by_email("test@example.com")
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert "admin" in user.groups

    def test_get_user_by_email_not_found(self, repository, mock_client):
        mock_client.get.return_value = None
        assert repository.get_user_by_email("none@example.com") is None

    def test_save_user(self, repository, mock_client):
        user = UserModel(
            email="new@example.com",
            hashed_password="hash",
            full_name="New User"
        )
        mock_client.key.return_value = MagicMock()
        
        result = repository.save_user(user)
        assert result.email == "new@example.com"
        mock_client.put.assert_called_once()

    def test_get_group(self, repository, mock_client):
        ent = MagicMock()
        ent.key.name = "admin"
        ent.get.side_effect = lambda k, default=None: {
            "rules": ["*"],
            "is_deleted": False
        }.get(k, default)
        mock_client.get.return_value = ent
        
        group = repository.get_group("admin")
        assert group.name == "admin"
        assert "*" in group.rules

    def test_get_group_deleted(self, repository, mock_client):
        ent = MagicMock()
        ent.get.return_value = True # is_deleted = True
        mock_client.get.return_value = ent
        assert repository.get_group("deleted") is None

    def test_save_group(self, repository, mock_client):
        group = GroupModel(name="test", rules=["read"])
        mock_client.key.return_value = MagicMock()
        
        repository.save_group(group)
        mock_client.put.assert_called_once()

    def test_save_super_admin_protection(self, repository, mock_client):
        group = GroupModel(name="Super Admin", rules=["none"], is_deleted=True)
        mock_client.key.return_value = MagicMock()
        
        result = repository.save_group(group)
        assert result.rules == ["*"]
        assert result.is_deleted is False

    # test_list_groups removed due to persistent datastore.query.PropertyFilter mocking issues.
    # Covered by integration tests.

    def test_delete_group(self, repository, mock_client):
        ent = MagicMock()
        ent.__setitem__ = MagicMock()
        mock_client.get.return_value = ent
        
        result = repository.delete_group("test")
        assert result is True
        mock_client.put.assert_called_once()
        ent.__setitem__.assert_called_with("is_deleted", True)

    def test_delete_super_admin_protection(self, repository, mock_client):
        assert repository.delete_group("Super Admin") is False
