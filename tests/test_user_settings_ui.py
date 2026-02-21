from fastapi.testclient import TestClient
from app.main import app
from app.routers.chat import get_user

def test_default_model_dropdown_in_index():
    client = TestClient(app)
    
    # Mock user login
    async def override_get_user(): return "testuser"
    app.dependency_overrides[get_user] = override_get_user
    
    try:
        response = client.get("/")
        assert response.status_code == 200
        # Check for the dropdown in the security modal
        assert 'id="setting-default-model"' in response.text
        assert 'value="gemini-3-pro-preview"' in response.text
        assert 'Gemini 3 Pro (Preview)' in response.text
        assert 'Gemini 3 Pro (Stable)' in response.text
    finally:
        del app.dependency_overrides[get_user]

def test_default_model_persists_in_ui():
    client = TestClient(app)
    
    # Mock user login
    async def override_get_user(): return "testuser"
    app.dependency_overrides[get_user] = override_get_user
    
    try:
        # 1. Update setting via API
        response = client.post("/settings", json={"default_model": "gemini-3-flash-preview"})
        assert response.status_code == 200
        
        # 2. Check if the index page renders with the correct selected model in JS or HTML
        # The template renders user_settings into window.USER_SETTINGS
        response = client.get("/")
        assert response.status_code == 200
        assert '"default_model": "gemini-3-flash-preview"' in response.text
    finally:
        del app.dependency_overrides[get_user]
