
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from backend.services.video_search_service import VideoSearchService

class TestVideoSearchService:
    @pytest.fixture
    def service(self):
        return VideoSearchService()

    @pytest.mark.asyncio
    async def test_search_pexels_implementation(self, service):
        # Setup specific mock for the client instance
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        # Sync json
        mock_resp.json.side_effect = lambda: {
            "videos": [
                {
                    "id": 123,
                    "image": "http://img.jpg",
                    "width": 1920,
                    "height": 1080,
                    "video_files": [{"link": "http://v.mp4", "quality": "hd", "width": 1920}]
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        
        # Async get
        mock_client_instance.get.return_value = mock_resp

        service.pexels_api_key = "key"
        
        # Patch local _create_client to return our prepared mock
        with patch.object(service, '_create_client', return_value=mock_client_instance):
            results = await service._search_pexels("query", "landscape", "medium", 10)
        
        assert len(results) > 0
        assert "http://v.mp4" in results[0]["video_url"]

    @pytest.mark.asyncio
    async def test_search_pixabay_implementation(self, service):
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = lambda: {"hits": [{"id": 999, "pageURL": "http://pixa", "videos": {"large": {"url": "http://v.mp4"}}}]}
        mock_resp.raise_for_status = MagicMock()
        
        mock_client_instance.get.return_value = mock_resp

        service.pixabay_api_key = "key"

        with patch.object(service, '_create_client', return_value=mock_client_instance):
            results = await service._search_pixabay("query", "landscape", "medium", 10)
            
        assert len(results) > 0
        assert "http://v.mp4" in results[0]["video_url"]

    @patch("backend.services.video_search_service.search_cache")
    @pytest.mark.asyncio
    async def test_search_videos_dispatcher(self, mock_cache, service):
        # 1. Cache Miss
        mock_cache.get.return_value = None
        
        # Mock _search_pexels method
        with patch.object(service, '_search_pexels', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = [{"id": "1", "provider": "pexels"}]
            
            results = await service.search_videos("query", provider="pexels")
        
            assert len(results) == 1
            assert results[0]["provider"] == "pexels"
            mock_cache.get.assert_called_once()
            mock_cache.set.assert_called_once()
            mock_search.assert_called_once()

    @patch("backend.services.video_search_service.search_cache")
    @pytest.mark.asyncio
    async def test_search_videos_cache_hit(self, mock_cache, service):
        mock_cache.get.return_value = [{"id": "cached"}]
        
        results = await service.search_videos("query", provider="pexels")
        
        assert len(results) == 1
        assert results[0]["id"] == "cached"
        # Verify provider method NOT called logic implicitly verified by lack of error/mock setup
    @patch("backend.services.video_search_service.serpapi_service.search_videos", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_search_google_implementation(self, mock_serp_search, service):
        mock_serp_search.return_value = [{"id": "g1", "provider": "google"}]
        service.serpapi_key = "key"
        
        results = await service._search_google("query", "landscape", "medium", 10)
        
        assert len(results) == 1
        assert results[0]["provider"] == "google"
        mock_serp_search.assert_called_once()

    @patch("backend.services.video_search_service.os.makedirs")
    @patch("backend.services.video_search_service.os.path.exists")
    @patch("backend.services.video_search_service.os.path.getsize")
    @pytest.mark.asyncio
    async def test_download_video_youtube(self, mock_getsize, mock_exists, mock_makedirs, service):
        # Mock youtube flow
        mock_exists.side_effect = [False, True] # First check false, second true
        mock_getsize.return_value = 1000
        
        # Mock yt_dlp module specifically since it is imported inside the function
        mock_ytdlp_module = MagicMock()
        mock_ytdl_class = MagicMock()
        mock_ytdlp_module.YoutubeDL.return_value.__enter__.return_value = mock_ytdl_class
        
        # We need to simulate loop.run_in_executor
        with patch.dict("sys.modules", {"yt_dlp": mock_ytdlp_module}):
            with patch("asyncio.get_event_loop") as mock_loop:
                # Setup executor to just call the function passsed to it
                async def side_effect(executor, func, *args):
                    return func(*args)
                
                mock_loop.return_value.run_in_executor.side_effect = side_effect
                
                res = await service.download_video(
                    "https://youtube.com/watch?v=123", "123", "google"
                )
                
        assert res["file_size"] == 1000
        assert "local_path" in res

    @patch("backend.services.video_search_service.os.makedirs")
    @patch("backend.services.video_search_service.os.path.exists")
    @patch("backend.services.video_search_service.os.path.getsize")
    @pytest.mark.asyncio
    async def test_download_video_direct_success(self, mock_getsize, mock_exists, mock_makedirs, service):
        mock_exists.return_value = False
        mock_getsize.return_value = 500
        
        # Setup Async Context Manager for stream
        mock_client = AsyncMock()
        
        # Response setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'content-length': '100'}
        # aiter_bytes needs to be an async iterator
        async def async_iter(chunk_size=None):
            yield b'chunk'
        mock_response.aiter_bytes = MagicMock(side_effect=async_iter)
        mock_response.raise_for_status = MagicMock()

        # Context manager setup for client.stream (which is NOT async itself, but returns an async CM)
        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)
        
        # IMPORTANT: stream is NOT async
        mock_client.stream = MagicMock(return_value=mock_stream_ctx)
        
        # Context manager for client itself (async with self._create_client() as client)
        mock_client_ctx = MagicMock()
        mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_ctx.__aexit__ = AsyncMock(return_value=None)
        
        with patch.object(service, '_create_client', return_value=mock_client_ctx):
            with patch("builtins.open", new_callable=MagicMock):
                res = await service.download_video("http://direct.mp4", "456", "pexels")
        
        assert res.get("file_size") == 500

    @patch("backend.services.video_search_service.os.path.exists", return_value=False)
    @pytest.mark.asyncio
    async def test_download_direct_retry_logic(self, mock_exists, service):
        # Setup failures then success
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        # Fail response
        mock_resp_fail = MagicMock()
        mock_resp_fail.status_code = 403
        
        # Success response
        mock_resp_ok = MagicMock()
        mock_resp_ok.status_code = 200
        mock_resp_ok.headers = {'content-length': '100'}
        async def async_iter(chunk_size=None):
            yield b'data'
        mock_resp_ok.aiter_bytes = MagicMock(side_effect=async_iter)

        # Stream context managers
        ctx_fail = MagicMock()
        ctx_fail.__aenter__ = AsyncMock(return_value=mock_resp_fail)
        ctx_fail.__aexit__ = AsyncMock(return_value=None)
        
        ctx_ok = MagicMock()
        ctx_ok.__aenter__ = AsyncMock(return_value=mock_resp_ok)
        ctx_ok.__aexit__ = AsyncMock(return_value=None)
        
        # Side effect on stream call
        mock_client.stream = MagicMock(side_effect=[ctx_fail, ctx_ok])
        
        mock_client_ctx = MagicMock()
        mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch.object(service, '_create_client', return_value=mock_client_ctx):
            with patch("builtins.open"), \
                 patch("backend.services.video_search_service.os.path.getsize", return_value=100), \
                 patch("backend.services.video_search_service.os.makedirs"), \
                 patch("asyncio.sleep", new_callable=AsyncMock): # Speed up retry
                 
                res = await service._download_direct("http://url", "id", "dir", "path")
        
        assert mock_client.stream.call_count == 2
        assert res.get("file_size") == 100
