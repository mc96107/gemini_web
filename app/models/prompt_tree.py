from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class TreeNode(BaseModel):
    id: str
    parent_id: Optional[str] = None
    question: str
    answer: Optional[str] = None
    options: List[str] = []
    metadata: Dict[str, Any] = {}

class PromptTreeSession(BaseModel):
    id: str
    nodes: List[TreeNode] = []
    current_node_id: Optional[str] = None
    context: Optional[str] = None
