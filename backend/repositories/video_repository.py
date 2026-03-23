import asyncio
import json
from typing import List, Optional
from datetime import datetime
from google.cloud import datastore
from backend.core.datastore_client import get_datastore_client
from backend.models.video import VideoModel, VideoStatus

class VideoRepository:
    def __init__(self):
        self.kind = "Script"  # Keep "Script" to preserve data

    @property
    def client(self) -> datastore.Client:
        return get_datastore_client()

    async def save(self, video: VideoModel) -> VideoModel:
        """Async wrapper for save_sync."""
        return await asyncio.to_thread(self.save_sync, video)

    def save_sync(self, video: VideoModel) -> VideoModel:
        client = self.client
        
        # SAFEGUARD: Prevent accidental data loss
        # Allow empty chapters if status is PENDING (e.g. during reset)
        if video.id and not video.chapters and video.status != VideoStatus.PENDING:
             # If we are saving a video with NO chapters, verify if it had them before
             # This prevents the "apagando o roteiro" bug if upstream logic failed
             try:
                 # Check existing entity without full reconstruction cost if possible
                 # But here we need to check if 'full_json' has chapters
                 existing_key = client.key(self.kind, int(video.id))
                 existing_ent = client.get(existing_key)
                 if existing_ent and "full_json" in existing_ent:
                     # Check quickly if chapters exist in json string
                     # Simple heuristics to avoid full parse
                     if '"chapters": [{' in existing_ent["full_json"] or '"chapters": [{' in existing_ent["full_json"]:
                          # We have chapters in DB, but empty here. ABORT SAVE.
                          print(f"CRITICAL: Attempted to save video {video.id} with empty chapters! blocked.")
                          # Return existing as best effort
                          data = json.loads(existing_ent["full_json"])
                          data["id"] = existing_ent.key.id
                          return VideoModel(**data)
             except Exception:
                 pass # Fallback to normal save if check fails
                  
        video.updated_at = datetime.now()
        
        # Prepare data for Datastore
        # We Separate metadata for indexing from the heavy nested content
        data_dict = video.model_dump(mode="json")
        
        if video.id:
            # Update
            key = client.key(self.kind, int(video.id))
            entity = datastore.Entity(key=key)
        else:
            # Create (Auto ID)
            key = client.key(self.kind)
            entity = datastore.Entity(key=key)
        
        entity.update({
            "prompt": video.prompt,
            "title": video.title, # Indexed for search
            "status": video.status,
            "language": video.language,
            "target_duration_minutes": video.target_duration_minutes,
            "progress": video.progress,
            "created_at": video.created_at,
            "updated_at": video.updated_at,
            "deleted_at": video.deleted_at,
            "error_message": video.error_message,
            "full_json": json.dumps(data_dict, ensure_ascii=False), # The Source of Truth
            "aspect_ratios": video.aspect_ratios # Indexable list for filtering
        })
        
        # Exclude huge JSON from index
        entity.exclude_from_indexes = [
            "full_json", 
            "error_message", 
            # "prompt",  # We might want to search by prompt too, leave indexed for now or choose one
            "description", 
            "audio_generation_instructions",
            "timestamps_index"
        ]
        
        # DEBUG: Check if generated_video_url is present in full_json
        if "generated_video_url" in entity["full_json"] and '"generated_video_url": "videos/' in entity["full_json"]:
             from backend.core.logger import log
             log.info(f"VideoRepository: Saving video {video.id} with generated_video_url detected in full_json")
        
        client.put(entity)
        
        # If created, assign ID
        if not video.id and entity.key.id:
            video.id = entity.key.id
            
        return video

    async def get(self, video_id: int, include_deleted: bool = False) -> Optional[VideoModel]:
        """Async wrapper for get_sync."""
        return await asyncio.to_thread(self.get_sync, video_id, include_deleted)

    def get_sync(self, video_id: int, include_deleted: bool = False) -> Optional[VideoModel]:
        client = self.client
        key = client.key(self.kind, video_id)
        entity = client.get(key)
        
        if not entity:
            return None
            
        # Reconstruct
        if "full_json" in entity:
            data = json.loads(entity["full_json"])
            # Ensure ID is correct from key
            data["id"] = entity.key.id
            video = VideoModel(**data)
            
            # Soft delete filter: by default, hide deleted records
            if video.deleted_at and not include_deleted:
                return None
            
            return video
        else:
            return None

    async def list_all(self, limit: int = 50) -> List[VideoModel]:
        """Legacy method, uses query_videos internally."""
        return await self.query_videos(limit=limit)

    async def query_videos(
        self, 
        status: Optional[str] = None, 
        show_deleted: bool = False,
        search_query: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 50
    ) -> List[VideoModel]:
        return await asyncio.to_thread(
            self._query_videos_sync,
            status=status,
            show_deleted=show_deleted,
            search_query=search_query,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit
        )

    def _query_videos_sync(
        self, 
        status: Optional[str] = None, 
        show_deleted: bool = False,
        search_query: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 50
    ) -> List[VideoModel]:
        client = self.client
        query = client.query(kind=self.kind)
        
        # Datastore Optimization: 
        # To avoid "no matching index found" errors, we only use ONE filter in the native query
        # and handle the rest in memory for now. 
        # Status is a good filter for the native query as it's highly selective.
        
        if status:
            query.add_filter("status", "=", status)

        # 1. Native Soft Delete Filtering (Improves reliability and performance)
        if show_deleted:
            # Native filter for "is NOT NULL" using inequality
            query.add_filter("deleted_at", ">", None)
        else:
            # Native filter for "is NULL"
            query.add_filter("deleted_at", "=", None)
            
        # Native sorting works fine if it's the only order or if combined with equality filters
        # on indexed fields. But to avoid "no matching index" errors in the emulator,
        # we skip native sorting here and rely on the in-memory sort at the end of this method.
        # query.order = ["-created_at"]
            
        # BUG FIX: Increase fetch buffer significantly. 100 was too small for 321+ total videos.
        # We fetch up to 500 or limit * 5 to ensure we have enough after in-memory filters (like search)
        fetch_limit = max(500, limit * 5)
        results = list(query.fetch(limit=fetch_limit)) 
        videos = []
        
        for entity in results:
            if "full_json" in entity:
                try:
                    data = json.loads(entity["full_json"])
                    data["id"] = entity.key.id
                    video = VideoModel(**data)
                    
                    # 1. Soft Delete Filtering (In-Memory)
                    if show_deleted:
                        if not video.deleted_at: continue
                    else:
                        if video.deleted_at: continue
                        
                    # 2. Search Filtering (In-Memory)
                    if search_query:
                        sq = search_query.lower()
                        title_match = video.title and sq in video.title.lower()
                        prompt_match = video.prompt and sq in video.prompt.lower()
                        if not (title_match or prompt_match):
                            continue
                            
                    videos.append(video)
                except Exception:
                    continue
        
        # 3. Dynamic Sorting (In-Memory)
        reverse = (sort_order == "desc")
        def sort_key(v):
            val = getattr(v, sort_by, None)
            if val is None:
                return datetime.min if sort_by.endswith('_at') else ""
            return val

        videos.sort(key=sort_key, reverse=reverse)
                    
        return videos[:limit]

    async def delete(self, video_id: int, status: Optional[VideoStatus] = None) -> bool:
        """Async wrapper for delete_sync."""
        return await asyncio.to_thread(self.delete_sync, video_id, status)

    def delete_sync(self, video_id: int, status: Optional[VideoStatus] = None) -> bool:
        """Soft delete a script by ID."""
        # Use low-level client to avoid reconstruction overhead
        client = self.client
        key = client.key(self.kind, int(video_id))
        entity = client.get(key)
        if not entity:
            return False
            
        entity["deleted_at"] = datetime.now()
        if status:
            entity["status"] = status.value if hasattr(status, 'value') else status

        # Update full_json as well for consistency
        data = json.loads(entity["full_json"])
        data["deleted_at"] = entity["deleted_at"].isoformat()
        if status:
            data["status"] = status.value if hasattr(status, 'value') else status
            
        entity["full_json"] = json.dumps(data, ensure_ascii=False)
        client.put(entity)
        
        return True

    async def restore(self, video_id: int) -> bool:
        """Async wrapper for restore_sync."""
        return await asyncio.to_thread(self.restore_sync, video_id)

    def restore_sync(self, video_id: int) -> bool:
        """Restore a soft-deleted video."""
        client = self.client
        key = client.key(self.kind, int(video_id))
        entity = client.get(key)
        if not entity:
            return False
            
        entity["deleted_at"] = None
        
        # Update full_json for consistency
        data = json.loads(entity["full_json"])
        data["deleted_at"] = None
        entity["full_json"] = json.dumps(data, ensure_ascii=False)
        
        client.put(entity)
        return True


    def get_by_status(self, statuses: List[str]) -> List[VideoModel]:
        """Optimized query for specific statuses."""
        return self.query_videos(status=statuses[0] if statuses else None) # Simplified for now

video_repository = VideoRepository()
