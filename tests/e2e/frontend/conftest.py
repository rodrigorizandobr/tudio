import pytest
import threading
import uvicorn
import time
from backend.main import app

# Configuration
# Using external dev server on port 8000 instead of starting a test server
PORT = 8000
BASE_URL = f"http://localhost:{PORT}"

# Commented out internal server startup - using external dev server
# class UvicornServer(uvicorn.Server):
#     def install_signal_handlers(self):
#         # Override to avoid conflicting with pytest's signal handlers
#         pass

@pytest.fixture(scope="session")
def test_server():
    """
    Use external dev server on port 8000 (started via ./start.sh)
    No need to start a separate test server.
    """
    # Simply return the base URL - assuming server is already running
    yield BASE_URL

@pytest.fixture(scope="session")
def base_url(test_server):
    return test_server

@pytest.fixture(scope="function")
def auth_header():
    # Helper to generate a valid JWT if needed for direct API calls,
    # but for Frontend E2E we usually login via UI.
    return {}

from backend.services.auth_service import auth_service
from backend.models.user import UserCreate

@pytest.fixture(scope="function", autouse=True)
def seed_admin_user():
    """
    Ensure Admin User exists for every frontend test.
    The parent 'clean_datastore' fixture clears the DB, so we must re-seed.
    """
    try:
        # Create user directly using service (mock persistence)
        # We wrap in try specific for unique violation if it wasn't cleared, 
        # but clean_datastore should have cleared it.
        # Passlib might send warnings but that's fine.
        auth_service.create_user(UserCreate(
            email="rodrigorizando@gmail.com",
            password="admin@123",
            is_active=True,
            is_superuser=True,
            groups=["admin"]
        ))
    except Exception:
        # If already exists (e.g. clean failed), ignore
        pass
