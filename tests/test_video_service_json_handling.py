import pytest
from backend.services.video_service import video_service


class TestConversationalDetection:
    """Test the conversational response detection logic"""
    
    def test_detects_portuguese_greeting(self):
        """Should detect Portuguese conversational greeting"""
        content = "Como posso ajudar você hoje?"
        assert video_service._is_conversational_response(content) is True
    
    def test_detects_english_greeting(self):
        """Should detect English conversational greeting"""
        content = "How can I help you today?"
        assert video_service._is_conversational_response(content) is True
    
    def test_detects_case_insensitive(self):
        """Should detect conversational patterns regardless of case"""
        content = "COMO POSSO AJUDAR você?"
        assert video_service._is_conversational_response(content) is True
    
    def test_detects_with_surrounding_text(self):
        """Should detect conversational pattern even with surrounding text"""
        content = "Olá! Como posso ajudar você hoje? Estou aqui para isso."
        assert video_service._is_conversational_response(content) is True
    
    def test_not_conversational_json(self):
        """Should not detect valid JSON as conversational"""
        content = '{"chapters": [{"order": 1, "title": "Introduction"}]}'
        assert video_service._is_conversational_response(content) is False
    
    def test_not_conversational_empty(self):
        """Should not detect empty string as conversational"""
        content = ""
        assert video_service._is_conversational_response(content) is False
    
    def test_not_conversational_whitespace(self):
        """Should not detect whitespace as conversational"""
        content = "   \n\t  "
        assert video_service._is_conversational_response(content) is False
    
    def test_detects_spanish_greeting(self):
        """Should detect Spanish conversational greeting"""
        content = "¿Cómo puedo ayudar?"
        assert video_service._is_conversational_response(content) is True
    
    def test_detects_french_greeting(self):
        """Should detect French conversational greeting"""
        content = "Je peux vous aider aujourd'hui"
        assert video_service._is_conversational_response(content) is True


class TestSafeJsonParse:
    """Test the safe JSON parsing with conversational detection"""
    
    def test_parse_valid_json(self):
        """Should successfully parse valid JSON"""
        content = '{"chapters": [{"order": 1, "title": "Test"}]}'
        result = video_service._safe_json_parse(content, "Test Context")
        assert result == {"chapters": [{"order": 1, "title": "Test"}]}
    
    def test_raises_on_conversational_response(self):
        """Should raise ValueError with THREAD_CORRUPTED prefix on conversational response"""
        content = "Como posso ajudar você hoje?"
        
        with pytest.raises(ValueError) as exc_info:
            video_service._safe_json_parse(content, "Test Context")
        
        error_msg = str(exc_info.value)
        assert "THREAD_CORRUPTED" in error_msg
        assert "Test Context" in error_msg
        assert "conversational response" in error_msg.lower()
    
    def test_raises_on_invalid_json(self):
        """Should raise ValueError on invalid JSON (not conversational)"""
        content = '{"invalid": json}'
        
        with pytest.raises(ValueError) as exc_info:
            video_service._safe_json_parse(content, "Test Context")
        
        error_msg = str(exc_info.value)
        # Should NOT have THREAD_CORRUPTED prefix for regular JSON errors
        assert "THREAD_CORRUPTED" not in error_msg or "Invalid JSON" in error_msg
    
    def test_recovers_from_markdown_code_block(self):
        """Should extract JSON from markdown code blocks"""
        content = '```json\n{"chapters": [{"order": 1}]}\n```'
        result = video_service._safe_json_parse(content, "Test Context")
        assert result == {"chapters": [{"order": 1}]}
    
    def test_recovers_from_trailing_comma(self):
        """Should fix trailing commas in JSON"""
        content = '{"chapters": [{"order": 1,}],}'
        result = video_service._safe_json_parse(content, "Test Context")
        assert result == {"chapters": [{"order": 1}]}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
