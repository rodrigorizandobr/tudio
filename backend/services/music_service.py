import os
import shutil
import uuid
import asyncio
from typing import Optional, List
from mutagen.mp3 import MP3
from fastapi import UploadFile
from backend.core.configs import settings
from backend.core.logger import log
from backend.models.music import MusicModel
from backend.repositories.music_repository import music_repository

class MusicService:
    def __init__(self):
        self.storage_dir = os.path.join(settings.STORAGE_DIR, "musics")
        os.makedirs(self.storage_dir, exist_ok=True)
        
    async def list_all(self) -> List[MusicModel]:
        return await music_repository.list_all()

    async def get(self, music_id: int) -> Optional[MusicModel]:
        return await music_repository.get(music_id)

    async def upload_music(self, 
                           file: UploadFile, 
                           title: str, 
                           artist: str, 
                           genre: str, 
                           mood: str) -> MusicModel:
        
        # 1. Generate unique filename
        file_ext = "mp3" 
        if file.filename.endswith(".mp3"): file_ext = "mp3"
        
        unique_name = f"{uuid.uuid4()}.{file_ext}"
        file_path = os.path.join(self.storage_dir, unique_name)
        
        # 2. Save File (Async I/O via thread)
        def _save_file():
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        
        await asyncio.to_thread(_save_file)
            
        # 3. Extract Metadata (Duration)
        def _extract_duration():
            try:
                audio = MP3(file_path)
                return int(audio.info.length)
            except Exception as e:
                log.warning(f"Failed to extract duration from {file.filename}: {e}")
                return 0
        
        duration = await asyncio.to_thread(_extract_duration)
            
        # 4. Save to DB
        music = MusicModel(
            title=title,
            artist=artist,
            genre=genre,
            mood=mood,
            filename=file.filename,
            file_path=f"musics/{unique_name}",
            duration_seconds=duration
        )
        
        return await music_repository.save(music)

    async def delete_music(self, music_id: int) -> bool:
        return await music_repository.delete(music_id)

music_service = MusicService()
