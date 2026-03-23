
import httpx
import json
import os
import random
from typing import List, Dict, Any, Optional
from backend.core.configs import settings
from backend.core.logger import log
from backend.services.cache_service import search_cache

class SerpApiService:
    def __init__(self):
        self.api_url = "https://scraperapi.thordata.com/request"

    def _get_engine(self, provider: str) -> str:
        if provider == "serpapi" or provider == "google":
            return "google_images"
        if provider == "bing":
            return "bing_images"
        return "google_images" # default

    async def search(self, provider: str, query: str, page: int = 1, per_page: int = 10, orientation: str = None, engine_override: Optional[str] = None, only_if_cached: bool = False) -> List[Dict[str, Any]]:
        """
        Unified search for Google/Bing via Thor Data (acting as SerpApi proxy), with Caching.
        """
        # 1. Check Cache
        cache_key = f"{query}_{orientation}_{engine_override}" if orientation or engine_override else query
        cached_results = await search_cache.get(provider, cache_key)
        if cached_results is not None:
            return cached_results
            
        if only_if_cached:
            log.info(f"SerpApiService ({provider}) cache MISS for '{query}' (only_if_cached=True). Returning empty.")
            return []

        if not settings.SERPAPI_API_KEY:
            log.warning("Thor Data (SerpApi) API Key not configured.")
            return []

        # 2. Prepare Payload
        engine = engine_override if engine_override else self._get_engine(provider)
        start = (page - 1) * per_page
        
        # Base params
        payload = {
            "engine": engine,
            "q": query,
            "json": "1",
            "gl": "br",
            "hl": "pt-br"
        }

        # Orientation Mapping (Google Images)
        # iar:w = Wide (Landscape), iar:t = Tall (Portrait), iar:s = Square
        if orientation and engine == "google_images":
            tbs_parts = []
            if orientation == "landscape":
                tbs_parts.append("iar:w")
            elif orientation == "portrait":
                tbs_parts.append("iar:t")
            elif orientation == "square":
                tbs_parts.append("iar:s")
            
            if tbs_parts:
                payload["tbs"] = ",".join(tbs_parts)

        # Specific mappings
        if engine == "google_images":
            payload["start"] = str(start)
            payload["num"] = str(per_page)
        elif engine == "bing_images":
             # Bing uses 'first' (1-based)
             payload["first"] = str(start + 1)
             payload["count"] = str(per_page)
        else: # Default fallback
             payload["num"] = str(per_page)

        headers = { 
            'Authorization': f'Bearer {settings.SERPAPI_API_KEY}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        # 3. Request
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(self.api_url, data=payload, headers=headers)
                response.raise_for_status()
            
            # 4. Parse Response (Handle wrapped strings & double encoding)
            root_data = response.json()
            data = root_data

            # Helper to unwrap strings recursively (up to 2 levels)
            def unwrap(d):
                if isinstance(d, str):
                    try:
                        parsed = json.loads(d)
                        if isinstance(parsed, (dict, list)) or (isinstance(parsed, str) and parsed != d):
                            return unwrap(parsed) # Recurse if we got a structure or a new string
                        return parsed
                    except:
                        return d
                return d

            # 1. unwrap root if string
            data = unwrap(data)

            # 2. Check for wrapped 'data' field
            if isinstance(data, dict) and 'data' in data:
                inner = data['data']
                unwrapped_inner = unwrap(inner)
                # If inner is just a string (like "Package has expired!"), it's likely an error message or invalid state
                if isinstance(unwrapped_inner, str):
                     log.error(f"SerpApiService Error: {unwrapped_inner}")
                     return []
                     
                if isinstance(unwrapped_inner, (dict, list)):
                    data = unwrapped_inner
            
            if isinstance(data, dict) and "code" in data and data["code"] >= 400:
                 msg = data.get("data") or data.get("message") or "Unknown API Error"
                 log.error(f"SerpApiService API Error ({data['code']}): {msg}")
                 return []

            if isinstance(data, dict) and "error" in data:
                log.error(f"SerpApiService Error: {data['error']}")
                return []
            
            # 5. Normalize Results
            normalized_results = []
            items = []

            # Strategy: Find the list of images
            if isinstance(data, dict):
                if 'images' in data: # Google often
                    items = data['images']
                elif 'images_results' in data: # Bing/Google standard
                    items = data['images_results']
                elif 'results' in data and isinstance(data['results'], list):
                    items = data['results']
            
            # Slice locally to ensure limit
            items = items[:per_page]
            
            for item in items:
                # Common fields keys across engines (Google vs Bing)
                # Google: original, link, image_base64/thumbnail
                # Bing: original/media_url, link, thumbnail
                
                if not isinstance(item, dict):
                    continue

                image_url = item.get("original") or item.get("media_url") or item.get("link")
                
                # Exclude if no URL
                if not image_url:
                    continue

                thumb = item.get("thumbnail") or item.get("thumb")
                
                # Fix Google base64 thumbs if needed
                base64_thumb = item.get("image_base64")
                if base64_thumb and not base64_thumb.startswith("data:"):
                     thumb = f"data:image/jpeg;base64,{base64_thumb}"
                
                if not thumb:
                    thumb = image_url

                normalized_results.append({
                    "id": image_url,
                    "url": image_url,
                    "thumb": thumb,
                    "width": item.get("original_width") or item.get("width") or 0,
                    "height": item.get("original_height") or item.get("height") or 0,
                    "description": item.get("title") or item.get("image_alt") or f"{provider} Result",
                    "provider": provider,
                    "author_name": item.get("source") or item.get("domain") or "",
                    "author_url": item.get("link") or item.get("source_url") or ""
                })

            # --- RANDOMIZATION (User Rule: Randomize top 10) ---
            if normalized_results and len(normalized_results) > 1:
                top_count = min(10, len(normalized_results))
                top_10 = normalized_results[:top_count]
                other_results = normalized_results[top_count:]
                
                random.shuffle(top_10)
                normalized_results = top_10 + other_results
                log.info(f"SerpApi ({provider} Images): Randomized top {top_count} results.")

            # 6. Save to Cache (if results found)
            if normalized_results:
                search_cache.set(provider, cache_key, normalized_results)
            
            return normalized_results

        except Exception as e:
            log.error(f"SerpApiService Error: {e}")
            return []

    async def search_videos(self, query: str, page: int = 1, per_page: int = 10) -> List[Dict[str, Any]]:
        """
        Specialized search for videos using google_videos engine.
        Uses the internal generic search mechanism but processes results differently if needed.
        Currently reusing search() but forcing engine='google_videos' and handling result keys inside it.
        """
        # For video search, we might need slightly different parsing logic.
        # However, to reuse code, we can try to adapt the main loop or just implement a separate flow if too different.
        # Let's try separate flow to be safe and clean.
        
        provider = "google"
        cache_key = f"{query}_videos"
        cached_results = await search_cache.get(provider, cache_key)
        if cached_results is not None:
            return cached_results

        if not settings.SERPAPI_API_KEY:
            log.warning("Thor Data (SerpApi) API Key not configured.")
            return []

        payload = {
            "engine": "google_videos",
            "q": query,
            "json": "1",
            "gl": "br",
            "hl": "pt-br",
            "num": str(per_page)
        }
        
        headers = { 
            'Authorization': f'Bearer {settings.SERPAPI_API_KEY}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        try:
            log.info(f"Starting Google Video Search for query='{query}'")
            
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(self.api_url, data=payload, headers=headers)
                response.raise_for_status()
                
            root_data = response.json()

            
            # Unwrap helper (reused)
            def unwrap(d):
                if isinstance(d, str):
                    try:
                        parsed = json.loads(d)
                        if isinstance(parsed, (dict, list)) or (isinstance(parsed, str) and parsed != d):
                            return unwrap(parsed)
                        return parsed
                    except:
                        return d
                return d
            
            # DEBUG: Write raw response to storage for inspection
            try:
                debug_path = "storage/debug_serpapi_video_response.json"
                with open(debug_path, "w") as f:
                    json.dump(root_data, f, indent=2)
                log.info(f"DEBUG: Raw response written to {debug_path}")
            except Exception as e:
                log.error(f"DEBUG: Failed to write debug file: {e}")
            
            data = unwrap(root_data)
            if isinstance(data, dict) and 'data' in data:
                 data = unwrap(data['data'])

            if isinstance(data, dict) and "error" in data:
                log.error(f"SerpApiService Error: {data['error']}")
                raise Exception(f"SerpApi Error: {data['error']}")
            
            results = []
            video_results = []
            if isinstance(data, dict):
                video_results = data.get("video_results", []) or data.get("videos", [])
                log.info(f"So Found {len(video_results)} video_results in data")
            else:
                log.warning(f"Data is not a dict: {type(data)}")

            import hashlib
            
            for item in video_results:
                link = item.get("link", "")
                if not link:
                    continue
                
                # MD5 ID generation
                video_id = hashlib.md5(link.encode()).hexdigest()[:12]
                
                results.append({
                    "id": video_id,
                    "provider": "google",
                    "thumbnail": item.get("thumbnail") or item.get("image", ""),
                    "video_url": link,
                    "duration": 0,
                    "width": 0,
                    "height": 0,
                    "author_name": item.get("source", "Google Result"),
                    "author_url": link,
                    "description": item.get("title", "Google Video Result"),
                    "file_size": 0,
                    "quality": "unknown",
                    "file_type": "video/mp4"
                })
            
            if results:
                log.info(f"DEBUG: Parsed video results (first item): {json.dumps(results[:1], default=str)}")
                
                # --- RANDOMIZATION (User Rule: Randomize top 10) ---
                if len(results) > 1:
                    top_count = min(10, len(results))
                    top_10 = results[:top_count]
                    remain = results[top_count:]
                    random.shuffle(top_10)
                    results = top_10 + remain
                    log.info(f"SerpApi (Google Videos): Randomized top {top_count} results.")

                search_cache.set(provider, cache_key, results)
                
            return results

        except Exception as e:
            log.error(f"SerpApiService Video Search Error: {e}")
            return []

serpapi_service = SerpApiService()
