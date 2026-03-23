import pytest
import httpx
from unittest.mock import MagicMock, patch, AsyncMock
from backend.services.video_search_service import VideoSearchService

@pytest.fixture
def video_search_service():
    with patch("backend.services.video_search_service.create_proxy_config") as mock_proxy:
        mock_proxy.return_value = MagicMock(use_proxy=False, verify_ssl=True)
        return VideoSearchService()

@pytest.mark.asyncio
async def test_search_videos_cache_hit(video_search_service):
    with patch("backend.services.video_search_service.search_cache") as mock_cache:
        mock_cache.get.return_value = [{"id": "1", "provider": "cached"}]
        
        results = await video_search_service.search_videos("query", use_cache=True)
        
        assert len(results) == 1
        assert results[0]["provider"] == "cached"
        mock_cache.get.assert_called()

@pytest.mark.asyncio
async def test_search_videos_pexels_success(video_search_service):
    with patch("backend.services.video_search_service.search_cache") as mock_cache, \
         patch.object(video_search_service, "_search_pexels", new_callable=AsyncMock) as mock_pexels:
         
         mock_cache.get.return_value = None
         mock_pexels.return_value = [{"id": "2", "provider": "pexels"}]
         
         results = await video_search_service.search_videos("query", provider="pexels")
         
         assert len(results) == 1
         assert results[0]["provider"] == "pexels"
         mock_pexels.assert_called()
         mock_cache.set.assert_called()

@pytest.mark.asyncio
async def test_search_videos_pixabay_success(video_search_service):
    with patch("backend.services.video_search_service.search_cache") as mock_cache, \
         patch.object(video_search_service, "_search_pixabay", new_callable=AsyncMock) as mock_pixabay:
         
         mock_cache.get.return_value = None
         mock_pixabay.return_value = [{"id": "3", "provider": "pixabay"}]
         
         results = await video_search_service.search_videos("query", provider="pixabay")
         
         assert len(results) == 1
         assert results[0]["provider"] == "pixabay"
         mock_pixabay.assert_called()

@pytest.mark.asyncio
async def test_search_videos_google_success(video_search_service):
    with patch("backend.services.video_search_service.search_cache") as mock_cache, \
         patch.object(video_search_service, "_search_google", new_callable=AsyncMock) as mock_google:
         
         mock_cache.get.return_value = None
         mock_google.return_value = [{"id": "4", "provider": "google"}]
         
         results = await video_search_service.search_videos("query", provider="google")
         
         assert len(results) == 1
         assert results[0]["provider"] == "google"
         mock_google.assert_called()

@pytest.mark.asyncio
async def test_search_videos_unknown_provider(video_search_service):
    results = await video_search_service.search_videos("query", provider="unknown")
    assert results == []

@pytest.mark.asyncio
async def test_search_videos_only_if_cached_miss(video_search_service):
    with patch("backend.services.video_search_service.search_cache") as mock_cache:
        mock_cache.get.return_value = None
        results = await video_search_service.search_videos("query", only_if_cached=True)
        assert results == []

@pytest.mark.asyncio
async def test_search_pexels_no_key(video_search_service):
    video_search_service.pexels_api_key = None
    results = await video_search_service._search_pexels("query", "landscape", "medium", 1)
    assert results == []

@pytest.mark.asyncio
async def test_search_pixabay_no_key(video_search_service):
    video_search_service.pixabay_api_key = None
    results = await video_search_service._search_pixabay("query", "landscape", "medium", 1)
    assert results == []

@pytest.mark.asyncio
async def test_search_google_no_key(video_search_service):
    video_search_service.serpapi_key = None
    results = await video_search_service._search_google("query", "landscape", "medium", 1)
    assert results == []

@pytest.mark.asyncio
async def test_download_video_error(video_search_service):
    with patch("os.makedirs"):
        # This will trigger the broad exception in download_video
        with patch.object(video_search_service, "_download_direct", side_effect=Exception("Download failed")):
            result = await video_search_service.download_video("url", "vid123", "pexels")
            assert "error" in result
            assert result["error"] == "Download failed"

@pytest.mark.asyncio
async def test_download_direct_pexels_error(video_search_service):
    with patch.object(video_search_service, "_create_client") as mock_client_factory:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.stream.side_effect = httpx.RequestError("Stream failed")
        mock_client_factory.return_value = mock_client
        
        # Test direct download retry failure
        with patch("asyncio.sleep", AsyncMock()): # skip delay
            result = await video_search_service._download_direct("url", "vid123", "dir", "path")
            assert "error" in result

@pytest.mark.asyncio
async def test_pexels_api_request_error(video_search_service):
    video_search_service.pexels_api_key = "test_key"
    with patch.object(video_search_service, "_create_client") as mock_client_factory:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.side_effect = httpx.RequestError("API failed")
        mock_client_factory.return_value = mock_client
        
        results = await video_search_service._search_pexels("query", "landscape", "medium", 1)
        assert results == []

@pytest.mark.asyncio
async def test_pixabay_api_request_error(video_search_service):
    video_search_service.pixabay_api_key = "test_key"
    with patch.object(video_search_service, "_create_client") as mock_client_factory:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.side_effect = httpx.RequestError("API failed")
        mock_client_factory.return_value = mock_client
        
        results = await video_search_service._search_pixabay("query", "landscape", "medium", 1)
        assert results == []
