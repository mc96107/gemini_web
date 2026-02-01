import os
import json
import pytest
from app.core.config import get_global_setting, update_global_setting
from fastapi.testclient import TestClient
from app.main import app
from app.routers.admin import get_user

def test_get_set_global_settings():
    test_key = "test_setting"
    test_value = "hello_world"
    
    update_global_setting(test_key, test_value)
    assert get_global_setting(test_key) == test_value

def test_admin_settings_routes():
    client = TestClient(app)
    
    # Override get_user dependency to mock admin
    async def override_get_user():
        return "admin"
    
    app.dependency_overrides[get_user] = override_get_user
    
    try:
        # Test GET /admin/settings
        response = client.get("/admin/settings")
        assert response.status_code == 200
        settings = response.json()
        assert "prompt_helper_instructions" in settings
        
        # Test POST /admin/settings
        new_instructions = "New instructions for test"
        response = client.post("/admin/settings", json={"prompt_helper_instructions": new_instructions})
        assert response.status_code == 200
        assert response.json()["success"] is True
        
        # Verify change
        response = client.get("/admin/settings")
        assert response.json()["prompt_helper_instructions"] == new_instructions
    finally:
        # Clear override
        del app.dependency_overrides[get_user]
