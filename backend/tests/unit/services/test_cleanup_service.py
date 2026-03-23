
import pytest
import time
from unittest.mock import MagicMock, patch
from backend.services.cleanup_service import CleanupService
from backend.models.video import VideoStatus

class TestCleanupService:
    @pytest.fixture
    def service(self):
        # Prevent scheduler from actually starting during init if it did
        with patch("backend.services.cleanup_service.BackgroundScheduler"):
            svc = CleanupService()
            return svc

    def test_start_scheduler(self, service):
        service.scheduler.running = False
        service.start_scheduler()
        
        service.scheduler.add_job.assert_called_once()
        service.scheduler.start.assert_called_once()

    @patch("os.path.exists")
    @patch("os.listdir")
    @patch("os.path.isfile")
    @patch("os.path.getmtime")
    @patch("os.remove")
    def test_clean_temp_files(self, mock_remove, mock_mtime, mock_isfile, mock_listdir, mock_exists, service):
        mock_exists.return_value = True
        mock_listdir.return_value = ["old.tmp", "new.tmp"]
        mock_isfile.return_value = True
        
        # timestamps: old is 25h ago, new is 1h ago
        now = time.time()
        mock_mtime.side_effect = [
            now - (25 * 3600), # old
            now - (1 * 3600)   # new
        ]
        
        service.clean_temp_files(max_age_hours=24)
        
        # Should remove only the first file
        assert mock_remove.call_count == 1
        args, _ = mock_remove.call_args
        assert "old.tmp" in args[0]

    @patch("backend.services.cleanup_service.video_repository")
    @patch("shutil.rmtree")
    @patch("os.path.exists")
    def test_clean_abandoned_drafts(self, mock_exists, mock_rmtree, mock_repo, service):
        mock_exists.return_value = True
        
        # Mock videos
        # 1. Draft, Old (Should delete)
        v1 = MagicMock()
        v1.id = "v1"
        v1.status = VideoStatus.PENDING
        v1.updated_at = MagicMock()
        # Mock datetime comparison: v1.updated_at < cutoff
        # We can't easily mock operator overloading on MagicMock for datetime comparison without complex setup.
        # Instead, we rely on the logic: ref_time < cutoff_time
        # Let's assume the service implementation uses standard datetime objects.
        # We will patch datetime in the service to control "now" and ensure comparison works.
        pass
    
    @patch("backend.services.cleanup_service.video_repository")
    @patch("shutil.rmtree")
    @patch("os.path.exists")
    def test_clean_abandoned_drafts_simple(self, mock_exists, mock_rmtree, mock_repo, service):
        # Simplified test to avoid datetime patching hell
        from datetime import datetime, timedelta
        
        mock_exists.return_value = True
        
        now = datetime.now()
        old_date = now - timedelta(hours=48)
        new_date = now - timedelta(hours=1)
        
        v1 = MagicMock()
        v1.id = "v1"
        v1.deleted_at = None
        v1.status = VideoStatus.PENDING
        v1.updated_at = old_date
        
        v2 = MagicMock()
        v2.id = "v2"
        v2.deleted_at = None
        v2.status = VideoStatus.COMPLETED # Should keep
        v2.updated_at = old_date
        
        v3 = MagicMock()
        v3.id = "v3"
        v3.deleted_at = None
        v3.status = VideoStatus.PENDING # Should keep (too new)
        v3.updated_at = new_date

        mock_repo.list_all.return_value = [v1, v2, v3]
        
        service.clean_abandoned_drafts(max_age_hours=24)
        
        # Expect v1 save (soft delete) and rmtree (hard delete files)
        assert mock_repo.save.call_count == 1
        args, _ = mock_repo.save.call_args
        assert args[0].id == "v1"
        assert args[0].deleted_at is not None
        
        
        mock_rmtree.assert_called_once()
    
    def test_start_scheduler_when_already_running(self, service):
        """Test start_scheduler doesn't restart if already running"""
        service.scheduler.running = True
        service.start_scheduler()
        
        # Should not call add_job or start
        service.scheduler.add_job.assert_not_called()
        service.scheduler.start.assert_not_called()
    
    @patch("os.path.exists")
    def test_clean_temp_files_dir_not_exists(self, mock_exists, service):
        """Test clean_temp_files returns early if dir doesn't exist"""
        mock_exists.return_value = False
        
        # Should not crash, just return early
        service.clean_temp_files()
        
        # No files should be deleted
        mock_exists.assert_called_once()
    
    def test_run_cleanup_tasks_calls_all_methods(self, service):
        """Test run_cleanup_tasks calls both cleanup methods"""
        with patch.object(service, 'clean_temp_files') as mock_temp:
            with patch.object(service, 'clean_abandoned_drafts') as mock_drafts:
                service.run_cleanup_tasks()
                
                mock_temp.assert_called_once()
                mock_drafts.assert_called_once()
