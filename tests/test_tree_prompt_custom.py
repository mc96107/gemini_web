import pytest
from unittest.mock import MagicMock, AsyncMock
from app.services.tree_prompt_service import TreePromptService
from app.core import config

@pytest.mark.asyncio
async def test_tree_prompt_service_uses_global_settings():
    service = TreePromptService()
    session_id = service.create_session()
    
    # Mock LLM service
    llm_service = AsyncMock()
    llm_service.generate_response.return_value = '{"question": "Test?", "options": [], "allow_multiple": false, "reasoning": "test", "is_complete": false}'
    
    # Set a unique global setting
    test_instruction = "YOU ARE A TEST BOT. ALWAYS ASK ABOUT CHEESE."
    config.update_global_setting("prompt_helper_instructions", test_instruction)
    
    await service.generate_next_question(session_id, llm_service)
    
    # Verify that the LLM was called with the custom instruction
    call_args = llm_service.generate_response.call_args
    sent_prompt = call_args[0][1]
    assert test_instruction in sent_prompt
    
    # Reset to default
    config.update_global_setting("prompt_helper_instructions", None)
