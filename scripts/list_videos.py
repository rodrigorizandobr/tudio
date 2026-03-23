
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
    try:
        videos = video_repository.list_all()
        print(f"Found {len(videos)} videos")
        for v in videos[:5]: # Show top 5
            print(f"ID: {v.id} | Title: {v.title} | Status: {v.status} | Created: {v.created_at}")
    except Exception as e:
        print(f"Error listing videos: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
