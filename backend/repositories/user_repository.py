import json
import asyncio
from datetime import datetime
from typing import Optional, List
from google.cloud import datastore
from backend.core.datastore_client import get_datastore_client
from backend.models.user import UserModel, GroupModel

class UserRepository:
    def __init__(self):
        self.user_kind = "User"
        self.group_kind = "Group"
    
    @property
    def client(self) -> datastore.Client:
        return get_datastore_client()

    # --- User Methods ---
    async def get_user_by_email(self, email: str) -> Optional[UserModel]:
        return await asyncio.to_thread(self._get_user_by_email_sync, email)

    def _get_user_by_email_sync(self, email: str) -> Optional[UserModel]:
        client = self.client
        key = client.key(self.user_kind, email)
        entity = client.get(key)
        if not entity: return None
        return UserModel(
            email=entity.key.name,
            hashed_password=entity["hashed_password"],
            full_name=entity.get("full_name"),
            is_active=entity.get("is_active", True),
            groups=entity.get("groups", []),
            created_at=entity.get("created_at"),
            updated_at=entity.get("updated_at")
        )

    async def save_user(self, user: UserModel) -> UserModel:
        return await asyncio.to_thread(self._save_user_sync, user)

    def _save_user_sync(self, user: UserModel) -> UserModel:
        client = self.client
        key = client.key(self.user_kind, user.email)
        entity = datastore.Entity(key=key)
        entity.update({
            "hashed_password": user.hashed_password,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "groups": user.groups,
            "created_at": user.created_at,
            "updated_at": datetime.now()
        })
        client.put(entity)
        return user

    # --- Group Methods ---
    async def get_group(self, name: str) -> Optional[GroupModel]:
        return await asyncio.to_thread(self._get_group_sync, name)

    def _get_group_sync(self, name: str) -> Optional[GroupModel]:
        client = self.client
        key = client.key(self.group_kind, name)
        entity = client.get(key)
        if not entity: return None
        if entity.get("is_deleted", False): return None
        return GroupModel(
            name=entity.key.name, 
            rules=entity.get("rules", []),
            is_deleted=entity.get("is_deleted", False)
        )

    async def save_group(self, group: GroupModel) -> GroupModel:
        return await asyncio.to_thread(self._save_group_sync, group)

    def _save_group_sync(self, group: GroupModel) -> GroupModel:
        client = self.client
        key = client.key(self.group_kind, group.name)
        if group.name == "Super Admin":
            group.rules = ["*"]
            group.is_deleted = False
        entity = datastore.Entity(key=key)
        entity.update({
            "rules": group.rules,
            "is_deleted": group.is_deleted
        })
        client.put(entity)
        return group
    
    async def list_groups(self) -> List[GroupModel]:
        return await asyncio.to_thread(self._list_groups_sync)

    def _list_groups_sync(self) -> List[GroupModel]:
        client = self.client
        query = client.query(kind=self.group_kind)
        query.add_filter(filter=datastore.query.PropertyFilter("is_deleted", "=", False))
        results = query.fetch()
        groups = []
        for entity in results:
            if not entity.get("is_deleted", False):
                groups.append(GroupModel(
                    name=entity.key.name, 
                    rules=entity.get("rules", []),
                    is_deleted=entity.get("is_deleted", False)
                ))
        return groups

    async def delete_group(self, name: str) -> bool:
        return await asyncio.to_thread(self._delete_group_sync, name)

    def _delete_group_sync(self, name: str) -> bool:
        if name == "Super Admin": return False
        client = self.client
        key = client.key(self.group_kind, name)
        entity = client.get(key)
        if not entity: return False
        entity["is_deleted"] = True
        client.put(entity)
        return True

user_repository = UserRepository()
