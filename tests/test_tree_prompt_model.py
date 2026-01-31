import pytest
from app.models.prompt_tree import TreeNode, PromptTreeSession

def test_tree_node_creation():
    node = TreeNode(id="1", question="What is your name?")
    assert node.id == "1"
    assert node.question == "What is your name?"
    assert node.answer is None
    assert node.options == []

def test_prompt_tree_session_creation():
    node = TreeNode(id="1", question="Question 1")
    session = PromptTreeSession(id="session_1", nodes=[node], current_node_id="1")
    assert session.id == "session_1"
    assert len(session.nodes) == 1
    assert session.current_node_id == "1"
