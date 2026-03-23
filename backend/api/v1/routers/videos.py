from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, File, UploadFile, Form, Query
from backend.core.logger import log
import os
import shutil
import uuid
from backend.schemas.video import VideoCreate, VideoRead
from backend.services.video_service import video_service
from backend.api.deps import get_current_user
from backend.models.user import UserModel
from backend.models.video import VideoStatus # Needed for reprocess logic

from typing import List

router = APIRouter()

async def run_video_processing(video_id: int, stop_after_scenes: bool = False):
    await video_service.process_video_background(video_id, stop_after_scenes=stop_after_scenes)

@router.get("/", response_model=List[VideoRead])
async def list_videos(
    current_user: UserModel = Depends(get_current_user)
):
    """
    List all videos.
    """
    return await video_service.list_all()

@router.post("/", response_model=VideoRead, status_code=201)
async def create_video(
    video_in: VideoCreate, 
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Creates a new video generation request.
    Processing happens in the background.
    """
    video = await video_service.create(video_in)
    
    if video.id is None:
        raise HTTPException(status_code=500, detail="Failed to generate video ID")
    
    # Audit Log
    from backend.services.audit_service import audit_service
    await audit_service.log_event(
        user_email=current_user.email,
        action="VIDEO_CREATED",
        target=f"Video:{video.id}",
        details=f"Prompt: {video.prompt[:50]}..."
    )

    background_tasks.add_task(video_service.process_video_background, video.id, stop_after_scenes=video_in.stop_after_scenes)
    
    return video

@router.get("/{video_id}", response_model=VideoRead)
async def get_video(
    video_id: int,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Returns the status and content of a video.
    """
    video = await video_service.get(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if video_id == 4897513676996608:
        from loguru import logger
        logger.debug(f"DEBUG_API_RESPONSE for {video_id}: status={video.status}, url={video.video_url}")
        
    return video

@router.delete("/{video_id}", status_code=204)
async def delete_video(
    video_id: int,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Soft deletes a video.
    """
    video = await video_service.get(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
        
    # Permission check (optional, assuming owner can delete)
    # if video.user_id != current_user.id: ...
    
    success = await video_service.delete(video_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete video")
    
    from backend.services.audit_service import audit_service
    await audit_service.log_event(
        user_email=current_user.email,
        action="VIDEO_DELETED",
        target=f"Video:{video_id}",
        details="Soft delete performed"
    )

@router.post("/{video_id}/restore", response_model=VideoRead)
async def restore_video(
    video_id: int,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Restores a soft-deleted video.
    """
    video = await video_service.get(video_id, include_deleted=True)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
        
    success = await video_service.restore(video_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to restore video")
    
    from backend.services.audit_service import audit_service
    await audit_service.log_event(
        user_email=current_user.email,
        action="VIDEO_RESTORED",
        target=f"Video:{video_id}",
        details="Video restored from trash"
    )
    
    return await video_service.get(video_id)


@router.post("/{video_id}/duplicate", response_model=VideoRead, status_code=201)
async def duplicate_video(
    video_id: int,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Duplicates a video project.
    """
    try:
        new_video = await video_service.duplicate_video(video_id)
        
        # Audit Log
        from backend.services.audit_service import audit_service
        await audit_service.log_event(
            user_email=current_user.email,
            action="VIDEO_DUPLICATED",
            target=f"Source:{video_id} -> New:{new_video.id}",
            details=f"Title: {new_video.title}"
        )
        
        return new_video
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to duplicate video: {str(e)}")
    
    return None

@router.put("/{video_id}", response_model=VideoRead)
async def update_video(
    video_id: int,
    video_data: dict,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Update video data (e.g., scene image URLs).
    """
    video = await video_service.get(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Update video with new data
    updated = await video_service.update(video_id, video_data)
    
    # Audit Log
    from backend.services.audit_service import audit_service
    await audit_service.log_event(
        user_email=current_user.email,
        action="VIDEO_UPDATED",
        target=f"Video:{video_id}",
        details="Video data updated"
    )
    
    return updated

@router.post("/{video_id}/reprocess", response_model=VideoRead)
async def reprocess_video(
    video_id: int,
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Resets an errored video and retries processing (Script Only).
    Wipes existing data and regenerates text, stopping before media generation.
    """
    # Use the service method to clean data
    success = await video_service.reprocess_script(video_id)
    if not success:
        raise HTTPException(status_code=404, detail="Video not found")
        
    video = await video_service.get(video_id)
    
    # Audit Log
    from backend.services.audit_service import audit_service
    await audit_service.log_event(
        user_email=current_user.email,
        action="VIDEO_REPROCESSED_SCRIPT",
        target=f"Video:{video_id}",
        details=f"Full script reset for: {video.prompt[:50]}..."
    )
    
    # Trigger with stop_after_scenes=True
    background_tasks.add_task(run_video_processing, video.id, stop_after_scenes=True)
    
    return video

@router.post("/{video_id}/reprocess/images", response_model=VideoRead)
async def reprocess_video_images(
    video_id: int,
    provider: str = "unsplash",
    current_user: UserModel = Depends(get_current_user)
):
    """
    Reprocesses images for the video with a specific provider.
    """
    success = await video_service.reprocess_images(video_id, provider)
    if not success:
         raise HTTPException(status_code=404, detail="Video not found")
         
    return await video_service.get(video_id)

@router.post("/{video_id}/reprocess/audio", response_model=VideoRead)
async def reprocess_video_audio(
    video_id: int,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Reprocesses narration (audio) for the video.
    """
    success = await video_service.reprocess_audio(video_id)
    if not success:
         raise HTTPException(status_code=404, detail="Video not found")
         
    return await video_service.get(video_id)

@router.post("/{video_id}/cancel", response_model=VideoRead)
async def cancel_video(
    video_id: int,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Cancels the current video processing.
    """
    success = await video_service.cancel_processing(video_id)
    if not success:
         # Could retrieve video to check if it exists or if it was not in a cancellable state
         video = await video_service.get(video_id)
         if not video:
             raise HTTPException(status_code=404, detail="Video not found")
         # If existing but not cancellable, we just return current state
         
    return await video_service.get(video_id)

@router.post("/{video_id}/chapters/{chapter_id}/subchapters/{subchapter_id}/scenes/{scene_idx}/reprocess/audio", response_model=VideoRead)
async def reprocess_scene_audio(
    video_id: int,
    chapter_id: int,
    subchapter_id: int,
    scene_idx: int,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Reprocesses narration (audio) for a single scene using hierarchical addressing.
    """
    success = await video_service.reprocess_scene_audio(video_id, chapter_id, subchapter_id, scene_idx)
    if not success:
         raise HTTPException(status_code=404, detail="Scene not found")
         
    return await video_service.get(video_id)

@router.post("/{video_id}/chapters/{chapter_id}/subchapters/{sub_id}/scenes/{scene_idx}/render", response_model=VideoRead)
async def reprocess_scene_render(
    video_id: int,
    chapter_id: int,
    sub_id: int,
    scene_idx: int,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Reprocesses the visual rendering for a single scene.
    """
    success = await video_service.render_single_scene(video_id, chapter_id, sub_id, scene_idx)
    if not success:
         raise HTTPException(status_code=404, detail="Scene not found")
         
    return await video_service.get(video_id)
@router.post("/{video_id}/render/scenes", response_model=VideoRead)
async def trigger_video_scenes_render(
    video_id: int,
    force: bool = Query(False),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Triggers rendering of individual scenes (Step 4 of workflow).
    """
    log.info(f"Router: trigger_video_scenes_render called for {video_id} with force={force}")
    try:
        success = await video_service.trigger_scene_render(video_id, force=force)
        if not success:
             raise HTTPException(status_code=404, detail="Video not found")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
         
    return await video_service.get(video_id)

@router.post("/{video_id}/render", response_model=VideoRead)
async def trigger_video_render(
    video_id: int,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Manually triggers the final video rendering.
    """
    try:
        success = await video_service.trigger_render(video_id)
        if not success:
             raise HTTPException(status_code=404, detail="Video not found")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
         
    return await video_service.get(video_id)

@router.post("/{video_id}/scenes/audio", response_model=VideoRead)
async def upload_scene_audio(
    video_id: int,
    chapter_id: int = Form(...),
    subchapter_id: int = Form(...),
    scene_index: int = Form(...),
    file: UploadFile = File(...),
    duration_seconds: float = Form(None),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Uploads an audio recording for a specific scene.
    """
    video = await video_service.get(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Find Scene FIRST (to check for existing audio)
    target_scene = None
    for chapter in video.chapters:
        if chapter.id == chapter_id:
            for sub in chapter.subchapters:
                if sub.id == subchapter_id:
                    if 0 <= scene_index < len(sub.scenes):
                        target_scene = sub.scenes[scene_index]
                        break
            if target_scene: break
 
    if not target_scene:
        raise HTTPException(status_code=404, detail="Scene not found in video structure")
 
    # Determine File Path (Overwrite Strategy)
    storage_dir = f"storage/audios/{video_id}"
    os.makedirs(storage_dir, exist_ok=True)
    
    file_path = None
    file_name = None
    audio_url = None
 
    if target_scene.audio_url:
        try:
            existing_url = target_scene.audio_url
            if existing_url.startswith("/api/"):
                relative_path = existing_url[5:] # remove /api/
            else:
                relative_path = existing_url
                
            if f"storage/audios/{video_id}" in relative_path:
                 full_existing_path = relative_path
                 if os.path.exists(os.path.dirname(full_existing_path)):
                     file_path = full_existing_path
                     file_name = os.path.basename(file_path)
                     audio_url = existing_url
        except Exception:
            pass
 
    if not file_path:
        file_ext = "webm" 
        if file.filename.endswith(".mp4"): file_ext = "mp4"
        if file.filename.endswith(".wav"): file_ext = "wav"
        
        file_name = f"{uuid.uuid4()}.{file_ext}"
        file_path = f"{storage_dir}/{file_name}"
        audio_url = f"/api/storage/audios/{video_id}/{file_name}"
 
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    target_scene.audio_url = audio_url
    if duration_seconds is not None and duration_seconds > 0:
        target_scene.duration_seconds = int(duration_seconds)
 
    from backend.repositories.video_repository import video_repository
    await video_repository.save(video)
    
    return video

@router.delete("/{video_id}/scenes/audio", response_model=VideoRead)
async def delete_scene_audio(
    video_id: int,
    chapter_id: int,
    subchapter_id: int,
    scene_index: int,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Deletes the audio recording for a specific scene.
    """
    video = await video_service.get(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
 
    # 1. Find Scene
    target_scene = None
    for chapter in video.chapters:
        if chapter.id == chapter_id:
            for sub in chapter.subchapters:
                if sub.id == subchapter_id:
                    if 0 <= scene_index < len(sub.scenes):
                        target_scene = sub.scenes[scene_index]
                        break
            if target_scene: break
    
    if not target_scene:
        raise HTTPException(status_code=404, detail="Scene not found")
 
    # 2. Delete File if exists
    if target_scene.audio_url:
        try:
            relative_path = target_scene.audio_url
            if relative_path.startswith("/api/"):
                relative_path = relative_path[5:] # remove /api/
            
            if "storage/audios" in relative_path and os.path.exists(relative_path):
                os.remove(relative_path)
        except Exception as e:
            pass
        
        target_scene.audio_url = None
        
        if target_scene.narration_content:
             word_count = len(target_scene.narration_content.split())
             target_scene.duration_seconds = max(1, int(float(word_count) * 0.4))
        else:
             target_scene.duration_seconds = 1
 
    from backend.repositories.video_repository import video_repository
    await video_repository.save(video)
    
    return video

@router.post("/{video_id}/chapters/{chapter_id}/reprocess", response_model=VideoRead)
async def reprocess_chapter(
    video_id: int,
    chapter_id: int,
    background_tasks: BackgroundTasks,
    stop_after_scenes: bool = True,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Reprocesses a specific chapter.
    """
    success = await video_service.reprocess_chapter(video_id, chapter_id, stop_after_scenes=stop_after_scenes)
    if not success:
         raise HTTPException(status_code=404, detail="Video or Chapter not found")
         
    return await video_service.get(video_id)

@router.post("/{video_id}/reset-thread", response_model=VideoRead)
async def reset_video_thread(
    video_id: int,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Reset OpenAI thread for a video. Useful when thread context is corrupted
    and OpenAI returns conversational responses instead of JSON.
    
    This will create a fresh thread, losing conversation history but fixing
    the corruption issue.
    """
    success = await video_service.reset_thread_for_video(video_id)
    if not success:
        raise HTTPException(status_code=404, detail="Video not found or no thread to reset")
    
    # Audit Log
    from backend.services.audit_service import audit_service
    await audit_service.log_event(
        user_email=current_user.email,
        action="VIDEO_THREAD_RESET",
        target=f"Video:{video_id}",
        details="OpenAI thread reset due to corruption"
    )
         
    return await video_service.get(video_id)

