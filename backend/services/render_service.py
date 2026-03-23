import os
import asyncio
import subprocess
from typing import Optional, List
from datetime import datetime
from backend.core.logger import log
from backend.models.video import VideoModel, VideoStatus
from backend.repositories.video_repository import video_repository

from backend.repositories.music_repository import music_repository
# --- MOVIEPY COMPATIBILITY PATCH ---
import PIL.Image
# MoviePy might use deprecated PIL.Image.ANTIALIAS. 
# We ensure LANCZOS is available as a fallback.
if not hasattr(PIL.Image, 'LANCZOS'):
    PIL.Image.LANCZOS = PIL.Image.Resampling.LANCZOS
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
# -----------------------------------

from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, VideoFileClip, concatenate_videoclips, CompositeAudioClip
import moviepy.video.fx.all as vfx
import moviepy.audio.fx.all as afx

class RenderService:
    def __init__(self):
        from backend.core.configs import settings
        self.storage_dir = settings.STORAGE_DIR
        self.output_dir = os.path.join(settings.STORAGE_DIR, "videos")
        # MoviePy manages its own binaries usually, but we keep this for legacy or specialized probes if needed
        self._ffmpeg_path = self._get_binary_path("ffmpeg")
        self._ffprobe_path = self._get_binary_path("ffprobe")
        
        # --- MOVIEPY BINARY CONFIGURE ---
        try:
            from moviepy.config import change_settings
            change_settings({"FFMPEG_BINARY": self._ffmpeg_path})
            log.info(f"RenderService: MoviePy configured to use FFmpeg at {self._ffmpeg_path}")
        except Exception as e:
            log.warning(f"RenderService: Failed to configure MoviePy binary: {e}")

    def _get_binary_path(self, name: str) -> str:
        """
        Robustly locates a binary (ffmpeg/ffprobe) in common system paths.
        """
        import shutil
        # 1. Try default system PATH
        path = shutil.which(name)
        if path:
            return path
        
        # 2. Try common installation paths for Mac
        common_paths = [
            f"/opt/homebrew/bin/{name}",
            f"/usr/local/bin/{name}",
            f"/usr/bin/{name}",
        ]
        for p in common_paths:
            if os.path.exists(p):
                log.info(f"Resolved {name} to: {p}")
                return p
        
        log.warning(f"Could not find {name} in common paths. Falling back to default name.")
        return name

    async def render_video(self, video: VideoModel, target_ratio: str = "16:9", progress_callback=None):
        """
        Orchestrates the final video assembly using MoviePy for a SPECIFIC aspect ratio.
        """
        video_id = video.id
        format_name = "horizontal" if target_ratio == "16:9" else "vertical"
        log.info(f"RenderService: Starting assembly for Video {video_id} - Format: {format_name}")
        
        # 1. First, ensure scenes are rendered
        scenes_paths = await self.render_scenes_only(video, target_ratio, progress_callback)
        if scenes_paths is None:
            return None # Error already handled
            
        if not scenes_paths:
            log.error(f"RenderService ({format_name}): No valid clips.")
            return None

        # 2. Concatenation Phase
        music_path = None
        if video.music_id:
            try:
                music = await music_repository.get(video.music_id)
                if music:
                    music_path = self._resolve_path(music.file_path)
            except Exception as e:
                log.warning(f"RenderService: Music error: {e}")

        # Final Output Per Format
        final_filename = f"final_{format_name}.mp4"
        final_output = os.path.join(self.storage_dir, "videos", str(video_id), final_filename)
        os.makedirs(os.path.dirname(final_output), exist_ok=True)
        
        # We consider scenes_only part of the progress, but we need to update it here too 
        # for the concatenation phase (last 10%)
        if progress_callback:
            await progress_callback(95.0)

        # --- MOCK VIDEO GENERATION FOR TESTING ---
        from backend.core.configs import settings
        if settings.TESTING and os.getenv("USE_E2E_MOCKS") == "True":
            log.warning(f"RenderService: Generating E2E mock video for Video {video_id} using FFmpeg.")
            duration = video.total_duration_seconds or 10
            cmd = [
                self._ffmpeg_path, "-y",
                "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={duration}",
                "-f", "lavfi", "-i", f"color=c=blue:s=1920x1080:d={duration}",
                "-c:v", "libx264", "-c:a", "aac", "-shortest", final_output
            ]
            try:
                # Add timeout to prevent hanging on mock generation
                subprocess.run(cmd, check=True, timeout=120)
                success = os.path.exists(final_output)
            except Exception as e:
                log.error(f"RenderService: Mock video generation failed: {e}")
                success = False
        else:
            success = await asyncio.to_thread(self._concatenate_clips, scenes_paths, final_output, music_path=music_path)
        
        if success:
            if progress_callback:
                await progress_callback(100.0)
            log.info(f"RenderService: Final video ({format_name}) rendered: {final_output}")
            return f"videos/{video_id}/{final_filename}"
        else:
            log.error(f"RenderService: Concatenation failed for {format_name}")
            return None

    async def render_scenes_only(self, video: VideoModel, target_ratio: str = "16:9", progress_callback=None) -> Optional[list[str]]:
        """
        Renders only the individual scene MP4s and updates scene.generated_video_url.
        Returns list of absolute paths to temp scene clips.
        """
        video_id = video.id
        format_name = "horizontal" if target_ratio == "16:9" else "vertical"
        log.info(f"RenderService: Rendering scenes for Video {video_id} ({format_name})")
        
        # 1. Validation Phase
        total_scenes = 0
        scenes_to_process = []
        for chapter in video.chapters:
            for sub in chapter.subchapters:
                for scene in sub.scenes:
                    if not scene.deleted:
                        total_scenes += 1
                        
                        has_audio = bool(scene.audio_url)
                        has_visual = bool(scene.original_image_url or scene.video_url)
                        
                        if not has_audio or not has_visual:
                             from backend.core.configs import settings
                             if settings.TESTING and os.getenv("USE_E2E_MOCKS") == "True":
                                 pass
                             else:
                                 log.error(f"Render Validation Failed: Scene {scene.id} missing assets.")
                                 video.status = VideoStatus.ERROR 
                                 video.error_message = f"Cena {scene.id} incompleta ({format_name})."
                                 await video_repository.save(video)
                                 return None
                        scenes_to_process.append(scene)

        # 2. Processing Phase
        scene_clips = []
        current_time_seconds = 0.0
        navigation_index = []
        scenes_processed_count = 0
        scene_counter = 0
        
        total_steps = total_scenes
        
        for chapter in video.chapters:
            # Navigation Marker (might be redundant here but good for consistency)
            timestamp_str = self._format_seconds_to_timestamp(current_time_seconds)
            navigation_index.append(f"{timestamp_str} - {chapter.title}")
            
            for subchapter in chapter.subchapters:
                for scene in subchapter.scenes:
                    if scene.deleted: continue
                    
                    # CHECK CANCELLATION during scene rendering loop
                    check_v = await video_repository.get(video_id)
                    if check_v and check_v.status == VideoStatus.CANCELLED:
                        log.info(f"RenderService: Video {video_id} CANCELLED during scene loop. Stopping.")
                        return None

                    scene_counter += 1
                    
                    try:
                        clip_path = None
                        
                        # 1. Prefer ALREADY CAPTIONED scene if available (fastest, preserves user edits)
                        # We should check for the SPECIFIC ratio
                        if not hasattr(scene, 'captioned_video_urls') or scene.captioned_video_urls is None:
                            scene.captioned_video_urls = {}
                        
                        target_captioned = scene.captioned_video_urls.get(target_ratio)
                            
                        if target_captioned:
                            path = self._resolve_path(target_captioned)
                            if os.path.exists(path):
                                clip_path = path
                                log.info(f"Using pre-captioned clip for scene {scene.id} ({target_ratio})")
                                
                        # 2. Prefer ALREADY GENERATED base scene if available
                        if not clip_path:
                            if not hasattr(scene, 'generated_video_urls') or scene.generated_video_urls is None:
                                scene.generated_video_urls = {}
                            
                            target_generated = scene.generated_video_urls.get(target_ratio)
                                
                            if target_generated:
                                path = self._resolve_path(target_generated)
                                if os.path.exists(path):
                                    clip_path = path
                                    log.info(f"Using pre-generated clip for scene {scene.id} ({target_ratio})")
                                    
                        # 3. Fallback: recreate from scratch
                        if not clip_path:
                            log.info(f"Recreating clip from scratch for scene {scene.id} ({target_ratio})")
                            clip_path = await self._create_scene_clip(video_id, scene, scene_counter, target_ratio=target_ratio)
                            
                    except Exception as e:
                        log.error(f"RenderService: Failed scene {scene.id} ({format_name}): {e}")
                        return None # Parent will handle status
                    
                    if clip_path:
                        scene_clips.append(clip_path)
                        try:
                            audio_path = self._resolve_path(scene.audio_url)
                            audio_dur = await self._get_media_duration(audio_path)
                            current_time_seconds += audio_dur
                            
                            perm_filename = f"{chapter.order}-{subchapter.order}-{scene.order}.mp4"
                            perm_path = os.path.join(self.storage_dir, "videos", str(video_id), "scenes", format_name, perm_filename)
                            os.makedirs(os.path.dirname(perm_path), exist_ok=True)
                            
                            import shutil
                            if os.path.abspath(clip_path) != os.path.abspath(perm_path):
                                shutil.copy2(clip_path, perm_path)
                                
                            # Update base URL so next time it skips base generation too
                            # Append timestamp to break browser cache (416 Range error fix)
                            ts = int(datetime.now().timestamp())
                            final_url = f"videos/{video_id}/scenes/{format_name}/{perm_filename}?t={ts}"
                            
                            # Maintain legacy and new multi-ratio dictionary
                            if not hasattr(scene, 'generated_video_urls') or scene.generated_video_urls is None:
                                scene.generated_video_urls = {}
                            scene.generated_video_urls[target_ratio] = final_url
                            
                            # Only update legacy singular if horizontal
                            if target_ratio == "16:9":
                                scene.generated_video_url = final_url
                            
                            # Perform atomic update instead of full save to prevent clobbering
                            # Re-fetch from repository isn't enough, we re-fetch within the service's update method
                            try:
                                from backend.services.video_service import video_service
                                await video_service.update_scene_generated_url(
                                    video_id=video_id,
                                    chapter_id=chapter.id,
                                    subchapter_id=subchapter.id,
                                    scene_idx=subchapter.scenes.index(scene),
                                    url=scene.generated_video_url
                                )
                                log.info(f"RenderService: Atomically updated generated_video_url for scene {scene.id}")
                            except Exception as e:
                                log.warning(f"Failed atomic update for scene {scene.id}: {e}")
                                # Fallback to direct save if atomic fails
                                await video_repository.save(video)
                        except Exception as e:
                            log.warning(f"Could not save scene clip: {e}")
                    else:
                        log.error(f"RenderService: Scene {scene.id} produced empty clip path. Skipping but continuing.")
                        # Do NOT return None here, just continue to keep loop alive
                        continue

                    scenes_processed_count += 1
                    if progress_callback and total_steps > 0:
                        p = (scenes_processed_count / total_steps) * 90 # Map scenes to 90% of sub-progress
                        await progress_callback(p)

        video.timestamps_index = "\n".join(navigation_index)
        return scene_clips

    def _resolve_path(self, url_or_path: str) -> str:
        """Helper to resolve API URLs to local file system paths."""
        if not url_or_path: return ""
        
        if "?" in url_or_path:
            url_or_path = url_or_path.split("?")[0]

        if "http" in url_or_path and "/api/storage/" in url_or_path:
             url_or_path = url_or_path.split("/api/storage/")[-1]
             return f"storage/{url_or_path}"
             
        if url_or_path.startswith("/api/storage/"):
            return url_or_path.replace("/api/storage/", "storage/")
        
        if url_or_path.startswith("storage/"):
            return url_or_path

        if url_or_path.startswith(("images/", "audios/", "videos/", "temp/", "musics/")):
            return f"storage/{url_or_path}"
            
        return url_or_path

    async def _get_media_duration(self, file_path: str) -> float:
        """
        Async wrapper for ffprobe duration.
        """
        return await asyncio.to_thread(self._get_media_duration_sync, file_path)

    def _get_media_duration_sync(self, file_path: str) -> float:
        """
        Uses ffprobe to get exact duration in seconds.
        """
        resolved_path = self._resolve_path(file_path)
        try:
             cmd = [
                self._ffprobe_path, "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", resolved_path
            ]
             return float(subprocess.check_output(cmd).decode().strip())
        except Exception as e:
            log.error(f"Failed to probe duration for {resolved_path}: {e}")
            return 0.0

    async def _create_scene_clip(self, video_id, scene, scene_counter: int, target_ratio: str = "16:9", padding: float = None) -> str:
        """
        Creates a scene clip strictly following audio duration using MoviePy.
        Implements Auto-Crop and Smooth Zoom (Ken Burns).
        """
        
        # Fetch padding from DB if not provided explicitly
        if padding is None:
            try:
                v = await video_repository.get(video_id)
                padding = (v.audio_transition_padding or 0.5) if v else 0.5
            except Exception:
                padding = 0.5
        
        # Run CPU-bound moviepy code in executor to avoid blocking async event loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._create_scene_clip_sync, video_id, scene, scene_counter, target_ratio, padding)

    def _create_scene_clip_sync(self, video_id, scene, scene_counter: int, target_ratio: str = "16:9", padding: float = 0.5) -> str:
        """
        Synchronous worker for MoviePy rendering with Auto-Crop.
        """
        # --- EARLY EXIT FOR TESTING ---
        from backend.core.configs import settings
        if settings.TESTING and os.getenv("USE_E2E_MOCKS") == "True":
            # We skip real scene clip creation and let the parent render_video 
            # generate a full mock video for the entire timeline.
            # We return a dummy path just to pass the check.
            dummy_path = os.path.join(self.storage_dir, "temp", f"scene_{video_id}_{scene_counter}.mp4")
            # CRITICAL: physically create the file so exists check passes
            os.makedirs(os.path.dirname(dummy_path), exist_ok=True)
            with open(dummy_path, "wb") as f:
                f.write(b"mock clip")
            return dummy_path

        try:
            # Resolve paths
            audio_path = self._resolve_path(scene.audio_url)
            visual_path = ""
            is_video = False
            
            # --- VISUAL RESOLUTION LOGIC ---
            # AUTO-CROP RULE: Always use Original Image or Video. Ignore manual crops.
            
            if scene.video_url:
                path = self._resolve_path(scene.video_url)
                if os.path.exists(path):
                    visual_path = path
                    is_video = True
                else:
                    log.warning(f"Video file missing for scene {scene.id}: {path}")

            if not visual_path and scene.original_image_url:
                path = self._resolve_path(scene.original_image_url)
                if os.path.exists(path):
                    visual_path = path
                else:
                     log.error(f"Original image missing for scene {scene.id}: {path}")
                
            if not os.path.exists(audio_path) or not visual_path:
                log.error(f"Missing files for scene {scene.id}: Audio({audio_path}) or Visual({visual_path})")
                return ""

            # Format name for filename context
            format_name = "horizontal" if target_ratio == "16:9" else "vertical"
            output_path = os.path.join(self.storage_dir, "temp", f"scene_{video_id}_{format_name}_{scene_counter:04d}.mp4")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Load Audio (Master Duration)
            audio_clip = AudioFileClip(audio_path)
            
            # --- AUDIO GLITCH FIX & PADDING ---
            # padding passed from async world
            
            audio_clip = audio_clip.subclip(0, audio_clip.duration)
            audio_clip = afx.audio_fadeout(audio_clip, 0.05)
            audio_clip = afx.audio_fadein(audio_clip, 0.05)
            
            padded_audio_path = self._add_padding_to_audio_ffmpeg_sync(audio_path, padding, video_id, scene_counter)
            
            if padded_audio_path and os.path.exists(padded_audio_path):
                 audio_clip.close()
                 audio_clip = AudioFileClip(padded_audio_path)
            
            final_audio = audio_clip
            duration = final_audio.duration
            
            if duration <= 0:
                log.error(f"Invalid audio duration: {duration}")
                return ""

            # --- AUTO-CROP & ASPECT RATIO LOGIC ---
            if target_ratio == "9:16":
                target_size = (1080, 1920)
                aspect_float = 9/16
            else:
                target_size = (1920, 1080)
                aspect_float = 16/9

            if is_video:
                clip = VideoFileClip(visual_path)
                w, h = clip.size
                input_aspect = w / h
                
                # Logic to 'cover' area and center crop
                if input_aspect > aspect_float:
                    # Input is wider than target => match height
                    formatted_clip = clip.resize(height=target_size[1])
                else:
                    # Input is taller/narrower => match width
                    formatted_clip = clip.resize(width=target_size[0])
                
                # Center Crop (w/ correct coordinates)
                formatted_clip = formatted_clip.crop(
                    x_center=formatted_clip.w / 2,
                    y_center=formatted_clip.h / 2,
                    width=target_size[0],
                    height=target_size[1]
                )
                
                if formatted_clip.duration < duration:
                     formatted_clip = formatted_clip.loop(duration=duration)
                elif formatted_clip.duration > duration:
                     formatted_clip = formatted_clip.subclip(0, duration)
                
                final_clip = formatted_clip.set_audio(audio_clip)

            else:
                # Static Image + Ken Burns
                img_clip = ImageClip(visual_path).set_duration(duration)
                img_w, img_h = img_clip.size
                img_ratio = img_w / img_h
                target_w, target_h = target_size
                
                # Cover logic
                if img_ratio > aspect_float:
                    # Wide image => fit height
                    img_clip = img_clip.resize(height=target_h)
                else:
                    # Tall/Narrow image => fit width
                    img_clip = img_clip.resize(width=target_w)
                
                # Zoom effect (starts from centered cover)
                # Safety: Ensure duration > 0 and add small epsilon to avoid divide by zero or extreme scaling
                z_duration = max(0.1, duration)
                img_clip = img_clip.resize(lambda t: 1.0 + (0.05 * t / z_duration)) 
                
                # Composite with explicit centering
                final_clip = CompositeVideoClip(
                    [img_clip.set_position('center')], 
                    size=target_size
                ).set_audio(audio_clip)

            # Write Video File
            final_clip.write_videofile(
                output_path, 
                fps=30, 
                codec='libx264', 
                audio_codec='aac',
                preset='fast',
                ffmpeg_params=['-pix_fmt', 'yuv420p'],
                threads=2
            )
            
            audio_clip.close()
            final_clip.close()

            return output_path

        except Exception as e:
            log.error(f"RenderService (MoviePy) Error Scene {scene.id}: {e}")
            import traceback
            log.error(traceback.format_exc())
            return ""

    def _crop_to_aspect_ratio(self, clip, target_w, target_h):
        """
        Crops a clip to match the target aspect ratio (centering it).
        Does NOT resize, just crops excess.
        """
        target_ratio = target_w / target_h
        current_w, current_h = clip.size
        current_ratio = current_w / current_h
        
        if current_ratio > target_ratio:
            # Too wide: crop width
            new_w = int(current_h * target_ratio)
            crop_x = (current_w - new_w) // 2
            return clip.crop(x1=crop_x, y1=0, width=new_w, height=current_h)
        else:
            # Too tall: crop height
            new_h = int(current_w / target_ratio)
            crop_y = (current_h - new_h) // 2
            return clip.crop(x1=0, y1=crop_y, width=current_w, height=new_h)

    def _concatenate_clips(self, clip_paths: list[str], output_path: str, music_path: str = None) -> bool:
        """
        Joins all scene clips using MoviePy.
        """
        try:
            clips = []
            for path in clip_paths:
                clips.append(VideoFileClip(path))
            
            final_concat = concatenate_videoclips(clips, method="chain") # chain is better if all sized match
            
            # --- BACKGROUND MUSIC MIXING ---
            if music_path and os.path.exists(music_path):
                try:
                    log.info(f"RenderService: Mixing background music from {music_path}")
                    music_clip = AudioFileClip(music_path)
                    
                    # 1. Loop/Trim to match video duration
                    # Note: afx.audio_loop might behavior differently depending on version, 
                    # usually it repeats. If it doesn't take duration, we might need manual loop.
                    # But standard MoviePy 'audio_loop' takes duration (or n). 
                    # Actually, 'afx.audio_loop' is often just 'loop'. Let's use the clip method if available or afx.
                    
                    # Safe loop implementation
                    # Use duration argument to handle looping and trimming automatically
                    music_clip = afx.audio_loop(music_clip, duration=final_concat.duration)
                    
                    # Trim to exact duration (redundant if audio_loop handles it, but safe)
                    music_clip = music_clip.subclip(0, final_concat.duration)
                    
                    # 2. Volume (20%)
                    music_clip = music_clip.volumex(0.2)
                    
                    # 3. Fade Out (5s)
                    fade_duration = min(5.0, final_concat.duration)
                    music_clip = afx.audio_fadeout(music_clip, fade_duration)
                    
                    # 4. Mix with Narration
                    if final_concat.audio:
                        final_audio = CompositeAudioClip([final_concat.audio, music_clip])
                    else:
                        final_audio = music_clip
                    
                    final_concat = final_concat.set_audio(final_audio)
                    
                except Exception as e:
                    log.error(f"RenderService: Failed to mix background music: {e}")
                    # Proceed without music
            # -------------------------------
            
            final_concat.write_videofile(
                output_path,
                fps=30,
                codec='libx264',
                audio_codec='aac',
                preset='fast',
                ffmpeg_params=['-pix_fmt', 'yuv420p'],
                threads=2
            )
            
            # Close all
            for c in clips:
                c.close()
            final_concat.close()
            
            return True
        except Exception as e:
            log.error(f"RenderService Concat Error: {e}")
            import traceback
            log.error(traceback.format_exc())
            return False

    def _format_seconds_to_timestamp(self, seconds: float) -> str:
        """
        Formats seconds into HH:MM:SS
        """
        td = int(seconds)
        m, s = divmod(td, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    async def _add_padding_to_audio_ffmpeg(self, input_path: str, padding: float, video_id: int, scene_idx: int) -> str:
        """
        Async wrapper for FFmpeg padding.
        """
        return await asyncio.to_thread(self._add_padding_to_audio_ffmpeg_sync, input_path, padding, video_id, scene_idx)

    def _add_padding_to_audio_ffmpeg_sync(self, input_path: str, padding: float, video_id: int, scene_idx: int) -> str:
        """
        Uses FFmpeg to add silence at start and end of audio.
        Returns path to new audio file.
        """
        if padding <= 0:
            return input_path
            
        try:
            output_filename = f"padded_audio_{video_id}_{scene_idx}.wav"
            output_path = os.path.join(self.storage_dir, "temp", output_filename)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Remove exist
            if os.path.exists(output_path):
                os.remove(output_path)
            
            # FFmpeg Command
            # Generate silence of 'padding' duration
            # Concat: Silence + Input + Silence
            
            # Filter Complex explanation:
            # 1. 'anullsrc' generates silence. -t specifies duration.
            # 2. [0:a] is the input audio.
            # 3. [silence][0:a][silence]concat=n=3:v=0:a=1 joins them.
            
            # Note: We must ensure input_path is absolute or correct.
            input_path = os.path.abspath(input_path)
            
            cmd = [
                self._ffmpeg_path, "-y",
                "-i", input_path,
                "-filter_complex", 
                f"anullsrc=channel_layout=stereo:sample_rate=44100:duration={padding}[s1];anullsrc=channel_layout=stereo:sample_rate=44100:duration={padding}[s2];[s1][0:a][s2]concat=n=3:v=0:a=1",
                "-c:a", "pcm_s16le", # Safe WAV format
                output_path
            ]
            
            log.info(f"Running FFmpeg padding: {' '.join(cmd)}")
            # Add timeout to prevent hanging on padding
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=60)
            
            if os.path.exists(output_path):
                return output_path
            return input_path
            
        except Exception as e:
            log.error(f"FFmpeg Padding Error: {e}")
            return input_path

render_service = RenderService()
