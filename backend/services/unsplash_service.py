import httpx
import json
import os
import random
from typing import List, Dict, Optional
from backend.core.configs import settings
from backend.core.logger import log
from backend.services.cache_service import search_cache


class UnsplashService:
    """
    Service to interact with Unsplash API for image search.
    """

    def __init__(self):
        self.api_key = settings.UNSPLASH_ACCESS_KEY
        self.base_url = "https://api.unsplash.com"
        
        if not self.api_key:
            log.warning("UNSPLASH_ACCESS_KEY not found. Image search will not work.")

    async def search_images(self, query: str, per_page: int = 20, orientation: str = "landscape", use_cache: bool = True, only_if_cached: bool = False) -> List[Dict]:
        """
        Search for images on Unsplash with persistent SQLite caching.
        """
        # --- MOCK FOR TESTING ---
        from backend.core.configs import settings
        if settings.TESTING and os.getenv("USE_E2E_MOCKS") == "True":
            log.warning("⚠️ E2E MOCK MODE DETECTED: Mocking UnsplashService.search_images.")
            import hashlib
            # Generate a stable but unique mock URL for this query
            q_hash = hashlib.md5(query.encode()).hexdigest()[:8]
            return [
                {
                    "id": f"mock_{q_hash}",
                    "url": f"https://images.unsplash.com/photo-mock-{q_hash}",
                    "width": 1920,
                    "height": 1080,
                    "alt_description": f"Mock image for {query}",
                    "user": {"name": "Mock Artist", "username": "mockartist"}
                }
            ]
        # ------------------------
        if not self.api_key:
            # log.warning("Unsplash API Key missing")
            return []

        # 1. Check Cache
        cache_key = f"{query}_{orientation}"
        if use_cache or only_if_cached:
            cached = await search_cache.get("unsplash", cache_key)
            if cached is not None:
                # log.info(f"Unsplash cache hit for '{query}'")
                return cached
            
            if only_if_cached:
                log.info(f"Unsplash cache MISS for '{query}' (only_if_cached=True). Returning empty.")
                return []

        # 2. API Request
        try:
            headers = {"Authorization": f"Client-ID {self.api_key}"}
            params = {
                "query": query,
                "per_page": min(per_page, 30),  # Free tier limit
                "orientation": orientation
            }
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.base_url}/search/photos",
                    params=params,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()

            # 3. Transform
            results = []
            for item in data.get("results", []):
                results.append({
                    "id": item["id"],
                    "url": item["urls"]["regular"],  # High quality
                    "thumb": item["urls"]["thumb"],  # Metadata for grid
                    "width": item["width"],
                    "height": item["height"],
                    "description": item.get("description") or item.get("alt_description", "") or "Unsplash Image",
                    "provider": "unsplash",
                    "author_name": item["user"]["name"],
                    "author_url": item["user"]["links"]["html"]
                })

            log.info(f"Unsplash search for '{query}': {len(results)} results")
            
            # --- RANDOMIZATION (User Rule: Randomize top 10) ---
            if results and len(results) > 1:
                top_count = min(10, len(results))
                top_10 = results[:top_count]
                other_results = results[top_count:]
                
                random.shuffle(top_10)
                results = top_10 + other_results
                log.info(f"Unsplash: Randomized top {top_count} results.")
            
            # 4. Save to Cache
            if results:
                search_cache.set("unsplash", cache_key, results)
            
            return results

        except httpx.RequestError as e:
            log.error(f"Unsplash API connection error: {str(e)}")
            return []
        except httpx.HTTPStatusError as e:
            log.error(f"Unsplash API status error: {e.response.status_code} - {e.response.text}")
            return []
        except Exception as e:
            log.error(f"Unsplash API unexpected error: {str(e)}")
            return []

# Singleton instance
unsplash_service = UnsplashService()

# --- MOCK FOR TESTING ---
if settings.TESTING and os.getenv("USE_E2E_MOCKS") == "True":
    log.warning("⚠️ E2E MOCK MODE DETECTED: Mocking UnsplashService global methods.")
    
    async def mock_search_images(self, query: str, per_page: int = 20, orientation: str = "landscape", use_cache: bool = True) -> List[Dict]:
        """
        Mock implementation returning placeholder images.
        """
        log.info(f"MOCK Unsplash search for '{query}'")
        results = []
        for i in range(per_page):
            results.append({
                "id": f"mock_{i}",
                "url": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&q=80&w=1000",
                "thumb": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&q=80&w=200",
                "width": 1000,
                "height": 1000,
                "description": f"Mock image for {query}",
                "provider": "unsplash",
                "author_name": "Antigravity Mock",
                "author_url": "https://unsplash.com"
            })
        return results

    import types
    UnsplashService.search_images = mock_search_images # type: ignore
    unsplash_service.search_images = types.MethodType(mock_search_images, unsplash_service) # Bind to instance
