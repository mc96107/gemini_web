from fastapi.testclient import TestClient
from app.main import app
import os

def test_redirect_to_setup_when_no_users(tmp_path, monkeypatch):
    # Use isolated users.json
    users_file = str(tmp_path / "users.json")
    monkeypatch.setenv("USERS_FILE", users_file)
    
    from app.services.user_manager import UserManager
    app.state.user_manager = UserManager()
    
    client = TestClient(app)
    
    # Root should redirect to /setup
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/setup"

def test_setup_flow(tmp_path, monkeypatch):
    # Use isolated users.json
    users_file = str(tmp_path / "users.json")
    monkeypatch.setenv("USERS_FILE", users_file)
    
    from app.services.user_manager import UserManager
    app.state.user_manager = UserManager()
    
    client = TestClient(app)
    
    # Post to setup
    response = client.post("/setup", data={"password": "testpassword123"}, follow_redirects=False)
    assert response.status_code == 303 or response.status_code == 302 or response.status_code == 307
    
    # Try setup again - should fail
    response = client.post("/setup", data={"password": "another"}, follow_redirects=False)
    assert response.status_code == 403
