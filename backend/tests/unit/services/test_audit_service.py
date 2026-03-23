import pytest
from unittest.mock import patch, MagicMock
from backend.services.audit_service import AuditService, audit_service
from datetime import datetime

class TestAuditService:
    @pytest.fixture
    def service(self):
        return AuditService()
    
    @patch("backend.services.audit_service.get_datastore_client")
    def test_log_event_success(self, mock_get_client, service):
        """Test log_event successfully writes to Datastore"""
        # Mock datastore client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Mock entity and key
        mock_key = MagicMock()
        mock_client.key.return_value = mock_key
        
        mock_entity = MagicMock()
        with patch("backend.services.audit_service.datastore.Entity", return_value=mock_entity):
            # Execute
            service.log_event(
                user_email="user@example.com",
                action="CREATE",
                target="video",
                details="Created video #123"
            )
            
            # Verify
            mock_client.key.assert_called_once_with("AuditLog")
            mock_entity.update.assert_called_once()
            update_dict = mock_entity.update.call_args[0][0]
            assert update_dict["user_email"] == "user@example.com"
            assert update_dict["action"] == "CREATE"
            assert update_dict["target"] == "video"
            assert update_dict["details"] == "Created video #123"
            assert isinstance(update_dict["timestamp"], datetime)
            mock_client.put.assert_called_once_with(mock_entity)
    
    @patch("backend.services.audit_service.get_datastore_client")
    @patch("builtins.print")
    def test_log_event_failure_does_not_raise(self, mock_print, mock_get_client, service):
        """Test log_event catches exceptions and doesn't break app flow"""
        # Mock client to raise exception
        mock_client = MagicMock()
        mock_client.put.side_effect = Exception("Datastore unavailable")
        mock_get_client.return_value = mock_client
        
        mock_key = MagicMock()
        mock_client.key.return_value = mock_key
        
        with patch("backend.services.audit_service.datastore.Entity"):
            # Should not raise exception
            service.log_event(
                user_email="user@example.com",
                action="DELETE",
                target="video"
            )
            
            # Verify error was printed (logged)
            mock_print.assert_called_once()
            assert "Failed to write audit log" in str(mock_print.call_args)
    
    @patch("backend.services.audit_service.get_datastore_client")
    def test_log_event_without_details(self, mock_get_client, service):
        """Test log_event works with optional details=None"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client  
        
        mock_key = MagicMock()
        mock_client.key.return_value = mock_key
        
        mock_entity = MagicMock()
        with patch("backend.services.audit_service.datastore.Entity", return_value=mock_entity):
            service.log_event(
                user_email="admin@test.com",
                action="UPDATE",
                target="settings"
            )
            
            mock_entity.update.assert_called_once()
            update_dict = mock_entity.update.call_args[0][0]
            assert update_dict["details"] is None
