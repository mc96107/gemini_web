import pytest
from app.services.tree_prompt_service import TreePromptService
from app.models.prompt_tree import TreeNode

def test_add_node():
    service = TreePromptService()
    session_id = service.create_session()
    
    node_id = service.add_question(session_id, "What is the project about?", options=["Web App", "CLI"])
    
    session = service.get_session(session_id)
    assert len(session.nodes) == 1
    assert session.nodes[0].question == "What is the project about?"
    assert session.current_node_id == node_id

def test_answer_and_next():
    service = TreePromptService()
    session_id = service.create_session()
    node_id = service.add_question(session_id, "Q1")
    
    service.answer_question(session_id, node_id, "Answer 1")
    
    session = service.get_session(session_id)
    assert session.nodes[0].answer == "Answer 1"

def test_rewind():
    service = TreePromptService()
    session_id = service.create_session()
    n1 = service.add_question(session_id, "Q1")
    service.answer_question(session_id, n1, "A1")
    n2 = service.add_question(session_id, "Q2")
    service.answer_question(session_id, n2, "A2")
    n3 = service.add_question(session_id, "Q3")
    
    # Rewind to n1
    service.rewind_to(session_id, n1)
    
    session = service.get_session(session_id)
    assert session.current_node_id == n1
    # Nodes after n1 should be removed (or marked as inactive/invalidated if we support branching, 
    # but for simplicity let's truncate for now as per "rewinds the state to that point")
    assert len(session.nodes) == 1
    assert session.nodes[0].answer is None

def test_synthesis():
    service = TreePromptService()
    session_id = service.create_session()
    n1 = service.add_question(session_id, "Q1")
    service.answer_question(session_id, n1, "A1")
    n2 = service.add_question(session_id, "Q2")
    service.answer_question(session_id, n2, "A2")
    
    prompt = service.synthesize_prompt(session_id)
    assert "Q: Q1" in prompt
    assert "A: A1" in prompt
    assert "Q: Q2" in prompt
    assert "A: A2" in prompt

def test_session_not_found():
    service = TreePromptService()
    with pytest.raises(ValueError, match="Session not found"):
        service.add_question("invalid", "Q")
    with pytest.raises(ValueError, match="Session not found"):
        service.answer_question("invalid", "node", "A")
    with pytest.raises(ValueError, match="Session not found"):
        service.rewind_to("invalid", "node")
    with pytest.raises(ValueError, match="Session not found"):
        service.synthesize_prompt("invalid")
