import uuid
from typing import List, Optional, Dict
from app.models.prompt_tree import TreeNode, PromptTreeSession

class TreePromptService:
    def __init__(self):
        # In-memory storage for sessions (can be moved to persistent storage later if needed)
        self.sessions: Dict[str, PromptTreeSession] = {}

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        session = PromptTreeSession(id=session_id, nodes=[], current_node_id=None)
        self.sessions[session_id] = session
        return session_id

    def get_session(self, session_id: str) -> Optional[PromptTreeSession]:
        return self.sessions.get(session_id)

    def add_question(self, session_id: str, question: str, options: List[str] = [], parent_id: Optional[str] = None) -> str:
        session = self.get_session(session_id)
        if not session:
            raise ValueError("Session not found")
        
        node_id = str(uuid.uuid4())
        new_node = TreeNode(
            id=node_id,
            parent_id=parent_id or session.current_node_id,
            question=question,
            options=options
        )
        session.nodes.append(new_node)
        session.current_node_id = node_id
        return node_id

    def answer_question(self, session_id: str, node_id: str, answer: str):
        session = self.get_session(session_id)
        if not session:
            raise ValueError("Session not found")
        
        for node in session.nodes:
            if node.id == node_id:
                node.answer = answer
                break

    def rewind_to(self, session_id: str, node_id: str):
        session = self.get_session(session_id)
        if not session:
            raise ValueError("Session not found")
        
        # Find the node index
        target_idx = -1
        for i, node in enumerate(session.nodes):
            if node.id == node_id:
                target_idx = i
                break
        
        if target_idx != -1:
            # Truncate nodes after the target node and clear target node's answer
            session.nodes = session.nodes[:target_idx + 1]
            session.nodes[target_idx].answer = None
            session.current_node_id = node_id

    def synthesize_prompt(self, session_id: str) -> str:
        session = self.get_session(session_id)
        if not session:
            raise ValueError("Session not found")
        
        lines = ["# Synthesized Prompt based on Guided Session", ""]
        for node in session.nodes:
            if node.answer:
                lines.append(f"Q: {node.question}")
                lines.append(f"A: {node.answer}")
                lines.append("")
        
        return "\n".join(lines).strip()
