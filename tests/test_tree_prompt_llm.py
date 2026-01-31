import pytest
from unittest.mock import AsyncMock
from app.services.tree_prompt_service import TreePromptService

@pytest.mark.asyncio
async def test_generate_next_question():
    service = TreePromptService()
    session_id = service.create_session()
    
    # Mock LLM service
    mock_llm = AsyncMock()
    mock_llm.generate_response.return_value = '{"question": "What is the topic?", "options": ["Tech", "Art"], "reasoning": "Need a topic.", "is_complete": false}'
    
    result = await service.generate_next_question(session_id, mock_llm)
    
    assert result["question"] == "What is the topic?"
    assert "Tech" in result["options"]
    assert result["is_complete"] is False
    mock_llm.generate_response.assert_called_once()

@pytest.mark.asyncio
async def test_generate_next_question_error_fallback():
    service = TreePromptService()
    session_id = service.create_session()
    
    # Mock LLM service with invalid JSON
    mock_llm = AsyncMock()
    mock_llm.generate_response.return_value = 'Invalid response'
    
    result = await service.generate_next_question(session_id, mock_llm)
    
    assert "goals" in result["question"]
    assert result["is_complete"] is False
