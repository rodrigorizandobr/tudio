import os
import httpx
from PIL import Image
from io import BytesIO
from typing import Tuple
from backend.core.configs import settings
from backend.core.logger import log


class ImageStorageService:
    """
    Service to download and store images.
    """

    def __init__(self):
        self.storage_base = os.path.join(settings.STORAGE_DIR, "images")
        os.makedirs(self.storage_base, exist_ok=True)

    async def download_image(
        self, 
        image_url: str, 
        video_id: int, 
        scene_id: str
    ) -> str:
        """
        Download an image from URL and save to storage.
        
        Args:
            image_url: URL of the image to download
            video_id: ID of the video/script
            scene_id: ID of the scene (e.g., "1-1-1")
        
        Returns:
            Relative path to saved image (for storage in DB)
        """
        import uuid
        
        # Create directory structure
        scene_dir = os.path.join(self.storage_base, str(video_id), str(scene_id))
        os.makedirs(scene_dir, exist_ok=True)

        # Clean up existing files first
        if os.path.exists(scene_dir):
            for f in os.listdir(scene_dir):
                # Match original* and cropped* to clean up old files
                if f.startswith('original') or f.startswith('cropped_'):
                    try:
                        os.path.join(scene_dir, f) # Access check
                        os.remove(os.path.join(scene_dir, f))
                    except OSError as e:
                        log.warning(f"Failed to delete old file {f}: {e}")

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
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            for attempt in range(max_retries):
                try:
                    # Rotate User-Agent based on attempt
                    current_ua = user_agents[attempt % len(user_agents)]
                    
                    headers = {
                        'User-Agent': current_ua,
                        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7',
                        'Referer': 'https://www.google.com/',
                        'Sec-Ch-Ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
                        'Sec-Ch-Ua-Mobile': '?0',
                        'Sec-Ch-Ua-Platform': '"macOS"',
                        'Sec-Fetch-Dest': 'image',
                        'Sec-Fetch-Mode': 'no-cors',
                        'Sec-Fetch-Site': 'cross-site'
                    }
                    
                    if not image_url or not image_url.startswith(('http://', 'https://')):
                         log.warning(f"Invalid image URL skipped: {image_url}")
                         return ""

                    response = await client.get(image_url, headers=headers)
                    
                    # If 403 and we have retries left, try next UA immediately
                    if response.status_code == 403 and attempt < max_retries - 1:
                        log.warning(f"403 Forbidden for {image_url} with UA {attempt}. Retrying with different UA...")
                        continue

                    response.raise_for_status()

                    # Open image to validate and get format
                    # Note: PIL.Image.open is CPU bound + read from memory stream.
                    # Ideally we run this in sync executor but for now this is cleaner than Requests.
                    img = Image.open(BytesIO(response.content))
                    
                    # Determine format
                    format_ext = img.format.lower() if img.format else 'jpg'
                    if format_ext == 'jpeg':
                        format_ext = 'jpg'
                    if format_ext == 'webp':
                         pass

                    # Save original with UUID to bust cache
                    unique_id = uuid.uuid4().hex[:8]
                    original_filename = f"original_{unique_id}.{format_ext}"
                    original_path = os.path.join(scene_dir, original_filename)
                    img.save(original_path, quality=95)

                    # Return relative path from storage root
                    rel_path = f"images/{video_id}/{scene_id}/{original_filename}"
                    log.info(f"Downloaded image to {rel_path} (attempt {attempt + 1})")
                    return rel_path
                    
                except (httpx.RequestError, 
                        httpx.HTTPStatusError,
                        ConnectionResetError) as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        import asyncio
                        log.warning(f"Download attempt {attempt + 1} failed: {str(e)}. Retrying in {retry_delay}s...")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                    continue
                    
                except Exception as e:
                    log.error(f"Failed to download image: {str(e)}")
                    return ""

        # All retries exhausted
        log.error(f"Failed to download image after {max_retries} attempts: {str(last_error)}")
        # Return empty string instead of raising to allow partial processing if desired, 
        # but current RenderService expects file. Let's return empty and handle upstream?
        # RenderService checks `if not os.path.exists...`. So returning "" means it won't exist.
        return ""

    async def crop_image(
        self,
        video_id: int,
        scene_id: str,
        x: int,
        y: int,
        width: int,
        height: int,
        aspect_ratio: str = "16:9"
    ) -> str:
        """
        Async wrapper for crop_image_sync.
        """
        import asyncio
        return await asyncio.to_thread(
            self._crop_image_sync,
            video_id, scene_id, x, y, width, height, aspect_ratio
        )

    def _crop_image_sync(
        self,
        video_id: int,
        scene_id: str,
        x: int,
        y: int,
        width: int,
        height: int,
        aspect_ratio: str = "16:9"
    ) -> str:
        """
        Crop an image based on coordinates.
        """
        if width <= 0 or height <= 0:
            raise ValueError(f"Invalid crop dimensions: width={width}, height={height}")

        try:
            scene_dir = os.path.join(self.storage_base, str(video_id), str(scene_id))
            
            # Find original image
            if not os.path.exists(scene_dir):
                raise FileNotFoundError(f"Scene dir not found: {scene_dir}")

            original_candidates = [
                f for f in os.listdir(scene_dir) 
                if f.startswith('original')
            ]
            if not original_candidates:
                raise FileNotFoundError("Original image not found")
            
            # Use latest original
            original_path = os.path.join(scene_dir, original_candidates[0])
            
            # Load and crop
            img = Image.open(original_path)
            cropped = img.crop((x, y, x + width, y + height))
            
            # Save cropped
            format_ext = img.format.lower() if img.format else 'jpg'
            if format_ext == 'jpeg':
                format_ext = 'jpg'
            
            import uuid
            unique_id = uuid.uuid4().hex[:8]
            aspect_safe = aspect_ratio.replace(':', 'x')
            cropped_filename = f"cropped_{aspect_safe}_{unique_id}.{format_ext}"
            cropped_path = os.path.join(scene_dir, cropped_filename)
            cropped.save(cropped_path, quality=95)

            rel_path = f"images/{video_id}/{scene_id}/{cropped_filename}"
            log.info(f"Cropped image saved to {rel_path}")
            return rel_path

        except Exception as e:
            log.error(f"Failed to crop image: {str(e)}")
            raise ValueError(f"Image crop failed: {str(e)}")


    async def calculate_center_crop_coords(
        self,
        image_path: str,
        target_aspect_ratio: str = "16:9"
    ) -> Tuple[int, int, int, int]:
        """
        Async wrapper for calculate_center_crop_coords_sync.
        """
        import asyncio
        return await asyncio.to_thread(
            self._calculate_center_crop_coords_sync,
            image_path, target_aspect_ratio
        )

    def _calculate_center_crop_coords_sync(
        self,
        image_path: str,
        target_aspect_ratio: str = "16:9"
    ) -> Tuple[int, int, int, int]:
        """
        Calculates crop coordinates (x, y, w, h) for a center crop.
        """
        try:
            # Resolve absolute path
            abs_path = os.path.join(settings.STORAGE_DIR, image_path)
            
            if not os.path.exists(abs_path):
                 log.warning(f"Image for crop calc not found: {abs_path}")
                 return 0,0,100,100

            with Image.open(abs_path) as img:
                width, height = img.size
                
                target_ratio = 16/9
                if target_aspect_ratio == "9:16":
                    target_ratio = 9/16
                    
                current_ratio = width / height
                
                if current_ratio > target_ratio:
                    # Too wide, crop width
                    new_width = int(height * target_ratio)
                    new_height = height
                    x = (width - new_width) // 2
                    y = 0
                else:
                    # Too tall, crop height
                    new_width = width
                    new_height = int(width / target_ratio)
                    x = 0
                    y = (height - new_height) // 2
                    
                return x, y, new_width, new_height
                
        except Exception as e:
            log.error(f"Failed to calc crop: {e}")
            return 0, 0, 100, 100 


# Singleton instance
image_storage_service = ImageStorageService()

# --- MOCK FOR TESTING ---
if settings.TESTING and os.getenv("USE_E2E_MOCKS") == "True":
    log.warning("⚠️ E2E MOCK MODE DETECTED: Mocking ImageStorageService for E2E tests.")
    
    async def mock_download_image(self, image_url: str, video_id: int, scene_id: str) -> str:
        """
        Mock implementation that creates a dummy image locally.
        """
        scene_dir = os.path.join(self.storage_base, str(video_id), str(scene_id))
        os.makedirs(scene_dir, exist_ok=True)
        
        import uuid
        unique_id = uuid.uuid4().hex[:8]
        filename = f"original_{unique_id}.jpg"
        file_path = os.path.join(scene_dir, filename)
        
        # Create a simple solid color image
        img = Image.new('RGB', (100, 100), color = (73, 109, 137))
        img.save(file_path)
        
        rel_path = f"images/{video_id}/{scene_id}/{filename}"
        log.info(f"MOCK Downloaded image to {rel_path}")
        return rel_path

    ImageStorageService.download_image = mock_download_image # type: ignore
