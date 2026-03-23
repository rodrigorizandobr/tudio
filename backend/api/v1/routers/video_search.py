from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
from pydantic import BaseModel
from backend.api.deps import get_current_user
from backend.models.user import UserModel
from backend.services.video_search_service import video_search_service
from backend.core.logger import log

router = APIRouter()


@router.get("/search")
async def search_videos(
    q: str = Query(..., description="Search query"),
    limit: int = Query(20, ge=1, le=80, description="Number of results"),
    provider: str = Query("pexels", description="Video provider", enum=["pexels", "pixabay", "google"]),
    orientation: str = Query("landscape", description="Video orientation", enum=["landscape", "portrait", "square"]),
    size: str = Query("medium", description="Video quality/size", enum=["large", "medium", "small"]),
    only_if_cached: bool = Query(False, description="If true, only return results if they are already cached"),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Search for videos using Pexels, Pixabay, or Google.
    
    Args:
        q: Search query (e.g., "nature")
        limit: Number of results to return (max 80 for Pexels)
        provider: 'pexels', 'pixabay', 'google'
        orientation: 'landscape', 'portrait', 'square'
        size: 'large' (1080p), 'medium' (720p), 'small' (480p)
        only_if_cached: If true, only checks cache
    
    Returns:
        List of video objects with urls and metadata
    """
    try:
        # 1. Check Cache
        # (Handled by service)

        # 2. Search
        results = await video_search_service.search_videos(
            query=q, 
            provider=provider,
            orientation=orientation,
            size=size,
            per_page=limit, # Keep per_page for limit
            only_if_cached=only_if_cached # Keep only_if_cached
        )
        
        # If only_if_cached is True and no results, it means cache miss
        if only_if_cached and not results:
            return {
                "query": q, 
                "provider": provider, 
                "count": 0, 
                "results": [], 
                "cached": False, 
                "message": "No cached data found"
            }
        
        return {
            "query": q, 
            "provider": provider, 
            "count": len(results), 
            "results": results, 
            "cached": False  # Cache checking is internal to service
        }
        
    except ValueError as e:
        log.error(f"Video search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        log.error(f"Unexpected error in video search: {str(e)}")
        raise HTTPException(status_code=500, detail="Video search failed")


class VideoDownloadRequest(BaseModel):
    video_url: str
    video_id: str
    provider: str
    # Context for auto-association (optional)
    project_video_id: Optional[int] = None
    chapter_id: Optional[int] = None
    subchapter_id: Optional[int] = None
    scene_index: Optional[int] = None


@router.post("/download")
async def download_video(req: VideoDownloadRequest, current_user: UserModel = Depends(get_current_user)):
    """
    Download a video from URL and save to storage.
    
    Args:
        video_url: Direct URL to video file
        video_id: Unique identifier for the video (provider ID)
        provider: Video provider (pexels, pixabay, google)
        project_video_id: ID of the project video (optional)
        chapter_id: Chapter ID (optional)
        subchapter_id: Subchapter ID (optional)
        scene_index: Scene Index (optional)
    
    Returns:
        {
            "local_path": "storage/videos/pexels/12345.mp4",
            "file_size": 15728640
        }
    """
    try:
        result = await video_search_service.download_video(
            req.video_url,
            req.video_id,
            req.provider,
            project_video_id=req.project_video_id,
            chapter_id=req.chapter_id,
            subchapter_id=req.subchapter_id,
            scene_index=req.scene_index
        )
        
        # Check if there was an error
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except ValueError as e:
        log.error(f"Video download failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Download failed")
