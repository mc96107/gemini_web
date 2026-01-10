import pytest
from app.services.llm_service import GeminiAgent
import inspect

@pytest.mark.anyio
async def test_generate_response_is_generator(tmp_path):
    agent = GeminiAgent(working_dir=str(tmp_path))
    response = agent.generate_response_stream("user", "hello")
    assert inspect.isasyncgen(response)
