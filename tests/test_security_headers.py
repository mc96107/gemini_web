from fastapi.testclient import TestClient
from app.main import app

def test_security_headers():
    client = TestClient(app)
    response = client.get("/login")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in response.headers
