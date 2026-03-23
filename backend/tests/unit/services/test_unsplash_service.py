import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from backend.services.unsplash_service import UnsplashService, unsplash_service
import httpx

class TestUnsplashService:
    @pytest.fixture
    def service(self):
        return UnsplashService()
    
    @patch("backend.services.unsplash_service.settings")
    @patch("backend.services.unsplash_service.log")
    def test_init_warns_on_missing_key(self, mock_log, mock_settings):
        """Test __init__ logs warning when API key is missing (line 20)"""
        mock_settings.UNSPLASH_ACCESS_KEY = None
        
        service = UnsplashService()
        
        mock_log.warning.assert_called_once()
        assert "UNSPLASH_ACCESS_KEY not found" in mock_log.warning.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_search_images_no_api_key(self, service):
        """Test search_images returns empty list when no API key (line 28)"""
        service.api_key = None
        
        results = await service.search_images("test")
        
        assert results == []
    
    @pytest.mark.asyncio
    @patch("backend.services.unsplash_service.search_cache")
    async def test_search_images_cache_hit(self, mock_cache, service):
        """Test search_images returns cached results (line 36)"""
        service.api_key = "test_key"
        cached_data = [{"id": "cached1"}]
        mock_cache.get.return_value = cached_data
        
        results = await service.search_images("test", use_cache=True)
        
        assert results == cached_data
        mock_cache.get.assert_called_once_with("unsplash", "test_landscape")
    
    @pytest.mark.asyncio
    @patch("backend.services.unsplash_service.search_cache")
    async def test_search_images_success_with_caching(self, mock_cache, service):
        """Test search_images fetches from API and caches results (lines 59, 75)"""
        service.api_key = "test_key"
        mock_cache.get.return_value = None  # Cache miss
        
        with patch("backend.services.unsplash_service.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": [{
                    "id": "img1",
                    "urls": {"regular": "http://img.com/reg.jpg", "thumb": "http://img.com/thumb.jpg"},
                    "width": 1920,
                    "height": 1080,
                    "description": "Test Image",
                    "user": {"name": "Test User", "links": {"html": "http://user.com"}}
                }]
            }
            mock_response.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_response
            
            results = await service.search_images("test", use_cache=True)
            
            assert len(results) == 1
            assert results[0]["id"] == "img1"
            # Verify cache was set
            mock_cache.set.assert_called_once_with("unsplash", "test_landscape", results)
    
    @pytest.mark.asyncio
    async def test_search_images_request_error(self, service):
        """Test search_images handles RequestError (lines 80-81)"""
        service.api_key = "test_key"
        
        with patch("backend.services.unsplash_service.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.RequestError("Network error")
            
            results = await service.search_images("test", use_cache=False)
            
            assert results == []
    
    @pytest.mark.asyncio
    async def test_search_images_http_status_error(self, service):
        """Test search_images handles HTTPStatusError (lines 83-84)"""
        service.api_key = "test_key"
        
        with patch("backend.services.unsplash_service.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_response.text = "Forbidden"
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "403 Forbidden", 
                request=MagicMock(), 
                response=mock_response
            )
            mock_client.get.return_value = mock_response
            
            results = await service.search_images("test", use_cache=False)
            
            assert results == []
    
    @pytest.mark.asyncio
    @patch("backend.services.unsplash_service.settings")
    async def test_search_images_api_error(self, mock_settings, service):
        """Test search_images handles API errors gracefully"""
        mock_settings.UNSPLASH_API_ACCESS_KEY = "test_key"
        
        with patch("backend.services.unsplash_service.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # Mock 403 error
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_client.get.return_value = mock_response
            
            # Execute
            results = await service.search_images("test", per_page=5, use_cache=False)
            
            # Verify returns empty list on error
            assert results == []
    
    @pytest.mark.asyncio
    @patch("backend.services.unsplash_service.settings")
    async def test_search_images_exception(self, mock_settings, service):
        """Test search_images handles exceptions gracefully"""
        mock_settings.UNSPLASH_API_ACCESS_KEY = "test_key"
        
        with patch("backend.services.unsplash_service.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # Mock exception
            mock_client.get.side_effect = Exception("Network error")
            
            # Execute
            results = await service.search_images("test", use_cache=False)
            
            # Verify returns empty list on exception
            assert results == []
    
    @pytest.mark.asyncio
    @patch("backend.services.unsplash_service.settings")
    async def test_search_images_portrait_orientation(self, mock_settings, service):
        """Test search_images with portrait orientation"""
        mock_settings.UNSPLASH_API_ACCESS_KEY = "test_key"
        
        with patch("backend.services.unsplash_service.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"results": []}
            mock_response.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_response
            
            await service.search_images("portrait", orientation="portrait", use_cache=False)
            
            # Verify orientation was passed
            call_args = mock_client.get.call_args
            assert call_args[1]["params"]["orientation"] == "portrait"
