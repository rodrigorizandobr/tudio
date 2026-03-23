import os
import sys
import json

# Setup environment
os.environ["STORAGE_DIR"] = "storage"
sys.path.append(os.getcwd())

from backend.models.video import VideoModel, ChapterModel, SubChapterModel, SceneModel, VideoStatus

def test_pydantic_nested_update():
    # 1. Create a dummy video model
    video = VideoModel(
        prompt="Test",
        target_duration_minutes=1,
        status=VideoStatus.PENDING,
        chapters=[
            ChapterModel(
                id=1, order=1, title="Ch 1", estimated_duration_minutes=1.0, description="D 1",
                subchapters=[
                    SubChapterModel(
                        id=1, order=1, title="Sub 1", description="SD 1",
                        scenes=[
                            SceneModel(
                                id=1, order=1, narration_content="Hi", image_prompt="Image", video_prompt="Video"
                            )
                        ]
                    )
                ]
            )
        ]
    )
    
    # 2. Modify scene nestedly
    video.chapters[0].subchapters[0].scenes[0].generated_video_url = "updated_url.mp4"
    
    # 3. Dump to JSON
    dumped = video.model_dump(mode="json")
    
    # 4. Verify in dict
    scenes = dumped['chapters'][0]['subchapters'][0]['scenes']
    url = scenes[0].get('generated_video_url')
    
    print(f"Dumped URL: {url}")
    if url == "updated_url.mp4":
        print("Pydantic nested update works!")
    else:
        print("Pydantic nested update FAILED in dump!")

if __name__ == "__main__":
    test_pydantic_nested_update()
