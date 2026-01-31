from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import Optional, List
import os
import uuid
from datetime import datetime
from app.core import config

router = APIRouter()

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
    
    # Get active chat context if available
    chat_context = None
    try:
        if user in llm_service.user_data:
            active_uuid = llm_service.user_data[user].get("active_session")
            if active_uuid:
                # Fetch last 10 messages from active session
                msg_data = await llm_service.get_session_messages(active_uuid, limit=10)
                messages = msg_data.get("messages", [])
                if messages:
                    chat_context = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in messages])
    except Exception as e:
        print(f"Error fetching chat context: {e}")

    session_id = tree_service.create_session(context=chat_context)
    request.session["prompt_tree_session_id"] = session_id
    
    # Generate the first question
    next_q = await tree_service.generate_next_question(session_id, llm_service)
    
    node_id = tree_service.add_question(
        session_id, 
        next_q["question"], 
        options=next_q.get("options", []),
        allow_multiple=next_q.get("allow_multiple", False)
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
    
    # Check if we were already in a 'complete' state (waiting for user to agree to synth)
    # If the user says 'yes' to the completion question, we don't need a next question.
    if answer.lower() in ["yes", "y", "sure", "ok", "proceed", "show me"]:
        # We can just return success and let the frontend show the Save button
        # which is rendered based on node.answer being present.
        return {
            "success": True,
            "next_question": {
                "question": "I have gathered enough information. Click 'Save Final Prompt' to see the result.",
                "options": [],
                "reasoning": "User agreed to finalize.",
                "is_complete": True
            },
            "node_id": None
        }

    # Generate the next question
    next_q = await tree_service.generate_next_question(session_id, llm_service)
    
    new_node_id = None
    if not next_q.get("is_complete"):
        new_node_id = tree_service.add_question(
            session_id, 
            next_q["question"], 
            options=next_q.get("options", []),
            allow_multiple=next_q.get("allow_multiple", False)
        )
    
    return {
        "success": True,
        "next_question": next_q,
        "node_id": new_node_id
    }

@router.post("/edit")
async def edit_answer(request: Request, node_id: str = Form(...), answer: str = Form(...), user=Depends(get_user)):
    tree_service = request.app.state.tree_prompt_service
    session_id = request.session.get("prompt_tree_session_id")
    
    if not session_id:
        raise HTTPException(400, "No active session")
    
    tree_service.answer_question(session_id, node_id, answer)
    
    return {"success": True}

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
    llm_service = request.app.state.agent
    session_id = request.session.get("prompt_tree_session_id")
    
    if not session_id:
        raise HTTPException(400, "No active session")
    
    prompt_text = await tree_service.synthesize_prompt(session_id, llm_service)
    
    # Save to prompts/ directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join([c if c.isalnum() else "_" for c in title])
    filename = f"prompt_{timestamp}_{safe_title}.md"
    filepath = os.path.join("prompts", filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(prompt_text)
    
    return {"success": True, "filename": filename, "prompt": prompt_text}

@router.get("/prompts/{filename}")
async def get_prompt_content(filename: str, user=Depends(get_user)):
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(400, "Invalid filename")
        
    filepath = os.path.join("prompts", filename)
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            return {"success": True, "content": content}
        except Exception as e:
            raise HTTPException(500, f"Failed to read file: {e}")
    else:
        raise HTTPException(404, "Prompt not found")

@router.delete("/prompts/{filename}")
async def delete_prompt(filename: str, request: Request, user=Depends(get_user)):
    # Security check: filename should be simple to avoid path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(400, "Invalid filename")
    
    filepath = os.path.join("prompts", filename)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            return {"success": True}
        except Exception as e:
            raise HTTPException(500, f"Failed to delete file: {e}")
    else:
        raise HTTPException(404, "Prompt not found")

@router.put("/prompts/{filename}")
async def update_prompt(filename: str, request: Request, content: str = Form(...), user=Depends(get_user)):
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(400, "Invalid filename")
        
    filepath = os.path.join("prompts", filename)
    if os.path.exists(filepath):
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            return {"success": True}
        except Exception as e:
            raise HTTPException(500, f"Failed to update file: {e}")
    else:
        raise HTTPException(404, "Prompt not found")
