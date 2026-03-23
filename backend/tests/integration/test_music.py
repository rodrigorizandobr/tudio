import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.models.user import UserModel
from backend.services.auth_service import auth_service

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def auth_headers(client):
    # Mock auth or login
    # Assuming we have a test user in DB or can create one
    # For now, let's try to mock the dependency override or use a known user
    # Simplified: We'll override get_current_user
    from backend.api.deps import get_current_user
    
    # Define a Test User with ID
    class TestUserModel(UserModel):
        id: int = 1

    user = TestUserModel(
        email="test@tudio.com", 
        hashed_password="hash", 
        is_active=True, 
        groups=["admin"]
    )
    # Monkeypatch ID not needed as it is part of TestUserModel
    app.dependency_overrides[get_current_user] = lambda: user
    
    return {"Authorization": "Bearer mock_token"}

def test_music_flow(client, auth_headers):
    # 1. Upload
    # Create a dummy mp3 content
    dummy_mp3 = b'ID3' + b'\x00'*100 
    
    files = {'file': ('test_song.mp3', dummy_mp3, 'audio/mpeg')}
    data = {
        'title': 'Test Song',
        'artist': 'Test Artist',
        'genre': 'Rock',
        'mood': 'Happy'
    }
    
    response = client.post("/api/v1/music/", files=files, data=data, headers=auth_headers)
    assert response.status_code == 200, response.text
    music = response.json()
    assert music['title'] == 'Test Song'
    assert music['id'] is not None
    music_id = music['id']
    
    # 2. List
    response = client.get("/api/v1/music/", headers=auth_headers)
    assert response.status_code == 200
    musics = response.json()
    assert any(m['id'] == music_id for m in musics)
    
    # 3. Delete
    response = client.delete(f"/api/v1/music/{music_id}", headers=auth_headers)
    assert response.status_code == 204
    
    # 4. Verify Deleted (List again)
    response = client.get("/api/v1/music/", headers=auth_headers)
    musics = response.json()
    assert not any(m['id'] == music_id for m in musics)

    # Clean up overrides
    app.dependency_overrides = {}
