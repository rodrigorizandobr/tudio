
import pytest
from unittest.mock import patch, Mock
from backend.services.serpapi_service import serpapi_service

@patch("backend.services.serpapi_service.requests.post")
def test_search_videos_payload_localization(mock_post):
    """
    Verify that search_videos sends the correct payload with gl=br and hl=pt-br
    """
    # Setup mock response
    mock_response = Mock()
    mock_response.json.return_value = {"video_results": []}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    # Call service
    serpapi_service.search_videos("test query")

    # Assert POST was called
    mock_post.assert_called_once()
    
    # Check arguments
    args, kwargs = mock_post.call_args
    data = kwargs.get("data", {})
    
    assert data["gl"] == "br"
    assert data["hl"] == "pt-br"
    assert data["engine"] == "google_videos"
    assert data["q"] == "test query"

@patch("backend.services.serpapi_service.requests.post")
def test_search_payload_localization(mock_post):
    """
    Verify that search (images) sends the correct payload with gl=br and hl=pt-br
    """
    # Setup mock response
    mock_response = Mock()
    mock_response.json.return_value = {"images_results": []}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    # Call service
    serpapi_service.search("google", "test query")

    # Assert POST was called
    mock_post.assert_called_once()
    
    # Check arguments
    args, kwargs = mock_post.call_args
    data = kwargs.get("data", {})
    
    assert data["gl"] == "br"
    assert data["hl"] == "pt-br"
    assert data["engine"] == "google_images"
