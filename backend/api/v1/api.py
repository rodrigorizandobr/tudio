from fastapi import APIRouter
from backend.api.v1.routers import videos, auth, users, settings, images, agents, video_search, voices, social, music, captions

api_router = APIRouter()
api_router.include_router(videos.router, prefix="/videos", tags=["videos"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(images.router, prefix="/images", tags=["images"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(video_search.router, prefix="/video-search", tags=["video-search"])
api_router.include_router(voices.router, prefix="/voices", tags=["voices"])
api_router.include_router(social.router, prefix="/social", tags=["social"])
api_router.include_router(music.router, prefix="/music", tags=["music"])
api_router.include_router(captions.router, prefix="", tags=["captions"])


