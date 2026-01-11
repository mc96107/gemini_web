from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_main():
    # Index should redirect to login if not authenticated
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].endswith("/login")

def test_login_page():
    response = client.get("/login")
    assert response.status_code == 200
    assert "Login" in response.text
