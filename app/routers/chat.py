from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException, Depends
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    StreamingResponse,
)
from typing import Optional
import os
import shutil
import json
import asyncio
import re
import uuid
from datetime import datetime
from app.core import config
from app.services.skill_service import SkillService

router = APIRouter()


async def get_user(request: Request):
    return request.session.get("user")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    agent = request.app.state.agent
    if not user_manager.has_users():
        return RedirectResponse(str(request.url_for("setup_pg")), status_code=303)
    if not user:
        return RedirectResponse(str(request.url_for("login_pg")), status_code=303)

    # Pre-load active session and initial messages for faster start
    sessions_data = await agent.get_user_sessions(user)
    all_sessions_list = sessions_data.get("pinned", []) + sessions_data.get(
        "history", []
    )
    active_session = next((s for s in all_sessions_list if s.get("active")), None)
    initial_messages = []
    has_more = False
    total_messages = 0
    if active_session:
        msg_data = await agent.get_session_messages(active_session["uuid"], limit=20)
        if isinstance(msg_data, dict):
            initial_messages = msg_data.get("messages", [])
            total_messages = msg_data.get("total", 0)
        else:
            # Fallback for unexpected return type
            initial_messages = msg_data
            total_messages = len(msg_data)
        # If the total messages in the session exceeds 20, there are more older messages
        if total_messages > 20:
            has_more = True

    user_settings = agent.get_user_settings(user)

    return request.app.state.render(
        "index.html",
        request=request,
        user=user,
        is_admin=(user_manager.get_role(user) == "admin"),
        initial_messages=initial_messages,
        active_session=active_session,
        has_more=has_more,
        total_messages=total_messages,
        user_settings=user_settings,
    )


@router.get("/settings")
async def get_settings(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    return agent.get_user_settings(user)


@router.post("/settings")
async def update_settings(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    data = await request.json()
    agent.update_user_settings(user, data)
    return {"success": True}


@router.get("/sessions")
async def get_sess(
    request: Request,
    limit: Optional[int] = None,
    offset: int = 0,
    tags: Optional[str] = None,
    user=Depends(get_user),
):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    tag_list = tags.split(",") if tags else None
    return await agent.get_user_sessions(
        user, limit=limit, offset=offset, tags=tag_list
    )


@router.get("/sessions/search")
async def search_sess(request: Request, q: str = "", user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    return await agent.search_sessions(user, q)


@router.get("/sessions/{session_uuid}/messages")
async def get_sess_messages(
    session_uuid: str,
    request: Request,
    limit: Optional[int] = None,
    offset: int = 0,
    user=Depends(get_user),
):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    # Security: check if this session belongs to the user
    if not agent.is_user_session(user, session_uuid):
        raise HTTPException(403, "Access denied")
    return await agent.get_session_messages(session_uuid, limit=limit, offset=offset)


@router.post("/sessions/switch")
async def sw_sess(
    request: Request, session_uuid: str = Form(...), user=Depends(get_user)
):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    return {"success": await agent.switch_session(user, session_uuid)}


@router.post("/sessions/new")
async def nw_sess(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    await agent.new_session(user)
    return {"success": True}


@router.post("/sessions/delete")
async def dl_sess(
    request: Request, session_uuid: str = Form(...), user=Depends(get_user)
):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    return {"success": await agent.delete_specific_session(user, session_uuid)}


@router.post("/sessions/{session_uuid}/share")
async def share_sess(session_uuid: str, request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    user_manager = request.app.state.user_manager
    if not user:
        raise HTTPException(401)

    # 1. Verify session ownership (or participation)
    if not agent.is_user_session(user, session_uuid):
        raise HTTPException(403, "Access denied")

    data = await request.json()
    target_username = data.get("username")
    if not target_username:
        raise HTTPException(400, "Username is required")

    # 2. Call agent.share_session
    success = await agent.share_session(
        user, session_uuid, target_username, user_manager
    )
    return {"success": success}


@router.post("/sessions/{session_uuid}/pin")
async def pin_sess(session_uuid: str, request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    # Security: check if this session belongs to the user
    if not agent.is_user_session(user, session_uuid):
        raise HTTPException(403, "Access denied")
    return {"pinned": agent.toggle_pin(user, session_uuid)}


@router.post("/sessions/{session_uuid}/clone")
async def clone_sess(session_uuid: str, request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    data = await request.json()
    message_index = data.get("message_index")
    if message_index is None:
        raise HTTPException(400, "message_index is required")

    new_uuid = await agent.clone_session(user, session_uuid, message_index)
    if not new_uuid:
        raise HTTPException(500, "Failed to clone session")
    return {"success": True, "new_uuid": new_uuid}


@router.get("/sessions/{session_uuid}/forks")
async def get_forks(session_uuid: str, request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    return {"forks": agent.get_session_forks(user, session_uuid)}


@router.get("/sessions/fork-graph")
async def get_fork_graph(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    return {"graph": agent.get_fork_graph(user)}


@router.post("/sessions/{session_uuid}/title")
async def rename_sess(session_uuid: str, request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    data = await request.json()
    new_title = data.get("title")
    if not new_title:
        raise HTTPException(400, "Title is required")

    # Update and sync forks
    await agent.sync_session_updates(user, session_uuid, title=new_title)
    return {"success": True}


@router.get("/sessions/tags")
async def get_all_tags(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    return {"tags": agent.get_unique_tags(user)}


@router.post("/sessions/{session_uuid}/tags")
async def set_sess_tags(session_uuid: str, request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    data = await request.json()
    tags = data.get("tags", [])
    if not isinstance(tags, list):
        raise HTTPException(400, "Tags must be a list of strings")

    # Update and sync forks
    await agent.sync_session_updates(user, session_uuid, tags=tags)
    return {"success": True}


@router.get("/sessions/{session_uuid}/tools")
async def get_sess_tools(session_uuid: str, request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    if session_uuid != "pending":
        if not agent.is_user_session(user, session_uuid):
            raise HTTPException(403, "Access denied")
    return {"tools": agent.get_session_tools(user, session_uuid)}


@router.post("/sessions/{session_uuid}/tools")
async def set_sess_tools(
    session_uuid: str, request: Request, data: dict, user=Depends(get_user)
):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    if session_uuid != "pending":
        if not agent.is_user_session(user, session_uuid):
            raise HTTPException(403, "Access denied")
    tools = data.get("tools", [])
    agent.set_session_tools(user, session_uuid, tools)
    return {"success": True}


async def get_effective_workspace(agent, user):
    active_session = agent.user_data.get(user, {}).get("active_session")
    if active_session:
        return agent.get_session_workspace(user, active_session)
    return agent.get_user_settings(user).get("default_workspace", agent.WORKSPACE_ROOT)


@router.get("/patterns")
async def get_pats(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)

    workspace = await get_effective_workspace(agent, user)

    from app.core.patterns import PATTERNS
    import re

    expl = PATTERNS.get("__explanations__", "")
    res = []

    # Custom Prompts from Workspace
    prompts_dir = os.path.join(workspace, "prompts")
    if os.path.exists(prompts_dir):
        for filename in os.listdir(prompts_dir):
            if filename.endswith(".md") or filename.endswith(".txt"):
                res.append(
                    {
                        "name": filename,
                        "description": f"User generated prompt in {os.path.basename(workspace)}",
                        "type": "user",
                    }
                )

    # Skills from Workspace (.opencode/skills)
    skills_dir = os.path.join(workspace, ".opencode", "skills")
    if os.path.exists(skills_dir):
        for skill_name in os.listdir(skills_dir):
            skill_path = os.path.join(skills_dir, skill_name)
            if os.path.isdir(skill_path):
                # Look for SKILL.md
                skill_md = os.path.join(skill_path, "SKILL.md")
                description = "Workspace Skill"
                if os.path.exists(skill_md):
                    try:
                        with open(skill_md, "r", encoding="utf-8") as f:
                            first_line = f.readline().strip()
                            if first_line.startswith("#"):
                                description = first_line.lstrip("#").strip()
                    except:
                        pass

                res.append(
                    {
                        "name": f"skill:{skill_name}",
                        "description": description,
                        "type": "skill",
                    }
                )

    for line in expl.splitlines():
        m = re.match(
            r"^\d+\.\s+\*\*(?P<name>.*?)\*\*: (?P<description>.*)", line.strip()
        )
        if m:
            item = m.groupdict()
            item["type"] = "system"
            res.append(item)
        elif "suggest_pattern" in line:
            m = re.search(
                r"\*\*(?P<name>suggest_pattern)\*\*, (?P<description>.*)", line
            )
            if m:
                item = m.groupdict()
                item["type"] = "system"
                res.append(item)

    if not res:
        res = [
            {"name": k, "description": "", "type": "system"}
            for k in agent.list_patterns()
        ]

    return res


@router.get("/prompts/{filename}")
async def get_prompt_content(filename: str, request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(400, "Invalid filename")

    workspace = await get_effective_workspace(agent, user)
    filepath = os.path.join(workspace, "prompts", filename)
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
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    # Security check: filename should be simple to avoid path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(400, "Invalid filename")

    workspace = await get_effective_workspace(agent, user)
    filepath = os.path.join(workspace, "prompts", filename)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            return {"success": True}
        except Exception as e:
            raise HTTPException(500, f"Failed to delete file: {e}")
    else:
        raise HTTPException(404, "Prompt not found")


@router.put("/prompts/{filename}")
async def update_prompt(filename: str, request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(400, "Invalid filename")

    data = await request.form()
    content = str(data.get("content") or "")
    if not content:
        raise HTTPException(400, "Content is required")

    workspace = await get_effective_workspace(agent, user)
    filepath = os.path.join(workspace, "prompts", filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    if not os.path.exists(filepath):
        raise HTTPException(404, "Prompt not found")

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True}
    except Exception as e:
        raise HTTPException(500, f"Failed to update file: {e}")


@router.post("/prompts/new")
async def create_prompt(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)

    data = await request.form()
    title = str(data.get("title") or "New Prompt")
    content = str(data.get("content") or "")

    # Save to prompts/ directory
    workspace = await get_effective_workspace(agent, user)
    prompts_dir = os.path.join(workspace, "prompts")
    os.makedirs(prompts_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join([c if c.isalnum() else "_" for c in title])
    filename = f"prompt_{timestamp}_{safe_title}.md"
    filepath = os.path.join(prompts_dir, filename)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "filename": filename}
    except Exception as e:
        raise HTTPException(500, f"Failed to create file: {e}")


@router.post("/chat")
async def chat(
    request: Request,
    message: str = Form(...),
    file: Optional[list[UploadFile]] = File(None),
    model: Optional[str] = Form(None),
    agent_name: Optional[str] = Form(None),
    plan_mode: Optional[str] = Form(None),
    user=Depends(get_user),
):
    agent = request.app.state.agent
    UPLOAD_DIR = request.app.state.UPLOAD_DIR
    print(f"DEBUG: /chat request received. User: {user}, Model: {model}, Agent: {agent_name}, Plan: {plan_mode}")
    if not user:
        raise HTTPException(401)

    file_paths = []
    if file:
        conversion_service = request.app.state.conversion_service
        pdf_service = request.app.state.pdf_service
        for f_upload in file:
            if f_upload.filename:
                # Sanitize filename to ensure ASCII-only for CLI compatibility
                base_name = os.path.basename(f_upload.filename)
                safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", base_name)

                # Fallback if sanitization leaves it empty
                if not safe_name or safe_name.replace("_", "") == "":
                    ext = os.path.splitext(base_name)[1]
                    safe_name = f"upload_{uuid.uuid4().hex}{ext}"

                fpath = os.path.join(UPLOAD_DIR, safe_name)
                with open(fpath, "wb") as f:
                    shutil.copyfileobj(f_upload.file, f)

                # Perform conversion if needed
                if fpath.lower().endswith((".docx", ".xlsx")):
                    try:
                        old_fpath = fpath
                        fpath = conversion_service.convert_to_markdown(fpath)
                        import logging

                        logging.getLogger(__name__).info(
                            f"Converted {old_fpath} to {fpath}"
                        )
                    except Exception as e:
                        # Fallback to original file on error
                        import logging
                        from app.services.conversion_service import (
                            PandocMissingError,
                            ConversionServiceError,
                        )

                        log = logging.getLogger(__name__)
                        if isinstance(e, PandocMissingError):
                            log.warning(f"Pandoc missing, using original file: {e}")
                        else:
                            log.error(
                                f"Conversion failed, falling back to original: {e}"
                            )
                elif fpath.lower().endswith(".pdf"):
                    try:
                        # Compress PDF
                        compressed_path = os.path.join(
                            UPLOAD_DIR, f"compressed_{os.path.basename(fpath)}"
                        )
                        # We use a distinct name for output to avoid issues during processing
                        fpath = await pdf_service.compress_pdf(fpath, compressed_path)
                    except Exception as e:
                        import logging

                        logging.getLogger(__name__).error(
                            f"PDF compression failed: {e}"
                        )

                file_paths.append(os.path.relpath(fpath))

    # Handle model selection
    m_override = None
    if model:
        if model == "pro":
            m_override = "google/antigravity-gemini-3.1-pro"
        else:
            m_override = model

    # Stop any existing task for this user
    await agent.stop_chat(user)

    msg = message.strip()
    is_plan = plan_mode == "true"
    if msg.startswith("/"):
        parts = msg.split(maxsplit=2)
        cmd = parts[0].lower()
        if cmd in ["/reset", "/clear"]:
            return {"response": await agent.reset_chat(user)}
        if cmd == "/pro":
            m_override = "google/antigravity-gemini-3.1-pro"
            if len(parts) > 1:
                return {
                    "response": await agent.generate_response(
                        user,
                        parts[1] + (f" {parts[2]}" if len(parts) > 2 else ""),
                        model=m_override,
                        file_paths=file_paths,
                    )
                }
            return {"response": "Model set to Pro."}
        if cmd == "/plan":
            is_plan = True
            if len(parts) > 1:
                message = parts[1] + (f" {parts[2]}" if len(parts) > 2 else "")
            else:
                return {
                    "response": "Plan mode requires a prompt. Usage: /plan <your prompt>"
                }
        if cmd == "/p" or cmd == "/pattern":
            if len(parts) >= 2:
                return {
                    "response": await agent.apply_pattern(
                        user,
                        parts[1],
                        parts[2] if len(parts) > 2 else "",
                        model=m_override,
                        file_paths=file_paths,
                    )
                }
        if cmd == "/yolo":
            agent.yolo_mode = not agent.yolo_mode
            return {
                "response": f"YOLO Mode {'ENABLED' if agent.yolo_mode else 'DISABLED'}."
            }
        if cmd == "/help":
            return {
                "response": "Commands: /reset, /pro, /plan, /p [pattern], /yolo, /help"
            }

    # Skill Detection & Injection
    try:
        workspace = await get_effective_workspace(agent, user)
        skill_service = SkillService(workspace)  # Create fresh instance per request
        detected_skill = skill_service.detect_skill(msg)
        
        if detected_skill:
            print(f"[SKILL] Detected skill: {detected_skill.name}")
            
            script_output = None
            if detected_skill.execution_type == "script":
                script_output = await skill_service.execute_skill_script(
                    detected_skill, msg, user
                )
                print(f"[SKILL] Script output: {script_output[:200]}...")
            
            message = skill_service.inject_context(
                detected_skill, msg, script_output
            )
            print(f"[SKILL] Context injected, new message length: {len(message)}")
    except Exception as e:
        print(f"[SKILL] Error in skill detection: {e}")

    async def event_generator():
        def log_sse(msg, level="DEBUG"):
            if config.LOG_LEVEL == "NONE":
                return
            if config.LOG_LEVEL == "INFO" and level == "DEBUG":
                return
            try:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                print(f"[{ts}] [{level}][SSE][{user}] {msg}")
            except:
                pass

        log_sse("Starting event_generator")
        try:
            stream = agent.generate_response_stream(
                user,
                message,
                model=m_override,
                agent_name=agent_name,
                file_paths=file_paths,
                plan_mode=is_plan,
            )
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
                            log_sse(f"Yielding chunk: {json.dumps(chunk)[:100]}...")
                            yield f"data: {json.dumps(chunk)}\n\n"
                            break  # Go to next task
                        except StopAsyncIteration:
                            log_sse("Stream finished (StopAsyncIteration)")
                            return  # Exit event_generator
                        except asyncio.CancelledError:
                            log_sse("Stream cancelled (CancelledError)")
                            stop_msg = json.dumps(
                                {
                                    "type": "message",
                                    "role": "assistant",
                                    "content": "\n\n[Response stopped by user.]",
                                }
                            )
                            yield f"data: {stop_msg}\n\n"
                            return
                        except Exception as e:
                            import traceback
                            error_trace = traceback.format_exc()
                            log_sse(f"Error in stream result: {str(e)}\n{error_trace}", level="ERROR")
                            err_msg = json.dumps({"type": "error", "content": f"Stream error: {str(e)}"})
                            yield f"data: {err_msg}\n\n"
                            return
                    else:
                        # Timeout happened, send heartbeat and keep waiting for the SAME task
                        log_sse("Sending SSE heartbeat...")
                        yield ": heartbeat\n\n"
                        # Continue inner while loop to keep waiting for next_task
        except asyncio.CancelledError:
            log_sse("event_generator task cancelled")
            stop_msg = json.dumps(
                {
                    "type": "message",
                    "role": "assistant",
                    "content": "\n\n[Response stopped by user.]",
                }
            )
            yield f"data: {stop_msg}\n\n"
        except Exception as e:
            log_sse(f"Fatal error in event_generator: {str(e)}")
            err_msg = json.dumps({"type": "error", "content": str(e)})
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
    if not user:
        raise HTTPException(401)
    success = await agent.stop_chat(user)
    return {"success": success}


@router.post("/reset")
async def reset(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    return {"response": await agent.reset_chat(user)}


@router.get("/workspaces")
async def get_workspaces(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    from app.services.llm_service import WORKSPACE_ROOT

    return {"workspaces": agent.get_available_workspaces(), "root": WORKSPACE_ROOT}


@router.post("/session/workspace")
async def update_session_workspace(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    data = await request.json()
    session_uuid = data.get("uuid")
    path = data.get("path")
    if not session_uuid or not path:
        raise HTTPException(400, detail="Missing uuid or path")

    success = agent.update_session_workspace(user, session_uuid, path)
    return {"success": success}


@router.get("/session/workspace/{uuid}")
async def get_session_workspace_path(
    uuid: str, request: Request, user=Depends(get_user)
):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    return {"path": agent.get_session_workspace(user, uuid)}


@router.get("/session/git-status")
async def get_git_status(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    
    workspace = await get_effective_workspace(agent, user)
    return await agent.get_git_status(workspace)


@router.get("/models")
async def get_models(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    return {"models": await agent.get_available_models()}


@router.get("/agents")
async def get_agents(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    return {"agents": await agent.get_available_agents()}
