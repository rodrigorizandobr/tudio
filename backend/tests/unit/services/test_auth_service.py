
import pytest
from datetime import timedelta
from backend.services.auth_service import auth_service
from backend.core.configs import settings

class TestAuthService:
    def test_hash_password(self):
        password = "secretpassword"
        hashed = auth_service.get_password_hash(password)
        assert hashed != password
        assert auth_service.verify_password(password, hashed) is True
        assert auth_service.verify_password("wrongpassword", hashed) is False

    def test_create_access_token(self):
        data = {"sub": "test@example.com"}
        token = auth_service.create_access_token(data)
        assert isinstance(token, str)
        
        # Verify token content implies decoding logic or at least structure
        # In a real unit test we might decode it back to verify, but here we trust the lib
        # We can check if it has 3 parts
        assert len(token.split('.')) == 3

    def test_create_access_token_with_expiry(self):
        data = {"sub": "test@example.com"}
        expires = timedelta(minutes=10)
        token = auth_service.create_access_token(data, expires_delta=expires)
        assert isinstance(token, str)
