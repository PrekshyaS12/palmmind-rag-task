from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
HEADERS = {"X-API-Key": "choose-any-secret-string-here-yourself"}  # match your .env value

def test_upload_rejects_without_api_key():
    response = client.post("/documents/upload")
    assert response.status_code == 401

def test_chat_rejects_without_api_key():
    response = client.post("/chat", json={"session_id": "test", "message": "hi"})
    assert response.status_code == 401