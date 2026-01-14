import os
import mimetypes
from fastapi import FastAPI, Request

# Register WebP MIME type if not present
mimetypes.add_type('image/webp', '.webp')

from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from jinja2 import Environment, FileSystemLoader
from app.core import config
from app.services.user_manager import UserManager
from app.services.auth_service import AuthService
from app.services.llm_service import GeminiAgent
from app.routers import auth, chat, admin

app = FastAPI()

# Session Middleware
# We enable https_only if the origin starts with https
https_only = config.ORIGIN.startswith("https")
app.add_middleware(
    SessionMiddleware, 
    secret_key=config.SESSION_SECRET,
    session_cookie="gemini_session",
    same_site="lax",
    https_only=https_only
)

# Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        if https_only:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' cdn.jsdelivr.net cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net cdnjs.cloudflare.com; "
            "font-src 'self' cdn.jsdelivr.net; "
            "img-src 'self' data: blob:; "
            "connect-src 'self' cdn.jsdelivr.net;"
        )
        response.headers["Content-Security-Policy"] = csp
        return response

app.add_middleware(SecurityHeadersMiddleware)

# UPLOAD_DIR
UPLOAD_DIR = config.UPLOAD_DIR
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Templates
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
jinja_env = Environment(loader=FileSystemLoader(templates_dir))

def render(name, **ctx):
    template = jinja_env.get_template(name)
    return HTMLResponse(template.render(**ctx))

# Services
user_manager = UserManager()
auth_service = AuthService(config.RP_ID, config.RP_NAME, config.ORIGIN)
agent = GeminiAgent()

# App State
app.state.user_manager = user_manager
app.state.auth_service = auth_service
app.state.agent = agent
app.state.render = render
app.state.UPLOAD_DIR = UPLOAD_DIR

# Static Files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Uploads
@app.get("/uploads/{filename}")
async def serve_upload(filename: str):
    fpath = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(fpath):
        from fastapi import HTTPException
        raise HTTPException(404)
    # Force webp mime type for .webp files
    media_type = None
    if filename.lower().endswith(".webp"):
        media_type = "image/webp"
    return FileResponse(fpath, media_type=media_type)

# Include Routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(admin.router)

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(os.path.join(static_dir, "favicon.ico"))

@app.get("/sw.js", include_in_schema=False)
async def service_worker():
    return FileResponse(os.path.join(static_dir, "sw.js"))

@app.get("/manifest.json", include_in_schema=False)
async def manifest():
    return FileResponse(os.path.join(static_dir, "manifest.json"))

if __name__ == "__main__":
    import uvicorn
    import argparse
    
    parser = argparse.ArgumentParser(description="Run the Gemini Agent")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the service on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    args = parser.parse_args()
    
    uvicorn.run(app, host=args.host, port=args.port)