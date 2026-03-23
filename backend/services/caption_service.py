"""
caption_service.py — Orchestrates generation of animated word-by-word captions.

Flow:
1. get_word_timestamps(scene) — smart: forced-alignment if narration exists, else Whisper
2. generate_ass_for_scene(scene, ratio, style, options) — generates .ass file
3. burn_captions_into_video(video_path, ass_path, output_path) — ffmpeg burn-in
4. generate_captions_for_video(video) — full pipeline for all formats
"""
import os
import asyncio
import tempfile
import json
from datetime import datetime
from typing import Optional
from pathlib import Path

from backend.core.logger import log
from backend.core.configs import settings
from backend.core.caption_styles import (
    generate_ass_content,
    group_words_into_lines,
    CAPTION_STYLES,
)
from backend.models.video import VideoModel, SceneModel
from backend.repositories.video_repository import video_repository
from backend.services.video_service import video_service
from backend.core.progress import update_video_progress


class CaptionService:
    def __init__(self):
        # Ensure common binary paths are in PATH (for tools calling ffmpeg directly)
        homebrew_bin = "/opt/homebrew/bin"
        if os.path.exists(homebrew_bin) and homebrew_bin not in os.environ["PATH"]:
            os.environ["PATH"] = f"{homebrew_bin}:{os.environ['PATH']}"
            log.info(f"CaptionService: Added {homebrew_bin} to PATH")

        self._ffmpeg_path = None
        self._has_ass_filter = None
        self.fallback_fonts = [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "Arial"
        ]

    @property
    def ffmpeg_path(self) -> str:
        """Find and memoize the ffmpeg path."""
        if self._ffmpeg_path:
            return self._ffmpeg_path
            
        self._ffmpeg_path = "ffmpeg"
        for common_path in ("/usr/local/bin/ffmpeg", "/opt/homebrew/bin/ffmpeg", "/usr/bin/ffmpeg"):
            if os.path.exists(common_path):
                self._ffmpeg_path = common_path
                break
        return self._ffmpeg_path

    def validate_ffmpeg_capabilities(self) -> bool:
        """
        Check if the installed FFmpeg supports required filters (ass).
        Returns True if all good, False otherwise.
        """
        if self._has_ass_filter is not None:
            return self._has_ass_filter

        import subprocess
        try:
            path = self.ffmpeg_path
            result = subprocess.run([path, "-filters"], capture_output=True, text=True, timeout=5)
            self._has_ass_filter = " ass " in result.stdout
            
            if not self._has_ass_filter:
                log.critical(
                    "\n" + "="*60 + "\n"
                    "FATAL: FFmpeg is missing 'ass' filter (libass support).\n"
                    "Captions will fail to generate.\n"
                    "\n"
                    "FIX (macOS):\n"
                    "brew uninstall ffmpeg\n"
                    "brew tap homebrew-ffmpeg/ffmpeg\n"
                    "brew install homebrew-ffmpeg/ffmpeg/ffmpeg --with-libass --with-freetype --with-fontconfig\n"
                    + "="*60 + "\n"
                )
            return self._has_ass_filter
        except Exception as e:
            log.error(f"Failed to validate FFmpeg capabilities: {e}")
            self._has_ass_filter = False
            return False


    # ─── Step 1: Get word-level timestamps ───────────────────────────────────

    async def get_word_timestamps(
        self,
        scene: SceneModel,
        force_whisper: bool = False,
    ) -> list[dict]:
        """
        Returns [{word, start, end}, ...] for the scene audio.
        Strategy:
          - If scene has narration_content and NOT force_whisper → forced alignment via stable-ts
          - Otherwise → OpenAI Whisper API (word-level timestamps)
        """
        # --- MOCK FOR TESTING ---
        from backend.core.configs import settings
        if settings.TESTING and os.getenv("USE_E2E_MOCKS") == "True":
            log.warning(f"CaptionService: E2E Mocking timestamps for scene {scene.id}")
            # Generate dummy words based on narration_content or duration
            text = scene.narration_content or "Mock caption text for testing purposes"
            words = text.split()
            scene_duration = scene.duration_seconds or 5.0
            word_duration = scene_duration / max(len(words), 1)
            
            return [
                {
                    "word": word,
                    "start": round(i * word_duration, 3),
                    "end": round((i + 1) * word_duration, 3)
                }
                for i, word in enumerate(words)
            ]
        # ------------------------

        audio_path = self._resolve_audio_path(scene)
        if not audio_path or not os.path.exists(audio_path):
            raise FileNotFoundError(
                f"Audio file not found for scene {scene.id}: {scene.audio_url}"
            )

        if scene.narration_content and not force_whisper:
            return await self._forced_alignment(audio_path, scene.narration_content)
        else:
            return await self._whisper_transcribe(audio_path)

    async def _forced_alignment(self, audio_path: str, text: str) -> list[dict]:
        """
        Uses stable-ts to align known text to audio, getting precise word timestamps.
        Much faster than full transcription and free (no API cost).
        """
        try:
            import stable_whisper  # type: ignore
            log.info(f"CaptionService: Running forced alignment on {audio_path}")

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._run_stable_alignment(audio_path, text)
            )
            return result
        except ImportError:
            log.warning("stable-whisper not installed, falling back to Whisper API")
            return await self._whisper_transcribe(audio_path)
        except Exception as e:
            log.warning(f"Forced alignment failed ({e}), falling back to Whisper API")
            return await self._whisper_transcribe(audio_path)

    def _run_stable_alignment(self, audio_path: str, text: str) -> list[dict]:
        """Synchronous stable-ts forced alignment (runs in executor)."""
        import stable_whisper  # type: ignore
        model = stable_whisper.load_model("base")
        result = model.align(audio_path, text, language="pt")
        words = []
        for seg in result.segments:
            for w in seg.words:
                word_text = w.word.strip()
                if word_text:
                    words.append({
                        "word": word_text,
                        "start": round(w.start, 3),
                        "end": round(w.end, 3),
                    })
        return words

    async def _whisper_transcribe(self, audio_path: str) -> list[dict]:
        """
        OpenAI Whisper API with word-level timestamps.
        Uses existing OpenAI client from settings.
        """
        from openai import AsyncOpenAI
        log.info(f"CaptionService: Whisper transcription on {audio_path}")
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        with open(audio_path, "rb") as audio_file:
            response = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["word"],
            )

        words = []
        for w in (response.words or []):
            word_text = w.word.strip()
            if word_text:
                words.append({
                    "word": word_text,
                    "start": round(w.start, 3),
                    "end": round(w.end, 3),
                })
        log.info(f"CaptionService: Whisper returned {len(words)} words")
        return words

    # ─── Step 2: Generate ASS file for a scene ───────────────────────────────

    async def generate_ass_for_scene(
        self,
        scene: SceneModel,
        ratio: str,
        style: str,
        options: dict,
        force_whisper: bool = False,
    ) -> tuple[list[dict], str]:
        """
        Returns (word_list, ass_file_path).
        Writes the ASS file to a temp location.
        """
        words = await self.get_word_timestamps(scene, force_whisper=force_whisper)

        words_per_line = options.get("words_per_line", 4)
        groups = group_words_into_lines(words, words_per_line=words_per_line)

        ass_content = generate_ass_content(groups, style=style, ratio=ratio, options=options)

        # Write to temp file
        fd, ass_path = tempfile.mkstemp(suffix=".ass")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(ass_content)

        log.info(f"CaptionService: ASS written to {ass_path} ({len(words)} words)")
        return words, ass_path

    # ─── Step 3: Burn captions into a video file ─────────────────────────────

    async def burn_captions_into_video(
        self,
        video_path: str,
        ass_path: str,
        output_path: str,
    ) -> bool:
        """
        Uses FFmpeg to burn ASS subtitles into video.
        Output: H.264 with subtitles burned (hard-coded, not soft subs).
        """
        import subprocess

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # --- IMMEDIATE MOCK FOR TESTING ---
        from backend.core.configs import settings
        if settings.TESTING and os.getenv("USE_E2E_MOCKS") == "True":
            log.warning("CaptionService: Mocking burn_captions_into_video (Immediate Success)")
            if not os.path.exists(output_path):
                with open(output_path, 'wb') as f:
                    f.write(b'dummy captioned video')
            return True
        # -----------------------------------
        
        # --- RESILIENCE: Check if input video is valid ---
        if not os.path.exists(video_path):
            log.error(f"CaptionService: Input video {video_path} not found.")
            return False
            
        file_size = os.path.getsize(video_path)
        if file_size < 100:  # Valid MP4 header + moov atom usually > 100 bytes
            log.warning(f"CaptionService: Input video {video_path} is too small ({file_size}b). Suspecting mock/corrupt.")
            # If it's a mock, just copy it to output instead of letting ffmpeg fail
            if settings.TESTING or os.getenv("USE_E2E_MOCKS") == "True":
                import shutil
                shutil.copy(video_path, output_path)
                return True
            return False
        # -------------------------------------------------

        # Use memoized path and validate
        ffmpeg_path = self.ffmpeg_path
        if not self.validate_ffmpeg_capabilities():
            log.error("CaptionService: FFmpeg missing 'ass' filter. Skipping burn.")
            return False

        # Escape the ass path for ffmpeg filter
        # On macOS/Unix, colons must be escaped as '\:' for the filter parser.
        # We use double backslashes in the python string to send a single backslash to the shell.
        escaped_ass_path = ass_path.replace("'", "'\\\\''").replace(":", "\\\\:")
        
        cmd = [
            ffmpeg_path, "-y",
            "-i", video_path,
            "-vf", f"ass=f='{escaped_ass_path}'",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "20",
            "-c:a", "copy",
            output_path
        ]

        log.info(f"CaptionService: Burning captions (async): {' '.join(cmd)}")
        
        from backend.core.configs import settings
        
        def run_ffmpeg():
            try:
                # Capture both stdout and stderr for better debugging
                result = subprocess.run(cmd, capture_output=True, text=True)
                return result
            except Exception as e:
                log.error(f"FFmpeg caption burn exception: {e}")
                return None

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, run_ffmpeg)
        
        success = (result and result.returncode == 0)
        if result and not success:
            log.error(f"FFmpeg caption burn FAILED with return code {result.returncode}")
            log.error(f"FFmpeg STDERR: {result.stderr}")
            log.error(f"FFmpeg STDOUT: {result.stdout}")
        elif result and success:
            if os.path.exists(output_path):
                size = os.path.getsize(output_path)
                log.info(f"FFmpeg caption burn SUCCESS: {output_path} ({size} bytes)")
            else:
                log.error(f"FFmpeg reported success but output file is missing at {output_path}")
                success = False

        # --- FALLBACK FOR TESTING ---
        if not success and settings.TESTING and os.getenv("USE_E2E_MOCKS") == "True":
            log.warning("CaptionService: Burn failed in E2E TESTING mode. Mocking output file.")
            # If input video is dummy, just copy it or touch it
            import shutil
            if os.path.exists(video_path):
                shutil.copy(video_path, output_path)
            else:
                with open(output_path, 'wb') as f:
                    f.write(b'dummy captioned video')
            return True

        return success

    # ─── Step 4: Full pipeline for a video ───────────────────────────────────

    async def generate_captions_for_video(
        self,
        video: VideoModel,
        style: Optional[str] = None,
        options: Optional[dict] = None,
        force_whisper: bool = False,
    ) -> bool:
        """
        Updates video.captioned_outputs and video.caption_status in the DB.
        """
        if video.deleted_at:
            log.warning(f"CaptionService: Video {video.id} is deleted. Skipping global captions.")
            return False
        if not video.outputs:
            log.warning(f"Video {video.id}: No rendered outputs yet, cannot generate captions.")
            return False

        effective_style = style or video.caption_style or "karaoke"
        effective_options = options or video.caption_options or {}

        log.info(f"Video {video.id}: Generating captions (style={effective_style})")

        video.caption_status = "processing"
        video.caption_progress = 0.0
        await video_service._save_video_merged(video.id, video)

        # Collect all scenes in order
        all_scenes: list[SceneModel] = []
        for chapter in video.chapters:
            for sub in chapter.subchapters:
                for scene in sub.scenes:
                    if not scene.deleted and scene.audio_url:
                        all_scenes.append(scene)

        total_steps = len(all_scenes) + (len(video.outputs) if video.outputs else 0)
        current_step = 0

        # Sprint 250: Also burn individual scene previews for dashboard FOR ALL RATIOS
        # This ensures we have captioned clips ready for both horizontal and vertical assembly
        target_ratios = list(video.outputs.keys()) if video.outputs else ["16:9"]
        if "aspect_ratios" in video.model_dump() and video.aspect_ratios:
             target_ratios = video.aspect_ratios

        for idx, scene in enumerate(all_scenes):
            # Check for cancellation
            if idx % 3 == 0: # Periodically refresh and check
                latest_state = await video_repository.get(video.id)
                if latest_state and latest_state.status == "cancelled":
                    log.warning(f"Video {video.id}: Captioning cancelled during scene burn-in.")
                    return False

            for ratio in target_ratios:
                try:
                    await self._caption_one_scene(
                        video, scene, ratio, effective_style, effective_options, force_whisper
                    )
                except Exception as e:
                    log.warning(f"Failed to burn scene {scene.id} ({ratio}) captions: {e}")
            
            # Update progress based on scenes processed
            current_step += 1
            video.caption_progress = round((current_step / total_steps) * 100, 1)
            await video_service._save_video_merged(video.id, video)

        total_scenes = len(all_scenes)
        if total_scenes == 0:
            log.warning(f"Video {video.id}: No scenes with audio found.")
            video.caption_status = "error"
            await video_service._save_video_merged(video.id, video)
            return False

        captioned_outputs = {}

        for ratio, video_url in video.outputs.items():
            # Check for cancellation
            latest_state = await video_repository.get(video.id)
            if latest_state and latest_state.status == "cancelled":
                log.warning(f"Video {video.id}: Captioning cancelled during format burn-in.")
                return False

            log.info(f"Video {video.id}: Processing format {ratio}...")
            try:
                captioned_url = await self._caption_one_format(
                    video=video,
                    ratio=ratio,
                    video_url=video_url,
                    all_scenes=all_scenes,
                    style=effective_style,
                    options=effective_options,
                    force_whisper=force_whisper,
                )
                if captioned_url:
                    ts = int(datetime.now().timestamp())
                    captioned_outputs[ratio] = f"{captioned_url}?t={ts}" if "?" not in captioned_url else f"{captioned_url}&t={ts}"
                
                current_step += 1
                video.caption_progress = min(99.0, round((current_step / total_steps) * 100, 1))
                await video_service._save_video_merged(video.id, video)
            except Exception as e:
                log.error(f"Video {video.id} format {ratio} caption error: {e}")
                try:
                    video.caption_status = "error"
                    await video_service._save_video_merged(video.id, video)
                except Exception:
                    pass

        if captioned_outputs:
            video.captioned_outputs = captioned_outputs
            video.caption_status = "done"
            video.caption_progress = 100.0
            video.caption_style = effective_style
            video.caption_options = effective_options
        else:
            video.caption_status = "error"

        await video_service._save_video_merged(video.id, video)
        log.info(f"Video {video.id}: Caption generation done. Outputs: {captioned_outputs}")
        return bool(captioned_outputs)

    async def _caption_one_format(
        self,
        video: VideoModel,
        ratio: str,
        video_url: str,
        all_scenes: list[SceneModel],
        style: str,
        options: dict,
        force_whisper: bool,
    ) -> Optional[str]:
        """Generate captioned video for ONE ratio/format."""

        # Resolve source video path
        video_path = self._resolve_video_path(video_url)
        if not video_path or not os.path.exists(video_path):
            log.error(f"Video path not found: {video_path}")
            return None

        # Build a "mega" transcript by concatenating scene words with time offsets
        # We need to know when each scene starts in the final video.
        # We use scene.duration_seconds as cumulative offset.
        all_words: list[dict] = []
        time_offset = 0.0

        for idx, scene in enumerate(all_scenes):
            try:
                # Always re-generate timestamps to ensure they match current audio/text
                # if scene.caption_words and not force_whisper:
                #     words = scene.caption_words
                # else:
                words = await self.get_word_timestamps(scene, force_whisper=force_whisper)
                # Cache words on scene
                scene.caption_words = words
                scene.caption_status = "done"

                # Offset words by cumulative time
                for w in words:
                    all_words.append({
                        "word": w["word"],
                        "start": round(w["start"] + time_offset, 3),
                        "end": round(w["end"] + time_offset, 3),
                    })

                # Advance offset by scene duration (plus padding)
                padding = getattr(video, "audio_transition_padding", 0.5)
                time_offset += (scene.duration_seconds or max(w["end"] for w in words)) + padding
                
            except Exception as e:
                log.warning(f"Scene {scene.id} caption failed, skipping: {e}")
                time_offset += scene.duration_seconds or 3.0

        if not all_words:
            log.error(f"No words extracted for ratio {ratio}")
            return None

        # Save scene caches to DB
        try:
            await video_service._save_video_merged(video.id, video)
        except Exception:
            pass

        # Group words into display lines
        words_per_line = options.get("words_per_line", 4)
        groups = group_words_into_lines(all_words, words_per_line=words_per_line)

        # Generate ASS file
        ass_content = generate_ass_content(groups, style=style, ratio=ratio, options=options)
        fd, ass_path = tempfile.mkstemp(suffix=f"_{ratio.replace(':', '_')}.ass")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(ass_content)

        # Output path
        ratio_slug = ratio.replace(":", "_")
        output_dir = os.path.join(settings.STORAGE_DIR, "videos", str(video.id), "captions")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"captioned_{ratio_slug}.mp4")
        output_url = f"storage/videos/{video.id}/captions/captioned_{ratio_slug}.mp4"

        # Burn captions
        success = await self.burn_captions_into_video(video_path, ass_path, output_path)

        # Cleanup ASS temp
        try:
            os.remove(ass_path)
        except Exception:
            pass

        return output_url if success else None

    async def _caption_one_scene(
        self,
        video: VideoModel,
        scene: SceneModel,
        ratio: str,
        style: str,
        options: dict,
        force_whisper: bool = False,
    ) -> Optional[str]:
        """
        Generates a captioned version of the individual scene video.
        Used for dashboard previews.
        """
        # Sprint 250: Use plural generated_video_urls if available for this ratio
        input_url = None
        if scene.generated_video_urls and ratio in scene.generated_video_urls:
            input_url = scene.generated_video_urls[ratio]
        # REMOVED: Fallback to singular generated_video_url to prevent ratio mixing

        if not input_url:
            return None

        # 1. Get words (current scene only)
        # Always re-generate timestamps to ensure they match current audio/text
        # if scene.caption_words and not force_whisper:
        #     words = scene.caption_words
        # else:
        words = await self.get_word_timestamps(scene, force_whisper=force_whisper)
        scene.caption_words = words
        scene.caption_status = "done"

        if not words:
            return None

        # 2. Resolve scene video path
        video_path = self._resolve_video_path(input_url)
        if not video_path or not os.path.exists(video_path):
            log.warning(f"Scene {scene.id} video path not found: {video_path}")
            return None

        # 3. Generate ASS for this specific scene
        words_per_line = options.get("words_per_line", 4)
        groups = group_words_into_lines(words, words_per_line=words_per_line)
        
        # Sprint 250: Use the actual target ratio for font/style scaling
        ass_content = generate_ass_content(groups, style=style, ratio=ratio, options=options)
        
        fd, ass_path = tempfile.mkstemp(suffix=f"_scene_{scene.id}_{ratio.replace(':', '_')}.ass")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(ass_content)

        # 4. Output path - UNIQUE NAMING PER FORMAT
        # Find the scene's "address" (chapter_order, sub_order, scene_order) for unique filename
        addr = "unknown"
        current_ratio = ratio
        
        for c in video.chapters:
            for s in c.subchapters:
                if scene in s.scenes:
                    addr = f"{c.order}-{s.order}-{scene.order}"
                    break
        
        # Organize by format (horizontal / vertical) to avoid overwrites between ratios
        format_name = "horizontal" if current_ratio == "16:9" else "vertical"
        output_dir = os.path.join(settings.STORAGE_DIR, "videos", str(video.id), "captions", format_name)
        os.makedirs(output_dir, exist_ok=True)
        
        # Unique filename prevents overwrites between different subchapters
        filename = f"scene_{addr}_captioned.mp4"
        output_path = os.path.join(output_dir, filename)
        output_url = f"storage/videos/{video.id}/captions/{format_name}/{filename}"

        # 5. Burn captions
        success = await self.burn_captions_into_video(video_path, ass_path, output_path)

        # Cleanup
        try:
            os.remove(ass_path)
        except Exception:
            pass

        if success:
            ts = int(datetime.now().timestamp())
            final_url = f"{output_url}?t={ts}" if "?" not in output_url else f"{output_url}&t={ts}"
            
            # Update both legacy and new multi-ratio dictionary
            # REMOVED: Legacy fallback to singular captioned_video_url
            if not hasattr(scene, 'captioned_video_urls') or scene.captioned_video_urls is None:
                scene.captioned_video_urls = {}
            scene.captioned_video_urls[current_ratio] = final_url
            
            return final_url
        return None

    # ─── Single scene caption generation ─────────────────────────────────────

    async def generate_captions_for_scene(
        self,
        video: VideoModel,
        scene: SceneModel,
        force_whisper: bool = False,
    ) -> list[dict]:
        """
        Generates word timestamps AND burns captions into the scene video 
        for dashboard preview.
        """
        if video.deleted_at:
            log.warning(f"CaptionService: Video {video.id} is deleted. Skipping scene captions.")
            return []
            
        # 1. Get/Cache words
        words = await self.get_word_timestamps(scene, force_whisper=force_whisper)
        scene.caption_words = words
        # Do not set "done" yet, wait for burn-in to complete

        # 2. Burn into scene video for preview
        style = video.caption_style or "karaoke"
        options = video.caption_options or {}
        
        # For single scene trigger, we process whatever ratios are available/requested
        target_ratios = video.aspect_ratios or ["16:9"]
        output_url = None
        for ratio in target_ratios:
             output_url = await self._caption_one_scene(video, scene, ratio, style, options, force_whisper=force_whisper)

        if output_url:
            scene.caption_status = "done"
            log.info(f"Scene {scene.id} captioning COMPLETED with burned-in video.")
        else:
            scene.caption_status = "error"
            log.warning(f"Scene {scene.id} caption burn-in failed or returned no URL.")

        await video_service._save_video_merged(video.id, video)
        return words

    # ─── Helpers ─────────────────────────────────────────────────────────────

    def _resolve_audio_path(self, scene: SceneModel) -> Optional[str]:
        """Convert scene.audio_url (relative API path) to filesystem path."""
        if not scene.audio_url:
            return None

        rel = scene.audio_url
        # Strip query strings (cache busters)
        if "?" in rel:
            rel = rel.split("?")[0]
        # Strip /api/ prefix
        for prefix in ("/api/storage/", "/api/", "/storage/"):
            if rel.startswith(prefix):
                rel = rel[len(prefix):]
                break
        rel = rel.lstrip("/")

        # Try STORAGE_DIR first, then BASE_PATH
        for base in (settings.STORAGE_DIR, settings.BASE_PATH):
            full = os.path.join(base, rel)
            if os.path.exists(full):
                return full

        return os.path.join(settings.STORAGE_DIR, rel)

    def _resolve_video_path(self, video_url: str) -> Optional[str]:
        """
        Convert video output URL to filesystem path.
        Handles cases like:
          - /api/storage/videos/123/final.mp4
          - storage/videos/123/final.mp4
          - videos/123/final.mp4 (relative to storage)
        """
        if not video_url:
            return None
            
        rel = video_url
        if "?" in rel:
            rel = rel.split("?")[0]
            
        # Strip common prefixes to get the "inner" storage path
        for prefix in ("/api/storage/", "/api/", "/storage/"):
            if rel.startswith(prefix):
                rel = rel[len(prefix):]
                break
        
        # If it still starts with storage/ (after maybe stripping /api/), strip it too
        if rel.startswith("storage/"):
            rel = rel[len("storage/"):]
            
        rel = rel.lstrip("/")

        # Search candidates in order of priority
        candidates = [
            os.path.join(settings.STORAGE_DIR, rel),
            os.path.join(settings.BASE_PATH, rel),
            os.path.join(settings.BASE_PATH, "storage", rel),
        ]
        
        for full in candidates:
            if os.path.exists(full):
                return full

        # Fallback to storage dir if not found (for creation)
        return os.path.join(settings.STORAGE_DIR, rel)


caption_service = CaptionService()
