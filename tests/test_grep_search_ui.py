from fastapi.testclient import TestClient
from app.main import app
from app.routers.chat import get_user
import pytest

def test_grep_search_in_index():
    client = TestClient(app)
    
    # Mock user login
    async def override_get_user(): return "testuser"
    app.dependency_overrides[get_user] = override_get_user
    
    try:
        response = client.get("/")
        assert response.status_code == 200
        # This SHOULD fail before the fix because it's still search_file_content
        assert 'grep_search' in response.text
        assert 'search_file_content' not in response.text
    finally:
        del app.dependency_overrides[get_user]
