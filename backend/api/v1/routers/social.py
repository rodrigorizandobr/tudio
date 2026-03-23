
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from typing import List, Optional
from backend.services.social_service import social_service
from backend.repositories.social_repository import social_repository
from backend.models.social import SocialChannelRead, SocialAccountRead
from backend.api.deps import get_current_user
from backend.models.user import UserModel
from backend.core.upload_jobs import upload_job_store
from backend.core.logger import log
from pydantic import BaseModel

router = APIRouter()

@router.get("/auth/google/url")
async def get_google_auth_url(
    current_user: UserModel = Depends(get_current_user)
):
    """Returns the Google OAuth Authorization URL."""
    state = current_user.email
    url = social_service.get_authorization_url(state=state)
    return {"url": url}

@router.get("/auth/callback")
async def google_auth_callback(
    code: str,
    state: str,
    error: Optional[str] = None
):
    """Handles the callback from Google OAuth.
    Exchanges code for tokens and syncs channels."""
    if error:
        raise HTTPException(status_code=400, detail=f"Google Auth Error: {error}")

    try:
        user_email = state
        await social_service.handle_callback(code, user_email)

        html_content = """
        <html>
            <script>
                if (window.opener) {
                    window.opener.postMessage({ type: 'SOCIAL_AUTH_SUCCESS' }, '*');
                    window.close();
                } else {
                    document.write("Conexão realizada com sucesso! Você pode fechar esta janela.");
                }
            </script>
        </html>
        """
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html_content)

    except Exception as e:
        log.error(f"Google Auth Error: {str(e)}")
        log.exception(e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/channels", response_model=List[SocialChannelRead])
async def list_connected_channels(
    current_user: UserModel = Depends(get_current_user)
):
    """Lists all YouTube channels connected to the current user's Google Accounts."""
    channels = await social_service.get_user_channels(current_user.email)
    return channels

@router.delete("/channels/{channel_id}")
async def disconnect_channel(
    channel_id: int,
    current_user: UserModel = Depends(get_current_user)
):
    """Removes a channel connection."""
    channel = await social_repository.get_channel_by_id(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    user_channels = await social_service.get_user_channels(current_user.email)
    if not any(c.id == channel.id for c in user_channels):
        raise HTTPException(status_code=403, detail="Not authorized to delete this channel")

    await social_repository.delete_channel(channel_id)
    return {"detail": "Channel disconnected"}


# ------- Upload Job Models -------

class SocialUploadRequest(BaseModel):
    video_id: int
    channel_id: int
    title: str
    description: str
    privacy: str = "private"  # public, unlisted, private
    tags: Optional[List[str]] = None
    format: Optional[str] = None  # e.g. "16:9" or "9:16" — selects from video.outputs


# ------- Background task -------

async def _background_upload_video_async(
    channel_id: int,
    video_path: str,
    title: str,
    description: str,
    privacy: str,
    tags: List[str],
    video_id: int,
    job_id: str,
):
    """Async background task that uploads a video and tracks progress via UploadJobStore."""
    from backend.services.video_service import video_service

    # Mark job as uploading
    upload_job_store.update_progress(job_id, 0.0)

    video = await video_service.get(video_id)
    if not video:
        upload_job_store.fail_job(job_id, "Video not found")
        return

    try:
        video.social_publish_status = "uploading"
        await video_service.save(video)

        youtube_id = await social_service.upload_video(
            channel_id=channel_id,
            video_path=video_path,
            title=title,
            description=description,
            privacy_status=privacy,
            tags=tags,
            job_id=job_id,
        )

        # Refresh and mark success
        video = await video_service.get(video_id)
        if video:
            video.social_publish_status = "uploaded"
            video.social_video_id = youtube_id
            await video_service.save(video)

    except Exception as e:
        log.error(f"Background Upload Failed (job={job_id}): {e}")
        upload_job_store.fail_job(job_id, str(e))
        video = await video_service.get(video_id)
        if video:
            video.social_publish_status = "error"
            await video_service.save(video)


# ------- Upload endpoint -------

@router.post("/upload")
async def upload_video_to_youtube(
    data: SocialUploadRequest,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Initiates upload of a generated video to YouTube in background.
    Returns job_id immediately for progress polling.
    """
    import asyncio
    import os
    from backend.services.video_service import video_service
    from backend.core.configs import settings

    # 1. Verify Video
    video = await video_service.get(data.video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # 2. Verify Channel Ownership
    user_channels = await social_service.get_user_channels(current_user.email)
    if not any(c.id == data.channel_id for c in user_channels):
        raise HTTPException(status_code=403, detail="Not authorized to use this channel")

    # 3. Resolve video file path
    # If format is specified, pick from outputs dict; otherwise fall back to video_url
    video_url = None
    if data.format and video.outputs and data.format in video.outputs:
        video_url = video.outputs[data.format]
    elif video.outputs and len(video.outputs) > 0:
        video_url = next(iter(video.outputs.values()))
    else:
        video_url = video.video_url

    if not video_url:
        raise HTTPException(status_code=404, detail="Video URL not set. Please render the video first.")

    # Normalise path
    relative_path = video_url
    if relative_path.startswith("/api/storage/"):
        relative_path = relative_path.replace("/api/storage/", "")
    elif relative_path.startswith("/api/"):
        relative_path = relative_path[5:]
    elif relative_path.startswith("/"):
        relative_path = relative_path.lstrip("/")

    # Strip query string (cache buster)
    if "?" in relative_path:
        relative_path = relative_path.split("?")[0]

    video_path = os.path.join(settings.STORAGE_DIR, relative_path)

    if not os.path.exists(video_path):
        fallback = os.path.join(settings.BASE_PATH, relative_path)
        if os.path.exists(fallback):
            video_path = fallback
        else:
            raise HTTPException(status_code=404, detail=f"Video file not found at {video_path}")

    # 4. Create job
    job = upload_job_store.create_job(
        video_id=data.video_id,
        video_title=data.title,
        format_ratio=data.format or "default",
        channel_id=data.channel_id,
    )

    # 5. Fire background task
    asyncio.create_task(_background_upload_video_async(
        channel_id=data.channel_id,
        video_path=video_path,
        title=data.title,
        description=data.description,
        privacy=data.privacy,
        tags=data.tags or [],
        video_id=video.id,
        job_id=job.job_id,
    ))

    log.info(f"Upload job {job.job_id} created for video {data.video_id} (format={data.format})")
    return {"status": "processing", "job_id": job.job_id, "detail": "Upload iniciado em segundo plano"}


# ------- Job Status / Polling endpoints -------

@router.get("/upload/jobs/{job_id}")
async def get_upload_job_status(
    job_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Polls the status and progress of a single upload job by ID."""
    job = upload_job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()


@router.get("/upload/jobs")
async def list_upload_jobs(
    video_id: Optional[int] = Query(None),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Lists upload jobs.
    Optionally filter by video_id to list all format-uploads for a specific video.
    """
    if video_id:
        jobs = upload_job_store.list_jobs_for_video(video_id)
    else:
        jobs = upload_job_store.get_all_active()
    return [j.to_dict() for j in jobs]
