from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form
from typing import List
from backend.api.deps import get_current_user
from backend.models.user import UserModel
from backend.models.music import MusicModel
from backend.services.music_service import music_service

router = APIRouter()

@router.get("/", response_model=List[MusicModel])
async def list_musics(
    current_user: UserModel = Depends(get_current_user)
):
    """
    List all available music tracks.
    """
    return await music_service.list_all()

@router.post("/", response_model=MusicModel)
async def upload_music(
    title: str = Form(...),
    artist: str = Form(...),
    genre: str = Form(...),
    mood: str = Form(...),
    file: UploadFile = File(...),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Upload a new music track (MP3).
    """
    if not file.filename.lower().endswith(".mp3"):
         raise HTTPException(status_code=400, detail="Only MP3 files are allowed.")
         
    return await music_service.upload_music(
        file=file,
        title=title,
        artist=artist,
        genre=genre,
        mood=mood
    )

@router.delete("/{music_id}", status_code=204)
async def delete_music(
    music_id: int,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Soft delete a music track.
    """
    success = await music_service.delete_music(music_id)
    if not success:
        raise HTTPException(status_code=404, detail="Music not found")
    return None
