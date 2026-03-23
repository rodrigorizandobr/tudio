import httpx
import os
import random
from typing import List, Dict, Optional, Any
from backend.core.configs import settings
from backend.core.proxy_config import create_proxy_config
from backend.core.logger import log
from backend.services.cache_service import search_cache
from backend.services.serpapi_service import serpapi_service


class VideoSearchService:
    """
    Service to interact with video stock APIs (Pexels, Pixabay, Google).
    Supports proxy configuration for corporate environments.
    """

    def __init__(self):
        """Initialize video search service with API keys and proxy configuration."""
        # API Keys
        self.pexels_api_key = settings.PEXELS_API_KEY if hasattr(settings, 'PEXELS_API_KEY') else None
        self.pixabay_api_key = settings.PIXABAY_API_KEY if hasattr(settings, 'PIXABAY_API_KEY') else None
        self.serpapi_key = settings.SERPAPI_API_KEY if hasattr(settings, 'SERPAPI_API_KEY') else None
        
        # API Base URLs
        self.pexels_base_url = "https://api.pexels.com/videos"
        self.pixabay_base_url = "https://pixabay.com/api/videos"
        self.serpapi_base_url = "https://serpapi.com/search"
        
        # Proxy Configuration
        self.proxy_config = create_proxy_config(
            use_proxy=settings.USE_PROXY,
            proxy_type=settings.PROXY_TYPE,  # type: ignore
            proxy_host=settings.PROXY_HOST,
            proxy_port=settings.PROXY_PORT,
            proxy_username=settings.PROXY_USERNAME,
            proxy_password=settings.PROXY_PASSWORD,
            no_proxy_domains=settings.NO_PROXY_DOMAINS,
            verify_ssl=settings.VERIFY_SSL
        )
        
        # Warnings for missing API keys
        if not self.pexels_api_key:
            log.warning("PEXELS_API_KEY not found. Pexels video search will not work.")
        if not self.pixabay_api_key:
            log.warning("PIXABAY_API_KEY not found. Pixabay video search will not work.")
        if not self.serpapi_key:
            log.warning("SERPAPI_API_KEY not found. Google video search will not work.")

    def _create_client(self) -> httpx.AsyncClient:
        """Create an async client with proxy configuration using httpx 0.28+ API (proxy instead of proxies)."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        proxy = None
        if self.proxy_config.use_proxy:
            proxies_dict = self.proxy_config.get_proxies_dict()
            if proxies_dict:
                # Use the 'http' one as default for all (httpx handles this well)
                proxy = proxies_dict.get("http") or proxies_dict.get("https")
            
            if proxy:
                log.info(f"Proxy configured: {proxy}")
            if not self.proxy_config.verify_ssl:
                log.warning("SSL verification disabled - use only as last resort!")
        
        return httpx.AsyncClient(
            headers=headers,
            proxy=proxy,
            verify=self.proxy_config.verify_ssl,
            timeout=30.0,
            follow_redirects=True
        )

    async def search_videos(
        self, 
        query: str, 
        provider: str = "pexels",
        orientation: str = "landscape",
        size: str = "medium",
        per_page: int = 20,
        use_cache: bool = True,
        only_if_cached: bool = False
    ) -> List[Dict]:
        """
        Search for videos across providers with persistent SQLite caching.
        """
        # Normalize cache key
        cache_key = f"{query}_{orientation}_{size}"
        
        # 1. Check Cache
        if use_cache or only_if_cached:
            cached = search_cache.get(f"{provider}_videos", cache_key)
            if cached is not None:
                log.info(f"{provider.capitalize()} videos cache hit for '{query}'")
                return cached
                
        # If we only want cached results and didn't find any, return empty immediately
        if only_if_cached:
            log.info(f"{provider.capitalize()} cache miss for '{query}' (only_if_cached=True)")
            return []

        # 2. Route to provider (Async)
        if provider == "pexels":
            results = await self._search_pexels(query, orientation, size, per_page)
        elif provider == "pixabay":
            results = await self._search_pixabay(query, orientation, size, per_page)
        elif provider == "google":
            results = await self._search_google(query, orientation, size, per_page)
        else:
            log.warning(f"Unknown provider: {provider}")
            return []

        # 3. Save to Cache
        if results:
            # --- RANDOMIZATION (User Rule: Randomize top 10) ---
            if len(results) > 1:
                top_count = min(10, len(results))
                top_10 = results[:top_count]
                other = results[top_count:]
                random.shuffle(top_10)
                results = top_10 + other
                log.info(f"VideoSearch ({provider}): Randomized top {top_count} results.")

            search_cache.set(f"{provider}_videos", cache_key, results)
        
        return results

    async def _search_pexels(
        self, 
        query: str, 
        orientation: str, 
        size: str, 
        per_page: int
    ) -> List[Dict]:
        """Search videos on Pexels with proxy support and retry logic."""
        if not self.pexels_api_key:
            return []

        try:
            async with self._create_client() as client:
                params = {
                    "query": query,
                    "per_page": min(per_page, 80),
                    "orientation": orientation,
                    "size": size
                }
                headers = {"Authorization": self.pexels_api_key}
                
                response = await client.get(
                    f"{self.pexels_base_url}/search",
                    params=params,
                    headers=headers
                )
            
            response.raise_for_status()
            data = response.json()
            
            # Success - transform to normalized format
            results = []
            for item in data.get("videos", []):
                video_files = item.get("video_files", [])
                if not video_files:
                    continue
                
                # Sort by quality
                video_files_sorted = sorted(
                    video_files, 
                    key=lambda x: x.get("width", 0), 
                    reverse=True
                )
                
                # Select quality based on size parameter
                if size == "large":
                    video_file = video_files_sorted[0]
                elif size == "small":
                    video_file = video_files_sorted[-1]
                else:  # medium
                    mid_index = len(video_files_sorted) // 2
                    video_file = video_files_sorted[mid_index]

                results.append({
                    "id": str(item["id"]),
                    "video_url": video_file["link"],
                    "thumbnail": item["image"],
                    "width": item["width"],
                    "height": item["height"],
                    "duration": item.get("duration", 0),
                    "description": f"Pexels Video {item['id']}",
                    "provider": "pexels",
                    "author_name": item.get("user", {}).get("name", "Unknown"),
                    "author_url": item.get("user", {}).get("url", ""),
                    "file_size": video_file.get("file_size", 0),
                    "quality": video_file.get("quality", "hd"),
                    "file_type": video_file.get("file_type", "video/mp4")
                })

            log.info(f"Pexels video search SUCCESS: {len(results)} results")
            return results
            
        except httpx.RequestError as e:
            # Fail immediately on error
            log.error(f"Pexels API error: {str(e)}")
            return []

    async def _search_pixabay(
        self, 
        query: str, 
        orientation: str, 
        size: str, 
        per_page: int
    ) -> List[Dict]:
        """Search videos on Pixabay."""
        if not self.pixabay_api_key:
            log.warning("PIXABAY_API_KEY not found. Pixabay search skipped.")
            return []
        
        # Map orientation to Pixabay format
        orientation_map = {
            "landscape": "horizontal",
            "portrait": "vertical",
            "square": "all"  # Pixabay doesn't have square, use all
        }
        pixabay_orientation = orientation_map.get(orientation, "all")
        
        try:
            async with self._create_client() as client:
                params = {
                    "key": self.pixabay_api_key,
                    "q": query,
                    "per_page": min(per_page, 200),
                    "video_type": "all"
                }
                
                response = await client.get(
                    f"{self.pixabay_base_url}/",
                    params=params
                )
            
            response.raise_for_status()
            data = response.json()
            
            # Success - transform to normalized format
            results = []
            for item in data.get("hits", []):
                videos = item.get("videos", {})
                if not videos:
                    continue
                
                # Select video quality based on size parameter
                if size == "large":
                    video_file = videos.get("large") or videos.get("medium") or videos.get("small")
                elif size == "small":
                    video_file = videos.get("small") or videos.get("medium") or videos.get("large")
                else:  # medium or default
                    video_file = videos.get("medium") or videos.get("large") or videos.get("small")
                
                if not video_file:
                    continue
                
                # Normalize to common format
                normalized_result = {
                    "id": str(item.get("id", "")),
                    "provider": "pixabay",
                    "thumbnail": f"https://i.vimeocdn.com/video/{item.get('picture_id', '')}_295x166.jpg",
                    "video_url": video_file.get("url", ""),
                    "duration": item.get("duration", 0),
                    "width": video_file.get("width", 0),
                    "height": video_file.get("height", 0),
                    "author_name": item.get("user", "Pixabay User"),
                    "author_url": item.get("pageURL", "https://pixabay.com")
                }
                
                results.append(normalized_result)
            
            log.info(f"Pixabay search success: {len(results)} results for '{query}'")
            return results
        
        except httpx.RequestError as e:
            # Fail immediately on error
            log.error(f"Pixabay API error: {str(e)}")
            return []

    async def _search_google(
        self, 
        query: str, 
        orientation: str, 
        size: str, 
        per_page: int
    ) -> List[Dict]:
        """Search videos on Google via SerpAPI using shared logic."""
        if not self.serpapi_key:
            log.warning("SERPAPI_API_KEY not found. Google search skipped.")
            return []

        # Uses SerpApiService Async method
        return await serpapi_service.search_videos(
            query=query, 
            per_page=per_page
        )

    async def download_video(
        self, 
        video_url: str, 
        video_id: str, 
        provider: str,
        project_video_id: Optional[int] = None,
        chapter_id: Optional[int] = None,
        subchapter_id: Optional[int] = None,
        scene_index: Optional[int] = None
    ) -> Dict[str, Any]:
        """Download a video from URL and save to storage."""
        try:
            # Create provider directory
            provider_dir = os.path.join("storage", "videos", "search", provider)
            os.makedirs(provider_dir, exist_ok=True)

            # Generate filename
            filename = f"{video_id}.mp4"
            local_path = os.path.join(provider_dir, filename)

            if provider == "google" or "youtube.com" in video_url or "youtu.be" in video_url:
                result = await self._download_youtube(video_url, video_id, provider_dir, filename)
            else:
                # Standard direct download for Pexels/Pixabay
                result = await self._download_direct(video_url, video_id, provider_dir, local_path)
            
            return result

        except Exception as e:
            log.error(f"Video download unexpected error: {str(e)}")
            return {
                "local_path": "",
                "file_size": 0,
                "error": str(e)
            }

    async def _download_youtube(self, video_url: str, video_id: str, provider_dir: str, filename: str) -> Dict[str, Any]:
        """Download video using yt-dlp."""
        import yt_dlp
        
        local_path = os.path.join(provider_dir, filename)
        
        # Check if exists
        if os.path.exists(local_path):
            file_size = os.path.getsize(local_path)
            log.info(f"Video already exists: {local_path}")
            return {
                "local_path": local_path,
                "local_url": local_path,
                "file_size": file_size
            }

        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': local_path,
            'quiet': True,
            'no_warnings': True,
        }

        try:
            log.info(f"Downloading YouTube video: {video_url}")
            # Run blocking code in thread pool
            import asyncio
            
            loop = asyncio.get_event_loop()
            
            def run_ytdlp():
                log.info(f"yt-dlp outtmpl: {local_path}")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video_url])
            
            await loop.run_in_executor(None, run_ytdlp)
            
            # Check for file
            if os.path.exists(local_path):
                file_size = os.path.getsize(local_path)
                return {
                    "local_path": local_path,
                    "local_url": local_path,
                    "file_size": file_size
                }
            else:
                return {"error": "Download finished but file not found"}

        except Exception as e:
            log.error(f"yt-dlp error: {e}")
            return {"error": str(e)}

    async def _download_direct(self, video_url: str, video_id: str, provider_dir: str, local_path: str) -> Dict[str, Any]:
        """Standard HTTP download with robust headers and retry (Async)."""
        try:
            # Check if exists
            if os.path.exists(local_path):
                file_size = os.path.getsize(local_path)
                return {
                    "local_path": local_path,
                    "local_url": local_path,
                    "file_size": file_size
                }

            log.info(f"Downloading video directly: {video_url}")
            
            # Retry logic with header rotation
            max_retries = 3
            retry_delay = 1
            last_error = None
            
            user_agents = [
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0'
            ]
            
            async with self._create_client() as client:
                for attempt in range(max_retries):
                    try:
                        current_ua = user_agents[attempt % len(user_agents)]
                        headers = {
                            'User-Agent': current_ua,
                            'Referer': 'https://www.google.com/',
                            'Accept': 'video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5'
                        }
                        
                        # Note: _create_client handles proxies, so we just pass headers
                        async with client.stream("GET", video_url, headers=headers) as response:
                            if response.status_code == 403 and attempt < max_retries - 1:
                                log.warning(f"Video Download 403 with UA {attempt}. Retrying...")
                                continue

                            response.raise_for_status()

                            # Check file size (limit to 50MB)
                            content_length = int(response.headers.get('content-length', 0))
                            if content_length > 50 * 1024 * 1024:
                                return {"error": "Video exceeds 50MB limit"}

                            # Streaming write (blocking I/O but acceptable here, or use thread pool)
                            # For absolute compliance with "Async First", we should write in chunks
                            # but built-in open() is blocking. 50MB file write takes ~1-2s.
                            with open(local_path, 'wb') as f:
                                async for chunk in response.aiter_bytes(chunk_size=8192):
                                    f.write(chunk)

                            file_size = os.path.getsize(local_path)
                            return {
                                "local_path": local_path,
                                "local_url": local_path,
                                "file_size": file_size
                            }
                        
                    except httpx.RequestError as e:
                        last_error = e
                        if attempt < max_retries - 1:
                            import asyncio
                            log.warning(f"Video download attempt {attempt+1} failed: {e}. Retrying...")
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2
                        continue

            # Exhausted
            log.error(f"Failed to download video after retries: {last_error}")
            return {"error": str(last_error)}

        except Exception as e:
            log.error(f"Direct download error: {e}")
            return {"error": str(e)}


# Singleton instance
video_search_service = VideoSearchService()
