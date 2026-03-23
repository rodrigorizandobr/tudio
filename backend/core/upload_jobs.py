"""
upload_jobs.py — In-memory store for YouTube upload job progress.
Supports multiple concurrent jobs (one per format per video upload action).
Thread-safe via threading.Lock.
"""
import threading
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional
from enum import Enum


class UploadStatus(str, Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    DONE = "done"
    ERROR = "error"


class UploadJob:
    def __init__(
        self,
        job_id: str,
        video_id: int,
        video_title: str,
        format_ratio: str,
        channel_id: int,
    ):
        self.job_id = job_id
        self.video_id = video_id
        self.video_title = video_title
        self.format_ratio = format_ratio
        self.channel_id = channel_id
        self.status: UploadStatus = UploadStatus.PENDING
        self.progress: float = 0.0  # 0-100
        self.youtube_video_id: Optional[str] = None
        self.error: Optional[str] = None
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "video_id": self.video_id,
            "video_title": self.video_title,
            "format_ratio": self.format_ratio,
            "channel_id": self.channel_id,
            "status": self.status.value,
            "progress": round(self.progress, 1),
            "youtube_video_id": self.youtube_video_id,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class UploadJobStore:
    """Thread-safe singleton store for upload jobs."""

    def __init__(self):
        self._jobs: Dict[str, UploadJob] = {}
        self._lock = threading.Lock()

    def create_job(
        self,
        video_id: int,
        video_title: str,
        format_ratio: str,
        channel_id: int,
    ) -> UploadJob:
        job_id = str(uuid.uuid4())
        job = UploadJob(
            job_id=job_id,
            video_id=video_id,
            video_title=video_title,
            format_ratio=format_ratio,
            channel_id=channel_id,
        )
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[UploadJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def update_progress(self, job_id: str, progress: float) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.progress = progress
                job.status = UploadStatus.UPLOADING
                job.updated_at = datetime.now()

    def complete_job(self, job_id: str, youtube_video_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.progress = 100.0
                job.status = UploadStatus.DONE
                job.youtube_video_id = youtube_video_id
                job.updated_at = datetime.now()

    def fail_job(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = UploadStatus.ERROR
                job.error = error
                job.updated_at = datetime.now()

    def list_jobs_for_video(self, video_id: int) -> list[UploadJob]:
        with self._lock:
            return [j for j in self._jobs.values() if j.video_id == video_id]

    def get_all_active(self) -> list[UploadJob]:
        """Returns all non-done/non-erred jobs."""
        with self._lock:
            return [
                j
                for j in self._jobs.values()
                if j.status in (UploadStatus.PENDING, UploadStatus.UPLOADING)
            ]

    def purge_old(self, max_age_hours: int = 24) -> None:
        """Remove jobs older than max_age_hours to avoid unbounded memory growth."""
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        with self._lock:
            stale = [
                jid
                for jid, j in self._jobs.items()
                if j.updated_at < cutoff
                and j.status in (UploadStatus.DONE, UploadStatus.ERROR)
            ]
            for jid in stale:
                del self._jobs[jid]


# Module-level singleton
upload_job_store = UploadJobStore()
