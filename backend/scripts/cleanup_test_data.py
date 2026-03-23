import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.getcwd())

from backend.repositories.video_repository import video_repository
from backend.core.logger import log

def cleanup():
    log.info("Starting cleanup of test videos...")
    
    # 1. List active and deleted videos
    vids_active = video_repository.query_videos(limit=100, show_deleted=False)
    vids_deleted = video_repository.query_videos(limit=100, show_deleted=True)
    vids = vids_active + vids_deleted
    
    test_titles = [
        "Teste de edição",
        "Teste E2E",
        "Um documentário sobre a história da internet",
        "Roteiro de Verificação de Re-Crop",
        "Mock Video Title"
    ]
    
    test_prompts = [
        "Integration Test",
        "Flow Test",
        "Test Bug Video Sync",
        "Roteiro de Verificação de Re-Crop"
    ]

    deleted_count = 0
    now = datetime.now()
    
    for video in vids:
        # Check active videos for test signatures
        if not video.deleted_at:
            should_delete = False
            
            # Criteria A: ID is very small (manual injection or test ID)
            if video.id and video.id < 1000:
                log.info(f"Cleanup: Marking video {video.id} for deletion (Small ID)")
                should_delete = True
                
            # Criteria B: Title matches test patterns (Only for recent videos < 10m)
            elif video.title and any(t in video.title for t in test_titles):
                if video.created_at and (now - video.created_at) < timedelta(minutes=10):
                    log.info(f"Cleanup: Marking video {video.id} for deletion (Title matches test patterns: {video.title})")
                    should_delete = True
                else:
                    log.info(f"Cleanup: Skipping video {video.id} with test title (Older than 10m safety window)")
                
            # Criteria C: Prompt matches test patterns (Only for recent videos < 10m)
            elif video.prompt and any(p in video.prompt for p in test_prompts):
                if video.created_at and (now - video.created_at) < timedelta(minutes=10):
                    log.info(f"Cleanup: Marking video {video.id} for deletion (Prompt matches test patterns)")
                    should_delete = True
                else:
                    log.info(f"Cleanup: Skipping video {video.id} with test prompt (Older than 10m safety window)")
                
            # Criteria D: Empty title AND created VERY recently (last 10 minutes)
            # This catches failed tests that didn't set a title
            elif (not video.title or video.title.strip() == "") and video.created_at:
                 if (now - video.created_at) < timedelta(minutes=10):
                     log.info(f"Cleanup: Marking video {video.id} for deletion (Empty title + Recent creation)")
                     should_delete = True

            if should_delete:
                try:
                    # Soft delete + CANCELLED status
                    from backend.models.video import VideoStatus
                    video_repository.delete(video.id, status=VideoStatus.CANCELLED)
                    deleted_count += 1
                except Exception as e:
                    log.error(f"Cleanup: Failed to delete video {video.id}: {e}")
        
        # Check ALREADY deleted videos (trash) - ensure none are "processing"
        else:
            from backend.models.video import VideoStatus
            if video.status in [VideoStatus.PENDING, VideoStatus.PROCESSING, VideoStatus.RENDERING]:
                log.warning(f"Cleanup: Found active video {video.id} in trash (Status: {video.status}). Fixing to CANCELLED.")
                try:
                    video_repository.delete(video.id, status=VideoStatus.CANCELLED)
                    deleted_count += 1 # Count fixes as well
                except Exception as e:
                    log.error(f"Cleanup: Failed to fix video {video.id} status: {e}")

    log.info(f"Cleanup finished. Processed {deleted_count} video(s).")

if __name__ == "__main__":
    cleanup()
