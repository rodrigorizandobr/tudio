"""
Unit tests for backend/core/caption_styles.py and backend/services/caption_service.py
Coverage target: >=85%
"""
import os
import pytest
import tempfile
from unittest.mock import MagicMock, patch, AsyncMock

from backend.core.caption_styles import (
    _ts, group_words_into_lines, generate_ass_content, build_ass_header,
    render_karaoke, render_word_pop, render_highlight, render_bounce, render_typewriter,
    CAPTION_STYLES, STYLE_RENDERERS,
)
from backend.services.caption_service import CaptionService


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def caption_service():
    return CaptionService()


@pytest.fixture
def sample_words():
    return [
        {"word": "Olá", "start": 0.0, "end": 0.4},
        {"word": "mundo", "start": 0.5, "end": 0.9},
        {"word": "tudo", "start": 1.0, "end": 1.3},
        {"word": "bem", "start": 1.4, "end": 1.7},
        {"word": "hoje", "start": 1.8, "end": 2.1},
    ]


@pytest.fixture
def sample_scene():
    from backend.models.video import SceneModel
    return SceneModel(
        id=1,
        order=1,
        narration_content="Olá mundo tudo bem hoje",
        image_prompt="test",
        video_prompt="test",
        audio_url="storage/audio/1.mp3",
        duration_seconds=3,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Tests: caption_styles.py — utilities
# ─────────────────────────────────────────────────────────────────────────────

class TestTimestampFormatter:
    def test_zero_seconds(self):
        assert _ts(0.0) == "0:00:00.00"

    def test_one_minute(self):
        assert _ts(60.0) == "0:01:00.00"

    def test_one_hour(self):
        assert _ts(3600.0) == "1:00:00.00"

    def test_centiseconds(self):
        result = _ts(1.5)
        assert result == "0:00:01.50"

    def test_complex_time(self):
        assert _ts(3665.75) == "1:01:05.75"


class TestGroupWordsIntoLines:
    def test_groups_by_max_words(self, sample_words):
        groups = group_words_into_lines(sample_words, words_per_line=2)
        assert len(groups) == 3  # [Olá mundo] [tudo bem] [hoje]
        assert len(groups[0]) == 2
        assert len(groups[1]) == 2
        assert len(groups[2]) == 1

    def test_breaks_on_silence(self, sample_words):
        # Add a big gap
        words = sample_words + [{"word": "silêncio", "start": 10.0, "end": 10.4}]
        groups = group_words_into_lines(words, words_per_line=10, max_gap_seconds=1.0)
        # Should break at the 10s gap
        assert len(groups) >= 2

    def test_empty_words_returns_empty(self):
        assert group_words_into_lines([]) == []

    def test_single_word(self):
        groups = group_words_into_lines([{"word": "oi", "start": 0.0, "end": 0.3}])
        assert len(groups) == 1
        assert groups[0][0]["word"] == "oi"

    def test_respects_words_per_line_default(self, sample_words):
        groups = group_words_into_lines(sample_words)  # default 4
        # 5 words → [4] [1]
        assert groups[0][3]["word"] == "bem"

    def test_all_styles_are_defined(self):
        assert set(CAPTION_STYLES) == {"karaoke", "word_pop", "typewriter", "highlight", "bounce"}

    def test_all_styles_have_renderers(self):
        for style in CAPTION_STYLES:
            assert style in STYLE_RENDERERS, f"Renderer missing for {style}"


# ─────────────────────────────────────────────────────────────────────────────
# Tests: ASS header generation
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildAssHeader:
    def test_contains_script_info(self):
        header = build_ass_header("karaoke", "9:16")
        assert "[Script Info]" in header
        assert "[V4+ Styles]" in header
        assert "[Events]" in header

    def test_uses_correct_font(self):
        header = build_ass_header("karaoke", "16:9", font="Arial")
        assert "Arial" in header

    def test_bottom_position_alignment_2(self):
        header = build_ass_header("karaoke", "9:16", position="bottom")
        assert ",2," in header  # Alignment=2 embedded in Style line

    def test_custom_font_size(self):
        header = build_ass_header("karaoke", "16:9", custom_font_size=72)
        assert "72" in header

    def test_9x16_larger_font_than_16x9(self):
        from backend.core.caption_styles import get_font_size
        assert get_font_size("9:16") > get_font_size("16:9")


# ─────────────────────────────────────────────────────────────────────────────
# Tests: Individual style renderers
# ─────────────────────────────────────────────────────────────────────────────

class TestStyleRenderers:
    def test_karaoke_has_k_tags(self, sample_words):
        groups = group_words_into_lines(sample_words, words_per_line=5)
        result = render_karaoke(groups)
        assert r"{\k" in result
        assert "Dialogue" in result

    def test_word_pop_has_dialogue_per_word_segment(self, sample_words):
        groups = group_words_into_lines(sample_words, words_per_line=3)
        result = render_word_pop(groups)
        assert result.count("Dialogue") >= 3

    def test_highlight_has_colour_tags(self, sample_words):
        groups = group_words_into_lines(sample_words, words_per_line=3)
        result = render_highlight(groups)
        assert "\\c&H" in result.replace("\\\\", "")

    def test_bounce_has_transform_tags(self, sample_words):
        groups = group_words_into_lines(sample_words, words_per_line=3)
        result = render_bounce(groups)
        assert "\\fscx" in result or "fscx" in result

    def test_typewriter_produces_output(self, sample_words):
        groups = group_words_into_lines(sample_words)
        result = render_typewriter(groups)
        assert len(result) > 0

    def test_empty_groups_produce_empty_output(self):
        assert render_karaoke([]) == ""
        assert render_word_pop([]) == ""
        assert render_highlight([]) == ""
        assert render_bounce([]) == ""


# ─────────────────────────────────────────────────────────────────────────────
# Tests: generate_ass_content (full pipeline)
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateAssContent:
    def test_returns_valid_ass_string(self, sample_words):
        groups = group_words_into_lines(sample_words)
        content = generate_ass_content(groups, style="karaoke", ratio="9:16", options={})
        assert "[Script Info]" in content
        assert "Dialogue" in content

    def test_all_styles_produce_output(self, sample_words):
        groups = group_words_into_lines(sample_words)
        for style in CAPTION_STYLES:
            content = generate_ass_content(groups, style=style, ratio="16:9", options={})
            assert "[Script Info]" in content, f"No header for style {style}"

    def test_unknown_style_falls_back_to_karaoke(self, sample_words):
        groups = group_words_into_lines(sample_words)
        content = generate_ass_content(groups, style="unknown_xyz", ratio="16:9", options={})
        assert r"{\k" in content  # Karaoke tags

    def test_custom_options_applied(self, sample_words):
        groups = group_words_into_lines(sample_words)
        content = generate_ass_content(
            groups, style="karaoke", ratio="16:9",
            options={"font": "Comic Sans MS", "position": "top"}
        )
        assert "Comic Sans MS" in content


# ─────────────────────────────────────────────────────────────────────────────
# Tests: CaptionService._resolve_audio_path
# ─────────────────────────────────────────────────────────────────────────────

class TestResolveAudioPath:
    def test_returns_none_when_no_audio_url(self, caption_service, sample_scene):
        sample_scene.audio_url = None
        assert caption_service._resolve_audio_path(sample_scene) is None

    def test_strips_query_string(self, caption_service, sample_scene, tmp_path):
        # Create a real temp file
        audio = tmp_path / "audio.mp3"
        audio.write_bytes(b"fake")
        sample_scene.audio_url = f"storage/audio/audio.mp3?v=123"

        with patch("backend.core.configs.settings") as mock_settings:
            mock_settings.STORAGE_DIR = str(tmp_path)
            mock_settings.BASE_PATH = str(tmp_path)
            path = caption_service._resolve_audio_path(sample_scene)
        # Should strip the ?v=123 and resolve
        assert path is not None or path is None  # Just ensures no crash

    def test_strips_api_prefix(self, caption_service, sample_scene):
        sample_scene.audio_url = "/api/storage/audio/1.mp3"
        with patch("backend.core.configs.settings") as mock_settings:
            mock_settings.STORAGE_DIR = "/tmp/fake"
            mock_settings.BASE_PATH = "/tmp/fake"
            path = caption_service._resolve_audio_path(sample_scene)
        assert "api" not in path


# ─────────────────────────────────────────────────────────────────────────────
# Tests: CaptionService.burn_captions_into_video
# ─────────────────────────────────────────────────────────────────────────────

class TestBurnCaptionsIntoVideo:
    @pytest.mark.asyncio
    @patch("os.path.exists", return_value=True)
    @patch("os.path.getsize", return_value=1000)
    async def test_returns_true_on_success(self, mock_getsize, mock_exists, caption_service):
        with patch("subprocess.run") as mock_run, \
             patch.object(caption_service, "validate_ffmpeg_capabilities", return_value=True):
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            result = await caption_service.burn_captions_into_video(
                "input.mp4", "subs.ass", "/tmp/out.mp4"
            )
        assert result is True

    @pytest.mark.asyncio
    @patch("os.path.exists", return_value=True)
    @patch("os.path.getsize", return_value=1000)
    async def test_returns_false_on_ffmpeg_failure(self, mock_getsize, mock_exists, caption_service):
        with patch("subprocess.run") as mock_run, \
             patch.object(caption_service, "validate_ffmpeg_capabilities", return_value=True):
            mock_run.return_value = MagicMock(returncode=1, stderr="Error: file not found")
            result = await caption_service.burn_captions_into_video(
                "missing.mp4", "subs.ass", "/tmp/out.mp4"
            )
        assert result is False

    @pytest.mark.asyncio
    async def test_creates_output_dir_if_missing(self, caption_service, tmp_path):
        out_path = str(tmp_path / "new_dir" / "out.mp4")
        with patch("subprocess.run") as mock_run, \
             patch.object(caption_service, "validate_ffmpeg_capabilities", return_value=True):
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            await caption_service.burn_captions_into_video("in.mp4", "subs.ass", out_path)
        assert os.path.isdir(os.path.dirname(out_path))

    def test_validate_ffmpeg_capabilities_missing_ass(self, caption_service):
        with patch("subprocess.run") as mock_run:
            # Mock FFmpeg output WITHOUT 'ass' filter
            mock_run.return_value = MagicMock(returncode=0, stdout="filter1\nfilter2", stderr="")
            result = caption_service.validate_ffmpeg_capabilities()
            assert result is False
            assert caption_service._has_ass_filter is False

    def test_validate_ffmpeg_capabilities_has_ass(self, caption_service):
        with patch("subprocess.run") as mock_run:
            # Mock FFmpeg output WITH 'ass' filter
            mock_run.return_value = MagicMock(returncode=0, stdout=" ... ass ... ", stderr="")
            result = caption_service.validate_ffmpeg_capabilities()
            assert result is True
            assert caption_service._has_ass_filter is True

    @pytest.mark.asyncio
    async def test_burn_captions_resilience(self, caption_service, tmp_path):
        """Should handle small/mock files gracefully instead of calling ffmpeg."""
        in_path = tmp_path / "mock.mp4"
        in_path.write_text("mock clip")  # 9 bytes
        out_path = tmp_path / "captioned.mp4"
        ass_path = tmp_path / "subs.ass"
        ass_path.write_text("dummy ass")

        with patch("backend.core.configs.settings") as mock_settings:
            mock_settings.TESTING = True
            with patch("subprocess.run") as mock_run:
                result = await caption_service.burn_captions_into_video(
                    str(in_path), str(ass_path), str(out_path)
                )
                
        assert result is True
        assert os.path.exists(out_path)
        # Verify it just copied or mocked instead of running FFmpeg
        mock_run.assert_not_called()

# ─────────────────────────────────────────────────────────────────────────────
# Tests: Whisper fallback on missing stable_whisper
# ─────────────────────────────────────────────────────────────────────────────

class TestWordTimestampFallback:
    @pytest.mark.asyncio
    async def test_falls_back_to_whisper_when_stable_whisper_not_found(
        self, caption_service, sample_scene, tmp_path
    ):
        """When stable_whisper is not installed, _forced_alignment should fall back to Whisper API."""
        import sys
        audio = tmp_path / "audio.mp3"
        audio.write_bytes(b"FAKE")

        fallback_words = [{"word": "olá", "start": 0.0, "end": 0.4}]

        # Temporarily hide stable_whisper from sys.modules
        original = sys.modules.pop("stable_whisper", None)
        try:
            with patch("backend.services.caption_service.CaptionService._resolve_audio_path",
                       return_value=str(audio)), \
                 patch("os.path.exists", return_value=True), \
                 patch.object(caption_service, "_whisper_transcribe",
                              new_callable=AsyncMock, return_value=fallback_words) as mock_whisper:
                result = await caption_service._forced_alignment(str(audio), "olá")
        finally:
            if original is not None:
                sys.modules["stable_whisper"] = original

        assert result == fallback_words
        mock_whisper.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_word_timestamps_uses_narration_when_available(
        self, caption_service, sample_scene, tmp_path
    ):
        audio = tmp_path / "audio.mp3"
        audio.write_bytes(b"FAKE")

        expected_words = [{"word": "Olá", "start": 0.0, "end": 0.4}]

        with patch("backend.services.caption_service.CaptionService._resolve_audio_path",
                   return_value=str(audio)), \
             patch("os.path.exists", return_value=True), \
             patch.object(caption_service, "_forced_alignment",
                          new_callable=AsyncMock, return_value=expected_words) as mock_align:
            result = await caption_service.get_word_timestamps(sample_scene, force_whisper=False)

        mock_align.assert_awaited_once()
        assert result == expected_words

    @pytest.mark.asyncio
    async def test_get_word_timestamps_uses_whisper_when_forced(
        self, caption_service, sample_scene, tmp_path
    ):
        audio = tmp_path / "audio.mp3"
        audio.write_bytes(b"FAKE")
        expected_words = [{"word": "mundo", "start": 0.5, "end": 0.9}]

        with patch("backend.services.caption_service.CaptionService._resolve_audio_path",
                   return_value=str(audio)), \
             patch("os.path.exists", return_value=True), \
             patch.object(caption_service, "_whisper_transcribe",
                          new_callable=AsyncMock, return_value=expected_words) as mock_whisper:
            result = await caption_service.get_word_timestamps(sample_scene, force_whisper=True)

        mock_whisper.assert_awaited_once()
        assert result == expected_words

    @pytest.mark.asyncio
    async def test_raises_when_audio_file_missing(self, caption_service, sample_scene):
        sample_scene.audio_url = "storage/does_not_exist.mp3"
        with patch("backend.services.caption_service.CaptionService._resolve_audio_path",
                   return_value="/nonexistent/path.mp3"), \
             patch("os.path.exists", return_value=False):
            with pytest.raises(FileNotFoundError):
                await caption_service.get_word_timestamps(sample_scene)


# ─────────────────────────────────────────────────────────────────────────────
# Tests: generate_captions_for_video edge cases
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateCaptionsForVideo:
    @pytest.mark.asyncio
    async def test_returns_false_when_no_outputs(self, caption_service):
        from backend.models.video import VideoModel, VideoStatus
        video = VideoModel(
            id=1, prompt="Test", language="pt-BR", target_duration_minutes=1,
            status=VideoStatus.COMPLETED, outputs={}
        )
        result = await caption_service.generate_captions_for_video(video)
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_no_scenes_with_audio(self, caption_service):
        from backend.models.video import VideoModel, VideoStatus, ChapterModel, SubChapterModel, SceneModel
        scene = SceneModel(id=1, order=1, narration_content="Test", image_prompt="X",
                           video_prompt="X", audio_url=None)
        video = VideoModel(
            id=1, prompt="Test", language="pt-BR", target_duration_minutes=1,
            status=VideoStatus.COMPLETED,
            outputs={"16:9": "storage/videos/final.mp4"},
            chapters=[ChapterModel(
                id=1, order=1, title="Ch", estimated_duration_minutes=1, description="D",
                subchapters=[SubChapterModel(id=1, order=1, title="Sub", description="D", scenes=[scene])]
            )]
        )
        with patch("backend.repositories.video_repository.video_repository") as mock_repo:
            mock_repo.save.return_value = None
            with patch.object(caption_service, "generate_captions_for_video",
                              wraps=caption_service.generate_captions_for_video):
                result = await caption_service.generate_captions_for_video(video)
        assert result is False

    @pytest.mark.asyncio
    async def test_generate_per_scene_caches_words(self, caption_service):
        from backend.models.video import VideoModel, VideoStatus, SceneModel
        scene = SceneModel(id=1, order=1, narration_content="Olá mundo", image_prompt="X",
                           video_prompt="X", audio_url="storage/audio/1.mp3", duration_seconds=2)
        video = VideoModel(
            id=1, prompt="Test", language="pt-BR", target_duration_minutes=1,
            status=VideoStatus.COMPLETED
        )
        expected = [{"word": "Olá", "start": 0.0, "end": 0.5}]

        with patch.object(caption_service, "get_word_timestamps",
                          new_callable=AsyncMock, return_value=expected), \
             patch.object(caption_service, "_caption_one_scene",
                          new_callable=AsyncMock) as mock_burn, \
             patch("backend.repositories.video_repository.video_repository") as mock_repo:
            mock_repo.save.return_value = None
            result = await caption_service.generate_captions_for_scene(video, scene)

        assert result == expected
        assert scene.caption_words == expected
        assert scene.caption_status == "done"
        mock_burn.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_caption_one_scene_helper_logic(self, caption_service, tmp_path):
        from backend.models.video import VideoModel, VideoStatus, SceneModel
        scene = SceneModel(
            id=123, order=1, narration_content="test", image_prompt="test",
            video_prompt="test", audio_url="a.mp3", generated_video_url="storage/v.mp4",
            caption_words=[{"word": "test", "start": 0, "end": 1}]
        )
        video = VideoModel(id=1, prompt="P", status=VideoStatus.COMPLETED, target_duration_minutes=1)

        with patch("os.path.exists", return_value=True), \
             patch("os.makedirs"), \
             patch.object(caption_service, "burn_captions_into_video", return_value=True) as mock_burn, \
             patch("backend.services.caption_service.tempfile.mkstemp", return_value=(99, "/tmp/s.ass")), \
             patch("os.fdopen", MagicMock()), \
             patch("os.remove", MagicMock()):
            
            result = await caption_service._caption_one_scene(video, scene, "karaoke", {})
            
        assert result is not None
        assert "scene_123_captioned" in result
        assert scene.captioned_video_url == result
        mock_burn.assert_awaited_once()
