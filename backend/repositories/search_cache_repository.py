import json
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from google.cloud import datastore
from backend.core.datastore_client import get_datastore_client
from backend.models.search_cache import SearchCacheModel

class SearchCacheRepository:
    def __init__(self):
        self.kind = "SearchCache"

    @property
    def client(self) -> datastore.Client:
        return get_datastore_client()

    async def get(self, key_id: str) -> Optional[SearchCacheModel]:
        return await asyncio.to_thread(self._get_sync, key_id)

    def _get_sync(self, key_id: str) -> Optional[SearchCacheModel]:
        client = self.client
        key = client.key(self.kind, key_id)
        entity = client.get(key)
        if not entity: return None
        data = json.loads(entity["full_json"])
        return SearchCacheModel(**data)

    async def save(self, cache: SearchCacheModel) -> SearchCacheModel:
        return await asyncio.to_thread(self._save_sync, cache)

    def _save_sync(self, cache: SearchCacheModel) -> SearchCacheModel:
        client = self.client
        cache.updated_at = datetime.now()
        key = client.key(self.kind, cache.id)
        entity = datastore.Entity(key=key, exclude_from_indexes=("full_json",))
        entity.update({
            "provider": cache.provider,
            "created_at": cache.created_at,
            "updated_at": cache.updated_at,
            "full_json": json.dumps(cache.model_dump(mode="json"), ensure_ascii=False)
        })
        client.put(entity)
        return cache

    async def list_recent(self, limit: int = 100) -> List[SearchCacheModel]:
        return await asyncio.to_thread(self._list_recent_sync, limit)

    def _list_recent_sync(self, limit: int = 100) -> List[SearchCacheModel]:
        client = self.client
        query = client.query(kind=self.kind)
        query.order = ["-updated_at"]
        results = []
        for entity in query.fetch(limit=limit):
            if "full_json" in entity:
                data = json.loads(entity["full_json"])
                results.append(SearchCacheModel(**data))
        return results

search_cache_repository = SearchCacheRepository()
