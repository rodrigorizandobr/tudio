import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.repositories.video_repository import video_repository
from backend.models.video import VideoModel

def migrate_scenes():
    print("Starting Scene Migration...")
    videos = video_repository.list_all()
    count = 0
    
    for video in videos:
        updated = False
        if not video.chapters:
            continue
            
        for chapter in video.chapters:
            if not chapter.subchapters:
                continue
                
            for subchapter in chapter.subchapters:
                if not subchapter.scenes:
                    continue
                    
                for scene in subchapter.scenes:
                    # Migration Logic
                    
                    # 1. voice (Migration from voice_type if missing)
                    if not scene.voice and scene.voice_type:
                        scene.voice = scene.voice_type
                        updated = True
                        
                    # 2. Defaults for new fields (Auto-handled by Pydantic defaults usually if re-instantiated, but explicit here)
                    if scene.audio_effect_seconds_start is None:
                        scene.audio_effect_seconds_start = 0
                        updated = True
                    
        if updated:
            video_repository.save(video)
            count += 1
            print(f"Migrated Video ID: {video.id}")

    print(f"Migration Complete. Updated {count} videos.")

if __name__ == "__main__":
    migrate_scenes()
