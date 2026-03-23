
import sys
import os
import asyncio

# Add project root to path
sys.path.append(os.getcwd())

from backend.services.video_service import video_service

def main():
    if len(sys.argv) < 2:
        print("Usage: python reprocess_video.py <video_id>")
        return
    
    video_id = int(sys.argv[1])
    print(f"Triggering background processing for {video_id}...")
    
    # We need to run the async method
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(video_service.process_video_background(video_id))
    print("Processing complete.")

if __name__ == "__main__":
    main()
