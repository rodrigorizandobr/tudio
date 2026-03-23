
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, mock_open
from backend.services.image_storage_service import ImageStorageService
import os
from PIL import Image
import httpx

class TestImageStorageService:
    @pytest.fixture
    def service(self):
        return ImageStorageService()

    # EXISTING TESTS (keep them)
    @patch("backend.services.image_storage_service.httpx.AsyncClient")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.makedirs")
    @patch("os.path.exists", return_value=False)
    @patch("PIL.Image.open")
    @pytest.mark.asyncio
    async def test_download_image_success(self, mock_img_open, mock_exists, mock_makedirs, mock_file, mock_client, service):
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"fake image"
        mock_response.raise_for_status = MagicMock()
        mock_instance.get.return_value = mock_response

        mock_img = MagicMock()
        mock_img.format = "JPEG"
        mock_img_open.return_value = mock_img
        
        result = await service.download_image("http://img.com/a.jpg", 1, "1-1")
        
        assert "images/1/1-1/original_" in result
        mock_makedirs.assert_called()
        mock_img.save.assert_called() 

    # NEW TESTS FOR UNCOVERED LINES
    @patch("os.path.exists", return_value=True)
    @patch("os.listdir", return_value=["original_old.jpg", "cropped_old.jpg"])
    @patch("os.remove")
    @patch("backend.services.image_storage_service.httpx.AsyncClient")
    @patch("PIL.Image.open")
    @pytest.mark.asyncio
    async def test_download_image_cleans_old_files(self, mock_img_open, mock_client, mock_remove, mock_listdir, mock_exists, service):
        """Test that download_image cleans up old files (lines 44-51)"""
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"fake"
        mock_response.raise_for_status = MagicMock()
        mock_instance.get.return_value = mock_response

        mock_img = MagicMock()
        mock_img.format = "JPEG"
        mock_img_open.return_value = mock_img
        
        await service.download_image("http://img.com/a.jpg", 1, "1-1")
        
        # Verify old files were removed (lines 46-51)
        assert mock_remove.call_count == 2  # Both original and cropped

    @patch("backend.services.image_storage_service.httpx.AsyncClient")
    @pytest.mark.asyncio
    async def test_download_image_invalid_url(self, mock_client, service):
        """Test invalid URL returns empty string (lines 84-86)"""
        result = await service.download_image("not-a-url", 1, "1-1")
        assert result == ""
        
        result = await service.download_image("", 1, "1-1")
        assert result == ""

    @patch("backend.services.image_storage_service.httpx.AsyncClient")
    @patch("os.makedirs")
    @patch("os.path.exists", return_value=False)
    @pytest.mark.asyncio
    async def test_download_image_403_retries(self, mock_exists, mock_makedirs, mock_client, service):
        """Test 403 responses trigger retry with different UA (lines 91-93)"""
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        
        # First two attempts return 403, third succeeds
        mock_response_403 = MagicMock()
        mock_response_403.status_code = 403
        
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.content = b"image"
        mock_response_200.raise_for_status = MagicMock()
        
        mock_instance.get.side_effect = [mock_response_403, mock_response_403, mock_response_200]
        
        with patch("PIL.Image.open") as mock_img_open:
            mock_img = MagicMock()
            mock_img.format = "JPEG"
            mock_img_open.return_value = mock_img
            
            result = await service.download_image("http://img.com/a.jpg", 1, "1-1")
            
            assert "images/1/1-1/original_" in result
            assert mock_instance.get.call_count == 3  # Retried twice

    @patch("backend.services.image_storage_service.httpx.AsyncClient")
    @patch("os.makedirs")
    @patch("os.path.exists", return_value=False)
    @pytest.mark.asyncio
    async def test_download_image_all_retries_fail(self, mock_exists, mock_makedirs, mock_client, service):
        """Test all retries exhausted returns empty (lines 120-140)"""
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        
        mock_instance.get.side_effect = httpx.RequestError("Network error")
        
        result = await service.download_image("http://img.com/a.jpg", 1, "1-1")
        
        assert result == ""
        assert mock_instance.get.call_count == 3  # Max retries

    @patch("os.path.exists", return_value=True)
    def test_crop_image_invalid_dimensions(self, mock_exists, service):
        """Test crop_image raises error for invalid dimensions (line 156)"""
        with pytest.raises(ValueError, match="Invalid crop dimensions"):
            service.crop_image(1, "1-1", 0, 0, -100, 50)
        
        with pytest.raises(ValueError, match="Invalid crop dimensions"):
            service.crop_image(1, "1-1", 0, 0, 100, 0)

    @patch("os.path.exists", return_value=False)
    def test_crop_image_dir_not_found(self, mock_exists, service):
        """Test crop_image raises error when dir doesn't exist (line 164)"""
        with pytest.raises(ValueError, match="Image crop failed"):
            service.crop_image(1, "1-1", 0, 0, 100, 100)

    @patch("os.path.exists", return_value=True)
    @patch("os.listdir", return_value=[])
    def test_crop_image_no_original_found(self, mock_listdir, mock_exists, service):
        """Test crop_image raises error when no original image (line 171)"""
        with pytest.raises(ValueError, match="Image crop failed"):
            service.crop_image(1, "1-1", 0, 0, 100, 100)

    @patch("os.path.exists", return_value=True)
    @patch("os.listdir", return_value=["original_123.jpg"])
    @patch("PIL.Image.open")
    def test_crop_image_generic_error(self, mock_img_open, mock_listdir, mock_exists, service):
        """Test crop_image handles generic errors (lines 197-199)"""
        mock_img_open.side_effect = Exception("PIL error")
        
        with pytest.raises(ValueError, match="Image crop failed"):
            service.crop_image(1, "1-1", 0, 0, 100, 100)

    @patch("os.path.exists", return_value=False)
    @patch("backend.services.image_storage_service.settings")
    def test_calculate_center_crop_file_not_found(self, mock_settings, mock_exists, service):
        """Test calculate_center_crop returns default when file not found (lines 215-216)"""
        mock_settings.STORAGE_DIR = "/fake"
        
        x, y, w, h = service.calculate_center_crop_coords("fake/path.jpg")
        
        assert (x, y, w, h) == (0, 0, 100, 100)

    @patch("os.path.exists", return_value=True)
    @patch("PIL.Image.open")
    @patch("backend.services.image_storage_service.settings")
    def test_calculate_center_crop_error_handling(self, mock_settings, mock_img_open, mock_exists, service):
        """Test calculate_center_crop returns default on error (lines 242-244)"""
        mock_settings.STORAGE_DIR = "/fake"
        mock_img_open.side_effect = Exception("Can't open")
        
        x, y, w, h = service.calculate_center_crop_coords("fake/path.jpg")
        
        assert (x, y, w, h) == (0, 0, 100, 100)

    # Keep existing crop tests
    @patch("os.path.exists", return_value=True)
    def test_crop_image_success(self, mock_exists, service):
        with patch("PIL.Image.open") as mock_img_open:
            mock_img = MagicMock()
            mock_img.format = "JPEG"
            mock_img.crop.return_value = mock_img
            mock_img_open.return_value = mock_img
            
            with patch("os.listdir", return_value=["original_123.jpg"]):
                result = service.crop_image(1, "1-1", 0, 0, 100, 100)
                
                assert "images/1/1-1/cropped_" in result
                mock_img.crop.assert_called()
                mock_img.save.assert_called()

    @patch("os.path.exists", return_value=True)
    def test_calculate_center_crop(self, mock_exists, service):
        with patch("PIL.Image.open") as mock_img_open:
            mock_img = MagicMock()
            mock_img.size = (1920, 1080)
            mock_img_open.return_value.__enter__.return_value = mock_img
            
            x, y, w, h = service.calculate_center_crop_coords("path", "16:9")
            assert w == 1920
            
            mock_img.size = (1920, 1080)
            x, y, w, h = service.calculate_center_crop_coords("path", "9:16")
            assert w == 607
            assert h == 1080
            assert x > 0
