from fastapi import APIRouter, Depends
from typing import List, Dict, Any
from backend.core.voice_data import VOICES_DATA
from backend.api.deps import get_current_user
from backend.models.user import UserModel

router = APIRouter()

@router.get("", response_model=List[Dict[str, Any]])
async def list_voices(
    current_user: UserModel = Depends(get_current_user)
):
    """
    Returns a list of all available voices with metadata and demo URLs.
    """
    voices = []
    for voice in VOICES_DATA:
        # Construct the demo URL
        # Assumes the generation script has run or will run
        demo_url = f"/api/storage/audios/demos/{voice['name']}.mp3"
        
        voice_data = voice.copy()
        voice_data["demo_url"] = demo_url
        voices.append(voice_data)
        
    return voices
