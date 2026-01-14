from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from typing import Optional
import os
import shutil
import json

router = APIRouter()

async def get_user(request: Request):
    return request.session.get("user")

@router.get("/", response_class=HTMLResponse)
async def index(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    agent = request.app.state.agent
    if not user_manager.has_users():
        return RedirectResponse(str(request.url_for("setup_pg")), status_code=303)
    if not user: return RedirectResponse(str(request.url_for("login_pg")), status_code=303)
    
    # Pre-load active session and initial messages for faster start
    sessions = await agent.get_user_sessions(user)
    active_session = next((s for s in sessions if s.get('active')), None)
    initial_messages = []
    if active_session:
        initial_messages = await agent.get_session_messages(active_session['uuid'], limit=20)
    
    return request.app.state.render(
        "index.html", 
        request=request, 
        user=user, 
        is_admin=(user_manager.get_role(user) == "admin"),
        initial_messages=initial_messages,
        active_session=active_session
    )

@router.get("/sessions")
async def get_sess(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    return await agent.get_user_sessions(user)

@router.get("/sessions/{session_uuid}/messages")
async def get_sess_messages(session_uuid: str, request: Request, limit: Optional[int] = None, offset: int = 0, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    # Security: check if this session belongs to the user
    user_sessions = await agent.get_user_sessions(user)
    if not any(s['uuid'] == session_uuid for s in user_sessions):
        raise HTTPException(403, "Access denied")
    return await agent.get_session_messages(session_uuid, limit=limit, offset=offset)

@router.post("/sessions/switch")
async def sw_sess(request: Request, session_uuid: str = Form(...), user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    return {"success": await agent.switch_session(user, session_uuid)}

@router.post("/sessions/new")
async def nw_sess(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    await agent.new_session(user)
    return {"success": True}

@router.post("/sessions/delete")
async def dl_sess(request: Request, session_uuid: str = Form(...), user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    return {"success": await agent.delete_specific_session(user, session_uuid)}

@router.get("/sessions/{session_uuid}/tools")
async def get_sess_tools(session_uuid: str, request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    if session_uuid != "pending":
        user_sessions = await agent.get_user_sessions(user)
        if not any(s['uuid'] == session_uuid for s in user_sessions):
            raise HTTPException(403, "Access denied")
    return {"tools": agent.get_session_tools(user, session_uuid)}

@router.post("/sessions/{session_uuid}/tools")
async def set_sess_tools(session_uuid: str, request: Request, data: dict, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    if session_uuid != "pending":
        user_sessions = await agent.get_user_sessions(user)
        if not any(s['uuid'] == session_uuid for s in user_sessions):
            raise HTTPException(403, "Access denied")
    tools = data.get("tools", [])
    agent.set_session_tools(user, session_uuid, tools)
    return {"success": True}

@router.get("/patterns")
async def get_pats(request: Request):
    agent = request.app.state.agent
    # This logic was a bit involved in original_app.py
    # I'll simplify or copy it.
    from app.core.patterns import PATTERNS
    import re
    expl = PATTERNS.get("__explanations__", "")
    res = []
    for line in expl.splitlines():
        m = re.match(r"^\d+\.\s+\*\*(?P<name>.*?)\*\*: (?P<description>.*)", line.strip())
        if m: res.append(m.groupdict())
        elif "suggest_pattern" in line:
            m = re.search(r"\*\*(?P<name>suggest_pattern)\*\*, (?P<description>.*)", line)
            if m: res.append(m.groupdict())
    if not res: res = [{"name": k, "description": ""} for k in agent.list_patterns()]
    return res

@router.post("/chat")
async def chat(request: Request, message: str = Form(...), file: Optional[UploadFile] = File(None), model: Optional[str] = Form(None), user=Depends(get_user)):
    agent = request.app.state.agent
    UPLOAD_DIR = request.app.state.UPLOAD_DIR
    if not user: raise HTTPException(401)
    fpath = None
    if file and file.filename:
        fpath = os.path.join(UPLOAD_DIR, os.path.basename(file.filename))
        with open(fpath, "wb") as f: shutil.copyfileobj(file.file, f)
        fpath = os.path.relpath(fpath)
    
    # Handle model selection
    m_override = None
    if model:
        if model == "pro":
            m_override = "gemini-3-pro-preview"
        else:
            m_override = model

    msg = message.strip()
    if msg.startswith("/"):
        parts = msg.split(maxsplit=2)
        cmd = parts[0].lower()
        if cmd in ["/reset", "/clear"]: return {"response": await agent.reset_chat(user)}
        if cmd == "/pro":
            m_override = "gemini-3-pro-preview"
            if len(parts) > 1: return {"response": await agent.generate_response(user, parts[1] + (f" {parts[2]}" if len(parts) > 2 else ""), model=m_override, file_path=fpath)}
            return {"response": "Model set to Pro."}
        if cmd == "/p" or cmd == "/pattern":
            if len(parts) >= 2: return {"response": await agent.apply_pattern(user, parts[1], parts[2] if len(parts) > 2 else "", model=m_override, file_path=fpath)}
        if cmd == "/yolo":
            agent.yolo_mode = not agent.yolo_mode
            return {"response": f"YOLO Mode {'ENABLED' if agent.yolo_mode else 'DISABLED'}."}
        if cmd == "/help": return {"response": "Commands: /reset, /pro, /p [pattern], /yolo, /help"}
    
    async def event_generator():
        async for chunk in agent.generate_response_stream(user, message, model=m_override, file_path=fpath):
            yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/reset")
async def reset(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    return {"response": await agent.reset_chat(user)}
