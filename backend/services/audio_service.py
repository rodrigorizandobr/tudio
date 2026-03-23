import os
from backend.core.logger import log
from backend.services.openai_service import openai_service
from backend.models.video import VideoModel, VideoStatus

from backend.repositories.video_repository import video_repository

class AudioService:
    def __init__(self):
        self.base_dir = "storage/audios"

    async def generate_narration_for_video(self, video: VideoModel, force: bool = False, standalone: bool = False):
        """
        Generates TTS for all scenes in a video. 
        """
        log.info(f"AudioService: Generating narration for Video {video.id} (force={force}, standalone={standalone})")
        
        if video.deleted_at:
            log.warning(f"AudioService: Video {video.id} is deleted. Skipping narration.")
            return False
        total_scenes = 0
        for chapter in video.chapters:
            for subchapter in chapter.subchapters:
                total_scenes += len(subchapter.scenes)
        
        processed_scenes = 0
        
        for chapter in video.chapters:
            for subchapter in chapter.subchapters:
                for scene in subchapter.scenes:
                    if scene.deleted:
                        continue
                        
                    processed_scenes += 1
                    
                    if total_scenes > 0:
                        if standalone:
                            progress_increment = (processed_scenes / total_scenes) * 95.0
                            new_progress = progress_increment
                        else:
                            # Update progress: Range 75% -> 95%
                            progress_increment = (processed_scenes / total_scenes) * 20.0
                            new_progress = 75.0 + progress_increment
                            
                        video.progress = min(95.0, round(new_progress, 1))
                        await video_repository.save(video)

                    # Check for deletion or cancellation during loop
                    check_video = await video_repository.get(video.id)
                    if not check_video or check_video.deleted_at or check_video.status == VideoStatus.CANCELLED:
                        log.info(f"AudioService: Video {video.id} deleted or CANCELLED during narration loop. Stopping.")
                        return False

                    await self.generate_narration_for_single_scene(video, chapter, subchapter, scene, force=force)

        return True

    async def generate_narration_for_single_scene(self, video: VideoModel, chapter, subchapter, scene, force: bool = True):
        """
        Generates TTS for a single specific scene.
        """
        if not scene.narration_content:
            return False

        if video.deleted_at:
            log.warning(f"AudioService: Video {video.id} deleted. Skipping single scene narration.")
            return False

        log.info(f"AudioService: Generating audio for Scene {scene.order} in Video {video.id}")
        
        # Base path without timestamp (for checking if ANY exists but force is True)
        # We now generate a unique path with a timestamp to prevent OS/FFmpeg caching issues
        import time
        timestamp = int(time.time())
        audio_rel_path = f"{video.id}/{chapter.order}-{subchapter.order}-{scene.order}_{timestamp}.mp3"
        audio_full_path = os.path.join(self.base_dir, audio_rel_path)
        
        # If force is false, we should check if ANY audio exists for this scene.
        # But since we changed the naming, we just check if it already has an audio_url.
        if scene.audio_url and "api/storage/audios" in scene.audio_url and not force:
            log.info(f"AudioService: Audio already exists for scene {scene.order}, skipping.")
            return True
        
        if scene.audio_url and force:
            log.info(f"AudioService: Audio exists for scene {scene.order}, but force=True. Overwriting with new unique file.")

        try:
            from backend.core.voice_data import VOICES_DATA
            allowed_voices = {v['name'].lower() for v in VOICES_DATA}
            # Add strict OpenAI basics just in case they are not in VOICES_DATA (though they should be)
            allowed_voices.update({'alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer', 'ash', 'coral', 'sage', 'verse', 'ballad'})
            voice = "nova"
            
            if scene.character:
                 # Find character (case-insensitive name match is standard practice)
                 normalized_scene_char = scene.character.lower()
                 
                 # Normalization Bridge (Common LLM variations)
                 if normalized_scene_char in ["narrator", "narrador"]:
                     normalized_scene_char = "narrador" # Preference for Portuguese/Main character
                
                 target_char = next((c for c in video.characters if c.name.lower() == normalized_scene_char), None)
                 
                 # SAFETY FALLBACK: If mismatch persists but there's a character defined, use the first one
                 # Especially useful when LLM hallucinates names or translations.
                 if not target_char and video.characters:
                     target_char = video.characters[0]
                     log.warning(f"AudioService: Scene character '{scene.character}' not matched exactly. Falling back to first available character: '{target_char.name}'")

                 if target_char and target_char.voice:
                     # STRICT: Always convert to lowercase
                     voice_candidate = target_char.voice.lower()
                     
                     if voice_candidate in allowed_voices:
                         voice = voice_candidate
                         log.info(f"AudioService: Selected voice '{voice}' for character '{target_char.name}'")
                     else:
                         log.warning(f"Character '{target_char.name}' has voice '{target_char.voice}' but '{voice_candidate}' is NOT in allowed list. Fallback to 'nova'.")
            
            text_preview = scene.narration_content[:100] if scene.narration_content else "EMPTY"
            log.info(f"AudioService: Generating TTS for scene {scene.order} with text: '{text_preview}...'")

            await openai_service.generate_tts(
                text=scene.narration_content,
                output_path=audio_full_path,
                voice=voice,
                instructions=video.audio_generation_instructions or "Atue como um locutor profissional brasileiro, nativo de São Paulo. Seu sotaque deve ser exclusivamente brasileiro (paulistano). Nunca use entonação ou pronúncia de Portugal. Fale de forma calma e pausada."
            )
            
            # VALIDATION: Check if file exists and is non-empty
            if not os.path.exists(audio_full_path) or os.path.getsize(audio_full_path) < 100:
                raise ValueError(f"Generated audio file is invalid or too small: {audio_full_path}")

            from datetime import datetime
            scene.audio_url = f"/api/storage/audios/{audio_rel_path}"
            log.info(f"AudioService: Generated audio for Scene {scene.order} (Size: {os.path.getsize(audio_full_path)} bytes)")
            
            # Save scene URL immediately
            await video_repository.save(video)
            return True
            
        except Exception as e:
            log.error(f"AudioService: Failed for scene {scene.order}: {e}")
            return False

        return True

audio_service = AudioService()
