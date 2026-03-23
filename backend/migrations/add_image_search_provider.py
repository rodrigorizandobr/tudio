"""
Migration: Add image_search_provider to scenes

This migration adds a new column to store the image provider
used for each scene's image search (unsplash, serpapi, bing).
"""

from google.cloud import ndb
from backend.models.video import Video
from backend.core.logger import log

def upgrade():
    """Add image_search_provider field to all existing scenes."""
    log.info("Starting migration: Add image_search_provider to scenes")
    
    # Query all videos
    videos = Video.query().fetch()
    updated_count = 0
    
    for video in videos:
        modified = False
        
        if video.chapters:
            for chapter in video.chapters:
                if hasattr(chapter, 'subchapters') and chapter.subchapters:
                    for subchapter in chapter.subchapters:
                        if hasattr(subchapter, 'scenes') and subchapter.scenes:
                            for scene in subchapter.scenes:
                                # Add provider field if it doesn't exist
                                if not hasattr(scene, 'image_search_provider'):
                                    # Default to 'unsplash' for existing scenes
                                    scene.image_search_provider = 'unsplash'
                                    modified = True
        
        if modified:
            video.put()
            updated_count += 1
            log.info(f"Updated video {video.id}: Added image_search_provider to scenes")
    
    log.info(f"Migration complete: Updated {updated_count} videos")
    return updated_count

def downgrade():
    """Remove image_search_provider field (not implemented for NoSQL)."""
    log.warning("Downgrade not implemented for NoSQL databases")
    pass

if __name__ == "__main__":
    # Run migration
    count = upgrade()
    print(f"Migration completed: {count} videos updated")
