import asyncio
from typing import List, Optional
from datetime import datetime
from google.cloud import datastore
from backend.core.datastore_client import get_datastore_client
from backend.models.social import SocialAccountModel, SocialChannelModel, SocialProvider

class SocialRepository:
    def __init__(self):
        self.account_kind = "SocialAccount"
        self.channel_kind = "SocialChannel"
    
    @property
    def client(self) -> datastore.Client:
        return get_datastore_client()
        
    async def save_account(self, account: SocialAccountModel) -> SocialAccountModel:
        return await asyncio.to_thread(self._save_account_sync, account)

    def _save_account_sync(self, account: SocialAccountModel) -> SocialAccountModel:
        client = self.client
        account.updated_at = datetime.now()
        data = account.model_dump(mode="json")
        if account.id:
            key = client.key(self.account_kind, int(account.id))
        else:
            key = client.key(self.account_kind)
        entity = datastore.Entity(key=key)
        entity.update(data)
        client.put(entity)
        account.id = entity.key.id
        return account
        
    async def get_account_by_email(self, email: str, provider: SocialProvider) -> Optional[SocialAccountModel]:
        return await asyncio.to_thread(self._get_account_by_email_sync, email, provider)

    def _get_account_by_email_sync(self, email: str, provider: SocialProvider) -> Optional[SocialAccountModel]:
        client = self.client
        query = client.query(kind=self.account_kind)
        query.add_filter(filter="email", operator="=", value=email)
        query.add_filter(filter="provider", operator="=", value=provider.value)
        results = list(query.fetch(limit=1))
        if not results: return None
        entity = results[0]
        data = dict(entity)
        data["id"] = entity.key.id
        return SocialAccountModel(**data)

    async def list_accounts(self, user_email: str) -> List[SocialAccountModel]:
        return await asyncio.to_thread(self._list_accounts_sync, user_email)

    def _list_accounts_sync(self, user_email: str) -> List[SocialAccountModel]:
        client = self.client
        query = client.query(kind=self.account_kind)
        query.add_filter(filter="user_email", operator="=", value=user_email)
        results = list(query.fetch())
        accounts = []
        for entity in results:
            data = dict(entity)
            data["id"] = entity.key.id
            accounts.append(SocialAccountModel(**data))
        return accounts

    async def get_account_by_id(self, account_id: int) -> Optional[SocialAccountModel]:
        return await asyncio.to_thread(self._get_account_by_id_sync, account_id)

    def _get_account_by_id_sync(self, account_id: int) -> Optional[SocialAccountModel]:
        client = self.client
        key = client.key(self.account_kind, int(account_id))
        entity = client.get(key)
        if not entity: return None
        data = dict(entity)
        data["id"] = entity.key.id
        return SocialAccountModel(**data)

    async def save_channel(self, channel: SocialChannelModel) -> SocialChannelModel:
        return await asyncio.to_thread(self._save_channel_sync, channel)

    def _save_channel_sync(self, channel: SocialChannelModel) -> SocialChannelModel:
        client = self.client
        channel.updated_at = datetime.now()
        data = channel.model_dump(mode="json")
        if channel.id:
            key = client.key(self.channel_kind, int(channel.id))
        else:
            key = client.key(self.channel_kind)
        entity = datastore.Entity(key=key)
        entity.update(data)
        client.put(entity)
        channel.id = entity.key.id
        return channel
        
    async def get_channels_by_account(self, account_id: int) -> List[SocialChannelModel]:
        return await asyncio.to_thread(self._get_channels_by_account_sync, account_id)

    def _get_channels_by_account_sync(self, account_id: int) -> List[SocialChannelModel]:
        client = self.client
        query = client.query(kind=self.channel_kind)
        query.add_filter(filter="social_account_id", operator="=", value=int(account_id))
        results = list(query.fetch())
        channels = []
        for entity in results:
            data = dict(entity)
            data["id"] = entity.key.id
            channels.append(SocialChannelModel(**data))
        return channels

    async def get_channel_by_id(self, channel_id: int) -> Optional[SocialChannelModel]:
        return await asyncio.to_thread(self._get_channel_by_id_sync, channel_id)

    def _get_channel_by_id_sync(self, channel_id: int) -> Optional[SocialChannelModel]:
        client = self.client
        key = client.key(self.channel_kind, int(channel_id))
        entity = client.get(key)
        if not entity: return None
        data = dict(entity)
        data["id"] = entity.key.id
        return SocialChannelModel(**data)

    async def delete_channel(self, channel_id: int):
        await asyncio.to_thread(self._delete_channel_sync, channel_id)

    def _delete_channel_sync(self, channel_id: int):
        client = self.client
        key = client.key(self.channel_kind, int(channel_id))
        client.delete(key)

social_repository = SocialRepository()
