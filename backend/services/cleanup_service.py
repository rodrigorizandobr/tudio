import os
import shutil
import time
import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from backend.core.configs import settings
from backend.core.logger import log
from backend.models.video import VideoStatus
from backend.repositories.video_repository import video_repository

class CleanupService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.temp_dir = os.path.join(settings.STORAGE_DIR, "temp")
        self.videos_dir = os.path.join(settings.STORAGE_DIR, "videos")

    def start_scheduler(self):
        """Starts the async scheduler with cleanup jobs."""
        if not self.scheduler.running:
            self.scheduler.add_job(
                self.run_cleanup_tasks,
                trigger=IntervalTrigger(hours=1),
                id="garbage_collector",
                name="Garbage Collector: Temp & Drafts",
                replace_existing=True
            )
            self.scheduler.start()
            log.info("CleanupService: Scheduler started (Run interval: 1h).")

    async def run_cleanup_tasks(self):
        """Wrapper to run all cleanup tasks."""
        log.info("CleanupService: Starting cleanup cycle...")
        await self.clean_temp_files()
        await self.clean_abandoned_drafts()
        log.info("CleanupService: Cleanup cycle finished.")

    async def clean_temp_files(self, max_age_hours: int = 24):
        """Deletes files in storage/temp older than max_age_hours."""
        if not os.path.exists(self.temp_dir):
            return

        log.info(f"CleanupService: Scanning {self.temp_dir} for old files (> {max_age_hours}h)...")
        
        def _scan_and_remove():
            now = time.time()
            cutoff = max_age_hours * 3600
            count = 0
            for filename in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        file_age = now - os.path.getmtime(file_path)
                        if file_age > cutoff:
                            os.remove(file_path)
                            count += 1
                except Exception as e:
                    log.error(f"Error deleting {filename}: {e}")
            return count

        count = await asyncio.to_thread(_scan_and_remove)
        if count > 0:
            log.info(f"CleanupService: Removed {count} temp files.")

    async def clean_abandoned_drafts(self, max_age_hours: int = 24):
        """Soft deletes and removes files for abandoned videos."""
        log.info(f"CleanupService: Scanning for abandoned drafts (> {max_age_hours}h)...")
        
        all_videos = await video_repository.list_all()
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        count = 0
        
        for video in all_videos:
            if video.deleted_at is not None: continue
            if video.status not in [VideoStatus.PENDING, VideoStatus.ERROR]: continue
            
            ref_time = video.updated_at or video.created_at
            if not ref_time: continue
                
            if ref_time < cutoff_time:
                try:
                    count += 1
                    video_id = str(video.id)
                    log.info(f"CleanupService: Deleting abandoned draft {video_id}")
                    
                    video.deleted_at = datetime.now()
                    await video_repository.save(video)
                    
                    def _remove_dir():
                        video_path = os.path.join(self.videos_dir, video_id)
                        if os.path.exists(video_path):
                            shutil.rmtree(video_path)
                    
                    await asyncio.to_thread(_remove_dir)
                except Exception as e:
                    log.error(f"Failed to cleanup video {video.id}: {e}")

        if count > 0:
            log.info(f"CleanupService: Cleaned up {count} abandoned drafts.")

cleanup_service = CleanupService()
