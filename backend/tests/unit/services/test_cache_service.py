"""
Unit tests for backend/services/cache_service.py
API: Datastore-backed SearchCacheService (no SQLite, no settings dependency)
"""
import pytest
from unittest.mock import MagicMock, patch


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_repo():
    return MagicMock()


@pytest.fixture
def service(mock_repo):
    from backend.services.cache_service import SearchCacheService
    with patch("backend.services.cache_service.search_cache_repository", mock_repo):
        yield SearchCacheService()


# ─── _get_key ─────────────────────────────────────────────────────────────────

class TestGetKey:
    def test_combines_provider_and_query(self, service):
        assert service._get_key("unsplash", "Mountains") == "unsplash:mountains"

    def test_lowercases_query(self, service):
        assert service._get_key("pexels", "CATS") == "pexels:cats"

    def test_strips_whitespace(self, service):
        assert service._get_key("unsplash", "  Mountains  ") == "unsplash:mountains"

    def test_different_providers_produce_different_keys(self, service):
        k1 = service._get_key("unsplash", "nature")
        k2 = service._get_key("pexels", "nature")
        assert k1 != k2


# ─── get ──────────────────────────────────────────────────────────────────────

class TestCacheGet:
    def test_returns_data_on_hit(self, service, mock_repo):
        cached = MagicMock()
        cached.data = [{"url": "https://img.example.com/1.jpg"}]
        mock_repo.get.return_value = cached

        result = service.get("unsplash", "mountains")

        assert result == [{"url": "https://img.example.com/1.jpg"}]
        mock_repo.get.assert_called_once_with("unsplash:mountains")

    def test_returns_none_on_miss(self, service, mock_repo):
        mock_repo.get.return_value = None

        result = service.get("unsplash", "missing-query")

        assert result is None

    def test_returns_none_on_repository_error(self, service, mock_repo):
        mock_repo.get.side_effect = Exception("Datastore unavailable")

        result = service.get("unsplash", "mountains")

        assert result is None  # error swallowed, does not raise

    def test_key_normalization_applied(self, service, mock_repo):
        mock_repo.get.return_value = None
        service.get("unsplash", "  MOUNTAINS  ")
        mock_repo.get.assert_called_once_with("unsplash:mountains")


# ─── set ──────────────────────────────────────────────────────────────────────

class TestCacheSet:
    def test_saves_to_repository(self, service, mock_repo):
        results = [{"url": "https://img.example.com/1.jpg"}]
        service.set("unsplash", "mountains", results)

        mock_repo.save.assert_called_once()
        saved_model = mock_repo.save.call_args[0][0]
        assert saved_model.id == "unsplash:mountains"
        assert saved_model.data == results
        assert saved_model.provider == "unsplash"

    def test_key_normalization_applied(self, service, mock_repo):
        service.set("pexels", "  CATS  ", [{"url": "cat.jpg"}])
        saved_model = mock_repo.save.call_args[0][0]
        assert saved_model.id == "pexels:cats"

    def test_swallows_repository_error(self, service, mock_repo):
        mock_repo.save.side_effect = Exception("Datastore write error")
        # Must not raise — error is logged and swallowed
        service.set("unsplash", "mountains", [{"url": "img.jpg"}])

    def test_overwrites_existing_key(self, service, mock_repo):
        old = [{"url": "old.jpg"}]
        new = [{"url": "new.jpg"}]
        service.set("unsplash", "mountains", old)
        service.set("unsplash", "mountains", new)
        assert mock_repo.save.call_count == 2
        saved_model = mock_repo.save.call_args[0][0]
        assert saved_model.data == new


# ─── cleanup_expired ──────────────────────────────────────────────────────────

class TestCleanupExpired:
    def test_returns_zero_deprecated(self, service):
        """cleanup_expired is deprecated — always returns 0."""
        assert service.cleanup_expired() == 0
