"""
captions.py — REST API router for animated caption generation.
"""
import asyncio
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

from backend.api.deps import get_current_user
from backend.models.user import UserModel
from backend.services.video_service import video_service
from backend.services.caption_service import caption_service
from backend.core.caption_styles import CAPTION_STYLES
from backend.core.logger import log

router = APIRouter()


# ─── Request / Response schemas ───────────────────────────────────────────────

class CaptionGenerateRequest(BaseModel):
    style: str = "karaoke"          # karaoke | word_pop | typewriter | highlight | bounce
    force_whisper: bool = False     # Force OpenAI Whisper even if narration text exists
    scope: str = "video"            # "video" = all formats; "scene" = single scene
    scene_id: Optional[int] = None  # Required when scope="scene"
    options: dict = {}              # Font, colors, position, etc.


class CaptionStyleRequest(BaseModel):
    style: str
    force_whisper: bool = False
    options: dict = {}


class WordTimestamp(BaseModel):
    word: str
    start: float
    end: float


class SceneCaptionPreview(BaseModel):
    scene_id: int
    words: List[WordTimestamp]


# ─── Background task ─────────────────────────────────────────────────────────

async def _bg_generate_captions(
    video_id: int,
    style: str,
    options: dict,
    force_whisper: bool,
):
    video = await video_service.get(video_id)
    if not video:
        log.error(f"Caption BG task: Video {video_id} not found")
        return
    try:
        await caption_service.generate_captions_for_video(
            video=video,
            style=style,
            options=options,
            force_whisper=force_whisper,
        )
    except Exception as e:
        log.error(f"Caption BG task failed for video {video_id}: {e}")
        try:
            video = await video_service.get(video_id)
            if video:
                video.caption_status = "error"
                await video_service.save(video)
        except Exception:
            pass


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/videos/{video_id}/captions/generate")
async def generate_captions(
    video_id: int,
    data: CaptionGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(get_current_user),
):
    """
    Initiate caption generation for a video (all formats) or a single scene.
    Returns immediately; generation runs in background.
    """
    video = await video_service.get(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if data.style not in CAPTION_STYLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid style '{data.style}'. Valid: {CAPTION_STYLES}"
        )

    if data.scope == "scene":
        # Per-scene: find the scene and generate immediately (fast, no burn-in)
        if not data.scene_id:
            raise HTTPException(status_code=400, detail="scene_id required for scope='scene'")

        scene = None
        for chapter in video.chapters:
            for sub in chapter.subchapters:
                for s in sub.scenes:
                    if s.id == data.scene_id and not s.deleted:
                        scene = s
                        break

        if not scene:
            raise HTTPException(status_code=404, detail="Scene not found")

        scene.caption_status = "processing"
        await video_service.save(video)

        async def _bg_scene():
            try:
                words = await caption_service.generate_captions_for_scene(
                    video=video,
                    scene=scene,
                    force_whisper=data.force_whisper,
                )
                log.info(f"Scene {data.scene_id}: {len(words)} words generated")
            except Exception as e:
                log.error(f"Scene {data.scene_id} caption error: {e}")
                scene.caption_status = "error"
                await video_service.save(video)

        background_tasks.add_task(_bg_scene)
        return {"status": "processing", "scope": "scene", "scene_id": data.scene_id}

    else:
        # Full video: fire background task
        if video.caption_status == "processing":
            raise HTTPException(
                status_code=409,
                detail="Caption generation already in progress"
            )
        if not video.outputs:
            raise HTTPException(
                status_code=422,
                detail="Video has no rendered outputs. Render the video first."
            )

        video.caption_status = "processing"
        video.caption_style = data.style
        video.caption_options = data.options
        await video_service.save(video)

        background_tasks.add_task(_bg_generate_captions, 
            video_id=video_id,
            style=data.style,
            options=data.options,
            force_whisper=data.force_whisper,
        )

        return {
            "status": "processing",
            "scope": "video",
            "style": data.style,
            "detail": "Geração de legendas iniciada em segundo plano",
        }


@router.get("/videos/{video_id}/captions/status")
async def get_caption_status(
    video_id: int,
    current_user: UserModel = Depends(get_current_user),
):
    """Polling endpoint for caption generation status."""
    video = await video_service.get(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    return {
        "caption_status": video.caption_status,
        "caption_style": video.caption_style,
        "caption_options": video.caption_options,
        "captioned_outputs": video.captioned_outputs,
    }


@router.get("/videos/{video_id}/captions/preview")
async def get_captions_preview(
    video_id: int,
    current_user: UserModel = Depends(get_current_user),
):
    """
    Returns cached word timestamps for all scenes in the video.
    Used for frontend preview animations.
    """
    video = await video_service.get(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    scene_previews = []
    for chapter in video.chapters:
        for sub in chapter.subchapters:
            for scene in sub.scenes:
                if not scene.deleted and scene.caption_words:
                    scene_previews.append({
                        "scene_id": scene.id,
                        "words": scene.caption_words,
                    })

    return {"scenes": scene_previews}


@router.patch("/videos/{video_id}/captions/style")
async def update_caption_style(
    video_id: int,
    data: CaptionStyleRequest,
    current_user: UserModel = Depends(get_current_user),
):
    """Update the caption style and options without regenerating."""
    video = await video_service.get(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if data.style not in CAPTION_STYLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid style. Valid: {CAPTION_STYLES}"
        )

    video.caption_style = data.style
    video.caption_force_whisper = data.force_whisper
    video.caption_options = data.options
    await video_service.save(video)

    return {"detail": "Style updated", "style": data.style, "force_whisper": data.force_whisper}


@router.post("/videos/{video_id}/scenes/{scene_id}/captions/generate", status_code=202)
async def generate_scene_captions(
    video_id: int,
    scene_id: int,
    background_tasks: BackgroundTasks,
    force_whisper: bool = False,
    current_user: UserModel = Depends(get_current_user),
):
    """
    Shortcut endpoint: generate captions for a single scene in background.
    """
    video = await video_service.get(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    scene = None
    for chapter in video.chapters:
        for sub in chapter.subchapters:
            for s in sub.scenes:
                if s.id == scene_id and not s.deleted:
                    scene = s
                    break

    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    if not scene.audio_url:
        raise HTTPException(status_code=422, detail="Scene has no audio. Upload or generate audio first.")

    # Set scene to processing
    scene.caption_status = "processing"
    await video_service.save(video)
    log.info(f"Scene {scene_id} captioning triggered (BackgroundTasks)")

    async def _run_captioning():
        log.info(f"Background task _run_captioning STARTED for scene {scene_id}")
        try:
            # Re-fetch video to get freshest data in background
            v = await video_service.get(video_id)
            if not v:
                log.error(f"Background task: Video {video_id} not found during re-fetch")
                return

            # Find scene again in fresh video object
            s_target = None
            for c in v.chapters:
                for sub in c.subchapters:
                    for sc in sub.scenes:
                        if sc.id == scene_id:
                            s_target = sc
                            break
            
            if s_target:
                log.info(f"Found target scene {scene_id} for background captioning")
                await caption_service.generate_captions_for_scene(
                    video=v,
                    scene=s_target,
                    force_whisper=force_whisper,
                )
                log.info(f"Background task _run_captioning COMPLETED for scene {scene_id}")
            else:
                log.error(f"Background task: Scene {scene_id} not found in video {video_id} (re-fetch)")
        except Exception as e:
            log.error(f"Background scene captioning failed for scene {scene_id}: {e}")
            log.exception(e)  # Traceback
            # Try to set error status
            try:
                v = await video_service.get(video_id)
                for c in v.chapters:
                    for sub in c.subchapters:
                        for sc in sub.scenes:
                            if sc.id == scene_id:
                                sc.caption_status = "error"
                                break
                await video_service.save(v)
            except Exception as inner_e:
                log.error(f"Failed to set error status: {inner_e}")

    background_tasks.add_task(_run_captioning)

    return {
        "detail": "Scene captioning started in background",
        "scene_id": scene_id,
        "caption_status": "processing"
    }


@router.get("/captions/styles")
async def list_caption_styles(
    current_user: UserModel = Depends(get_current_user),
):
    """Returns available caption styles."""
    return {
        "styles": [
            {"id": "karaoke", "label": "Karaoke", "desc": "Palavra fica colorida conforme é falada"},
            {"id": "word_pop", "label": "Word Pop", "desc": "Cada palavra aparece no timing exato com destaque"},
            {"id": "typewriter", "label": "Typewriter", "desc": "Palavras reveladas progressivamente"},
            {"id": "highlight", "label": "Highlight", "desc": "Linha visível, palavra atual em destaque"},
            {"id": "bounce", "label": "Bounce", "desc": "Palavra aparece com animação de escala"},
        ]
    }
