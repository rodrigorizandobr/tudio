import sys
import os
import asyncio
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from backend.repositories.video_repository import video_repository
from backend.models.video import VideoStatus

VIDEO_ID = 5103757536788480

async def fix_video():
    print(f"Fetching video {VIDEO_ID}...")
    video = video_repository.get(VIDEO_ID)
    
    if not video:
        print(f"Video {VIDEO_ID} not found!")
        return

    print(f"Video found: {video.prompt}")
    print(f"Current Status: {video.status}")
    
    updated = False
    for chapter in video.chapters:
        print(f"  Chapter {chapter.order}: {chapter.status}")
        
        # Logic to fix stuck processing
        if chapter.status == VideoStatus.PROCESSING:
            # Check if it has content
            has_content = len(chapter.subchapters) > 0
            
            if has_content:
                print(f"    -> FIXED: Marked as COMPLETED (had content)")
                chapter.status = VideoStatus.COMPLETED
                updated = True
            else:
                print(f"    -> WARNING: Stuck in PROCESSING but has no content.")
                # Optional: Reset to PENDING? 
                # User complaint is about "stuck". If it has no content, it SHOULD be pending or processing.
                # But it's not running. So reset to PENDING so user can reprocess?
                # Actually, if we reset to PENDING, the UI might show "Reprocess" button enabled?
                # Let's reset to ERROR so user sees it failed?
                # Or PENDING.
                print(f"    -> RESETTING to PENDING to allow reprocess.")
                chapter.status = VideoStatus.PENDING
                updated = True

    if updated:
        video_repository.save(video)
        print("Video saved with updates.")
    else:
        print("No changes needed.")

if __name__ == "__main__":
    asyncio.run(fix_video())
