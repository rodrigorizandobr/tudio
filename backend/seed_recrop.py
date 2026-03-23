import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models.video import VideoModel, ChapterModel, SubChapterModel, SceneModel, VideoStatus
from backend.repositories.video_repository import video_repository
from datetime import datetime

def seed():
    print("Seeding re-crop verification video...")
    
    scene = SceneModel(
        id=1,
        order=1,
        duration_seconds=10,
        narration_content="Cena de Teste Para Re-Crop",
        character_name="Narrador",
        voice_type="Neutro",
        visual_description="Uma paisagem bonita para testar crop",
        image_prompt="Uma paisagem natural com montanhas",
        image_search="forest", # Enabled for search
        video_prompt="Video teste",
        audio_prompt="Audio teste"
    )

    sub = SubChapterModel(
        id=1,
        order=1,
        title="Subcapítulo de Teste",
        description="Descrição do subcapítulo",
        scenes=[scene]
    )

    chapter = ChapterModel(
        id=1,
        order=1,
        title="Capítulo de Teste",
        estimated_duration_minutes=1,
        description="Descrição do capítulo",
        subchapters=[sub]
    )

    video = VideoModel(
        prompt="Roteiro de Verificação de Re-Crop",
        target_duration_minutes=1,
        language="pt-br",
        status=VideoStatus.COMPLETED,
        progress=100.0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        chapters=[chapter],
        visual_style="Realista",
        characters=[]
    )

    try:
        saved = video_repository.save(video)
        print(f"SUCCESS: Created video with ID: {saved.id}")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    seed()
