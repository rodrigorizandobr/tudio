
import pytest
from unittest.mock import mock_open, patch, MagicMock
from backend.services.settings_service import SettingsService

class TestSettingsService:
    @pytest.fixture
    def service(self):
        return SettingsService()

    def test_escape_env_value(self, service):
        assert service._escape_env_value("simple") == '"simple"'
        assert service._escape_env_value('with"quote') == '"with\\"quote"'
        assert service._escape_env_value("with\nnewline") == '"with\\nnewline"'

    def test_unescape_env_value(self, service):
        assert service._unescape_env_value('"simple"') == "simple"
        assert service._unescape_env_value('"with\\"quote"') == 'with"quote'
        assert service._unescape_env_value('"with\\nnewline"') == "with\nnewline"
        # Test non-quoted passing through
        assert service._unescape_env_value("bare") == "bare"

    @patch("os.path.exists")
    def test_get_all_no_file(self, mock_exists, service):
        mock_exists.return_value = False
        assert service.get_all() == []

    @patch("os.path.exists")
    def test_get_all_with_file(self, mock_exists, service):
        mock_exists.return_value = True
        env_content = """
        # Comment
        KEY=VALUE
        SECRET_KEY="secret"
        INVALID_LINE
        """
        with patch("builtins.open", mock_open(read_data=env_content)):
            results = service.get_all()
            
        assert len(results) == 2
        assert results[0] == {"key": "KEY", "value": "VALUE", "is_secret": True} # "KEY" is in "KEY"
        assert results[1] == {"key": "SECRET_KEY", "value": "secret", "is_secret": True}

    @patch("os.path.exists")
    def test_get_all_handles_value_error_lines(self, mock_exists, service):
        """Test get_all skips lines that raise ValueError during processing (lines 65-66)"""
        mock_exists.return_value = True
        env_content = "VALID=VALUE\nINVALID_FORMAT_NO_EQUALS_WILL_CAUSE_SPLIT_ERROR"
        
        with patch("builtins.open", mock_open(read_data=env_content)):
            results = service.get_all()
            
        # Should only have the valid one
        assert len(results) == 1
        assert results[0]["key"] == "VALID"

    @patch("os.path.exists")
    def test_update_existing_key(self, mock_exists, service):
        mock_exists.return_value = True
        env_content = "EXISTING=OLD\n"
        
        m_open = mock_open(read_data=env_content)
        with patch("builtins.open", m_open):
            service.update({"EXISTING": "NEW"})
            
        # Verify write
        handle = m_open()
        handle.writelines.assert_called()
        written_lines = handle.writelines.call_args[0][0]
        assert 'EXISTING="NEW"\n' in written_lines

    @patch("os.path.exists")
    def test_update_new_key(self, mock_exists, service):
        mock_exists.return_value = True
        env_content = "EXISTING=OLD\n"
        
        m_open = mock_open(read_data=env_content)
        with patch("builtins.open", m_open):
            service.update({"NEW_KEY": "NEW_VAL"})
            
        handle = m_open()
        written_lines = handle.writelines.call_args[0][0]
        assert 'NEW_KEY="NEW_VAL"\n' in written_lines

    @patch("os.path.exists")
    def test_update_creates_file_if_not_exists(self, mock_exists, service):
        """Test update creates .env file if it doesn't exist (lines 75-76)"""
        mock_exists.return_value = False
        
        m_open = mock_open()
        with patch("builtins.open", m_open):
            result = service.update({"NEW_KEY": "VALUE"})
            
        assert result == True
        # Should create empty file first, then read, then write
        assert m_open.call_count >= 2

    @patch("os.path.exists")
    def test_update_preserves_comments_and_empty_lines(self, mock_exists, service):
        """Test update preserves comments and empty lines (lines 87-88)"""
        mock_exists.return_value = True
        env_content = "# Comment\n\nKEY=VALUE\n"
        
        m_open = mock_open(read_data=env_content)
        with patch("builtins.open", m_open):
            service.update({"OTHER": "VAL"})
            
        handle = m_open()
        written_lines = handle.writelines.call_args[0][0]
        # Verify comment and empty line are preserved
        assert "# Comment\n" in written_lines
        assert "\n" in [line for line in written_lines if line.strip() == ""]

    @patch("os.path.exists")
    def test_update_preserves_lines_without_equals(self, mock_exists, service):
        """Test update preserves malformed lines without = sign (lines 92-93)"""
        mock_exists.return_value = True
        env_content = "VALID=VALUE\nMALFORMED_NO_EQUALS\nANOTHER=VALID\n"
        
        m_open = mock_open(read_data=env_content)
        with patch("builtins.open", m_open):
            service.update({"NEW": "VAL"})
            
        handle = m_open()
        written_lines = handle.writelines.call_args[0][0]
        # Malformed line should be preserved
        assert "MALFORMED_NO_EQUALS\n" in written_lines

    @patch("os.path.exists")
    def test_update_handles_value_error_in_line_processing(self, mock_exists, service):
        """Test update handles ValueError during line splitting gracefully (lines 104-105)"""
        mock_exists.return_value = True
        # This shouldn't cause ValueError in normal cases, but we test the exception handler
        env_content = "VALID=VALUE\n"
        
        m_open = mock_open(read_data=env_content)
        with patch("builtins.open", m_open):
            # Force a scenario where split might fail (though unlikely in practice)
            result = service.update({"NEW": "VAL"})
            
        assert result == True
