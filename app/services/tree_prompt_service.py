import uuid
import re
import json
from typing import List, Optional, Dict
from app.models.prompt_tree import TreeNode, PromptTreeSession

class TreePromptService:
    def __init__(self):
        # In-memory storage for sessions (can be moved to persistent storage later if needed)
        self.sessions: Dict[str, PromptTreeSession] = {}

    def create_session(self, context: Optional[str] = None) -> str:
        session_id = str(uuid.uuid4())
        session = PromptTreeSession(
            id=session_id, 
            nodes=[], 
            current_node_id=None,
            context=context
        )
        self.sessions[session_id] = session
        return session_id

    def get_session(self, session_id: str) -> Optional[PromptTreeSession]:
        return self.sessions.get(session_id)

    def add_question(self, session_id: str, question: str, options: List[str] = [], parent_id: Optional[str] = None, allow_multiple: bool = False) -> str:
        session = self.get_session(session_id)
        if not session:
            raise ValueError("Session not found")
        
        node_id = str(uuid.uuid4())
        new_node = TreeNode(
            id=node_id,
            parent_id=parent_id or session.current_node_id,
            question=question,
            options=options,
            metadata={"allow_multiple": allow_multiple}
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

    async def synthesize_prompt(self, session_id: str, llm_service) -> str:
        session = self.get_session(session_id)
        if not session:
            raise ValueError("Session not found")
        
        facts = []
        if session.context:
            facts.append(f"Background Context:\n{session.context}")
            
        for node in session.nodes:
            if node.answer:
                facts.append(f"Requirement: {node.question}\nUser Choice: {node.answer}")
        
        facts_str = "\n\n".join(facts)

        system_prompt = """
        You are an elite prompt engineer. Your task is to synthesize a high-quality, professional, and effective system prompt based on the requirements and preferences gathered from a user interaction.
        
        The output should be a well-structured, clear, and comprehensive prompt that could be used to initialize another AI agent. 
        Focus on:
        - Role and Identity.
        - Core Goals and Purpose.
        - Specific Constraints and Guidelines.
        - Preferred Output Format.
        
        Output ONLY the synthesized prompt text. Do not include any meta-commentary, explanations, or labels like "Synthesized Prompt:".
        """

        prompt = f"### GATHERED REQUIREMENTS:\n{facts_str}\n\n### TASK:\nSynthesize the final system prompt."
        
        response = await llm_service.generate_response("system_tree_helper_synth", f"{system_prompt}\n\n{prompt}")
        return response.strip()

    async def generate_next_question(self, session_id: str, llm_service) -> Optional[Dict]:
        """
        Uses LLM to analyze the current tree and generate the next logical question.
        Returns a dict with 'question' and 'options' (if any).
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError("Session not found")

        # Build context from existing nodes
        context = []
        
        if session.context:
            context.append(f"--- ACTIVE CHAT CONTEXT ---\n{session.context}\n---------------------------")
            
        for node in session.nodes:
            if node.answer:
                context.append(f"Question: {node.question}\nAnswer: {node.answer}")
        
        context_str = "\n\n".join(context) if context else "No questions answered yet. This is the start of the session."

        system_prompt = """
        You are an expert prompt engineer. Your goal is to help the user build a high-quality, effective prompt through a guided interaction.
        Based on the information gathered so far, your task is to ask the NEXT logical question to further refine the prompt.
        
        If 'ACTIVE CHAT CONTEXT' is provided, use it to infer the user's likely goal and skip initial general questions (like "What is the topic?"). Instead, ask a more specific starting question relevant to that context.
        
        Output your response EXCLUSIVELY in JSON format with the following keys:
        - "question": The question to ask the user.
        - "options": A list of suggested short answers (buttons), or an empty list [] if it's an open-ended question.
        - "allow_multiple": Boolean, true if the user should be allowed to select multiple options.
        - "reasoning": A brief explanation of why you are asking this question.
        - "is_complete": Boolean, true if you have enough information to synthesize the final prompt.

        Guidelines:
        - Keep questions concise and focused.
        - Provide 2-4 options when possible.
        - Set "allow_multiple" to true if the question asks for "all that apply" or features/topics.
        - DO NOT loop indefinitely. If you have a clear idea of the role, goal, and constraints, set 'is_complete' to true.
        - If 'is_complete' is true, set 'question' to "I have gathered enough information to build your prompt. Would you like to review it now?" and provide options ["Yes", "Not yet, I want to add more"].
        """

        prompt = f"### GATHERED INFORMATION:\n{context_str}\n\n### TASK:\nGenerate the next question to help build a great prompt."
        
        # Use a unique ID for this session to prevent cross-session memory
        llm_user_id = f"tree_helper_{session_id}"
        response_text = await llm_service.generate_response(llm_user_id, f"{system_prompt}\n\n{prompt}")
        
        try:
            # Basic JSON extraction in case there's markdown wrapping
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                return data
            else:
                return {
                    "question": "Could you provide more details about your goals for this prompt?",
                    "options": [],
                    "reasoning": "Failed to parse LLM response as JSON.",
                    "is_complete": False
                }
        except Exception:
            return {
                "question": "Could you provide more details about your goals for this prompt?",
                "options": [],
                "reasoning": "Exception while parsing LLM response.",
                "is_complete": False
            }
