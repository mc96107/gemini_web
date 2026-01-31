from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import Optional, List
import os
import uuid
from datetime import datetime
from app.core import config

router = APIRouter(prefix="/api/prompt-helper")

async def get_user(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(401, "Unauthorized")
    return user

@router.get("/session")
async def get_session(request: Request, user=Depends(get_user)):
    tree_service = request.app.state.tree_prompt_service
    # For now, we use a simple mapping of user -> session_id
    # In a real app, this might be in a database or session state
    session_id = request.session.get("prompt_tree_session_id")
    if not session_id:
        return {"session": None}
    
    session = tree_service.get_session(session_id)
    return {"session": session}

@router.post("/start")
async def start_session(request: Request, user=Depends(get_user)):
    tree_service = request.app.state.tree_prompt_service
    llm_service = request.app.state.agent
    
    session_id = tree_service.create_session()
    request.session["prompt_tree_session_id"] = session_id
    
    # Generate the first question
    next_q = await tree_service.generate_next_question(session_id, llm_service)
    
    node_id = tree_service.add_question(
        session_id, 
        next_q["question"], 
        options=next_q.get("options", [])
    )
    
    return {
        "success": True, 
        "session_id": session_id,
        "next_question": next_q,
        "node_id": node_id
    }

@router.post("/answer")
async def answer_question(request: Request, node_id: str = Form(...), answer: str = Form(...), user=Depends(get_user)):
    tree_service = request.app.state.tree_prompt_service
    llm_service = request.app.state.agent
    session_id = request.session.get("prompt_tree_session_id")
    
    if not session_id:
        raise HTTPException(400, "No active session")
    
    tree_service.answer_question(session_id, node_id, answer)
    
    # Generate the next question
    next_q = await tree_service.generate_next_question(session_id, llm_service)
    
    new_node_id = None
    if not next_q.get("is_complete"):
        new_node_id = tree_service.add_question(
            session_id, 
            next_q["question"], 
            options=next_q.get("options", [])
        )
    
    return {
        "success": True,
        "next_question": next_q,
        "node_id": new_node_id
    }

@router.post("/rewind")
async def rewind_session(request: Request, node_id: str = Form(...), user=Depends(get_user)):
    tree_service = request.app.state.tree_prompt_service
    session_id = request.session.get("prompt_tree_session_id")
    
    if not session_id:
        raise HTTPException(400, "No active session")
    
    tree_service.rewind_to(session_id, node_id)
    
    session = tree_service.get_session(session_id)
    return {"success": True, "session": session}

@router.post("/save")
async def save_prompt(request: Request, title: str = Form(...), user=Depends(get_user)):
    tree_service = request.app.state.tree_prompt_service
    session_id = request.session.get("prompt_tree_session_id")
    
    if not session_id:
        raise HTTPException(400, "No active session")
    
    prompt_text = tree_service.synthesize_prompt(session_id)
    
    # Save to prompts/ directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join([c if c.isalnum() else "_" for c in title])
    filename = f"prompt_{timestamp}_{safe_title}.md"
    filepath = os.path.join("prompts", filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(prompt_text)
    
    return {"success": True, "filename": filename, "prompt": prompt_text}
