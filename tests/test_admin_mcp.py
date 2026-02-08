from fastapi.testclient import TestClient
from app.main import app
from app.routers.admin import get_user
from unittest.mock import patch, MagicMock
import pytest

def test_admin_mcp_list():
    client = TestClient(app)
    # Mock admin login
    async def override_get_admin(): return "admin"
    app.dependency_overrides[get_user] = override_get_admin
    
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="✓ web-inspector: npx -y mcp-web-inspector (stdio) - Connected", check_returncode=MagicMock())
        
        response = client.get("/admin/mcp")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "web-inspector"
        assert data[0]["enabled"] is True
    
    del app.dependency_overrides[get_user]

def test_admin_mcp_toggle():
    client = TestClient(app)
    # Mock admin login
    async def override_get_admin(): return "admin"
    app.dependency_overrides[get_user] = override_get_admin
    
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="Enabled server web-inspector", check_returncode=MagicMock())
        
        response = client.post("/admin/mcp/toggle", json={"name": "web-inspector", "enabled": True})
        assert response.status_code == 200
        assert response.json()["success"] is True
        
        # Verify call
        args = mock_run.call_args[0][0]
        assert "enable" in args
        assert "web-inspector" in args
    
    del app.dependency_overrides[get_user]
