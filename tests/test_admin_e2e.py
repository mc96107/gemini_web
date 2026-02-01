import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.routers.admin import get_user as get_admin_user
from app.routers.prompt_helper import get_user as get_helper_user
from unittest.mock import AsyncMock, patch

def test_admin_customization_e2e():
    client = TestClient(app)
    
    # 1. Mock Admin User
    async def override_get_admin(): return "admin"
    app.dependency_overrides[get_admin_user] = override_get_admin
    
    # 2. Update Prompt Helper Instructions via Admin API
    test_instructions = "You are a specialized test helper. Only ask about 'Feature X'."
    response = client.post("/admin/settings", json={"prompt_helper_instructions": test_instructions})
    assert response.status_code == 200
    assert response.json()["success"] is True
    
    # 3. Verify via Prompt Helper Session
    # Mock Prompt Helper User
    async def override_get_helper(): return "admin"
    app.dependency_overrides[get_helper_user] = override_get_helper
    
    # Mock LLM response for the first question
    with patch.object(app.state.agent, 'generate_response', new_callable=AsyncMock) as mock_gen:
        # The prompt passed to generate_response should contain our test_instructions
        mock_gen.return_value = '{"question": "How do you want to test Feature X?", "options": [], "allow_multiple": false, "reasoning": "test", "is_complete": false}'
        
        # Start a session
        response = client.post("/api/prompt-helper/start")
        assert response.status_code == 200
        
        # Verify that generate_response was called with our custom instructions
        # It's the second call in start_session flow (actually the first call to generate_next_question)
        call_args = mock_gen.call_args
        sent_prompt = call_args[0][1]
        assert test_instructions in sent_prompt
        
    # 4. Cleanup
    del app.dependency_overrides[get_admin_user]
    del app.dependency_overrides[get_helper_user]
    # Reset settings
    client.post("/admin/settings", json={"prompt_helper_instructions": None})
