from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from backend.services.unsplash_service import unsplash_service
from backend.services.image_storage_service import image_storage_service
from backend.core.logger import log
from backend.models.user import UserModel
from backend.api.deps import get_current_user

router = APIRouter()


from backend.services.serpapi_service import serpapi_service
from backend.services.cache_service import search_cache

@router.get("/search")
async def search_images(
    q: Optional[str] = Query(None, description="Search query"),
    limit: int = Query(20, ge=1, le=300, description="Number of results"),
    provider: str = Query("unsplash", description="Image provider", enum=["unsplash", "serpapi", "bing", "cache"]),
    orientation: Optional[str] = Query(None, description="Image orientation (landscape, portrait, square)"),
    only_if_cached: bool = Query(False, description="If true, only return results if they are already cached"),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Search for images using Unsplash, SerpApi (Google), Bing, or local Cache.
    
    Args:
        q: Search query (optional for 'cache', e.g., "sunset beach")
        limit: Number of results to return (max 300)
        provider: 'unsplash', 'serpapi', 'bing', 'cache'
        orientation: 'landscape', 'portrait', 'square'
        only_if_cached: If true, only checks cache. If miss, returns empty list.
    
    Returns:
        List of image objects with urls and metadata
    """
    try:
        results = []
        
        # 0. Cache Provider Logic (List recent images)
        if provider == "cache":
            # If q is just whitespace or empty, treat as None to list all recent
            search_query = q.strip() if q and q.strip() else None
            results = await search_cache.list_recent_images(limit=limit, query=search_query)
            return {"query": q, "provider": provider, "count": len(results), "results": results, "cached": True}

        # 1. Live Search (with internal service caching)
        if provider == "unsplash":
            # Delegation: UnsplashService handles its own caching logic
            results = await unsplash_service.search_images(
                q, 
                per_page=limit, 
                orientation=orientation or "landscape", 
                use_cache=True,
                only_if_cached=only_if_cached
            )
        elif provider in ["serpapi", "bing"]:
            # Delegation: SerpApiService handles its own caching logic
            results = await serpapi_service.search(
                provider=provider, 
                query=q, 
                per_page=limit, 
                orientation=orientation,
                only_if_cached=only_if_cached
            )
            
        return {"query": q, "provider": provider, "count": len(results), "results": results, "cached": True if only_if_cached else None}
        
    except ValueError as e:
        log.error(f"Image search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        log.error(f"Unexpected error in image search: {str(e)}")
        raise HTTPException(status_code=500, detail="Image search failed")


class ImageDownloadRequest(BaseModel):
    image_url: str
    video_id: int
    scene_id: str


class ImageCropRequest(BaseModel):
    video_id: int
    scene_id: str
    x: int = Query(..., ge=0)
    y: int = Query(..., ge=0)
    width: int = Query(..., gt=0)
    height: int = Query(..., gt=0)
    aspect_ratio: str = "16:9"


@router.post("/download")
async def download_image(req: ImageDownloadRequest, current_user: UserModel = Depends(get_current_user)):
    """
    Download an image from URL and save to storage.
    
    Returns:
        {
            "original_image_url": "images/123/1-1-1/original.jpg"
        }
    """
    try:
        path = await image_storage_service.download_image(
            req.image_url,
            req.video_id,
            req.scene_id
        )
        
        if not path:
             raise HTTPException(status_code=400, detail="Failed to download image (provider/access error)")
             
        return {"original_image_url": path}
    except ValueError as e:
        log.error(f"Image download failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Download failed")


@router.post("/crop")
async def crop_image(req: ImageCropRequest, current_user: UserModel = Depends(get_current_user)):
    """
    Crop an image based on coordinates.
    
    Returns:
        {
            "cropped_image_url": "images/123/1-1-1/cropped_16x9.jpg"
        }
    """
    try:
        path = await image_storage_service.crop_image(
            req.video_id,
            req.scene_id,
            req.x,
            req.y,
            req.width,
            req.height,
            req.aspect_ratio
        )
        return {"cropped_image_url": path}
    except ValueError as e:
        log.error(f"Image crop failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        log.error(f"Original image not found: {str(e)}")
        raise HTTPException(status_code=404, detail="Original image not found")
    except Exception as e:
        log.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Crop failed")
