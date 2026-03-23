import pytest
from backend.models.script import ScriptStatus

def test_create_script(client):
    response = client.post(
        "/api/v1/scripts/",
        json={"prompt": "How to bake a carrot cake", "target_duration_minutes": 10, "language": "en"}
    )
    assert response.status_code == 201
    content = response.json()
    assert content["prompt"] == "How to bake a carrot cake"
    assert content["language"] == "en"
    assert content["id"] is not None
    assert content["status"] == ScriptStatus.PENDING
    # New fields initialized as dry/empty by default or by model
    assert "visual_style" in content
    assert "characters" in content

def test_read_nonexistent_script(client):
    response = client.get("/api/v1/scripts/999")
    assert response.status_code == 404

def test_full_script_flow(client):
    # 1. Create
    create_res = client.post(
        "/api/v1/scripts/",
        json={"prompt": "History of Brazil", "target_duration_minutes": 5}
    )
    assert create_res.status_code == 201
    script_id = create_res.json()["id"]

    # 2. Read initial status
    get_res = client.get(f"/api/v1/scripts/{script_id}")
    assert get_res.status_code == 200
    assert get_res.json()["status"] in [ScriptStatus.PENDING, ScriptStatus.PROCESSING, ScriptStatus.COMPLETED]
