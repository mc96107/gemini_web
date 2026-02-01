from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional

from app.core import config
from app.services.pattern_sync_service import PatternSyncService
from app.models.agent import AgentModel

router = APIRouter()

async def get_user(request: Request):
    return request.session.get("user")

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
