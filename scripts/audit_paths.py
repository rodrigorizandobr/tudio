
import sys
import os
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from backend.repositories.script_repository import script_repository

def audit_script(script_id):
    print(f"Auditing script {script_id}...")
    script = script_repository.get(int(script_id))
    if not script:
        print("Script not found")
        return

    for chapter in script.chapters:
        for sub in chapter.subchapters:
            for scene in sub.scenes:
                if scene.original_image_url:
                    print(f"[{chapter.order}-{sub.order}-{scene.order}] Original: {scene.original_image_url}")
                if scene.cropped_image_url:
                    print(f"[{chapter.order}-{sub.order}-{scene.order}] Cropped: {scene.cropped_image_url}")

if __name__ == "__main__":
    audit_script(sys.argv[1])
