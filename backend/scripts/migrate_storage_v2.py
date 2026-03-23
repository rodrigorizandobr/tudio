import os
import shutil
import asyncio
from backend.core.configs import settings
from backend.core.logger import log
from backend.repositories.video_repository import video_repository
from backend.models.video import VideoModel

# Initialize logging
log.info("Starting Storage Migration to V2 Structure...")

STORAGE_ROOT = settings.STORAGE_DIR
VIDEOS_ROOT = os.path.join(STORAGE_ROOT, "videos")

def migrate_stock_folders():
    """
    Moves provider folders (pexels, pixabay, google, youtube) 
    from storage/videos/ to storage/videos/search/
    """
    log.info("--- Migrating Stock Folders ---")
    search_root = os.path.join(VIDEOS_ROOT, "search")
    os.makedirs(search_root, exist_ok=True)

    providers = ["pexels", "pixabay", "google", "youtube"]
    
    for provider in providers:
        old_path = os.path.join(VIDEOS_ROOT, provider)
        new_path = os.path.join(search_root, provider)
        
        if os.path.exists(old_path) and os.path.isdir(old_path):
            if os.path.exists(new_path):
                # Merge: Move files individually
                log.info(f"Merging {provider} into {new_path}...")
                for item in os.listdir(old_path):
                    s = os.path.join(old_path, item)
                    d = os.path.join(new_path, item)
                    if os.path.isfile(s):
                        shutil.move(s, d)
                try:
                    os.rmdir(old_path) # Remove if empty
                except:
                    pass
            else:
                # Move entire folder
                log.info(f"Moving {provider} to {new_path}...")
                shutil.move(old_path, new_path)
        else:
           pass # Folder doesn't exist, skip

def migrate_project_videos():
    """
    Iterates all videos and updates file structure.
    """
    log.info("--- Migrating Project Videos ---")
    videos = video_repository.list_all()
    
    for video in videos:
        log.info(f"Processing Video {video.id}...")
        project_dir = os.path.join(VIDEOS_ROOT, str(video.id))
        os.makedirs(project_dir, exist_ok=True)
        
        updated = False
        
        # 1. Final Video
        # Old: storage/videos/final_{id}.mp4 OR storage/videos/{id}/Final.mp4
        # New: storage/videos/{id}/final.mp4
        old_legacy_path = os.path.join(VIDEOS_ROOT, f"final_{video.id}.mp4")
        capital_final_path = os.path.join(project_dir, "Final.mp4")
        final_path = os.path.join(project_dir, "final.mp4")
        
        if os.path.exists(old_legacy_path):
            log.info(f"  Moving Final Video: {old_legacy_path} -> {final_path}")
            shutil.move(old_legacy_path, final_path)
            video.video_url = f"videos/{video.id}/final.mp4"
            updated = True
            
        # Recovery: Check for interrupted rename
        tmp_final_path = os.path.join(project_dir, "final_tmp_rename.mp4")
        if os.path.exists(tmp_final_path):
             try:
                 log.info(f"  Recovery: Moving {tmp_final_path} -> {final_path}")
                 os.rename(tmp_final_path, final_path)
                 video.video_url = f"videos/{video.id}/final.mp4"
                 updated = True
             except Exception as e:
                 log.error(f"  Failed to recover {tmp_final_path}: {e}")
             
        elif os.path.exists(capital_final_path):
            # Check if it is actually capitalized (or if we just found it via case-insensitive OS)
            actual_name = next((f for f in os.listdir(project_dir) if f.lower() == "final.mp4"), None)
            
            if actual_name and actual_name == "Final.mp4":
                try:
                    log.info(f"  Renaming Final.mp4 -> final.mp4 for video {video.id}")
                    # Use absolute paths constructed from dir + actual_name to be safe
                    src = os.path.join(project_dir, actual_name)
                    if os.path.exists(src):
                        os.rename(src, tmp_final_path)
                        os.rename(tmp_final_path, final_path)
                        video.video_url = f"videos/{video.id}/final.mp4"
                        updated = True
                except Exception as e:
                    log.error(f"  Failed to rename {actual_name}: {e}")

        # Check DB consistency
        if video.video_url and ("Final.mp4" in video.video_url or "final_" in video.video_url):
             if video.video_url != f"videos/{video.id}/final.mp4":
                video.video_url = f"videos/{video.id}/final.mp4"
                updated = True

        # 2. Scene Clips
        # Old: storage/videos/scenes/{id}/scene_{id}_{c}_{s}_{sc}.mp4 OR videos/{id}/Scenes/...
        # New: storage/videos/{id}/scenes/{c}-{s}-{sc}.mp4
        
        capital_scenes_dir = os.path.join(project_dir, "Scenes")
        scenes_dir = os.path.join(project_dir, "scenes") # Lowercase target

        # Fix: If "Scenes" (Capitalized) exists from previous run, rename it to lowercase
        # On macOS (Case Insensitive), we must rename to temp first
        if os.path.exists(capital_scenes_dir):
            try:
                # Check if it's already lowercase in specific (hard to do strictly in python on mac without stat)
                # But we can just force the rename loop if we are sure we want 'scenes'
                
                # If we rely on os.path.exists vs string matching, on mac "scenes" exists if "Scenes" exists.
                # So we just rename to temp and back to target if it exists.
                
                # Check if the directory name on disk is actually "Scenes" is tricky.
                # Listing the parent dir is the reliable way.
                actual_name = next((d for d in os.listdir(project_dir) if d.lower() == "scenes"), None)
                
                if actual_name and actual_name == "Scenes":
                    log.info(f"  Renaming {actual_name} -> scenes in {project_dir}")
                    tmp_dir = os.path.join(project_dir, "scenes_tmp_rename")
                    os.rename(capital_scenes_dir, tmp_dir)
                    os.rename(tmp_dir, scenes_dir)
            except Exception as e:
                log.warning(f"  Error fixing case for scenes folder: {e}")

        os.makedirs(scenes_dir, exist_ok=True)
        
        # Check old scenes dir (legacy root)
        old_scenes_dir = os.path.join(VIDEOS_ROOT, "scenes", str(video.id))
        
        if video.chapters:
            for chapter in video.chapters:
                for subchapter in chapter.subchapters:
                    for scene in subchapter.scenes:
                        new_filename = f"{chapter.order}-{subchapter.order}-{scene.order}.mp4"
                        
                        # Update DB path to lowercase 'scenes'
                        if scene.generated_video_url and "Scenes" in scene.generated_video_url:
                             scene.generated_video_url = f"videos/{video.id}/scenes/{new_filename}"
                             updated = True
                        
                        # Construct legacy filename pattern
                        old_filename = f"scene_{video.id}_{chapter.order}_{subchapter.order}_{scene.order}.mp4"
                        
                        # Check where it is
                        candidates = []
                        if os.path.exists(old_scenes_dir):
                            candidates.append(os.path.join(old_scenes_dir, old_filename))
                        
                        candidates.append(os.path.join(VIDEOS_ROOT, old_filename))
                        
                        found_path = None
                        for p in candidates:
                            if os.path.exists(p):
                                found_path = p
                                break
                        
                        if found_path:
                            new_path = os.path.join(scenes_dir, new_filename)
                            
                            if not os.path.exists(new_path): 
                                log.info(f"  Moving Scene {scene.id}: {found_path} -> {new_path}")
                                shutil.move(found_path, new_path)
                            
                            scene.generated_video_url = f"videos/{video.id}/scenes/{new_filename}"
                            updated = True

        if updated:
            log.info(f"  Saving updates for Video {video.id}...")
            video_repository.save(video)
        
        # Cleanup old scenes dir if empty
        if os.path.exists(old_scenes_dir) and not os.listdir(old_scenes_dir):
             os.rmdir(old_scenes_dir)

def main():
    migrate_stock_folders()
    migrate_project_videos()
    
    # Final cleanup
    old_scenes_root = os.path.join(VIDEOS_ROOT, "scenes")
    if os.path.exists(old_scenes_root) and not os.listdir(old_scenes_root):
        os.rmdir(old_scenes_root)
        
    log.info("Migration Complete! 🚀")

if __name__ == "__main__":
    main()
