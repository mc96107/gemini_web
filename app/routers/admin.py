from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional

import subprocess
import json
import re
import shutil
import os
from app.core import config
from app.services.pattern_sync_service import PatternSyncService
from app.models.agent import AgentModel

router = APIRouter()

async def get_user(request: Request):
    return request.session.get("user")

def run_gemini_mcp_command(args):
    cmd = [shutil.which(config.GEMINI_CMD) or config.GEMINI_CMD, "mcp"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"

@router.get("/admin/mcp")
async def list_mcp(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    output = run_gemini_mcp_command(["list"])
    servers = []
    lines = output.split("\n")
    for line in lines:
        line = line.strip()
        if not line or ":" not in line: continue
        
        # Match pattern like: ✓ web-inspector: npx -y mcp-web-inspector (stdio) - Connected
        # Or: ✗ browser: npx -y mcp-server-browser (stdio) - Disconnected
        # We make the prefix optional and the status optional
        match = re.search(r'([✓✗]?)\s*(.*?):\s*(.*?)\s*\((stdio|sse)\)(?:\s*-\s*(.*))?', line)
        if match:
            enabled_char = match.group(1)
            servers.append({
                "name": match.group(2).strip(),
                "command": match.group(3).strip(),
                "enabled": enabled_char != '✗', # Default to true if not specifically disabled
                "status": (match.group(5) or "Unknown").strip()
            })
    return servers

@router.post("/admin/mcp/add")
async def add_mcp(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    data = await request.json()
    name = data.get("name")
    command = data.get("command")
    args = data.get("args", [])
    
    if not name or not command:
        raise HTTPException(status_code=400, detail="Name and command are required")
    
    full_args = ["add", name, command] + (args if isinstance(args, list) else args.split())
    output = run_gemini_mcp_command(full_args)
    return {"success": "Error" not in output, "output": output}

@router.post("/admin/mcp/remove")
async def remove_mcp(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    data = await request.json()
    name = data.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    
    output = run_gemini_mcp_command(["remove", name])
    return {"success": "Error" not in output, "output": output}

@router.post("/admin/mcp/toggle")
async def toggle_mcp(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    data = await request.json()
    name = data.get("name")
    enabled = data.get("enabled")
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    
    cmd = "enable" if enabled else "disable"
    output = run_gemini_mcp_command([cmd, name])
    return {"success": "Error" not in output, "output": output}

@router.get("/admin/skills")
async def list_skills(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    skills_dir = os.path.join(os.getcwd(), ".agents", "skills")
    skills = []
    if os.path.exists(skills_dir):
        for f in os.listdir(skills_dir):
            if f.endswith(".md"):
                skills.append(f[:-3]) # Remove .md
    return sorted(skills)

@router.get("/admin/skills/{name}")
async def get_skill(request: Request, name: str, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    skill_path = os.path.join(os.getcwd(), ".agents", "skills", f"{name}.md")
    if not os.path.exists(skill_path):
        raise HTTPException(status_code=404, detail="Skill not found")
    
    with open(skill_path, "r", encoding="utf-8") as f:
        content = f.read()
    return {"name": name, "content": content}

@router.post("/admin/skills")
async def save_skill(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    data = await request.json()
    name = data.get("name")
    content = data.get("content")
    
    if not name or not content:
        raise HTTPException(status_code=400, detail="Name and content are required")
    
    # Sanitize name
    name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    
    skills_dir = os.path.join(os.getcwd(), ".agents", "skills")
    os.makedirs(skills_dir, exist_ok=True)
    
    skill_path = os.path.join(skills_dir, f"{name}.md")
    with open(skill_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    return {"success": True}

@router.delete("/admin/skills/{name}")
async def delete_skill(request: Request, name: str, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    skill_path = os.path.join(os.getcwd(), ".agents", "skills", f"{name}.md")
    if os.path.exists(skill_path):
        os.remove(skill_path)
        return {"success": True}
    return {"success": False, "error": "Skill not found"}

@router.post("/admin/patterns/sync")
async def sync_patterns(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    sync_service = PatternSyncService()
    try:
        count = await sync_service.sync_all()
        return {"success": True, "count": count}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await sync_service.close()

@router.post("/admin/system/restart-setup")
async def restart_setup(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    user_manager.clear_all_users()
    request.session.clear()
    return {"success": True}

@router.post("/admin/system/log-level")
async def set_log_level(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    data = await request.json()
    level = data.get("level", "NONE").upper()
    if level not in ["NONE", "INFO", "DEBUG"]:
        raise HTTPException(status_code=400, detail="Invalid log level")
    
    config.update_env("LOG_LEVEL", level)
    config.LOG_LEVEL = level
    return {"success": True}

@router.post("/admin/sessions/cleartags")
async def clear_all_tags(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    agent = request.app.state.agent
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        count = await agent.clear_all_session_tags()
        return {"success": True, "count": count}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/admin/settings")
async def get_settings(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    return config.get_all_global_settings()

@router.post("/admin/settings")
async def update_settings(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    data = await request.json()
    for key, value in data.items():
        config.update_global_setting(key, value)
    return {"success": True}

@router.get("/admin", response_class=HTMLResponse)
async def admin_db(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin": return RedirectResponse("/")
    return request.app.state.render("admin.html", request=request, users=user_manager.get_all_users(), log_level=config.LOG_LEVEL)

@router.post("/admin/user/add")
async def adm_add(request: Request, username: str = Form(...), password: str = Form(...), role: str = Form(...), user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) == "admin": user_manager.register_user(username, password, role=role)
    return RedirectResponse("/admin", status_code=303)

@router.post("/admin/user/remove")
async def adm_rem(request: Request, username: str = Form(...), user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) == "admin" and username != "admin": user_manager.remove_user(username)
    return {"success": True}

@router.post("/admin/user/toggle-pattern")
async def adm_tog_pat(request: Request, username: str = Form(...), disabled: str = Form(...), user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) == "admin":
        is_disabled = disabled.lower() == 'true'
        user_manager.set_pattern_disabled(username, is_disabled)
        return {"success": True}
    return {"success": False}

@router.post("/admin/user/toggle-role")
async def adm_tog_role(request: Request, username: str = Form(...), role: str = Form(...), user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) == "admin":
        if username == "admin" and role == "user":
            return {"success": False, "error": "Cannot demote primary admin."}
        if user_manager.update_role(username, role):
            return {"success": True}
    return {"success": False}

@router.post("/admin/user/update-password")
async def adm_upd(request: Request, username: str = Form(...), new_password: str = Form(...), user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) == "admin": user_manager.update_password(username, new_password)
    return RedirectResponse("/admin", status_code=303)

# Agent Management Routes

@router.get("/admin/agents")
async def list_agents(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    agent_manager = request.app.state.agent_manager
    agents = agent_manager.list_agents()
    return agents

@router.get("/admin/agents/{category}/{name}")
async def get_agent_details(request: Request, category: str, name: str, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    agent_manager = request.app.state.agent_manager
    agent = agent_manager.get_agent(category, name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.post("/admin/agents")
async def save_agent(request: Request, agent_data: AgentModel, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    agent_manager = request.app.state.agent_manager
    success = agent_manager.save_agent(agent_data)
    return {"success": success}

@router.get("/admin/agents/root")
async def get_root_agent(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    agent_manager = request.app.state.agent_manager
    agent = agent_manager.get_root_orchestrator()
    if not agent:
        agent_manager.initialize_root_orchestrator()
        agent = agent_manager.get_root_orchestrator()
    return agent

@router.post("/admin/agents/root")
async def save_root_agent(request: Request, agent_data: AgentModel, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    agent_manager = request.app.state.agent_manager
    success = agent_manager.save_root_orchestrator(agent_data)
    return {"success": success}

@router.delete("/admin/agents/{category}/{name}")
async def delete_agent(request: Request, category: str, name: str, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    agent_manager = request.app.state.agent_manager
    success = agent_manager.delete_agent(category, name)
    return {"success": success}

@router.post("/admin/agents/{category}/{name}/toggle-enabled")
async def toggle_agent_enabled(request: Request, category: str, name: str, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    data = await request.json()
    enabled = data.get("enabled", False)
    
    agent_manager = request.app.state.agent_manager
    success = agent_manager.set_agent_enabled(category, name, enabled)
    return {"success": success}

@router.get("/admin/agents/validate")
async def validate_orchestration(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    agent_manager = request.app.state.agent_manager
    warnings = agent_manager.validate_orchestration()
    return {"warnings": warnings}
