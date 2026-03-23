
import sys
import os
import json

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.repositories.script_repository import script_repository

def fix_image_paths(script_id):
    print(f"Fetching script {script_id}...")
    script = script_repository.get(int(script_id))
    
    if not script:
        print("Script not found!")
        return

    modified = False
    
    for chapter in script.chapters:
        for sub in chapter.subchapters:
            for scene in sub.scenes:
                # Check original_image_url
                if scene.original_image_url and 'undefined-undefined' in scene.original_image_url:
                    old_url = scene.original_image_url
                    # Replace undefined-undefined-X with X-X-X (assuming chapter-sub-scene)
                    # Actually, the user specifically mentioned "undefined-undefined-1" -> "1-1-1"
                    # But if we have dynamic ones, we should construct it from IDs?
                    # The user prompt implied specific mapping for THIS video: "1-1-1"
                    # Let's use the scene orders to be safe: {chapter.order}-{sub.order}-{scene.order}
                    
                    correct_id = f"{chapter.order}-{sub.order}-{scene.order}"
                    new_url = old_url.replace(f"undefined-undefined-{scene.order}", correct_id)
                    new_url = new_url.replace("undefined-undefined", correct_id) # Fallback
                    
                    scene.original_image_url = new_url
                    print(f"Fixed Original: {old_url} -> {new_url}")
                    modified = True

                # Check cropped_image_url
                if scene.cropped_image_url and 'undefined-undefined' in scene.cropped_image_url:
                    old_url = scene.cropped_image_url
                    correct_id = f"{chapter.order}-{sub.order}-{scene.order}"
                    new_url = old_url.replace(f"undefined-undefined-{scene.order}", correct_id)
                    new_url = new_url.replace("undefined-undefined", correct_id)
                    
                    scene.cropped_image_url = new_url
                    print(f"Fixed Cropped: {old_url} -> {new_url}")
                    modified = True

    if modified:
        print("Saving changes...")
        script_repository.save(script)
        print("Done!")
    else:
        print("No changes needed.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_image_paths.py <script_id>")
        sys.exit(1)
        
    fix_image_paths(sys.argv[1])
