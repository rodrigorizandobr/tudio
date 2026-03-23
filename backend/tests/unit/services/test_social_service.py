import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from backend.services.social_service import SocialService
from backend.models.social import SocialAccountModel, SocialChannelModel, SocialProvider
from googleapiclient.errors import HttpError
import json

@pytest.fixture
def social_service():
    return SocialService()

@pytest.fixture
def mock_account():
    return SocialAccountModel(
        id=1,
        user_email="user@test.com",
        provider=SocialProvider.GOOGLE,
        provider_account_id="123",
        email="acc@test.com",
        name="Test Acc",
        photo_url="http://photo.url",
        access_token="token",
        refresh_token="ref",
        token_expiry=1234567890,
        scopes=["scope1"]
    )

def test_get_authorization_url(social_service):
    with patch.object(social_service, "_get_flow") as mock_flow_method:
        mock_flow = MagicMock()
        mock_flow.authorization_url.return_value = ("http://auth.url", "state")
        mock_flow_method.return_value = mock_flow
        
        url = social_service.get_authorization_url("state_abc")
        
        assert url == "http://auth.url"
        mock_flow.authorization_url.assert_called()

@pytest.mark.asyncio
async def test_handle_callback_new_account(social_service):
    """Test handle_callback creates new account when not exists"""
    with patch.object(social_service, "_get_flow") as mock_get_flow, \
         patch("backend.services.social_service.build") as mock_build, \
         patch("backend.services.social_service.social_repository") as mock_repo, \
         patch.object(social_service, "sync_channels", new_callable=AsyncMock) as mock_sync:
         
         mock_flow = MagicMock()
         mock_flow.credentials.token = "new_token"
         mock_flow.credentials.refresh_token = "new_refresh"
         mock_flow.credentials.expiry = 999999
         mock_get_flow.return_value = mock_flow
         
         mock_service = MagicMock()
         mock_service.userinfo.return_value.get.return_value.execute.return_value = {
             "email": "acc@test.com", "id": "123", "picture": "pic", "name": "Name"
         }
         mock_build.return_value = mock_service
         
         mock_repo.get_account_by_email.return_value = None  # New account
         mock_repo.save_account.side_effect = lambda x: x
         
         result = await social_service.handle_callback("code", "user@test.com")
         
         assert result.email == "acc@test.com"
         assert result.access_token == "new_token"
         assert result.provider == SocialProvider.GOOGLE
         mock_sync.assert_called()

@pytest.mark.asyncio
async def test_handle_callback_existing_account(social_service):
    """Test handle_callback updates existing account (lines 78-87)"""
    with patch.object(social_service, "_get_flow") as mock_get_flow, \
         patch("backend.services.social_service.build") as mock_build, \
         patch("backend.services.social_service.social_repository") as mock_repo, \
         patch.object(social_service, "sync_channels", new_callable=AsyncMock) as mock_sync:
         
         mock_flow = MagicMock()
         mock_flow.credentials.token = "updated_token"
         mock_flow.credentials.refresh_token = "updated_refresh"
         mock_flow.credentials.expiry = 111111
         mock_get_flow.return_value = mock_flow
         
         mock_service = MagicMock()
         mock_service.userinfo.return_value.get.return_value.execute.return_value = {
             "email": "acc@test.com", "id": "123", "picture": "new_pic", "name": "Updated Name"
         }
         mock_build.return_value = mock_service
         
         # Existing account
         existing = SocialAccountModel(
             id=99,
             user_email="old_user@test.com",
             provider=SocialProvider.GOOGLE,
             provider_account_id="123",
             email="acc@test.com",
             name="Old Name",
             photo_url="old_pic",
             access_token="old_token",
             refresh_token="old_refresh",
             token_expiry=1234,
             scopes=["old_scope"]
         )
         mock_repo.get_account_by_email.return_value = existing
         mock_repo.save_account.side_effect = lambda x: x
         
         result = await social_service.handle_callback("code", "user@test.com")
         
         # Verify account was updated
         assert result.access_token == "updated_token"
         assert result.refresh_token == "updated_refresh"
         assert result.token_expiry == 111111
         assert result.photo_url == "new_pic"
         assert result.name == "Updated Name"
         assert result.user_email == "user@test.com"  # Ownership linkage updated

@pytest.mark.asyncio
async def test_sync_channels(social_service, mock_account):
    with patch("backend.services.social_service.Credentials"), \
         patch("backend.services.social_service.build") as mock_build, \
         patch("backend.services.social_service.social_repository") as mock_repo:
         
         mock_yt = MagicMock()
         mock_yt.channels.return_value.list.return_value.execute.return_value = {
             "items": [{
                 "id": "chan1",
                 "snippet": {
                     "title": "My Channel",
                     "description": "Desc",
                     "thumbnails": {"default": {"url": "thumb"}},
                     "customUrl": "custom"
                 },
                 "statistics": {"subscriberCount": "100", "videoCount": "10"}
             }]
         }
         mock_build.return_value = mock_yt
         
         mock_repo.get_channels_by_account.return_value = []
         mock_repo.save_channel.side_effect = lambda x: x
         
         channels = await social_service.sync_channels(mock_account)
         
         assert len(channels) == 1
         assert channels[0].title == "My Channel"
         assert channels[0].channel_id == "chan1"

@pytest.mark.asyncio
async def test_sync_channels_updates_existing(social_service, mock_account):
    """Test sync_channels updates existing channel (line 149)"""
    with patch("backend.services.social_service.Credentials"), \
         patch("backend.services.social_service.build") as mock_build, \
         patch("backend.services.social_service.social_repository") as mock_repo:
         
         mock_yt = MagicMock()
         mock_yt.channels.return_value.list.return_value.execute.return_value = {
             "items": [{
                 "id": "chan1",
                 "snippet": {
                     "title": "Updated Channel",
                     "description": "Updated",
                     "thumbnails": {"default": {"url": "thumb"}},
                     "customUrl": "custom"
                 },
                 "statistics": {"subscriberCount": "200", "videoCount": "20"}
             }]
         }
         mock_build.return_value = mock_yt
         
         # Existing channel with same channel_id
         existing_channel = SocialChannelModel(
             id=555,
             social_account_id=1,
             platform="youtube",
             channel_id="chan1",
             title="Old Title",
             description="Old",
             thumbnail_url="old_thumb",
             custom_url="old_custom",
             subscriber_count=100,
             video_count=10
         )
         mock_repo.get_channels_by_account.return_value = [existing_channel]
         mock_repo.save_channel.side_effect = lambda x: x
         
         channels = await social_service.sync_channels(mock_account)
         
         # Verify channel was updated (kept same ID)
         assert len(channels) == 1
         assert channels[0].id == 555  # Preserved existing ID

def test_get_user_channels(social_service):
    """Test get_user_channels aggregates from all accounts (lines 157-162)"""
    with patch("backend.services.social_service.social_repository") as mock_repo:
        account1 = MagicMock(id=1)
        account2 = MagicMock(id=2)
        mock_repo.list_accounts.return_value = [account1, account2]
        
        chan1 = MagicMock(title="Channel 1")
        chan2 = MagicMock(title="Channel 2")
        chan3 = MagicMock(title="Channel 3")
        
        mock_repo.get_channels_by_account.side_effect = [
            [chan1, chan2],  # Account 1
            [chan3]           # Account 2
        ]
        
        channels = social_service.get_user_channels("user@test.com")
        
        assert len(channels) == 3
        assert channels[0].title == "Channel 1"
        assert channels[2].title == "Channel 3"

@pytest.mark.asyncio
async def test_upload_video_success(social_service):
    with patch("backend.services.social_service.social_repository") as mock_repo, \
         patch("backend.services.social_service.Credentials"), \
         patch("backend.services.social_service.build") as mock_build, \
         patch("googleapiclient.http.MediaFileUpload"):
         
         mock_channel = MagicMock(social_account_id=1)
         mock_repo.get_channel_by_id.return_value = mock_channel
         mock_repo.get_account_by_id.return_value = MagicMock()
         
         mock_yt = MagicMock()
         mock_request = MagicMock()
         mock_request.next_chunk.return_value = (None, {'id': 'vid1'})
         mock_yt.videos.return_value.insert.return_value = mock_request
         mock_build.return_value = mock_yt
         
         vid_id = await social_service.upload_video(1, "file.mp4", "Title", "Desc", "private")
         
         assert vid_id == 'vid1'

@pytest.mark.asyncio
async def test_upload_video_channel_not_found(social_service):
    """Test upload_video raises when channel not found (line 178)"""
    with patch("backend.services.social_service.social_repository") as mock_repo:
        mock_repo.get_channel_by_id.return_value = None
        
        with pytest.raises(ValueError, match="Channel not found"):
            await social_service.upload_video(1, "file.mp4", "Title", "Desc", "private")

@pytest.mark.asyncio
async def test_upload_video_account_not_found(social_service):
    """Test upload_video raises when account not found (line 182)"""
    with patch("backend.services.social_service.social_repository") as mock_repo:
        mock_channel = MagicMock(social_account_id=1)
        mock_repo.get_channel_by_id.return_value = mock_channel
        mock_repo.get_account_by_id.return_value = None
        
        with pytest.raises(ValueError, match="Social Account not found"):
            await social_service.upload_video(1, "file.mp4", "Title", "Desc", "private")

@pytest.mark.asyncio
async def test_upload_video_with_progress(social_service):
    """Test upload_video logs progress during chunked upload (lines 227)"""
    with patch("backend.services.social_service.social_repository") as mock_repo, \
         patch("backend.services.social_service.Credentials"), \
         patch("backend.services.social_service.build") as mock_build, \
         patch("googleapiclient.http.MediaFileUpload"):
         
         mock_channel = MagicMock(social_account_id=1)
         mock_repo.get_channel_by_id.return_value = mock_channel
         mock_repo.get_account_by_id.return_value = MagicMock()
         
         mock_yt = MagicMock()
         mock_request = MagicMock()
         
         # Simulate chunked upload with progress
         mock_status1 = MagicMock()
         mock_status1.progress.return_value = 0.5
         mock_status2 = MagicMock()
         mock_status2.progress.return_value = 0.9
         
         mock_request.next_chunk.side_effect = [
             (mock_status1, None),  # 50% progress
             (mock_status2, None),  # 90% progress
             (None, {'id': 'vid1'}) # Done
         ]
         mock_yt.videos.return_value.insert.return_value = mock_request
         mock_build.return_value = mock_yt
         
         vid_id = await social_service.upload_video(1, "file.mp4", "Title", "Desc", "private")
         
         assert vid_id == 'vid1'
         assert mock_request.next_chunk.call_count == 3



@pytest.mark.asyncio
async def test_upload_video_generic_http_error(social_service):
    """Test upload_video re-raises other HTTP errors (lines 241-242)"""
    with patch("backend.services.social_service.social_repository") as mock_repo, \
         patch("backend.services.social_service.Credentials"), \
         patch("backend.services.social_service.build") as mock_build, \
         patch("googleapiclient.http.MediaFileUpload"):
         
         mock_channel = MagicMock(social_account_id=1)
         mock_repo.get_channel_by_id.return_value = mock_channel
         mock_repo.get_account_by_id.return_value = MagicMock()
         
         mock_yt = MagicMock()
         mock_request = MagicMock()
         
         http_error = HttpError(
             resp=MagicMock(status=500),
             content=b"Internal Server Error"
         )
         mock_request.next_chunk.side_effect = http_error
         mock_yt.videos.return_value.insert.return_value = mock_request
         mock_build.return_value = mock_yt
         
         with pytest.raises(HttpError):
             await social_service.upload_video(1, "file.mp4", "Title", "Desc", "private")

@pytest.mark.asyncio
async def test_upload_video_generic_exception(social_service):
    """Test upload_video handles generic exceptions (lines 244-245)"""
    with patch("backend.services.social_service.social_repository") as mock_repo, \
         patch("backend.services.social_service.Credentials"), \
         patch("backend.services.social_service.build") as mock_build, \
         patch("googleapiclient.http.MediaFileUpload"):
         
         mock_channel = MagicMock(social_account_id=1)
         mock_repo.get_channel_by_id.return_value = mock_channel
         mock_repo.get_account_by_id.return_value = MagicMock()
         
         mock_yt = MagicMock()
         mock_request = MagicMock()
         mock_request.next_chunk.side_effect = Exception("Network timeout")
         mock_yt.videos.return_value.insert.return_value = mock_request
         mock_build.return_value = mock_yt
         
         with pytest.raises(Exception, match="Network timeout"):
             await social_service.upload_video(1, "file.mp4", "Title", "Desc", "private")
