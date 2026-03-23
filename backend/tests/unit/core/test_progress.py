"""
Tests for backend/core/progress.py
Covers: calculate_parallel_progress and update_video_progress
"""
from backend.core.progress import calculate_parallel_progress, update_video_progress
from unittest.mock import MagicMock


class TestCalculateParallelProgress:
    def test_empty_tasks_returns_zero(self):
        assert calculate_parallel_progress({}) == 0.0

    def test_single_task(self):
        assert calculate_parallel_progress({"a": 50.0}) == 50.0

    def test_averages_multiple_tasks(self):
        assert calculate_parallel_progress({"a": 50, "b": 100}) == 75.0

    def test_averages_three_tasks(self):
        assert calculate_parallel_progress({"a": 10, "b": 20, "c": 30}) == 20.0

    def test_clamps_at_100(self):
        assert calculate_parallel_progress({"a": 150}) == 100.0

    def test_clamps_at_100_multiple(self):
        assert calculate_parallel_progress({"a": 120.0, "b": 100.0}) == 100.0


class MockVideo:
    def __init__(self):
        self.rendering_progress = 0.0
        self.id = "test-video"


class TestUpdateVideoProgress:
    def test_first_update(self):
        video = MockVideo()
        repo = MagicMock()
        new_progress = update_video_progress(video, "task1", 50.0, repo)
        assert new_progress == 50.0
        assert video.rendering_progress == 50.0
        repo.save.assert_called_once_with(video)

    def test_same_task_improving(self):
        video = MockVideo()
        repo = MagicMock()
        update_video_progress(video, "task1", 50.0, repo)
        repo.save.reset_mock()
        new_progress = update_video_progress(video, "task1", 60.0, repo)
        assert new_progress == 60.0
        assert video.rendering_progress == 60.0
        repo.save.assert_called_once_with(video)

    def test_regression_does_not_save(self):
        """If combined progress goes down, rendering_progress must not update."""
        video = MockVideo()
        repo = MagicMock()
        update_video_progress(video, "task1", 60.0, repo)
        repo.save.reset_mock()
        # task2=20 → avg(60,20)=40 which is less than current 60 → no save
        new_progress = update_video_progress(video, "task2", 20.0, repo)
        assert new_progress == 40.0
        assert video.rendering_progress == 60.0
        repo.save.assert_not_called()

    def test_second_task_improving(self):
        video = MockVideo()
        repo = MagicMock()
        update_video_progress(video, "task1", 60.0, repo)
        repo.save.reset_mock()
        # task2=80 → avg(60,80)=70 which is > 60 → saves
        new_progress = update_video_progress(video, "task2", 80.0, repo)
        assert new_progress == 70.0
        assert video.rendering_progress == 70.0
        repo.save.assert_called_once_with(video)
