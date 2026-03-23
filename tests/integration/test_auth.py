import pytest
from backend.services.auth_service import auth_service
from backend.models.user import UserModel
from backend.repositories.user_repository import user_repository

def test_login_flow(client):
    # 1. Seed User
    email = "auth_test@gmail.com"
    pwd = "password123"
    hashed = auth_service.get_password_hash(pwd)
    
    user = UserModel(
        email=email,
        hashed_password=hashed,
        full_name="Auth Test",
        is_active=True,
        groups=["user"]
    )
    user_repository.save_user(user) # Saves to MockDatastore in test env

    # 2. Try Login Success
    res = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": pwd},
        headers={"content-type": "application/x-www-form-urlencoded"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # 3. Try Login Failure
    res_fail = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "wrongpassword"},
        headers={"content-type": "application/x-www-form-urlencoded"}
    )
    assert res_fail.status_code == 400

    # 4. Verify Access to Protected Route (using the token)
    # The client fixture overrides get_current_user by default.
    # To test REAL auth middleware, we must disable the override for this request.
    
    # Access internal app from client
    client.app.dependency_overrides = {} 
    
    # Try generic endpoint that requires auth
    # GET /scripts/999 (should fail 404 if auth works, or 401 if auth fails)
    
    # With token
    res_protected = client.get(
        "/api/v1/scripts/999",
        headers={"Authorization": f"Bearer {data['access_token']}"}
    )
    # If auth works, it reaches controller -> returns 404 (script not found)
    # If auth fails, it returns 401
    assert res_protected.status_code == 404
    
    # Without token
    res_unauth = client.get("/api/v1/scripts/999")
    assert res_unauth.status_code == 401
