import os
from typing import List, Optional, Any
from fastapi import FastAPI, Query, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.core.configs import settings
from backend.api.v1.api import api_router
from backend.schemas.video import VideoRead
from backend.core.logger import log

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/doc",
    redoc_url=None
)

# CORS Configuration (Security GAP-SEC-01 Fix)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",  # Development
        # Add production URLs when deploying
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Security Headers Middleware (Security GAP-SEC-03 Fix)
from backend.middleware.security import SecurityHeadersMiddleware
app.add_middleware(SecurityHeadersMiddleware)

# Rate Limiting (Security GAP-SEC-02 Fix)
from backend.core.rate_limiting import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(api_router, prefix=settings.API_V1_STR)


# Mount storage directory for serving uploaded/downloaded files
app.mount("/api/storage", StaticFiles(directory=settings.STORAGE_DIR), name="storage")

@app.on_event("startup")
async def startup_event():
    log.info("Starting Tudio V2 Application (JSON Persistence)...")
    log.info(f"Checking data directories...")
    if not os.path.exists(settings.DATA_DIR):
        log.warning(f"Data dir not found at {settings.DATA_DIR}, creating...")
        os.makedirs(settings.DATA_DIR, exist_ok=True)
        
    # Debug API Key Loading
    key = settings.OPENAI_API_KEY
    if key:
        masked = key[:4] + "..." + key[-4:] if len(key) > 8 else "***"
        log.info(f"API Key loaded: {masked}")
    else:
        log.error("API Key NOT loaded from settings! Value is None or empty.")
        # Try reading file directly to debug
        env_path = os.path.join(settings.BASE_PATH, ".env")
        if os.path.exists(env_path):
             log.info(f".env file found at {env_path}")
        else:
             log.error(f".env file NOT found at {env_path}")
    
    # Datastore Logic - Seeding
    try:
        from backend.repositories.user_repository import user_repository
        from backend.models.user import UserModel, GroupModel
        from backend.services.auth_service import auth_service
        
        # Ensure Admin Group
        admin_group = await user_repository.get_group("Super Admin")
        if not admin_group:
            log.info("Seeding 'Super Admin' group...")
            await user_repository.save_group(GroupModel(name="Super Admin", rules=["*"]))
            
        # Ensure Admin User
        admin_email = "rodrigorizando@gmail.com"
        admin = await user_repository.get_user_by_email(admin_email)
        if not admin:
            log.info(f"Seeding admin user {admin_email}...")
            hashed = await auth_service.get_password_hash("admin@123")
            await user_repository.save_user(UserModel(
                email=admin_email,
                hashed_password=hashed,
                full_name="Admin",
                groups=["Super Admin"]
            ))
        else:
            log.info(f"Admin user {admin_email} already exists.")

        # Ensure Default Agent
        from backend.services.agent_service import agent_service
        await agent_service.ensure_default_agent()

        # Validate FFmpeg Capabilities
        from backend.services.caption_service import caption_service
        caption_service.validate_ffmpeg_capabilities()
            
    except Exception as e:
        log.error(f"Seeding failed (Datastore might be unreachable locally): {e}")

    # --- Auto-Resume Interrupted Renders ---
    try:
        from backend.services.video_service import video_service
        # We use create_task to run in background and not block startup
        import asyncio
        asyncio.create_task(video_service.resume_interrupted_tasks())
    except Exception as e:
        log.error(f"Failed to initialize auto-resume task: {e}")

    # --- Garbage Collector (APScheduler) ---
    try:
        from backend.services.cleanup_service import cleanup_service
        cleanup_service.start_scheduler()
    except Exception as e:
        log.error(f"Failed to initialize Garbage Collector: {e}")

    log.info("Datastore Persistence ready.")

@app.get("/api/v1/videos", response_model=list[VideoRead])
async def list_videos(
    status: Optional[str] = Query(None),
    show_deleted: bool = Query(False),
    search: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    limit: int = Query(50)
):
    from backend.services.video_service import video_service
    return await video_service.list_all(
        status=status,
        show_deleted=show_deleted,
        search_query=search,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit
    )
@app.get("/health")
async def health_check():
    return {"status": "ok"}

# --- Static Files (Frontend) ---
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Ensure frontend/dist exists or create dummy to prevent crash on dev
frontend_dist = os.path.join(settings.BASE_PATH, "frontend", "dist")
if not os.path.exists(frontend_dist):
    log.warning(f"Frontend dist not found at {frontend_dist}. Please run 'npm run build' in frontend.")
    os.makedirs(frontend_dist, exist_ok=True)

# Mount Assets with a dedicated name to avoid conflict
assets_dir = os.path.join(frontend_dist, "assets")
if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
else:
    log.warning(f"Assets directory not found at {assets_dir}. Skipping mount.")

# Mount Storage (Dynamic User Content) - Already mounted above using settings.STORAGE_DIR
# storage_dir = "storage"
# if not os.path.exists(storage_dir):
#     os.makedirs(storage_dir, exist_ok=True)
# app.mount("/api/storage", StaticFiles(directory=storage_dir), name="storage")

# Catch-all for SPA
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    # If API path passed through, return 404
    if full_path.startswith("api"):
        return {"detail": "Not Found"}
        
    # Serve index.html
    index_path = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"detail": "Frontend not built. Run 'npm run build'."}

    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

