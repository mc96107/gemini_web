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
    has_more = False
    if active_session:
        initial_messages = await agent.get_session_messages(active_session['uuid'], limit=20)
        # If we got exactly 20, there might be more
        if len(initial_messages) == 20:
            has_more = True
    
    return request.app.state.render(
        "index.html", 
        request=request, 
        user=user, 
        is_admin=(user_manager.get_role(user) == "admin"),
        initial_messages=initial_messages,
        active_session=active_session,
        has_more=has_more
    )

@router.get("/sessions")
async def get_sess(request: Request, limit: Optional[int] = None, offset: int = 0, tags: Optional[str] = None, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    tag_list = tags.split(",") if tags else None
    return await agent.get_user_sessions(user, limit=limit, offset=offset, tags=tag_list)

@router.get("/sessions/search")
async def search_sess(request: Request, q: str = "", user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    return await agent.search_sessions(user, q)

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

@router.post("/sessions/{session_uuid}/pin")
async def pin_sess(session_uuid: str, request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    # Security: check if this session belongs to the user
    user_sessions = await agent.get_user_sessions(user)
    if not any(s['uuid'] == session_uuid for s in user_sessions):
        raise HTTPException(403, "Access denied")
    return {"pinned": agent.toggle_pin(user, session_uuid)}

@router.post("/sessions/{session_uuid}/title")
async def rename_sess(session_uuid: str, request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    data = await request.json()
    new_title = data.get("title")
    if not new_title:
        raise HTTPException(400, "Title is required")
    success = await agent.update_session_title(user, session_uuid, new_title)
    if not success:
        raise HTTPException(404, "Session not found")
    return {"success": True}

@router.get("/sessions/tags")
async def get_all_tags(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    return {"tags": agent.get_unique_tags(user)}

@router.post("/sessions/{session_uuid}/tags")
async def set_sess_tags(session_uuid: str, request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    data = await request.json()
    tags = data.get("tags", [])
    if not isinstance(tags, list):
        raise HTTPException(400, "Tags must be a list of strings")
    success = await agent.update_session_tags(user, session_uuid, tags)
    if not success:
        raise HTTPException(404, "Session not found")
    return {"success": True}

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

    # Stop any existing task for this user
    await agent.stop_chat(user)

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
        def log_sse(msg, level="DEBUG"):
            if config.LOG_LEVEL == "NONE":
                return
            if config.LOG_LEVEL == "INFO" and level == "DEBUG":
                return
            try:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                print(f"[{ts}] [{level}][SSE][{user}] {msg}")
            except: pass

        log_sse("Starting event_generator")
        try:
            stream = agent.generate_response_stream(user, message, model=m_override, file_path=fpath)
            it = stream.__aiter__()
            
            while True:
                # Create a task for the next chunk
                log_sse("Waiting for chunk (next_task)...")
                next_task = asyncio.create_task(it.__anext__())
                
                while True:
                    # Wait for next chunk or timeout
                    done, pending = await asyncio.wait([next_task], timeout=15.0)
                    
                    if next_task in done:
                        try:
                            chunk = next_task.result()
                            log_sse(f"Yielding chunk: {json.dumps(chunk)[:50]}...")
                            yield f"data: {json.dumps(chunk)}\n\n"
                            break # Go to next task
                        except StopAsyncIteration:
                            log_sse("Stream finished (StopAsyncIteration)")
                            return # Exit event_generator
                        except asyncio.CancelledError:
                            log_sse("Stream cancelled (CancelledError)")
                            stop_msg = json.dumps({'type': 'message', 'role': 'assistant', 'content': '\n\n[Response stopped by user.]'})
                            yield f"data: {stop_msg}\n\n"
                            return
                        except Exception as e:
                            log_sse(f"Error in stream result: {str(e)}")
                            err_msg = json.dumps({'type': 'error', 'content': str(e)})
                            yield f"data: {err_msg}\n\n"
                            return
                    else:
                        # Timeout happened, send heartbeat and keep waiting for the SAME task
                        log_sse("Sending SSE heartbeat...")
                        yield ": heartbeat\n\n"
                        # Continue inner while loop to keep waiting for next_task
        except asyncio.CancelledError:
            log_sse("event_generator task cancelled")
            stop_msg = json.dumps({'type': 'message', 'role': 'assistant', 'content': '\n\n[Response stopped by user.]'})
            yield f"data: {stop_msg}\n\n"
        except Exception as e:
            log_sse(f"Fatal error in event_generator: {str(e)}")
            err_msg = json.dumps({'type': 'error', 'content': str(e)})
            yield f"data: {err_msg}\n\n"
        
        log_sse("Yielding [DONE]")
        yield "data: [DONE]\n\n"
    
    async def wrapped_generator():
        # Capture the current task
        current_task = asyncio.current_task()
        agent.active_tasks[user] = current_task
        try:
            async for item in event_generator():
                yield item
        finally:
            if agent.active_tasks.get(user) == current_task:
                del agent.active_tasks[user]

    return StreamingResponse(wrapped_generator(), media_type="text/event-stream")

@router.post("/stop")
async def stop_chat(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    success = await agent.stop_chat(user)
    return {"success": success}

@router.post("/reset")
async def reset(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    return {"response": await agent.reset_chat(user)}
