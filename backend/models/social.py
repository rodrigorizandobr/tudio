
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime
from enum import Enum

class SocialProvider(str, Enum):
    GOOGLE = "google"
    # Future: FACEBOOK, INSTAGRAM, TIKTOK

class SocialAccountModel(BaseModel):
    id: Optional[int] = None # Datastore ID
    user_email: str
    provider: SocialProvider
    provider_account_id: str # sub from Google
    email: str
    name: str # Full name from Google
    photo_url: Optional[str] = None
    
    # Tokens
    access_token: str
    refresh_token: Optional[str] = None
    token_expiry: Optional[datetime] = None
    scopes: List[str] = []
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class SocialChannelModel(BaseModel):
    id: Optional[int] = None
    social_account_id: int # Link to SocialAccount
    platform: str = "youtube"
    
    channel_id: str # YouTube Channel ID
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    custom_url: Optional[str] = None
    
    subscriber_count: int = 0
    video_count: int = 0
    
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
class SocialAccountRead(BaseModel):
    id: int
    provider: SocialProvider
    email: str
    name: str
    photo_url: Optional[str]
    created_at: datetime

class SocialChannelRead(BaseModel):
    id: int
    social_account_id: int
    platform: str
    title: str
    thumbnail_url: Optional[str]
    custom_url: Optional[str]
    subscriber_count: int
    is_active: bool
