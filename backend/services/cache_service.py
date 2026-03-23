from typing import Optional, Dict, Any, List
from backend.core.logger import log
from backend.models.search_cache import SearchCacheModel
from backend.repositories.search_cache_repository import search_cache_repository

class SearchCacheService:
    def __init__(self):
        pass

    def _get_key(self, provider: str, query: str) -> str:
        return f"{provider}:{query.lower().strip()}"

    async def get(self, provider: str, query: str) -> Optional[List[Dict[str, Any]]]:
        key = self._get_key(provider, query)
        try:
            cache_entry = await search_cache_repository.get(key)
            if cache_entry:
                log.info(f"Datastore Cache HIT for {key}")
                return cache_entry.data
            else:
                log.info(f"Datastore Cache MISS for {key}")
                return None
        except Exception as e:
            log.error(f"Cache read error: {e}")
            return None

    async def set(self, provider: str, query: str, results: List[Dict[str, Any]]):
        key = self._get_key(provider, query)
        try:
            cache_model = SearchCacheModel(
                id=key,
                data=results,
                provider=provider
            )
            await search_cache_repository.save(cache_model)
            log.info(f"Datastore Cache SAVED for {key}")
        except Exception as e:
            log.error(f"Cache write error: {e}")

    def cleanup_expired(self) -> int:
        return 0

    async def list_recent_images(self, limit: int = 100, query: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            entries = await search_cache_repository.list_recent(limit=limit)
            all_images = []
            seen_ids = set()
            q_lower = query.lower().strip() if query else None
            
            for entry in entries:
                for img in entry.data:
                    img_id = img.get("id")
                    if img_id and img_id not in seen_ids:
                        if q_lower:
                            desc = (img.get("description") or img.get("alt_description", "")).lower()
                            if q_lower not in desc and q_lower not in entry.id.lower():
                                continue
                        all_images.append(img)
                        seen_ids.add(img_id)
                        if len(all_images) >= limit: break
                if len(all_images) >= limit: break
            return all_images
        except Exception as e:
            log.error(f"Error listing recent images: {e}")
            return []

search_cache = SearchCacheService()
