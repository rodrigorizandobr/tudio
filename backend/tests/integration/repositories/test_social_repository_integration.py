import pytest
from backend.repositories.social_repository import social_repository
from backend.models.social import SocialAccountModel, SocialChannelModel, SocialProvider
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
    with patch("backend.repositories.social_repository.get_datastore_client", return_value=fake_db):
        yield

@pytest.fixture
def clean_datastore(fake_db):
    yield
    fake_db._storage.clear()

# --- Tests ---

def test_create_and_get_social_account(clean_datastore):
    """Test CRUD basics: create and retrieve social account"""
    # Create account
    account = SocialAccountModel(
        user_email="test@example.com",
        provider=SocialProvider.GOOGLE,
        provider_account_id="google123",
        email="social@gmail.com",
        name="Test User",
        access_token="token123",
        scopes=["youtube.upload"]
    )
    
    saved = social_repository.save_account(account)
    
    # Verify ID assigned
    assert saved.id is not None
    assert saved.email == "social@gmail.com"
    
    # Retrieve
    retrieved = social_repository.get_account_by_id(saved.id)
    assert retrieved is not None
    assert retrieved.id == saved.id
    assert retrieved.provider == SocialProvider.GOOGLE
    assert retrieved.name == "Test User"

def test_list_accounts_by_user(clean_datastore):
    """Test listing accounts by user email"""
    # Create multiple accounts for same user
    account1 = SocialAccountModel(
        user_email="user@example.com",
        provider=SocialProvider.GOOGLE,
        provider_account_id="google1",
        email="social1@gmail.com",
        name="Account 1",
        access_token="token1"
    )
    
    account2 = SocialAccountModel(
        user_email="user@example.com",
        provider=SocialProvider.GOOGLE,
        provider_account_id="google2",
        email="social2@gmail.com",
        name="Account 2",
        access_token="token2"
    )
    
    # Different user
    account3 = SocialAccountModel(
        user_email="other@example.com",
        provider=SocialProvider.GOOGLE,
        provider_account_id="google3",
        email="other@gmail.com",
        name="Other User",
        access_token="token3"
    )
    
    social_repository.save_account(account1)
    social_repository.save_account(account2)
    social_repository.save_account(account3)
    
    # List for specific user
    user_accounts = social_repository.list_accounts("user@example.com")
    assert len(user_accounts) == 2
    emails = [a.email for a in user_accounts]
    assert "social1@gmail.com" in emails
    assert "social2@gmail.com" in emails
    assert "other@gmail.com" not in emails

def test_get_account_by_email_and_provider(clean_datastore):
    """Test finding account by email and provider"""
    # Create account
    account = SocialAccountModel(
        user_email="user@example.com",
        provider=SocialProvider.GOOGLE,
        provider_account_id="google123",
        email="unique@gmail.com",
        name="Unique User",
        access_token="token123"
    )
    social_repository.save_account(account)
    
    # Find by email and provider
    found = social_repository.get_account_by_email("unique@gmail.com", SocialProvider.GOOGLE)
    assert found is not None
    assert found.email == "unique@gmail.com"
    assert found.provider == SocialProvider.GOOGLE
    
    # Not found - wrong email
    not_found = social_repository.get_account_by_email("wrong@gmail.com", SocialProvider.GOOGLE)
    assert not_found is None

def test_create_and_list_channels(clean_datastore):
    """Test CRUD for channels"""
    # First create account
    account = SocialAccountModel(
        user_email="user@example.com",
        provider=SocialProvider.GOOGLE,
        provider_account_id="google123",
        email="channel_owner@gmail.com",
        name="Channel Owner",
        access_token="token123"
    )
    saved_account = social_repository.save_account(account)
    
    # Create channels for this account
    channel1 = SocialChannelModel(
        social_account_id=saved_account.id,
        channel_id="UC123",
        title="Main Channel",
        subscriber_count=1000,
        is_active=True
    )
    
    channel2 = SocialChannelModel(
        social_account_id=saved_account.id,
        channel_id="UC456",
        title="Secondary Channel",
        subscriber_count=500,
        is_active=True
    )
    
    saved_ch1 = social_repository.save_channel(channel1)
    saved_ch2 = social_repository.save_channel(channel2)
    
    # Verify IDs
    assert saved_ch1.id is not None
    assert saved_ch2.id is not None
    
    # List channels by account
    channels = social_repository.get_channels_by_account(saved_account.id)
    assert len(channels) == 2
    titles = [c.title for c in channels]
    assert "Main Channel" in titles
    assert "Secondary Channel" in titles
    
    # Get channel by ID
    retrieved_ch = social_repository.get_channel_by_id(saved_ch1.id)
    assert retrieved_ch is not None
    assert retrieved_ch.title == "Main Channel"
    assert retrieved_ch.subscriber_count == 1000

def test_delete_channel(clean_datastore):
    """Test deleting channel"""
    # Create account
    account = SocialAccountModel(
        user_email="user@example.com",
        provider=SocialProvider.GOOGLE,
        provider_account_id="google123",
        email="test@gmail.com",
        name="Test User",
        access_token="token123"
    )
    saved_account = social_repository.save_account(account)
    
    # Create channel
    channel = SocialChannelModel(
        social_account_id=saved_account.id,
        channel_id="UC789",
        title="To Delete",
        is_active=True
    )
    saved_channel = social_repository.save_channel(channel)
    channel_id = saved_channel.id
    
    # Verify exists
    assert social_repository.get_channel_by_id(channel_id) is not None
    
    # Delete
    social_repository.delete_channel(channel_id)
    
    # Verify deleted
    deleted = social_repository.get_channel_by_id(channel_id)
    assert deleted is None

def test_update_account_tokens(clean_datastore):
    """Test updating account access tokens"""
    # Create account
    account = SocialAccountModel(
        user_email="user@example.com",
        provider=SocialProvider.GOOGLE,
        provider_account_id="google123",
        email="test@gmail.com",
        name="Test User",
        access_token="old_token",
        refresh_token="old_refresh"
    )
    saved = social_repository.save_account(account)
    account_id = saved.id
    
    # Update tokens
    saved.access_token = "new_token"
    saved.refresh_token = "new_refresh"
    saved.token_expiry = datetime(2025, 12, 31)
    
    updated = social_repository.save_account(saved)
    
    # Verify ID unchanged
    assert updated.id == account_id
    
    # Retrieve and verify
    retrieved = social_repository.get_account_by_id(account_id)
    assert retrieved.access_token == "new_token"
    assert retrieved.refresh_token == "new_refresh"
    assert retrieved.token_expiry == datetime(2025, 12, 31)
