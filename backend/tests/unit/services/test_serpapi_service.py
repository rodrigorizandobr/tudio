
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from backend.services.serpapi_service import SerpApiService
import json

class TestSerpapiService:

    @pytest.fixture
    def service(self):
        return SerpApiService()

    @pytest.mark.asyncio
    async def test_search_cache_hit(self, service):
        with patch("backend.services.serpapi_service.search_cache") as mock_cache:
            mock_cache.get.return_value = [{"id": "cached"}]
            
            results = await service.search("google", "query")
            
            assert len(results) == 1
            assert results[0]["id"] == "cached"
            mock_cache.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_google_images_success(self, service):
        mock_response_data = {
            "images_results": [
                {
                    "original": "http://img.com/1.jpg",
                    "thumbnail": "http://thumb.com/1.jpg",
                    "title": "Title 1",
                    "source": "Source 1",
                    "original_width": 100,
                    "original_height": 100
                }
            ]
        }
        
        # Response must be MagicMock (sync methods)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        
        with patch("backend.services.serpapi_service.httpx.AsyncClient", return_value=mock_client):
            with patch("backend.services.serpapi_service.search_cache") as mock_cache:
                mock_cache.get.return_value = None
                
                results = await service.search("google", "query", orientation="landscape")
                
                assert len(results) == 1
                assert results[0]["url"] == "http://img.com/1.jpg"
                assert results[0]["provider"] == "google"
                mock_cache.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_videos_success(self, service):
        mock_response_data = {
            "video_results": [
                {
                    "link": "http://video.com/1.mp4",
                    "thumbnail": "http://thumb.com/v1.jpg",
                    "title": "Video 1",
                    "source": "Youtube"
                }
            ]
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        
        with patch("backend.services.serpapi_service.httpx.AsyncClient", return_value=mock_client):
             with patch("backend.services.serpapi_service.search_cache") as mock_cache:
                mock_cache.get.return_value = None
                
                results = await service.search_videos("query")
                
                assert len(results) == 1
                assert results[0]["video_url"] == "http://video.com/1.mp4"
                assert results[0]["id"]
    
    @pytest.mark.asyncio
    async def test_unwrap_logic_double_encoded(self, service):
        # Case where API returns a string that contains JSON that contains string that contains JSON
        inner_json = json.dumps({"images_results": [{"original": "http://img.com"}]})
        outer_json = json.dumps(inner_json) # String of JSON
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = outer_json
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        
        with patch("backend.services.serpapi_service.httpx.AsyncClient", return_value=mock_client):
             with patch("backend.services.serpapi_service.search_cache") as mock_cache:
                mock_cache.get.return_value = None
                
                results = await service.search("google", "complex_query")
                
                assert len(results) == 1
                assert results[0]["url"] == "http://img.com"

    @pytest.mark.asyncio
    async def test_search_error_handling(self, service):
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.side_effect = Exception("Network Error")
        
        with patch("backend.services.serpapi_service.httpx.AsyncClient", return_value=mock_client):
             results = await service.search("google", "query")
             assert results == []

    @pytest.mark.asyncio
    async def test_search_api_error_response(self, service):
         mock_response = MagicMock()
         mock_response.status_code = 200
         mock_response.json.return_value = {"error": "Invalid API Key"}
         mock_response.raise_for_status = MagicMock()

         mock_client = AsyncMock()
         mock_client.__aenter__.return_value = mock_client
         mock_client.post.return_value = mock_response
         
         with patch("backend.services.serpapi_service.httpx.AsyncClient", return_value=mock_client):
             results = await service.search("google", "query")
             assert results == []
