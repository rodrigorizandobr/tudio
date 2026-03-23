import pytest
import os
import requests
from unittest.mock import MagicMock, patch, AsyncMock, ANY
from backend.services.video_search_service import VideoSearchService, video_search_service


@pytest.fixture
def mock_pexels_response():
    """Mock Pexels API response"""
    return {
        "videos": [
            {
                "id": 123456,
                "width": 1920,
                "height": 1080,
                "duration": 15,
                "image": "https://images.pexels.com/videos/123456/thumb.jpg",
                "user": {
                    "name": "Test User",
                    "url": "https://pexels.com/@testuser"
                },
                "video_files": [
                    {
                        "id": 1,
                        "quality": "hd",
                        "file_type": "video/mp4",
                        "width": 1920,
                        "height": 1080,
                        "link": "https://player.vimeo.com/video/123456",
                        "file_size": 15728640
                    },
                    {
                        "id": 2,
                        "quality": "sd",
                        "file_type": "video/mp4",
                        "width": 1280,
                        "height": 720,
                        "link": "https://player.vimeo.com/video/123456-sd",
                        "file_size": 7864320
                    }
                ]
            }
        ]
    }


def test_pexels_search_success(mock_pexels_response):
    """Test successful Pexels video search"""
    with patch("backend.core.configs.settings.PEXELS_API_KEY", "test-pexels-key"), \
         patch("backend.core.configs.settings.USE_PROXY", False):
        service = VideoSearchService()
        
        # Mock requests.get
        mock_response = MagicMock()
        mock_response.json.return_value = mock_pexels_response
        mock_response.raise_for_status = MagicMock()
        
        with patch("backend.services.video_search_service.requests.get", return_value=mock_response):
            results = service.search_videos(
                query="nature",
                provider="pexels",
                orientation="landscape",
                size="medium",
                per_page=10,
                use_cache=False
            )
            
            # Assertions
            assert len(results) == 1
            assert results[0]["id"] == "123456"
            assert results[0]["provider"] == "pexels"
            assert results[0]["thumbnail"] == "https://images.pexels.com/videos/123456/thumb.jpg"
            assert results[0]["duration"] == 15
            assert results[0]["author_name"] == "Test User"
            assert "video_url" in results[0]


def test_pexels_search_no_api_key():
    """Test Pexels search without API key"""
    with patch("backend.core.configs.settings.PEXELS_API_KEY", None):
        service = VideoSearchService()
        results = service.search_videos(
            query="nature",
            provider="pexels",
            use_cache=False
        )
        
        assert results == []


def test_pexels_search_api_error():
    """Test Pexels search with API error"""
    with patch("backend.core.configs.settings.PEXELS_API_KEY", "test-key"):
        service = VideoSearchService()
        
        # Mock request exception (must be RequestException to be caught)
        with patch("backend.services.video_search_service.requests.get", side_effect=requests.RequestException("API Error")):
            results = service.search_videos(
                query="nature",
                provider="pexels",
                use_cache=False
            )
            
            assert results == []


def test_pexels_quality_selection(mock_pexels_response):
    """Test video quality selection based on size parameter"""
    with patch("backend.core.configs.settings.PEXELS_API_KEY", "test-key"), \
         patch("backend.core.configs.settings.USE_PROXY", False):
        service = VideoSearchService()
        
        mock_response = MagicMock()
        mock_response.json.return_value = mock_pexels_response
        mock_response.raise_for_status = MagicMock()
        
        with patch("backend.services.video_search_service.requests.get", return_value=mock_response):
            # Test large (highest quality) - should pick first video_file
            results_large = service.search_videos(
                query="nature",
                provider="pexels",
                size="large",
                use_cache=False
            )
            # Large picks highest quality video file (1920x1080)
            assert results_large[0]["video_url"] == "https://player.vimeo.com/video/123456"
            
            # Test small (lowest quality) - should pick last video_file
            results_small = service.search_videos(
                query="nature",
                provider="pexels",
                size="small",
                use_cache=False
            )
            # Small picks lowest quality video file (1280x720)
            assert results_small[0]["video_url"] == "https://player.vimeo.com/video/123456-sd"


@pytest.mark.asyncio
async def test_download_video_success():
    """Test successful video download"""
    with patch("backend.core.configs.settings.PEXELS_API_KEY", "test-key"):
        service = VideoSearchService()
        
        # Mock video content
        mock_video_data = b"fake video content"
        mock_response = MagicMock()
        mock_response.headers = {"content-length": str(len(mock_video_data))}
        mock_response.iter_content = MagicMock(return_value=[mock_video_data])
        mock_response.raise_for_status = MagicMock()
        
        with patch("backend.services.video_search_service.requests.get", return_value=mock_response), \
             patch("backend.services.video_search_service.os.makedirs"), \
             patch("backend.services.video_search_service.os.path.exists", return_value=False), \
             patch("builtins.open", MagicMock()) as mock_open, \
             patch("backend.services.video_search_service.os.path.getsize", return_value=len(mock_video_data)):
            
            result = await service.download_video(
                video_url="https://test.com/video.mp4",
                video_id="12345",
                provider="pexels"
            )
            
            assert "local_path" in result
            assert result["local_path"].endswith("12345.mp4")
            assert result["file_size"] == len(mock_video_data)


@pytest.mark.asyncio
async def test_download_video_already_exists():
    """Test download when video already exists"""
    with patch("backend.core.configs.settings.PEXELS_API_KEY", "test-key"):
        service = VideoSearchService()
        
        with patch("backend.services.video_search_service.os.makedirs"), \
             patch("backend.services.video_search_service.os.path.exists", return_value=True), \
             patch("backend.services.video_search_service.os.path.getsize", return_value=1000000):
            
            result = await service.download_video(
                video_url="https://test.com/video.mp4",
                video_id="12345",
                provider="pexels"
            )
            
            assert result["local_path"].endswith("12345.mp4")
            assert result["file_size"] == 1000000


@pytest.mark.asyncio
async def test_download_video_too_large():
    """Test download fails for videos exceeding size limit"""
    with patch("backend.core.configs.settings.PEXELS_API_KEY", "test-key"):
        service = VideoSearchService()
        
        # Mock large file (60MB)
        large_size = 60 * 1024 * 1024
        mock_response = MagicMock()
        mock_response.headers = {"content-length": str(large_size)}
        mock_response.raise_for_status = MagicMock()
        
        with patch("backend.services.video_search_service.requests.get", return_value=mock_response), \
             patch("backend.services.video_search_service.os.makedirs"), \
             patch("backend.services.video_search_service.os.path.exists", return_value=False):
            
            result = await service.download_video(
                video_url="https://test.com/large_video.mp4",
                video_id="large123",
                provider="pexels"
            )
            
            assert "error" in result
            assert "exceeds 50MB limit" in result["error"]
            assert result["file_size"] == 0


def test_cache_functionality(mock_pexels_response):
    """Test that search results are cached"""
    with patch("backend.core.configs.settings.PEXELS_API_KEY", "test-key"), \
         patch("backend.core.configs.settings.USE_PROXY", False):
        service = VideoSearchService()
        
        mock_response = MagicMock()
        mock_response.json.return_value = mock_pexels_response
        mock_response.raise_for_status = MagicMock()
        
        with patch("backend.services.video_search_service.requests.get", return_value=mock_response) as mock_get, \
             patch("backend.services.cache_service.search_cache.get", return_value=None), \
             patch("backend.services.cache_service.search_cache.set") as mock_cache_set:
            
            results = service.search_videos(
                query="nature",
                provider="pexels",
                use_cache=True
            )
            
            # Should call cache.set with results
            mock_cache_set.assert_called_once()
            assert len(results) == 1


@pytest.fixture
def mock_pixabay_response():
    """Mock Pixabay API response"""
    return {
        "total": 500,
        "totalHits": 100,
        "hits": [
            {
                "id": 789012,
                "pageURL": "https://pixabay.com/videos/...",
                "type": "film",
                "tags": "beach, ocean, waves",
                "duration": 20,
                "picture_id": "456-789",
                "videos": {
                    "large": {
                        "url": "https://player.vimeo.com/large.mp4",
                        "width": 1920,
                        "height": 1080,
                        "size": 20000000
                    },
                    "medium": {
                        "url": "https://player.vimeo.com/medium.mp4",
                        "width": 1280,
                        "height": 720,
                        "size": 10000000
                    },
                    "small": {
                        "url": "https://player.vimeo.com/small.mp4",
                        "width": 640,
                        "height": 360,
                        "size": 5000000
                    }
                },
                "user": "pixabay_user",
                "userImageURL": "https://cdn.pixabay.com/user.jpg"
            }
        ]
    }


def test_pixabay_search_success(mock_pixabay_response):
    """Test successful Pixabay video search"""
    with patch("backend.core.configs.settings.PIXABAY_API_KEY", "test-pixabay-key"), \
         patch("backend.core.configs.settings.USE_PROXY", False):
        service = VideoSearchService()
        
        # Mock requests.get
        mock_response = MagicMock()
        mock_response.json.return_value = mock_pixabay_response
        mock_response.raise_for_status = MagicMock()
        
        with patch("backend.services.video_search_service.requests.get", return_value=mock_response) as mock_get:
            results = service.search_videos(
                query="beach",
                provider="pixabay",
                orientation="landscape",
                size="medium",
                per_page=10,
                use_cache=False
            )
            
            # Verify API call parameters
            mock_get.assert_called()
            call_args = mock_get.call_args
            assert call_args is not None
            url, kwargs = call_args[0], call_args[1]
            
            # Assert URL is correct
            assert "https://pixabay.com/api/videos/" in url[0] or url[0] == "https://pixabay.com/api/videos/"
            
            # Assert params do NOT contain orientation
            params = kwargs.get("params", {})
            assert "orientation" not in params
            assert params["q"] == "beach"
            assert params["video_type"] == "all"

            # Assertions
            assert len(results) == 1
            assert results[0]["id"] == "789012"
            assert results[0]["provider"] == "pixabay"
            assert results[0]["duration"] == 20
            assert results[0]["author_name"] == "pixabay_user"
            assert "video_url" in results[0]
            assert results[0]["video_url"] == "https://player.vimeo.com/medium.mp4"


def test_pixabay_search_no_api_key():
    """Test Pixabay search without API key"""
    with patch("backend.core.configs.settings.PIXABAY_API_KEY", None), \
         patch("backend.core.configs.settings.USE_PROXY", False):
        service = VideoSearchService()
        results = service.search_videos(
            query="beach",
            provider="pixabay",
            use_cache=False
        )
        
        assert results == []


def test_pixabay_search_api_error():
    """Test Pixabay search with API error"""
    with patch("backend.core.configs.settings.PIXABAY_API_KEY", "test-key"), \
         patch("backend.core.configs.settings.USE_PROXY", False):
        service = VideoSearchService()
        
        # Mock request exception
        with patch("backend.services.video_search_service.requests.get", side_effect=requests.RequestException("API Error")):
            results = service.search_videos(
                query="beach",
                provider="pixabay",
                use_cache=False
            )
            
            assert results == []


def test_pixabay_quality_selection(mock_pixabay_response):
    """Test video quality selection based on size parameter"""
    with patch("backend.core.configs.settings.PIXABAY_API_KEY", "test-key"), \
         patch("backend.core.configs.settings.USE_PROXY", False):
        service = VideoSearchService()
        
        mock_response = MagicMock()
        mock_response.json.return_value = mock_pixabay_response
        mock_response.raise_for_status = MagicMock()
        
        with patch("backend.services.video_search_service.requests.get", return_value=mock_response):
            # Test large (highest quality)
            results_large = service.search_videos(
                query="beach",
                provider="pixabay",
                size="large",
                use_cache=False
            )
            assert results_large[0]["video_url"] == "https://player.vimeo.com/large.mp4"
            assert results_large[0]["width"] == 1920
            
            # Test small (lowest quality)
            results_small = service.search_videos(
                query="beach",
                provider="pixabay",
                size="small",
                use_cache=False
            )
            assert results_small[0]["video_url"] == "https://player.vimeo.com/small.mp4"
            assert results_small[0]["width"] == 640




@pytest.fixture
def mock_serpapi_response():
    """Mock SerpApi video results"""
    return [
        {
            "id": "75170fc230cd",
            "provider": "google",
            "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
            "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "duration": 0,
            "width": 0,
            "height": 0,
            "author_name": "Rick Astley",
            "author_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "description": "Rick Astley - Never Gonna Give You Up"
        },
        {
            "id": "e6f477038e15",
            "provider": "google",
            "thumbnail": "https://i.vimeocdn.com/video/123_295x166.jpg",
            "video_url": "https://vimeo.com/12345678",
            "duration": 0,
            "width": 0,
            "height": 0,
            "author_name": "Vimeo",
            "author_url": "https://vimeo.com/12345678",
            "description": "Amazing Nature Content"
        }
    ]


def test_google_search_success(mock_serpapi_response):
    """Test successful Google video search via SerpApi delegation"""
    # We now check that VideoSearchService correctly delegates to SerpApiService
    
    with patch("backend.core.configs.settings.SERPAPI_API_KEY", "test-serp-key"):
        service = VideoSearchService()
        
        # Mock the imported serpapi_service instance
        with patch("backend.services.video_search_service.serpapi_service") as mock_serp_service:
            mock_serp_service.search_videos.return_value = mock_serpapi_response
            
            results = service.search_videos(
                query="rick roll",
                provider="google",
                per_page=10,
                use_cache=False
            )
            
            # Verify delegation
            mock_serp_service.search_videos.assert_called_once_with(
                query="rick roll",
                per_page=10
            )
            
            # Verify Results (just mapped from mock)
            assert len(results) == 2
            assert results[0]["provider"] == "google"
            assert results[0]["description"] == "Rick Astley - Never Gonna Give You Up"
            assert results[0]["id"] == "75170fc230cd"


def test_google_search_no_api_key():
    """Test Google search without API key checks"""
    # Even if key is missing in video service check, it returns empty list early
    # But let's verify if video service checks key before calling serpapi
    with patch("backend.core.configs.settings.SERPAPI_API_KEY", None):
        service = VideoSearchService()
        
        with patch("backend.services.video_search_service.serpapi_service") as mock_serp_service:
            results = service.search_videos(
                query="test",
                provider="google",
                use_cache=False
            )
            
            # Should return empty before calling service or service returns empty
            # Our implementation checks key first
            assert results == []
            mock_serp_service.search_videos.assert_not_called()


def test_google_search_error():
    """Test Google search error handling"""
    with patch("backend.core.configs.settings.SERPAPI_API_KEY", "test-key"):
        service = VideoSearchService()
        
        # Mock exception or empty return from serpapi_service
        # SerpApiService returns [] on error, so we test that propagation
        with patch("backend.services.video_search_service.serpapi_service") as mock_serp_service:
            mock_serp_service.search_videos.return_value = []
            
            results = service.search_videos(
                query="test",
                provider="google",
                use_cache=False
            )
            assert results == []


