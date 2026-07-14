from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

client = TestClient(app)
settings = get_settings()
HEADERS = {"X-API-Key": settings.api_key}


def test_upload_rejects_without_api_key():
    response = client.post("/documents/upload")
    assert response.status_code == 403


def test_chat_rejects_without_api_key():
    response = client.post("/chat", json={"session_id": "test", "message": "hi"})
    assert response.status_code == 403


def test_get_document_status_with_valid_key_returns_404_for_unknown_id():
    """Confirms auth actually passes with a correct key — a 404 (not 401/403)
    here proves the request got past the auth check and reached the route logic."""
    response = client.get("/documents/some-nonexistent-id", headers=HEADERS)
    assert response.status_code == 404