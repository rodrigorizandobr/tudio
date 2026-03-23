
import asyncio
import os
import sys

# Ensure backend path is in python path
sys.path.append(os.getcwd())

from backend.core.logger import log
from backend.services.openai_service import openai_service
from backend.core.voice_data import VOICES_DATA
from backend.core.configs import settings

async def main():
    log.info("Starting Voice Demo Generation...")
    
    # Ensure storage directory
    demo_dir = os.path.join(settings.STORAGE_DIR, "audios", "demos")
    os.makedirs(demo_dir, exist_ok=True)
    
    generated_count = 0
    
    for voice in VOICES_DATA:
        name = voice["name"]
        description = voice["description"]
        
        filename = f"{name}.mp3"
        output_path = os.path.join(demo_dir, filename)
        
        # Force regeneration for new audio voices or Ash
        is_audio_voice = name in ["ballad", "verse", "marin", "cedar", "ash"]
        if is_audio_voice:
             if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                    log.info(f"Removed '{name}' to force update with GPT-4o Audio.")
                except OSError:
                    pass

        if os.path.exists(output_path):
             log.info(f"Demo for '{name}' already exists. Skipping.")
             continue
            
        log.info(f"Generating demo for voice: {name}...")
        
        # REQUIRED PHRASE
        text = f"- Aqui esta um exemplo de voz. Esta é a voz {name}."
        
        try:
            # Instructions to ensure Portuguese accent even for short names/phrases
            # and to prevent the model from adding conversational filler.
            instructions = "Speak calmly, pausing between words, in Brazilian Portuguese, with a São Paulo accent, never in portuguese from Portugal."
            
            await openai_service.generate_tts(
                text=text,
                output_path=output_path,
                voice=name,
                instructions=instructions if is_audio_voice else None 
            )
            generated_count += 1
            log.info(f"Successfully generated {name}")
            
        except Exception as e:
            log.error(f"Failed to generate demo for '{name}': {e}")
            
    log.info(f"Voice Demo Generation Completed. New files: {generated_count}")

if __name__ == "__main__":
    asyncio.run(main())
