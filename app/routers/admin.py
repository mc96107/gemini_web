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
from app.routers.chat import get_effective_workspace

router = APIRouter()


async def get_user(request: Request):
    return request.session.get("user")


def run_opencode_mcp_command(args):
    cmd = [shutil.which(config.OPENCODE_CMD) or config.OPENCODE_CMD, "mcp"] + args
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

    output = run_opencode_mcp_command(["list"])
    servers = []
    lines = output.split("\n")
    for line in lines:
        line = line.strip()
        # Adapt parsing to opencode list output if needed
        # For now, let's see if the old regex still works or needs tweak
        if not line or ":" not in line:
            continue

        match = re.search(
            r"([✓✗]?)\s*(.*?):\s*(.*?)\s*\((stdio|sse)\)(?:\s*-\s*(.*))?", line
        )
        if match:
            enabled_char = match.group(1)
            servers.append(
                {
                    "name": match.group(2).strip(),
                    "command": match.group(3).strip(),
                    "enabled": enabled_char != "✗",
                    "status": (match.group(5) or "Unknown").strip(),
                }
            )
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

    full_args = ["add", name, command] + (
        args if isinstance(args, list) else args.split()
    )
    output = run_opencode_mcp_command(full_args)
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

    output = run_opencode_mcp_command(["remove", name])
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
    output = run_opencode_mcp_command([cmd, name])
    return {"success": "Error" not in output, "output": output}


# Agent Management Routes


@router.get("/admin/agents")
async def list_agents(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    agent_manager = request.app.state.agent_manager
    agent = request.app.state.agent
    workspace = await get_effective_workspace(agent, user)
    agents = agent_manager.list_agents(project_root=workspace)
    return agents


@router.get("/admin/agents/{category}/{name}")
async def get_agent_details(
    request: Request, category: str, name: str, user=Depends(get_user)
):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    agent_manager = request.app.state.agent_manager
    agent = request.app.state.agent
    workspace = await get_effective_workspace(agent, user)
    agent_data = agent_manager.get_agent(category, name, project_root=workspace)
    if not agent_data:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent_data


@router.post("/admin/agents")
async def save_agent(request: Request, agent_data: AgentModel, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    agent_manager = request.app.state.agent_manager
    agent = request.app.state.agent
    workspace = await get_effective_workspace(agent, user)
    success = agent_manager.save_agent(agent_data, project_root=workspace)
    return {"success": success}


@router.get("/admin/agents/root")
async def get_root_agent(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    agent_manager = request.app.state.agent_manager
    agent = request.app.state.agent
    workspace = await get_effective_workspace(agent, user)
    agent_data = agent_manager.get_root_orchestrator(project_root=workspace)
    if not agent_data:
        agent_manager.initialize_root_orchestrator(project_root=workspace)
        agent_data = agent_manager.get_root_orchestrator(project_root=workspace)
    return agent_data


@router.post("/admin/agents/root")
async def save_root_agent(
    request: Request, agent_data: AgentModel, user=Depends(get_user)
):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    agent_manager = request.app.state.agent_manager
    agent = request.app.state.agent
    workspace = await get_effective_workspace(agent, user)
    success = agent_manager.save_root_orchestrator(agent_data, project_root=workspace)
    return {"success": success}


@router.delete("/admin/agents/{category}/{name}")
async def delete_agent(
    request: Request, category: str, name: str, user=Depends(get_user)
):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    agent_manager = request.app.state.agent_manager
    agent = request.app.state.agent
    workspace = await get_effective_workspace(agent, user)
    success = agent_manager.delete_agent(category, name, project_root=workspace)
    return {"success": success}


@router.post("/admin/agents/{category}/{name}/toggle-enabled")
async def toggle_agent_enabled(
    request: Request, category: str, name: str, user=Depends(get_user)
):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    data = await request.json()
    enabled = data.get("enabled", False)

    agent_manager = request.app.state.agent_manager
    agent = request.app.state.agent
    workspace = await get_effective_workspace(agent, user)
    success = agent_manager.set_agent_enabled(
        category, name, enabled, project_root=workspace
    )
    return {"success": success}


@router.get("/admin/agents/validate")
async def validate_orchestration(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    agent_manager = request.app.state.agent_manager
    agent = request.app.state.agent
    workspace = await get_effective_workspace(agent, user)
    warnings = agent_manager.validate_orchestration(project_root=workspace)
    return {"warnings": warnings}


@router.get("/admin/skills")
async def list_skills(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    agent = request.app.state.agent
    workspace = await get_effective_workspace(agent, user)
    skills_dir = os.path.join(workspace, ".opencode", "skills")

    skills = []
    if os.path.exists(skills_dir):
        for name in os.listdir(skills_dir):
            if os.path.isdir(os.path.join(skills_dir, name)):
                skills.append(name)
    return sorted(skills)


@router.get("/admin/skills/{name}")
async def get_skill(name: str, request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    agent = request.app.state.agent
    workspace = await get_effective_workspace(agent, user)
    skill_md = os.path.join(workspace, ".opencode", "skills", name, "SKILL.md")

    if os.path.exists(skill_md):
        with open(skill_md, "r", encoding="utf-8") as f:
            content = f.read()

        # Try to extract description
        description = ""
        first_line = content.splitlines()[0] if content else ""
        if first_line.startswith("#"):
            description = first_line.lstrip("#").strip()

        return {"name": name, "content": content, "description": description}
    else:
        raise HTTPException(status_code=404, detail="Skill not found")


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

    agent = request.app.state.agent
    workspace = await get_effective_workspace(agent, user)
    skill_dir = os.path.join(workspace, ".opencode", "skills", name)
    os.makedirs(skill_dir, exist_ok=True)

    with open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(content)

    return {"success": True}


@router.delete("/admin/skills/{name}")
async def delete_skill(name: str, request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    agent = request.app.state.agent
    workspace = await get_effective_workspace(agent, user)
    skill_dir = os.path.join(workspace, ".opencode", "skills", name)

    if os.path.exists(skill_dir):
        shutil.rmtree(skill_dir)
        return {"success": True}
    else:
        raise HTTPException(status_code=404, detail="Skill not found")


@router.post("/admin/patterns/sync")
async def sync_patterns(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    service = PatternSyncService()
    try:
        count = await service.sync_all()
        return {"success": True, "count": count}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await service.close()


@router.post("/admin/tags/clear")
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
    if user_manager.get_role(user) != "admin":
        return RedirectResponse("/")
    return request.app.state.render(
        "admin.html",
        request=request,
        user=user,
        users=user_manager.get_all_users(),
        log_level=config.LOG_LEVEL,
    )


@router.post("/admin/user/add")
async def adm_add(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    user=Depends(get_user),
):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) == "admin":
        user_manager.register_user(username, password, role=role)
    return RedirectResponse("/admin", status_code=303)


@router.post("/admin/user/remove")
async def adm_rem(request: Request, username: str = Form(...), user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) == "admin" and username != "admin":
        user_manager.remove_user(username)
    return {"success": True}


@router.post("/admin/user/toggle-pattern")
async def adm_tog_pat(
    request: Request,
    username: str = Form(...),
    disabled: str = Form(...),
    user=Depends(get_user),
):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) == "admin":
        is_disabled = disabled.lower() == "true"
        user_manager.set_pattern_disabled(username, is_disabled)
        return {"success": True}
    return {"success": False}


@router.post("/admin/user/toggle-role")
async def adm_tog_role(
    request: Request,
    username: str = Form(...),
    role: str = Form(...),
    user=Depends(get_user),
):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) == "admin":
        if username == "admin" and role == "user":
            return {"success": False, "error": "Cannot demote primary admin."}
        if user_manager.update_role(username, role):
            return {"success": True}
    return {"success": False}


@router.post("/admin/user/update-password")
async def adm_upd(
    request: Request,
    username: str = Form(...),
    new_password: str = Form(...),
    user=Depends(get_user),
):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) == "admin":
        user_manager.update_password(username, new_password)
    return RedirectResponse("/admin", status_code=303)
