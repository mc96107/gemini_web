import os
import re
import json
import base64

def get_file_content(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def recombine():
    # 1. Collect Templates
    templates = {}
    templates_dir = 'app/templates'
    if os.path.exists(templates_dir):
        for filename in os.listdir(templates_dir):
            if filename.endswith('.html'):
                templates[filename] = get_file_content(os.path.join(templates_dir, filename))

    # 2. Collect Static Assets
    static = {}
    static_dir = 'app/static'
    if os.path.exists(static_dir):
        for filename in os.listdir(static_dir):
            path = os.path.join(static_dir, filename)
            if filename.endswith(('.css', '.js', '.json', '.svg')):
                static[filename] = {
                    'content': get_file_content(path),
                    'encoding': 'text'
                }
            elif filename.endswith(('.ico', '.png')):
                with open(path, 'rb') as f:
                    static[filename] = {
                        'content': base64.b64encode(f.read()).decode('utf-8'),
                        'encoding': 'base64'
                    }

    # 3. Helpers
    def strip_local_imports(code):
        lines = code.splitlines()
        filtered = []
        for line in lines:
            if re.match(r'^\s*(from|import) (app\.|core|services|routers)', line):
                continue
            if 'from app.core import config' in line or 'from app.core.patterns' in line:
                continue
            filtered.append(line)
        return '\n'.join(filtered)

    def clean_config_ref(code):
        return code.replace('config.', '')

    # 4. Read components
    config_code = strip_local_imports(get_file_content('app/core/config.py'))
    patterns_code = strip_local_imports(get_file_content('app/core/patterns.py'))
    # Fix PATTERNS_FILE path for bundled app
    patterns_code = patterns_code.replace('os.path.join(os.path.dirname(__file__), "../../data/patterns.json")', 'os.path.join(os.getcwd(), "data", "patterns.json")')
    patterns_code += "\n# Ensure data directory exists\nos.makedirs(os.path.dirname(PATTERNS_FILE), exist_ok=True)\n"
    
    user_manager_code = strip_local_imports(get_file_content('app/services/user_manager.py'))
    auth_service_code = clean_config_ref(strip_local_imports(get_file_content('app/services/auth_service.py')))
    llm_service_code = clean_config_ref(strip_local_imports(get_file_content('app/services/llm_service.py')))
    sync_service_code = strip_local_imports(get_file_content('app/services/pattern_sync_service.py'))
    conversion_service_code = clean_config_ref(strip_local_imports(get_file_content('app/services/conversion_service.py')))
    
    auth_router_code = clean_config_ref(strip_local_imports(get_file_content('app/routers/auth.py')))
    # Update auth_router setup to re-init auth_service
    auth_router_code = auth_router_code.replace(
        'RP_ID = rp_id',
        'RP_ID = rp_id\n    request.app.state.auth_service = AuthService(rp_id, RP_NAME, origin)'
    )
    
    chat_router_code = clean_config_ref(strip_local_imports(get_file_content('app/routers/chat.py')))
    admin_router_code = clean_config_ref(strip_local_imports(get_file_content('app/routers/admin.py')))
    
    main_code = clean_config_ref(strip_local_imports(get_file_content('app/main.py')))

    combined = []
    
    # Headers
    combined.append("import json, os, mimetypes, hashlib, asyncio, re, secrets, shutil, uvicorn, bcrypt, subprocess, sys, base64, httpx, pypandoc, pandas as pd")
    combined.append("from typing import Dict, Optional, List, Tuple, Any")
    combined.append("from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException, Depends, APIRouter")
    combined.append("from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response, FileResponse")
    combined.append("from fastapi.staticfiles import StaticFiles")
    combined.append("from starlette.middleware.sessions import SessionMiddleware")
    combined.append("from starlette.middleware.base import BaseHTTPMiddleware")
    combined.append("from jinja2 import Environment, FileSystemLoader, Template")
    combined.append("from eth_account.messages import encode_defunct")
    combined.append("from eth_account import Account")
    combined.append("import webauthn")
    combined.append("from webauthn.helpers.structs import AuthenticatorSelectionCriteria, UserVerificationRequirement, PublicKeyCredentialDescriptor, ResidentKeyRequirement")
    combined.append("from webauthn import generate_registration_options, verify_registration_response, generate_authentication_options, verify_authentication_response, options_to_json, base64url_to_bytes")
    combined.append("from webauthn.helpers import bytes_to_base64url")
    combined.append("\n")

    # Configuration and Data
    combined.append("# --- CONFIGURATION ---")
    combined.append(config_code)
    combined.append("\n")
    combined.append("# --- PATTERNS ---")
    combined.append(patterns_code)
    combined.append("\n")
    combined.append(f"TEMPLATES = {json.dumps(templates, indent=4)}")
    combined.append("\n")
    combined.append(f"STATIC = {json.dumps(static, indent=4)}")
    combined.append("\n")

    # Services
    combined.append("# --- SERVICES ---")
    combined.append(user_manager_code)
    combined.append("\n")
    combined.append(auth_service_code)
    combined.append("\n")
    combined.append(llm_service_code)
    combined.append("\n")
    combined.append(sync_service_code)
    combined.append("\n")
    combined.append(conversion_service_code)
    combined.append("\n")

    # Routers
    combined.append("# --- ROUTERS ---")
    combined.append("auth_router = APIRouter()")
    combined.append(auth_router_code.replace('router = APIRouter()', '').replace('@router.', '@auth_router.'))
    combined.append("\n")
    combined.append("chat_router = APIRouter()")
    combined.append(chat_router_code.replace('router = APIRouter()', '').replace('@router.', '@chat_router.'))
    combined.append("\n")
    combined.append("admin_router = APIRouter()")
    combined.append(admin_router_code.replace('router = APIRouter()', '').replace('@router.', '@admin_router.'))
    combined.append("\n")

    # Main
    combined.append("# --- MAIN ---")
    main_clean = main_code
    main_clean = re.sub(r'templates_dir = .*?\n', 'templates_dir = None\n', main_clean)
    main_clean = re.sub(r'jinja_env = .*?\n', '', main_clean)
    
    render_fixed = """
def render(name, **ctx):
    return HTMLResponse(Template(TEMPLATES[name]).render(**ctx))
"""
    main_clean = re.sub(r'def render\(name, \*\*ctx\):.*?\n\s+return .*?\n', render_fixed, main_clean, flags=re.DOTALL)
    
    static_handler = """
@app.get("/static/{path}")
async def get_static(path: str):
    if path in STATIC:
        data = STATIC[path]
        media = "text/css" if path.endswith(".css") else "application/javascript"
        if path.endswith(".json"): media = "application/json"
        if path.endswith(".svg"): media = "image/svg+xml"
        if path.endswith(".png"): media = "image/png"
        if path.endswith(".ico"): media = "image/x-icon"
        
        content = data['content']
        if data['encoding'] == 'base64':
            return Response(content=base64.b64decode(content), media_type=media)
        return Response(content=content, media_type=media)
    raise HTTPException(404)

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return await get_static("favicon.ico")

@app.get("/sw.js", include_in_schema=False)
async def service_worker():
    return await get_static("sw.js")

@app.get("/manifest.json", include_in_schema=False)
async def manifest():
    return await get_static("manifest.json")
"""
    # Remove old static mounting and individual routes
    # Use re.escape or simpler literal replacement for the complex line
    main_clean = main_clean.replace('app.mount("/static", StaticFiles(directory=static_dir), name="static")', '')
    
    # Remove individual route handlers that are now covered by static_handler
    main_clean = re.sub(r'@app\.get\("/favicon\.ico".*?return FileResponse\(.*?\)\n+', '', main_clean, flags=re.DOTALL)
    main_clean = re.sub(r'@app\.get\("/sw\.js".*?return FileResponse\(.*?\)\n+', '', main_clean, flags=re.DOTALL)
    main_clean = re.sub(r'@app\.get\("/manifest\.json".*?return FileResponse\(.*?\)\n+', '', main_clean, flags=re.DOTALL)

    # Clean up any leftover debris (e.g., if re.sub missed something or partial match)
    main_clean = main_clean.replace(', name="static")', '')

    # Ensure include_router calls are properly updated
    main_clean = main_clean.replace('app.include_router(auth.router)', 'app.include_router(auth_router)')
    main_clean = main_clean.replace('app.include_router(chat.router)', 'app.include_router(chat_router)')
    main_clean = main_clean.replace('app.include_router(admin.router)', 'app.include_router(admin_router)')
    
    # Prepare all our custom routes
    custom_logic = "\n" + static_handler + "\n"
    
    if 'app.include_router(chat_router)' not in main_clean:
        custom_logic += "\napp.include_router(auth_router)\napp.include_router(chat_router)\napp.include_router(admin_router)\n"

    # Insert everything before the if __name__ block to ensure it's executed
    if 'if __name__ == "__main__":' in main_clean:
        main_clean = main_clean.replace('if __name__ == "__main__":', custom_logic + '\nif __name__ == "__main__":')
    else:
        main_clean += custom_logic

    combined.append(main_clean)

    # Output
    output_file = 'gemini_agent_release.py'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(combined))
    
    print(f"Successfully created {output_file}")

if __name__ == "__main__":
    recombine()
