import json
import asyncio
from typing import List, Optional
from datetime import datetime
from google.cloud import datastore
from backend.core.datastore_client import get_datastore_client
from backend.models.music import MusicModel

class MusicRepository:
    def __init__(self):
        self.kind = "Music"

    @property
    def client(self) -> datastore.Client:
        return get_datastore_client()

    async def save(self, music: MusicModel) -> MusicModel:
        return await asyncio.to_thread(self._save_sync, music)

    def _save_sync(self, music: MusicModel) -> MusicModel:
        client = self.client
        music.updated_at = datetime.now()
        data_dict = music.model_dump(mode="json")
        
        if music.id:
            key = client.key(self.kind, int(music.id))
        else:
            key = client.key(self.kind)
            
        entity = datastore.Entity(key=key)
        entity.update({
            "title": music.title,
            "artist": music.artist,
            "genre": music.genre,
            "mood": music.mood,
            "created_at": music.created_at,
            "updated_at": music.updated_at,
            "deleted_at": music.deleted_at,
            "full_json": json.dumps(data_dict, ensure_ascii=False)
        })
        entity.exclude_from_indexes = ["full_json"]
        client.put(entity)
        
        if not music.id and entity.key.id:
            music.id = entity.key.id
        return music

    async def get(self, music_id: int) -> Optional[MusicModel]:
        return await asyncio.to_thread(self._get_sync, music_id)

    def _get_sync(self, music_id: int) -> Optional[MusicModel]:
        client = self.client
        key = client.key(self.kind, music_id)
        entity = client.get(key)
        if not entity: return None
        if "full_json" in entity:
            try:
                data = json.loads(entity["full_json"])
                data["id"] = entity.key.id
                music = MusicModel(**data)
                if music.deleted_at: return None
                return music
            except Exception:
                return None
        return None

    async def list_all(self) -> List[MusicModel]:
        return await asyncio.to_thread(self._list_all_sync)

    def _list_all_sync(self) -> List[MusicModel]:
        client = self.client
        query = client.query(kind=self.kind)
        query.order = ["-created_at"]
        results = list(query.fetch(limit=100))
        musics = []
        for entity in results:
            if "full_json" in entity:
                try:
                    data = json.loads(entity["full_json"])
                    data["id"] = entity.key.id
                    music = MusicModel(**data)
                    if not music.deleted_at:
                        musics.append(music)
                except Exception:
                    continue
        return sorted(musics, key=lambda m: m.created_at or datetime.min, reverse=True)

    async def delete(self, music_id: int) -> bool:
        return await asyncio.to_thread(self._delete_sync, music_id)

    def _delete_sync(self, music_id: int) -> bool:
        music = self._get_sync(music_id)
        if not music: return False
        music.deleted_at = datetime.now()
        self._save_sync(music)
        return True

music_repository = MusicRepository()
