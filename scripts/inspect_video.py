
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

try:
    from backend.repositories.video_repository import video_repository
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: python inspect_video.py <video_id>")
        return
    
    try:
        video_id = int(sys.argv[1])
    except ValueError:
        print("Video ID must be an integer")
        return

    try:
        video = video_repository.get(video_id)
        if not video:
            print(f"Video {video_id} not found in repository.")
        else:
            print(f"--- Video {video_id} Found ---")
            print(f"Title: '{video.title}'")
            print(f"Description: '{video.description}'")
            print(f"Tags: '{video.tags}'")
            print(f"Music: '{video.music}'")
            print(f"Status: {video.status}")
            print(f"Auto Image Source: {video.auto_image_source}")
            print("-" * 20)
            print("Scenes:")
            for chapter in video.chapters:
                for subchapter in chapter.subchapters:
                    for scene in subchapter.scenes:
                        print(f"  Scene {chapter.order}.{subchapter.order}.{scene.order}:")
                        print(f"    Image Prompt: {scene.image_prompt[:50]}...")
                        print(f"    Original Image: {scene.original_image_url}")
                        print(f"    Cropped Image: {scene.cropped_image_url}")
    except Exception as e:
        print(f"Error retrieving video: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
