from fastapi.testclient import TestClient
from app.main import app
from app.routers.chat import get_user

def test_stable_models_in_index():
    client = TestClient(app)
    
    # Mock user login
    async def override_get_user(): return "testuser"
    app.dependency_overrides[get_user] = override_get_user
    
    try:
        response = client.get("/")
        assert response.status_code == 200
        # Check for Gemini 3 models
        assert 'data-model="gemini-3-pro-preview"' in response.text
        assert 'value="gemini-3-pro-preview"' in response.text
    finally:
        del app.dependency_overrides[get_user]
