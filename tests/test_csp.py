from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_csp_connect_src():
    response = client.get("/login")
    csp = response.headers["Content-Security-Policy"]
    assert "connect-src 'self' cdn.jsdelivr.net;" in csp or "connect-src 'self' https://cdn.jsdelivr.net;" in csp
