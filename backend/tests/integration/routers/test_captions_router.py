"""
Integration tests for the captions API router.
Tests the full request/response cycle via TestClient + mocked services.
Coverage target: >=80%
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

# ─────────────────────────────────────────────────────────────────────────────
# App bootstrap (same pattern as other integration tests)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    """Provide a TestClient with auth bypass."""
    from backend.main import app
    from backend.api.deps import get_current_user
    from backend.models.user import UserModel

    fake_user = UserModel(
        id=1,
        email="rodrigorizando@gmail.com",
        name="Test User",
        hashed_password="x",
        is_active=True,
        role="admin",
    )
    app.dependency_overrides[get_current_user] = lambda: fake_user
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# Shared fixtures
# ─────────────────────────────────────────────────────────────────────────────

_UNSET = object()

def _make_video(caption_status="none", outputs=_UNSET, caption_words=None):
    from backend.models.video import VideoModel, VideoStatus, ChapterModel, SubChapterModel, SceneModel
    scene = SceneModel(
        id=1, order=1, narration_content="Olá mundo test",
        image_prompt="test", video_prompt="test",
        audio_url="storage/audio/1.mp3", duration_seconds=3,
        caption_words=caption_words or [],
        caption_status="done" if caption_words else "none",
    )
    resolved_outputs = {"16:9": "storage/videos/42/final.mp4"} if outputs is _UNSET else outputs
    return VideoModel(
        id=42,
        prompt="Test video",
        language="pt-BR",
        target_duration_minutes=1,
        status=VideoStatus.COMPLETED,
        caption_status=caption_status,
        caption_style="karaoke",
        caption_options={},
        captioned_outputs={},
        outputs=resolved_outputs,
        chapters=[ChapterModel(
            id=1, order=1, title="Ch1", estimated_duration_minutes=1, description="Desc",
            subchapters=[SubChapterModel(id=1, order=1, title="Sub", description="D", scenes=[scene])]
        )],
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/captions/styles
# ─────────────────────────────────────────────────────────────────────────────

class TestListStyles:
    def test_returns_5_styles(self, client):
        resp = client.get("/api/v1/captions/styles")
        assert resp.status_code == 200
        data = resp.json()
        assert "styles" in data
        assert len(data["styles"]) == 5

    def test_style_ids_are_valid(self, client):
        resp = client.get("/api/v1/captions/styles")
        ids = [s["id"] for s in resp.json()["styles"]]
        assert set(ids) == {"karaoke", "word_pop", "typewriter", "highlight", "bounce"}

    def test_each_style_has_label_and_desc(self, client):
        resp = client.get("/api/v1/captions/styles")
        for style in resp.json()["styles"]:
            assert "label" in style
            assert "desc" in style


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/videos/{video_id}/captions/status
# ─────────────────────────────────────────────────────────────────────────────

class TestCaptionStatus:
    def test_returns_status_for_existing_video(self, client):
        video = _make_video(caption_status="done")
        with patch("backend.api.v1.routers.captions.video_service") as mock_svc:
            mock_svc.get.return_value = video
            resp = client.get("/api/v1/videos/42/captions/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["caption_status"] == "done"
        assert "captioned_outputs" in data

    def test_returns_404_for_unknown_video(self, client):
        with patch("backend.api.v1.routers.captions.video_service") as mock_svc:
            mock_svc.get.return_value = None
            resp = client.get("/api/v1/videos/9999/captions/status")
        assert resp.status_code == 404

    def test_processing_status_is_returned(self, client):
        video = _make_video(caption_status="processing")
        with patch("backend.api.v1.routers.captions.video_service") as mock_svc:
            mock_svc.get.return_value = video
            resp = client.get("/api/v1/videos/42/captions/status")
        assert resp.json()["caption_status"] == "processing"


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/videos/{video_id}/captions/preview
# ─────────────────────────────────────────────────────────────────────────────

class TestCaptionPreview:
    def test_returns_scene_words(self, client):
        words = [{"word": "Olá", "start": 0.0, "end": 0.5}]
        video = _make_video(caption_words=words)
        with patch("backend.api.v1.routers.captions.video_service") as mock_svc:
            mock_svc.get.return_value = video
            resp = client.get("/api/v1/videos/42/captions/preview")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["scenes"]) == 1
        assert data["scenes"][0]["words"][0]["word"] == "Olá"

    def test_returns_empty_list_when_no_words(self, client):
        video = _make_video(caption_words=[])
        with patch("backend.api.v1.routers.captions.video_service") as mock_svc:
            mock_svc.get.return_value = video
            resp = client.get("/api/v1/videos/42/captions/preview")
        assert resp.json()["scenes"] == []

    def test_returns_404_for_unknown_video(self, client):
        with patch("backend.api.v1.routers.captions.video_service") as mock_svc:
            mock_svc.get.return_value = None
            resp = client.get("/api/v1/videos/9999/captions/preview")
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /api/v1/videos/{video_id}/captions/style
# ─────────────────────────────────────────────────────────────────────────────

class TestUpdateCaptionStyle:
    def test_updates_style_successfully(self, client):
        video = _make_video()
        with patch("backend.api.v1.routers.captions.video_service") as mock_svc:
            mock_svc.get.return_value = video
            mock_svc.save.return_value = video
            resp = client.patch("/api/v1/videos/42/captions/style", json={
                "style": "bounce",
                "options": {"position": "top"}
            })
        assert resp.status_code == 200
        assert resp.json()["style"] == "bounce"

    def test_rejects_invalid_style(self, client):
        video = _make_video()
        with patch("backend.api.v1.routers.captions.video_service") as mock_svc:
            mock_svc.get.return_value = video
            resp = client.patch("/api/v1/videos/42/captions/style", json={"style": "neon_glow"})
        assert resp.status_code == 400

    def test_returns_404_for_unknown_video(self, client):
        with patch("backend.api.v1.routers.captions.video_service") as mock_svc:
            mock_svc.get.return_value = None
            resp = client.patch("/api/v1/videos/42/captions/style", json={"style": "karaoke"})
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/videos/{video_id}/captions/generate
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateCaptions:
    def test_generates_for_video_scope(self, client):
        video = _make_video()
        with patch("backend.api.v1.routers.captions.video_service") as mock_svc, \
             patch("backend.api.v1.routers.captions.asyncio.create_task"):
            mock_svc.get.return_value = video
            mock_svc.save.return_value = None
            resp = client.post("/api/v1/videos/42/captions/generate", json={
                "style": "karaoke",
                "scope": "video",
                "force_whisper": False,
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "processing"
        assert data["scope"] == "video"

    def test_rejects_invalid_style(self, client):
        video = _make_video()
        with patch("backend.api.v1.routers.captions.video_service") as mock_svc:
            mock_svc.get.return_value = video
            resp = client.post("/api/v1/videos/42/captions/generate", json={
                "style": "bad_style",
                "scope": "video",
            })
        assert resp.status_code == 400

    def test_returns_409_when_already_processing(self, client):
        video = _make_video(caption_status="processing")
        with patch("backend.api.v1.routers.captions.video_service") as mock_svc:
            mock_svc.get.return_value = video
            resp = client.post("/api/v1/videos/42/captions/generate", json={
                "style": "karaoke",
                "scope": "video",
            })
        assert resp.status_code == 409

    def test_returns_422_when_no_outputs(self, client):
        with patch("backend.api.v1.routers.captions.video_service") as mock_svc, \
             patch("backend.api.v1.routers.captions.asyncio.create_task"):
            mock_svc.get.side_effect = lambda *a, **k: _make_video(outputs={})
            mock_svc.save.return_value = None
            resp = client.post("/api/v1/videos/42/captions/generate", json={
                "style": "karaoke",
                "scope": "video",
                "force_whisper": False,
                "options": {},
            })
        assert resp.status_code == 422, (
            f"Expected 422 for empty outputs, got {resp.status_code}: {resp.text}"
        )


    def test_returns_404_for_unknown_video(self, client):
        with patch("backend.api.v1.routers.captions.video_service") as mock_svc:
            mock_svc.get.return_value = None
            resp = client.post("/api/v1/videos/9999/captions/generate", json={"style": "karaoke"})
        assert resp.status_code == 404

    def test_scene_scope_returns_scene_id(self, client):
        video = _make_video()
        with patch("backend.api.v1.routers.captions.video_service") as mock_svc, \
             patch("backend.api.v1.routers.captions.asyncio.create_task"):
            mock_svc.get.return_value = video
            mock_svc.save.return_value = None
            resp = client.post("/api/v1/videos/42/captions/generate", json={
                "style": "karaoke",
                "scope": "scene",
                "scene_id": 1,
            })
        assert resp.status_code == 200
        assert resp.json()["scene_id"] == 1

    def test_scene_scope_without_scene_id_returns_400(self, client):
        video = _make_video()
        with patch("backend.api.v1.routers.captions.video_service") as mock_svc:
            mock_svc.get.return_value = video
            resp = client.post("/api/v1/videos/42/captions/generate", json={
                "style": "karaoke",
                "scope": "scene",
                # scene_id missing
            })
        assert resp.status_code == 400

    def test_scene_scope_with_unknown_scene_returns_404(self, client):
        video = _make_video()
        with patch("backend.api.v1.routers.captions.video_service") as mock_svc:
            mock_svc.get.return_value = video
            resp = client.post("/api/v1/videos/42/captions/generate", json={
                "style": "karaoke",
                "scope": "scene",
                "scene_id": 999,  # does not exist
            })
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/videos/{video_id}/scenes/{scene_id}/captions/generate
# ─────────────────────────────────────────────────────────────────────────────

class TestSceneCaptionGenerate:
    def test_generates_scene_captions_successfully(self, client):
        words = [{"word": "Olá", "start": 0.0, "end": 0.5}]
        video = _make_video()

        with patch("backend.api.v1.routers.captions.video_service") as mock_svc, \
             patch("backend.api.v1.routers.captions.caption_service") as mock_cap:
            mock_svc.get.return_value = video
            mock_svc.save.return_value = None
            mock_cap.generate_captions_for_scene = AsyncMock(return_value=words)

            resp = client.post("/api/v1/videos/42/scenes/1/captions/generate")

        assert resp.status_code == 202
        data = resp.json()
        assert data["caption_status"] == "processing"
        assert "scene_id" in data

    def test_returns_422_when_scene_has_no_audio(self, client):
        video = _make_video()
        video.chapters[0].subchapters[0].scenes[0].audio_url = None

        with patch("backend.api.v1.routers.captions.video_service") as mock_svc:
            mock_svc.get.return_value = video
            resp = client.post("/api/v1/videos/42/scenes/1/captions/generate")

        assert resp.status_code == 422

    def test_returns_404_for_unknown_scene(self, client):
        video = _make_video()
        with patch("backend.api.v1.routers.captions.video_service") as mock_svc:
            mock_svc.get.return_value = video
            resp = client.post("/api/v1/videos/42/scenes/9999/captions/generate")
        assert resp.status_code == 404

    def test_returns_500_on_service_error_initial_checks(self, client):
        # Since actual logic is in background, 500 can only happen in start-up checks
        # But we mock video_service.get to fail
        with patch("backend.api.v1.routers.captions.video_service") as mock_svc:
            mock_svc.get.side_effect = Exception("Datastore down")
            resp = client.post("/api/v1/videos/42/scenes/1/captions/generate")
        assert resp.status_code == 500
