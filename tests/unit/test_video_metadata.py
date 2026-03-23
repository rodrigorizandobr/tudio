import pytest
from backend.models.video import VideoModel, SceneModel, CharacterModel, VideoStatus

def test_video_model_metadata_sprint_62():
    """Verify Sprint 62 metadata fields: title, description, tags."""
    video = VideoModel(
        prompt="Test Prompt",
        target_duration_minutes=1.0,
        language="pt-BR",
        status=VideoStatus.PENDING,
        # New fields
        title="My Epic Movie",
        description="A story about testing.",
        tags="test,unit,python",
        visual_style="Anime",
        music="Epic Orchestral", # Sprint 63
        auto_image_source="unsplash" # Sprint 64
    )
    
    assert video.title == "My Epic Movie"
    assert video.description == "A story about testing."
    assert video.tags == "test,unit,python"
    assert video.visual_style == "Anime"
    assert video.music == "Epic Orchestral"
    assert video.auto_image_source == "unsplash"

def test_scene_model_schema_sprint_61():
    """Verify Sprint 61 schema fields: voice, audio_effect_search, etc."""
    scene = SceneModel(
        id=1,
        order=1,
        narration_content="Hello world",
        image_prompt="A beautiful world",
        video_prompt="Flying over world",
        # New fields
        voice="Male - Deep",
        audio_effect_search="Wind blowing",
        audio_effect_seconds_start=5
    )
    
    assert scene.voice == "Male - Deep"
    assert scene.audio_effect_search == "Wind blowing"
    assert scene.audio_effect_seconds_start == 5
    # Verify defaults
    assert scene.character_name is None
    assert scene.voice_type is None 

def test_video_characters():
    """Verify CharacterModel integration in VideoModel."""
    char = CharacterModel(
        name="Hero",
        physical_description="Strong",
        voice_type="Loud"
    )
    video = VideoModel(
        prompt="Test",
        target_duration_minutes=1,
        language="en",
        status=VideoStatus.PENDING,
        characters=[char]
    )
    
    assert len(video.characters) == 1
    assert video.characters[0].name == "Hero"
