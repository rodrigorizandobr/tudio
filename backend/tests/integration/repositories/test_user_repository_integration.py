import pytest
from backend.repositories.user_repository import user_repository
from backend.models.user import UserModel, GroupModel
from unittest.mock import patch
from datetime import datetime

# --- Integration Fixtures ---
from backend.tests.fakes.fake_datastore import FakeDatastoreClient

@pytest.fixture(scope="module")
def fake_db():
    return FakeDatastoreClient()

@pytest.fixture(autouse=True)
def patch_datastore(fake_db):
    # Patch the repository's access to the client
    with patch("backend.repositories.user_repository.get_datastore_client", return_value=fake_db):
        yield

@pytest.fixture
def clean_datastore(fake_db):
    yield
    fake_db._storage.clear()

# --- Tests ---

def test_create_and_get_user(clean_datastore):
    """Test CRUD basics: create and retrieve user"""
    # Create user
    user = UserModel(
        email="test@example.com",
        hashed_password="hashed_pw_123",
        full_name="Test User",
        is_active=True,
        groups=["editor"]
    )
    
    saved = user_repository.save_user(user)
    
    # Verify email is key
    assert saved.email == "test@example.com"
    
    # Retrieve
    retrieved = user_repository.get_user_by_email("test@example.com")
    assert retrieved is not None
    assert retrieved.email == "test@example.com"
    assert retrieved.full_name == "Test User"
    assert retrieved.hashed_password == "hashed_pw_123"
    assert "editor" in retrieved.groups

def test_update_user(clean_datastore):
    """Test updating existing user"""
    # Create
    user = UserModel(
        email="update@example.com",
        hashed_password="old_hash",
        full_name="Original Name"
    )
    saved = user_repository.save_user(user)
    
    # Update
    saved.full_name = "New Name"
    saved.hashed_password = "new_hash"
    saved.groups = ["admin", "editor"]
    
    updated = user_repository.save_user(saved)
    
    # Retrieve and verify
    retrieved = user_repository.get_user_by_email("update@example.com")
    assert retrieved.full_name == "New Name"
    assert retrieved.hashed_password == "new_hash"
    assert "admin" in retrieved.groups
    assert "editor" in retrieved.groups

def test_user_not_found(clean_datastore):
    """Test getting non-existent user"""
    result = user_repository.get_user_by_email("nonexistent@example.com")
    assert result is None

def test_user_deactivation(clean_datastore):
    """Test deactivating user"""
    # Create active user
    user = UserModel(
        email="active@example.com",
        hashed_password="hash123",
        is_active=True
    )
    user_repository.save_user(user)
    
    # Deactivate
    user.is_active = False
    user_repository.save_user(user)
    
    # Verify
    retrieved = user_repository.get_user_by_email("active@example.com")
    assert retrieved.is_active is False

def test_create_and_get_group(clean_datastore):
    """Test CRUD for groups"""
    # Create group
    group = GroupModel(
        name="editors",
        rules=["video:create", "video:edit"],
        is_deleted=False
    )
    
    saved = user_repository.save_group(group)
    assert saved.name == "editors"
    
    # Retrieve
    retrieved = user_repository.get_group("editors")
    assert retrieved is not None
    assert retrieved.name == "editors"
    assert "video:create" in retrieved.rules

def test_list_groups(clean_datastore):
    """Test listing active groups"""
    # Create multiple groups
    group1 = GroupModel(name="admins", rules=["*"], is_deleted=False)
    group2 = GroupModel(name="viewers", rules=["video:read"], is_deleted=False)
    group3 = GroupModel(name="deleted_group", rules=[], is_deleted=True)
    
    user_repository.save_group(group1)
    user_repository.save_group(group2)
    user_repository.save_group(group3)
    
    # List should only return active groups
    groups = user_repository.list_groups()
    group_names = [g.name for g in groups]
    
    assert "admins" in group_names
    assert "viewers" in group_names
    assert "deleted_group" not in group_names

def test_delete_group_soft_delete(clean_datastore):
    """Test soft delete for groups"""
    # Create group
    group = GroupModel(name="to_delete", rules=["test:rule"])
    user_repository.save_group(group)
    
    # Verify exists
    assert user_repository.get_group("to_delete") is not None
    
    # Soft delete
    result = user_repository.delete_group("to_delete")
    assert result is True
    
    # Verify soft deleted (get returns None for deleted groups)
    deleted = user_repository.get_group("to_delete")
    assert deleted is None

def test_super_admin_protection(clean_datastore):
    """Test that Super Admin group cannot be deleted or modified"""
    # Create Super Admin group
    super_admin = GroupModel(
        name="Super Admin",
        rules=["custom:rule"]  # Try to set custom rules
    )
    
    saved = user_repository.save_group(super_admin)
    
    # Should be forced to ["*"]
    assert saved.rules == ["*"]
    
    # Try to delete
    result = user_repository.delete_group("Super Admin")
    assert result is False
    
    # Verify still exists
    retrieved = user_repository.get_group("Super Admin")
    assert retrieved is not None
    assert retrieved.rules == ["*"]

def test_user_with_multiple_groups(clean_datastore):
    """Test user membership in multiple groups"""
    # Create user with multiple groups
    user = UserModel(
        email="multi@example.com",
        hashed_password="hash",
        groups=["admin", "editor", "viewer"]
    )
    
    user_repository.save_user(user)
    
    # Retrieve and verify
    retrieved = user_repository.get_user_by_email("multi@example.com")
    assert len(retrieved.groups) == 3
    assert "admin" in retrieved.groups
    assert "editor" in retrieved.groups
    assert "viewer" in retrieved.groups
