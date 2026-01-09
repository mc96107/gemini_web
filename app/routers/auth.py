from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional
import secrets
from eth_account import Account
from eth_account.messages import encode_defunct

# We will import the global instances from main later, or use dependencies.
# For now, we assume they are accessible via request.app.state.

router = APIRouter()

@router.get("/setup", response_class=HTMLResponse)
async def setup_pg(request: Request):
    user_manager = request.app.state.user_manager
    if user_manager.has_users():
        return RedirectResponse("/login")
    return request.app.state.render("setup.html", request=request)

@router.post("/setup")
async def setup(request: Request, password: str = Form(...), origin: str = Form("http://localhost:8000"), rp_id: str = Form("localhost")):
    user_manager = request.app.state.user_manager
    if user_manager.has_users():
        raise HTTPException(status_code=403, detail="Setup already complete")
    
    # Save to .env
    from app.core import config
    config.update_env("ORIGIN", origin)
    config.update_env("RP_ID", rp_id)
    
    # Update config in memory
    config.ORIGIN = origin
    config.RP_ID = rp_id
    
    user_manager.register_user("admin", password, role="admin")
    return RedirectResponse("/login", status_code=303)

@router.get("/login", response_class=HTMLResponse)
async def login_pg(request: Request):
    return request.app.state.render("login.html", request=request)

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    user_manager = request.app.state.user_manager
    if user_manager.authenticate_user(username, password):
        request.session["user"] = username
        # Use absolute URL for redirect to avoid potential issues with Service Worker or proxies
        return RedirectResponse(str(request.url_for("index")), status_code=303)
    return request.app.state.render("login.html", request=request, error="Invalid credentials")

@router.post("/login/pattern")
async def login_pat(request: Request, pattern: str = Form(...), username: Optional[str] = Form(None)):
    user_manager = request.app.state.user_manager
    u = username if username else user_manager.get_user_by_pattern(pattern)
    if u and (not username or user_manager.authenticate_with_pattern(u, pattern)):
        request.session["user"] = u
        # Use absolute URL for redirect to avoid potential issues with Service Worker or proxies
        return RedirectResponse(str(request.url_for("index")), status_code=303)
    return request.app.state.render("login.html", request=request, error="Invalid pattern")

@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login")

@router.get("/login/web3/challenge")
async def w3_ch(request: Request):
    c = f"Sign this: {secrets.token_hex(16)}"
    request.session["web3_challenge"] = c
    return {"challenge": c}

@router.post("/login/web3/verify")
async def w3_vf(request: Request, address: str = Form(...), signature: str = Form(...)):
    user_manager = request.app.state.user_manager
    c = request.session.get("web3_challenge")
    if not c: return {"success": False}
    try: 
        if Account.recover_message(encode_defunct(text=c), signature=signature).lower() == address.lower():
            u = user_manager.get_user_by_wallet(address)
            if u:
                request.session["user"] = u
                return {"success": True}
    except: pass
    return {"success": False}

@router.post("/user/update-pattern")
async def upd_pat(request: Request, pattern: str = Form(...)):
    user_manager = request.app.state.user_manager
    user = request.session.get("user")
    if user: return {"success": user_manager.set_pattern(user, pattern)}
    return {"success": False}

@router.post("/user/link-wallet")
async def lnk_w3(request: Request, address: str = Form(...), signature: str = Form(...)):
    user_manager = request.app.state.user_manager
    user = request.session.get("user")
    c = request.session.get("web3_challenge")
    if not (user and c): return {"success": False}
    try:
        if Account.recover_message(encode_defunct(text=c), signature=signature).lower() == address.lower():
            user_manager.set_wallet_address(user, address)
            return {"success": True}
    except: pass
    return {"success": False}

@router.get("/register/passkey/options")
async def pk_reg_opt(request: Request):
    auth_service = request.app.state.auth_service
    user = request.session.get("user")
    if not user: raise HTTPException(401)
    opts = auth_service.generate_registration_options(user, user)
    request.session["registration_challenge"] = auth_service.bytes_to_base64url(opts.challenge)
    return HTMLResponse(auth_service.options_to_json(opts), media_type="application/json")

@router.post("/register/passkey/verify")
async def pk_reg_vf(request: Request, data: dict):
    user_manager = request.app.state.user_manager
    auth_service = request.app.state.auth_service
    user = request.session.get("user")
    c = request.session.get("registration_challenge")
    if not (user and c): return {"success": False}
    try:
        v = auth_service.verify_registration_response(data, c)
        user_manager.add_passkey(user, v.credential_id, v.credential_public_key, v.sign_count)
        return {"success": True}
    except: return {"success": False}

@router.post("/login/passkey/options")
async def pk_log_opt(request: Request, username: Optional[str] = Form(None)):
    user_manager = request.app.state.user_manager
    auth_service = request.app.state.auth_service
    credential_ids = [pk["credential_id"] for pk in user_manager.get_passkeys(username)] if username else []
    opts = auth_service.generate_authentication_options(credential_ids)
    request.session["authentication_challenge"] = auth_service.bytes_to_base64url(opts.challenge)
    if username: request.session["authentication_username"] = username
    return HTMLResponse(auth_service.options_to_json(opts), media_type="application/json")

@router.post("/login/passkey/verify")
async def pk_log_vf(request: Request, data: dict):
    user_manager = request.app.state.user_manager
    auth_service = request.app.state.auth_service
    c = request.session.get("authentication_challenge")
    u = request.session.get("authentication_username")
    if not c: return {"success": False}
    cid = data.get("id")
    if not u: u, pk = user_manager.get_user_by_credential_id(cid)
    else: pk = next((p for p in user_manager.get_passkeys(u) if p["credential_id"] == cid), None)
    if not (u and pk): return {"success": False}
    try:
        v = auth_service.verify_authentication_response(data, c, pk["public_key"], pk["sign_count"])
        user_manager.update_passkey_sign_count(u, cid, v.new_sign_count)
        request.session["user"] = u
        return {"success": True}
    except: return {"success": False}
