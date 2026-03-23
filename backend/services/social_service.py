
import os
import json
from datetime import datetime
from typing import List, Optional
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from backend.core.configs import settings
from backend.core.logger import log
from backend.models.social import SocialAccountModel, SocialChannelModel, SocialProvider
from backend.repositories.social_repository import social_repository
import asyncio

class SocialService:
    def __init__(self):
        # Allow OAuth scope to change (Google adds openid/etc)
        os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
        # Allow HTTP for development (required for localhost)
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
        
        self.scopes = [
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/youtube.readonly",
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube",
            "openid"
        ]
        
    def _get_flow(self, state: Optional[str] = None) -> Flow:
        # Create flow from client config
        # We construct client_config dict manually since we read from settings env vars
        client_config = {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI]
            }
        }
        
        flow = Flow.from_client_config(
            client_config,
            scopes=self.scopes,
            state=state
        )
        flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
        return flow

    def get_authorization_url(self, state: str = "") -> str:
        flow = self._get_flow(state=state)
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent' # Force refresh token
        )
        return authorization_url

    async def handle_callback(self, code: str, user_email: str) -> SocialAccountModel:
        log.info(f"SocialService: Handling Google Callback for {user_email}")
        
        flow = self._get_flow()
        await asyncio.to_thread(flow.fetch_token, code=code)
        creds = flow.credentials
        
        # Get User Info
        service = build('oauth2', 'v2', credentials=creds)
        user_info = await asyncio.to_thread(service.userinfo().get().execute)
        
        # Create/Update SocialAccount
        account_email = user_info.get('email')
        account_id = user_info.get('id')
        
        # Check if exists
        existing_account = await social_repository.get_account_by_email(account_email, SocialProvider.GOOGLE)
        
        if existing_account:
            account = existing_account
            account.access_token = creds.token
            if creds.refresh_token:
                account.refresh_token = creds.refresh_token
            account.token_expiry = creds.expiry
            account.photo_url = user_info.get('picture')
            account.name = user_info.get('name')
            account.user_email = user_email # Ensure ownership linkage
            account.scopes = self.scopes # Update scopes in case they changed in code
        else:
            account = SocialAccountModel(
                user_email=user_email,
                provider=SocialProvider.GOOGLE,
                provider_account_id=account_id,
                email=account_email,
                name=user_info.get('name'),
                photo_url=user_info.get('picture'),
                access_token=creds.token,
                refresh_token=creds.refresh_token,
                token_expiry=creds.expiry,
                scopes=self.scopes
            )
            
        saved_account = await social_repository.save_account(account)
        
        # Fetch Channels immediately
        await self.sync_channels(saved_account)
        
        return saved_account

    async def sync_channels(self, account: SocialAccountModel) -> List[SocialChannelModel]:
        log.info(f"SocialService: Syncing channels for account {account.email}")
        
        creds = Credentials(
            token=account.access_token,
            refresh_token=account.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=account.scopes
        )
        
        youtube = build('youtube', 'v3', credentials=creds)
        
        # List "mine" channels
        request = youtube.channels().list(
            part="snippet,contentDetails,statistics",
            mine=True
        )
        # request.execute() is blocking, run in thread
        response = await asyncio.to_thread(request.execute)
        
        channels = []
        for item in response.get("items", []):
            channel = SocialChannelModel(
                social_account_id=account.id,
                platform="youtube",
                channel_id=item['id'],
                title=item['snippet']['title'],
                description=item['snippet']['description'],
                thumbnail_url=item['snippet']['thumbnails']['default']['url'],
                custom_url=item['snippet'].get('customUrl'),
                subscriber_count=int(item['statistics']['subscriberCount']),
                video_count=int(item['statistics']['videoCount'])
            )
            
            # Simple dedupe check:
            existing_channels = await social_repository.get_channels_by_account(account.id)
            match = next((c for c in existing_channels if c.channel_id == channel.channel_id), None)
            
            if match:
                channel.id = match.id
                
            saved_channel = await social_repository.save_channel(channel)
            channels.append(saved_channel)
            
        return channels
        
    async def get_user_channels(self, user_email: str) -> List[SocialChannelModel]:
        accounts = await social_repository.list_accounts(user_email)
        all_channels = []
        for account in accounts:
            channels = await social_repository.get_channels_by_account(account.id)
            all_channels.extend(channels)
        return all_channels

    async def upload_video(
        self,
        channel_id: int,
        video_path: str,
        title: str,
        description: str,
        privacy_status: str,
        tags: Optional[List[str]] = None,
        job_id: Optional[str] = None,
    ) -> str:
        from backend.core.upload_jobs import upload_job_store

        log.info(f"SocialService: Uploading video '{title}' to channel {channel_id} (job_id={job_id})")

        # Get Channel & Account
        channel = await social_repository.get_channel_by_id(channel_id)
        if not channel:
            raise ValueError("Channel not found")

        account = await social_repository.get_account_by_id(channel.social_account_id)
        if not account:
            raise ValueError("Social Account not found")

        # Refresh Creds
        creds = Credentials(
            token=account.access_token,
            refresh_token=account.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=account.scopes,
        )

        youtube = build("youtube", "v3", credentials=creds)

        # Prepare Body
        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags or [],
                "categoryId": "22",  # People & Blogs default
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }

        # Upload with chunked resumable upload
        from googleapiclient.http import MediaFileUpload
        from googleapiclient.errors import HttpError

        media = MediaFileUpload(video_path, chunksize=1024 * 1024, resumable=True)

        request = youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media,
        )

        response = None
        try:
            while response is None:
                status, response = await asyncio.to_thread(request.next_chunk)
                if status and job_id:
                    pct = round(status.progress() * 100, 1)
                    upload_job_store.update_progress(job_id, pct)
                    log.info(f"[Job {job_id}] Upload progress: {pct}%")
        except HttpError as e:
            if job_id:
                upload_job_store.fail_job(job_id, str(e))
            if e.resp.status == 403:
                try:
                    error_details = json.loads(e.content.decode())
                    reasons = [
                        err.get("reason")
                        for err in error_details.get("error", {}).get("errors", [])
                    ]
                    if "insufficientPermissions" in reasons:
                        log.error(f"Upload failed: insufficient permissions: {e}")
                        raise ValueError(
                            "Permissões insuficientes. Por favor, desconecte e reconecte o canal."
                        )
                except Exception:
                    pass
            log.error(f"YouTube Upload Failed: {e}")
            raise e
        except Exception as e:
            if job_id:
                upload_job_store.fail_job(job_id, str(e))
            log.error(f"Generic Upload Error: {e}")
            raise e

        youtube_video_id = response["id"]
        if job_id:
            upload_job_store.complete_job(job_id, youtube_video_id)
        log.info(f"Upload Complete! YouTube ID: {youtube_video_id}")
        return youtube_video_id


social_service = SocialService()
