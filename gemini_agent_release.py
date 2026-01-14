import json, os, mimetypes, hashlib, asyncio, re, secrets, shutil, uvicorn, bcrypt, subprocess, sys, base64, httpx
from typing import Dict, Optional, List, Tuple, Any
from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException, Depends, APIRouter
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from jinja2 import Environment, FileSystemLoader, Template
from eth_account.messages import encode_defunct
from eth_account import Account
import webauthn
from webauthn.helpers.structs import AuthenticatorSelectionCriteria, UserVerificationRequirement, PublicKeyCredentialDescriptor, ResidentKeyRequirement
from webauthn import generate_registration_options, verify_registration_response, generate_authentication_options, verify_authentication_response, options_to_json, base64url_to_bytes
from webauthn.helpers import bytes_to_base64url


# --- CONFIGURATION ---
import os
import secrets
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# WebAuthn Configuration
RP_ID = os.getenv("RP_ID", "localhost")
RP_NAME = os.getenv("RP_NAME", "Gemini Agent")
ORIGIN = os.getenv("ORIGIN", "http://localhost:8000")

# Security Configuration
SESSION_SECRET = os.getenv("SESSION_SECRET", secrets.token_hex(32))

# Application Configuration
UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(os.getcwd(), "tmp", "user_attachments"))
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-3-pro-preview")

def update_env(key: str, value: str):
    env_path = os.path.join(os.getcwd(), ".env")
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()
    
    found = False
    new_lines = []
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)
    
    if not found:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines.append("\n")
        new_lines.append(f"{key}={value}\n")
    
    with open(env_path, "w") as f:
        f.writelines(new_lines)


# --- PATTERNS ---
import json
import os
import logging

# Set up logging
logger = logging.getLogger(__name__)

PATTERNS_FILE = os.path.join(os.getcwd(), "data", "patterns.json")

def load_patterns():
    if os.path.exists(PATTERNS_FILE):
        try:
            with open(PATTERNS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading patterns from {PATTERNS_FILE}: {e}")
            return {}
    else:
        logger.warning(f"Patterns file {PATTERNS_FILE} not found.")
        return {}

PATTERNS = load_patterns()

def reload_patterns():
    global PATTERNS
    PATTERNS.clear()
    PATTERNS.update(load_patterns())
    return PATTERNS
# Ensure data directory exists
os.makedirs(os.path.dirname(PATTERNS_FILE), exist_ok=True)



TEMPLATES = {
    "admin.html": "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n    <meta charset=\"UTF-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n    <title>Admin Dashboard - Gemini Agent</title>\n    <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css\" rel=\"stylesheet\">\n    <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css\">\n    <link rel=\"icon\" type=\"image/svg+xml\" href=\"/static/icon.svg?v=2\">\n    <style>\n        body { background-color: #121212; color: #e0e0e0; }\n        .card { background-color: #1e1e1e; border: 1px solid #333; }\n        .table { color: #e0e0e0; }\n        .table-hover tbody tr:hover { background-color: #2c2c2c; }\n    </style>\n</head>\n<body>\n    <nav class=\"navbar navbar-expand-lg navbar-dark bg-dark border-bottom border-secondary\">\n        <div class=\"container\">\n            <a class=\"navbar-brand\" href=\"/\"><i class=\"bi bi-robot text-primary me-2\"></i>Gemini Agent Admin</a>\n            <div class=\"navbar-nav ms-auto\">\n                <a class=\"nav-link\" href=\"/\">Back to Chat</a>\n                <a class=\"nav-link\" href=\"/logout\">Logout</a>\n            </div>\n        </div>\n    </nav>\n\n    <div class=\"container mt-4\">\n        <h2 class=\"mb-4\">User Management</h2>\n\n        <div class=\"row\">\n            <div class=\"col-md-8\">\n                <div class=\"card shadow-sm\">\n                    <div class=\"card-body\">\n                        <h5 class=\"card-title\">Users</h5>\n                        <div class=\"table-responsive\">\n                            <table class=\"table table-dark table-hover\">\n                                <thead>\n                                    <tr>\n                                        <th>Username</th>\n                                        <th>Role</th>\n                                        <th>Pattern Login</th>\n                                        <th>Actions</th>\n                                    </tr>\n                                </thead>\n                                <tbody>\n                                    {% for user in users %}\n                                    <tr>\n                                        <td>{{ user.username }}</td>\n                                        <td><span class=\"badge {{ 'bg-primary' if user.role == 'admin' else 'bg-secondary' }}\">{{ user.role }}</span></td>\n                                        <td>\n                                            <div class=\"form-check form-switch\">\n                                                <input class=\"form-check-input\" type=\"checkbox\" role=\"switch\" \n                                                    id=\"patternSwitch_{{ user.username }}\" \n                                                    {% if not user.pattern_disabled %}checked{% endif %}\n                                                    onchange=\"togglePattern('{{ user.username }}', this.checked)\">\n                                                <label class=\"form-check-label\" for=\"patternSwitch_{{ user.username }}\">\n                                                    {{ 'Enabled' if not user.pattern_disabled else 'Disabled' }}\n                                                </label>\n                                            </div>\n                                        </td>\n                                        <td>\n                                            {% if user.username != 'admin' %}\n                                            <button class=\"btn btn-sm btn-outline-danger\" onclick=\"deleteUser('{{ user.username }}')\">Delete</button>\n                                            {% endif %}\n                                            <button class=\"btn btn-sm btn-outline-info\" onclick=\"showChangePassword('{{ user.username }}')\">Change Password</button>\n                                        </td>\n                                    </tr>\n                                    {% endfor %}\n                                </tbody>\n                            </table>\n                        </div>\n                    </div>\n                </div>\n            </div>\n\n            <div class=\"col-md-4\">\n                <div class=\"card shadow-sm mb-4\">\n                    <div class=\"card-body\">\n                        <h5 class=\"card-title\">System Actions</h5>\n                        <button class=\"btn btn-info w-100 mb-2\" onclick=\"syncPatterns()\">\n                            <i class=\"bi bi-arrow-repeat me-1\"></i> Sync Fabric Patterns\n                        </button>\n                        <button class=\"btn btn-warning w-100 mb-2\" onclick=\"restartSetup()\">\n                            <i class=\"bi bi-exclamation-triangle me-1\"></i> Restart Setup\n                        </button>\n                        <div id=\"sync-status\" class=\"small mt-2\"></div>\n                    </div>\n                </div>\n\n                <div class=\"card shadow-sm mb-4\">\n                    <div class=\"card-body\">\n                        <h5 class=\"card-title\">Add User</h5>\n                        <form action=\"/admin/user/add\" method=\"post\">\n                            <div class=\"mb-3\">\n                                <label class=\"form-label\">Username</label>\n                                <input type=\"text\" name=\"username\" class=\"form-control bg-dark text-light border-secondary\" required>\n                            </div>\n                            <div class=\"mb-3\">\n                                <label class=\"form-label\">Password</label>\n                                <input type=\"password\" name=\"password\" class=\"form-control bg-dark text-light border-secondary\" required>\n                            </div>\n                            <div class=\"mb-3\">\n                                <label class=\"form-label\">Role</label>\n                                <select name=\"role\" class=\"form-select bg-dark text-light border-secondary\">\n                                    <option value=\"user\">User</option>\n                                    <option value=\"admin\">Admin</option>\n                                </select>\n                            </div>\n                            <button type=\"submit\" class=\"btn btn-success w-100\">Add User</button>\n                        </form>\n                    </div>\n                </div>\n            </div>\n        </div>\n    </div>\n\n    <!-- Change Password Modal -->\n    <div class=\"modal fade\" id=\"passwordModal\" tabindex=\"-1\" aria-hidden=\"true\">\n        <div class=\"modal-dialog\">\n            <div class=\"modal-content bg-dark text-light border-secondary\">\n                <div class=\"modal-header border-secondary\">\n                    <h5 class=\"modal-title\">Change Password for <span id=\"targetUsername\"></span></h5>\n                    <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>\n                </div>\n                <form action=\"/admin/user/update-password\" method=\"post\">\n                    <div class=\"modal-body\">\n                        <input type=\"hidden\" name=\"username\" id=\"modalUsername\">\n                        <div class=\"mb-3\">\n                            <label class=\"form-label\">New Password</label>\n                            <input type=\"password\" name=\"new_password\" class=\"form-control bg-dark text-light border-secondary\" required>\n                        </div>\n                    </div>\n                    <div class=\"modal-footer border-secondary\">\n                        <button type=\"button\" class=\"btn btn-secondary\" data-bs-dismiss=\"modal\">Cancel</button>\n                        <button type=\"submit\" class=\"btn btn-primary\">Update Password</button>\n                    </div>\n                </form>\n            </div>\n        </div>\n    </div>\n\n    <script src=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js\"></script>\n    <script>\n        const passwordModal = new bootstrap.Modal(document.getElementById('passwordModal'));\n\n        function showChangePassword(username) {\n            document.getElementById('targetUsername').innerText = username;\n            document.getElementById('modalUsername').value = username;\n            passwordModal.show();\n        }\n\n        \n        async function togglePattern(username, enabled) {\n            try {\n                const formData = new FormData();\n                formData.append('username', username);\n                formData.append('disabled', !enabled);\n                const res = await fetch('/admin/user/toggle-pattern', { method: 'POST', body: formData });\n                const data = await res.json();\n                if (data.success) {\n                    const label = document.querySelector(`label[for=\"patternSwitch_${username}\"]`);\n                    if (label) label.textContent = enabled ? 'Enabled' : 'Disabled';\n                } else {\n                    alert('Failed to update');\n                    document.getElementById(`patternSwitch_${username}`).checked = !enabled;\n                }\n            } catch (e) { console.error(e); alert('Error'); }\n        }\n\n        async function deleteUser(username) {\n            if (confirm(`Are you sure you want to delete user ${username}?`)) {\n                const formData = new FormData();\n                formData.append('username', username);\n                const res = await fetch('/admin/user/remove', {\n                    method: 'POST',\n                    body: formData\n                });\n                if (res.ok) {\n                    location.reload();\n                } else {\n                    alert('Error deleting user');\n                }\n            }\n        }\n\n        async function syncPatterns() {\n            const status = document.getElementById('sync-status');\n            status.textContent = 'Syncing... Please wait.';\n            status.className = 'small mt-2 text-info';\n            \n            try {\n                const res = await fetch('/admin/patterns/sync', { method: 'POST' });\n                const data = await res.json();\n                if (data.success) {\n                    status.textContent = `Successfully synced ${data.count} patterns!`;\n                    status.className = 'small mt-2 text-success';\n                } else {\n                    status.textContent = 'Error: ' + (data.error || 'Unknown error');\n                    status.className = 'small mt-2 text-danger';\n                }\n            } catch (e) {\n                status.textContent = 'Error: ' + e.message;\n                status.className = 'small mt-2 text-danger';\n            }\n        }\n\n        async function restartSetup() {\n            if (confirm('Are you sure you want to RESTART SETUP? This will DELETE ALL USERS and you will need to re-configure the admin account.')) {\n                try {\n                    const res = await fetch('/admin/system/restart-setup', { method: 'POST' });\n                    const data = await res.json();\n                    if (data.success) {\n                        window.location.href = '/setup';\n                    } else {\n                        alert('Failed to restart setup');\n                    }\n                } catch (e) {\n                    console.error(e);\n                    alert('Error');\n                }\n            }\n        }\n    </script>\n</body>\n</html>\n",
    "index.html": "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n    <meta charset=\"UTF-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n    <title>Gemini Termux Agent</title>\n    <link rel=\"manifest\" href=\"/manifest.json?v=3\">\n    <link rel=\"icon\" type=\"image/svg+xml\" href=\"/static/icon.svg?v=2\">\n    <meta name=\"theme-color\" content=\"#0d6efd\">\n    <meta name=\"mobile-web-app-capable\" content=\"yes\">\n    <meta name=\"apple-mobile-web-app-status-bar-style\" content=\"black-translucent\">\n    <link rel=\"apple-touch-icon\" href=\"/static/icon.svg?v=2\">\n    <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css\" rel=\"stylesheet\">\n    <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css\">\n    <link rel=\"stylesheet\" href=\"https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/styles/github-dark.min.css\">\n    <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css\">\n    <link rel=\"stylesheet\" href=\"/static/style.css?v={{ range(1, 999999) | random }}\">\n    <script src=\"https://cdnjs.cloudflare.com/ajax/libs/ethers/5.7.2/ethers.umd.min.js\"></script>\n    <script defer src=\"https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js\"></script>\n    <script defer src=\"https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js\"></script>\n</head>\n<body class=\"bg-dark text-light\">\n\n<div class=\"container-fluid d-flex flex-column vh-100 p-0\">\n    <!-- Header -->\n    <header class=\"p-3 border-bottom border-secondary bg-black d-flex justify-content-between align-items-center\">\n        <div class=\"d-flex align-items-center gap-3\">\n            <button class=\"btn btn-outline-secondary btn-sm\" type=\"button\" data-bs-toggle=\"offcanvas\" data-bs-target=\"#historySidebar\" aria-controls=\"historySidebar\">\n                <i class=\"bi bi-layout-sidebar-inset\"></i>\n            </button>\n            <h1 class=\"h4 m-0\"><i class=\"bi bi-robot text-primary\"></i></h1>\n        </div>\n        <div class=\"d-flex gap-2 align-items-center\">\n            <span class=\"badge bg-secondary me-2\"><i class=\"bi bi-person\"></i> {{ user }}</span>\n            {% if is_admin %}\n            <a href=\"/admin\" class=\"btn btn-outline-info btn-sm\" title=\"Admin\"><i class=\"bi bi-gear\"></i> <span class=\"d-none d-sm-inline\">Admin</span></a>\n            {% endif %}\n            <button id=\"security-btn\" class=\"btn btn-outline-light btn-sm\" data-bs-toggle=\"modal\" data-bs-target=\"#securityModal\" title=\"Security\"><i class=\"bi bi-shield-lock\"></i> <span class=\"d-none d-sm-inline\">Security</span></button>\n            <button id=\"export-btn\" class=\"btn btn-outline-success btn-sm\" title=\"Export Chat\"><i class=\"bi bi-download\"></i> <span class=\"d-none d-sm-inline\">Export</span></button>\n            <button id=\"reset-btn\" class=\"btn btn-outline-warning btn-sm\" title=\"Reset Chat\"><i class=\"bi bi-trash\"></i> <span class=\"d-none d-sm-inline\">Reset</span></button>\n            <button id=\"patterns-btn\" class=\"btn btn-outline-info btn-sm\" data-bs-toggle=\"modal\" data-bs-target=\"#patternsModal\" title=\"Patterns\"><i class=\"bi bi-collection\"></i> <span class=\"d-none d-sm-inline\">Patterns</span></button>\n            <a href=\"/logout\" class=\"btn btn-outline-danger btn-sm\" title=\"Logout\"><i class=\"bi bi-box-arrow-right\"></i> <span class=\"d-none d-sm-inline\">Logout</span></a>\n        </div>\n    </header>\n\n    <!-- History Sidebar (Offcanvas) -->\n    <div class=\"offcanvas offcanvas-start bg-dark text-light border-end border-secondary\" tabindex=\"-1\" id=\"historySidebar\" aria-labelledby=\"historySidebarLabel\">\n      <div class=\"offcanvas-header border-bottom border-secondary\">\n        <h5 class=\"offcanvas-title\" id=\"historySidebarLabel\"><i class=\"bi bi-clock-history\"></i> Chat History</h5>\n        <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"offcanvas\" aria-label=\"Close\"></button>\n      </div>\n      <div class=\"offcanvas-body p-0\">\n        <div class=\"p-3 border-bottom border-secondary\">\n            <button id=\"new-chat-btn\" class=\"btn btn-primary w-100 mb-2\"><i class=\"bi bi-plus-lg\"></i> New Chat</button>\n        </div>\n        <div id=\"sessions-list\" class=\"list-group list-group-flush\">\n            <!-- Sessions will be loaded here -->\n            <div class=\"text-center p-3\">\n                <div class=\"spinner-border text-info spinner-border-sm\" role=\"status\"></div>\n            </div>\n        </div>\n      </div>\n    </div>\n\n    <!-- Chat Area -->\n    <div id=\"chat-container\" class=\"flex-grow-1 overflow-auto p-3\">\n        <div id=\"scroll-sentinel\" style=\"height: 10px; width: 100%;\"></div>\n        <div id=\"load-more-container\" class=\"text-center d-none mb-3\">\n            <button id=\"load-more-btn\" class=\"btn btn-outline-secondary btn-sm\">Load Older Messages</button>\n        </div>\n        <div id=\"chat-welcome\" class=\"text-center text-muted mt-5\">\n            <p>Start a conversation with Gemini.</p>\n            <p class=\"small\">Try <code>/help</code> to see available commands.</p>\n        </div>\n    </div>\n\n    <!-- Input Area -->\n    <footer class=\"py-3 px-3 border-top border-secondary bg-black\">\n        <form id=\"chat-form\" class=\"d-flex flex-column gap-2\">\n            \n            <div id=\"file-preview-area\" class=\"d-none alert alert-secondary p-2 d-flex justify-content-between align-items-center mb-2\">\n                <span id=\"file-name\" class=\"text-truncate\"></span>\n                <button type=\"button\" class=\"btn-close\" id=\"clear-file-btn\"></button>\n            </div>\n\n            <div class=\"d-flex align-items-end gap-2\">\n                <!-- Left Actions: Model & Attach -->\n                <div class=\"d-flex gap-1 pb-1\">\n                    <div class=\"btn-group dropup\">\n                        <button class=\"btn btn-secondary btn-sm rounded-circle\" type=\"button\" data-bs-toggle=\"dropdown\" aria-expanded=\"false\" title=\"Select Model\">\n                            <i class=\"bi bi-cpu\"></i>\n                        </button>\n                        <ul class=\"dropdown-menu\">\n                            <li><h6 class=\"dropdown-header\">Model Selection</h6></li>\n                            <li><a class=\"dropdown-item active\" href=\"#\" data-model=\"gemini-3-pro-preview\">Gemini 3 Pro <span class=\"badge bg-warning text-dark ms-1\">Preview</span></a></li>\n                            <li><a class=\"dropdown-item\" href=\"#\" data-model=\"gemini-3-flash-preview\">Gemini 3 Flash <span class=\"badge bg-success ms-1\">Preview</span></a></li>\n                            <li><a class=\"dropdown-item\" href=\"#\" data-model=\"gemini-2.5-pro\">Gemini 2.5 Pro</a></li>\n                            <li><a class=\"dropdown-item\" href=\"#\" data-model=\"gemini-2.5-flash\">Gemini 2.5 Flash</a></li>\n                            <li><a class=\"dropdown-item\" href=\"#\" data-model=\"gemini-2.5-flash-lite\">Gemini 2.5 Flash Lite</a></li>\n                        </ul>\n                    </div>\n                    <input type=\"hidden\" name=\"model\" id=\"model-input\" value=\"gemini-3-pro-preview\">\n                    \n                    <label class=\"btn btn-outline-secondary btn-sm rounded-circle\" for=\"file-upload\" title=\"Attach File\">\n                        <i class=\"bi bi-paperclip\"></i>\n                    </label>\n                    <input type=\"file\" id=\"file-upload\" name=\"file\" class=\"d-none\">\n                    \n                    <button class=\"btn btn-outline-secondary btn-sm rounded-circle\" type=\"button\" id=\"tools-config-btn\" data-bs-toggle=\"modal\" data-bs-target=\"#toolsModal\" title=\"Tools Settings\">\n                        <i class=\"bi bi-wrench\"></i>\n                    </button>\n                </div>\n\n                <!-- Text Input -->\n                <div class=\"flex-grow-1\">\n                    <textarea class=\"form-control bg-dark text-light border-secondary shadow-none\" id=\"message-input\" name=\"message\" rows=\"2\" placeholder=\"Message Gemini...\" required style=\"border-radius: 20px;\"></textarea>\n                </div>\n                \n                <!-- Send Button -->\n                <button class=\"btn btn-primary rounded-circle p-2\" type=\"submit\" id=\"send-btn\" style=\"width: 45px; height: 45px;\">\n                    <i class=\"bi bi-send-fill\"></i>\n                </button>\n            </div>\n            \n            <div class=\"text-center\">\n                <small class=\"text-muted\" style=\"font-size: 0.7rem;\">Currently using: <span id=\"model-label\">Gemini 3 Pro</span></small>\n            </div>\n        </form>\n    </footer>\n</div>\n\n<!-- Toast Container -->\n<div class=\"toast-container position-fixed bottom-0 end-0 p-3\">\n    <div id=\"liveToast\" class=\"toast align-items-center text-white bg-primary border-0\" role=\"alert\" aria-live=\"assertive\" aria-atomic=\"true\">\n        <div class=\"d-flex\">\n            <div class=\"toast-body\" id=\"toast-body\">\n                Notification message\n            </div>\n            <button type=\"button\" class=\"btn-close btn-close-white me-2 m-auto\" data-bs-dismiss=\"toast\" aria-label=\"Close\"></button>\n        </div>\n    </div>\n</div>\n\n<!-- Patterns Modal -->\n<div class=\"modal fade\" id=\"patternsModal\" tabindex=\"-1\" aria-labelledby=\"patternsModalLabel\" aria-hidden=\"true\">\n  <div class=\"modal-dialog modal-lg modal-dialog-scrollable\">\n    <div class=\"modal-content bg-dark text-light border-secondary\">\n      <div class=\"modal-header border-secondary\">\n        <h5 class=\"modal-title\" id=\"patternsModalLabel\"><i class=\"bi bi-collection\"></i> Available Patterns</h5>\n        <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>\n      </div>\n      <div class=\"modal-body\">\n        <div class=\"mb-3\">\n            <input type=\"text\" id=\"pattern-search\" class=\"form-control bg-dark text-light border-secondary\" placeholder=\"Search patterns...\">\n        </div>\n        <div class=\"list-group\" id=\"patterns-list\">\n            <!-- Patterns will be loaded here -->\n            <div class=\"text-center p-3\">\n                <div class=\"spinner-border text-info\" role=\"status\"></div>\n            </div>\n        </div>\n      </div>\n    </div>\n  </div>\n</div>\n\n<!-- Security Modal -->\n<div class=\"modal fade\" id=\"securityModal\" tabindex=\"-1\" aria-labelledby=\"securityModalLabel\" aria-hidden=\"true\">\n  <div class=\"modal-dialog\">\n    <div class=\"modal-content bg-dark text-light border-secondary\">\n      <div class=\"modal-header border-secondary\">\n        <h5 class=\"modal-title\" id=\"securityModalLabel\"><i class=\"bi bi-shield-lock\"></i> Security Settings</h5>\n        <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>\n      </div>\n      <div class=\"modal-body\">\n        <div class=\"mb-4\">\n            <h6><i class=\"bi bi-key\"></i> Passkeys</h6>\n            <p class=\"small text-muted\">Register a Passkey for faster, more secure login without a password.</p>\n            <button id=\"btn-register-passkey\" class=\"btn btn-outline-info w-100\"><i class=\"bi bi-plus-lg\"></i> Register New Passkey</button>\n            <div id=\"passkey-reg-status\" class=\"mt-2 small\"></div>\n        </div>\n        <hr class=\"border-secondary\">\n        <div class=\"mb-4\">\n            <h6><i class=\"bi bi-grid-3x3\"></i> Login Pattern</h6>\n            <p class=\"small text-muted\">Change your pattern-based login.</p>\n            <div class=\"text-center mb-3\">\n                <div id=\"pattern-container-security\" class=\"mx-auto\" style=\"width: 200px; height: 200px; position: relative; touch-action: none;\">\n                    <svg id=\"pattern-svg-security\" width=\"200\" height=\"200\" style=\"background: #252525; border-radius: 10px;\"></svg>\n                </div>\n                <input type=\"hidden\" id=\"pattern-input-security\">\n            </div>\n            <button id=\"btn-update-pattern\" class=\"btn btn-outline-warning w-100\">Update Pattern</button>\n            <div id=\"pattern-update-status\" class=\"mt-2 small\"></div>\n        </div>\n        <hr class=\"border-secondary\">\n        <div class=\"mb-3\">\n            <h6><i class=\"bi bi-wallet2\"></i> Crypto Wallet</h6>\n            <p class=\"small text-muted\">Link your Ethereum wallet (MetaMask/Brave) to sign in using your wallet.</p>\n            <div class=\"input-group mb-2\">\n                <input type=\"text\" id=\"wallet-address-input\" class=\"form-control bg-dark text-light border-secondary\" placeholder=\"0x...\" readonly>\n                <button id=\"btn-link-wallet\" class=\"btn btn-outline-primary\">Link Wallet</button>\n            </div>\n            <div id=\"wallet-link-status\" class=\"mt-2 small\"></div>\n        </div>\n      </div>\n    </div>\n  </div>\n</div>\n\n<!-- Tools Modal -->\n<div class=\"modal fade\" id=\"toolsModal\" tabindex=\"-1\" aria-labelledby=\"toolsModalLabel\" aria-hidden=\"true\">\n  <div class=\"modal-dialog\">\n    <div class=\"modal-content bg-dark text-light border-secondary\">\n      <div class=\"modal-header border-secondary\">\n        <h5 class=\"modal-title\" id=\"toolsModalLabel\"><i class=\"bi bi-wrench\"></i> Tools Settings</h5>\n        <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>\n      </div>\n      <div class=\"modal-body\">\n        <p class=\"small text-muted mb-3\">Enable or disable tools for the current session. All tools are disabled by default for security.</p>\n        \n        <div class=\"mb-4\">\n            <h6 class=\"text-info small mb-2 text-uppercase fw-bold\">Read-Only / Safe Tools</h6>\n            <div class=\"list-group list-group-flush bg-transparent\">\n                <div class=\"form-check form-switch mb-2\">\n                    <input class=\"form-check-input tool-toggle\" type=\"checkbox\" id=\"tool-list_directory\" value=\"list_directory\">\n                    <label class=\"form-check-label\" for=\"tool-list_directory\">Read Folder (list_directory)</label>\n                </div>\n                <div class=\"form-check form-switch mb-2\">\n                    <input class=\"form-check-input tool-toggle\" type=\"checkbox\" id=\"tool-read_file\" value=\"read_file\">\n                    <label class=\"form-check-label\" for=\"tool-read_file\">Read File (read_file)</label>\n                </div>\n                <div class=\"form-check form-switch mb-2\">\n                    <input class=\"form-check-input tool-toggle\" type=\"checkbox\" id=\"tool-glob\" value=\"glob\">\n                    <label class=\"form-check-label\" for=\"tool-glob\">Find Files (glob)</label>\n                </div>\n                <div class=\"form-check form-switch mb-2\">\n                    <input class=\"form-check-input tool-toggle\" type=\"checkbox\" id=\"tool-search_file_content\" value=\"search_file_content\">\n                    <label class=\"form-check-label\" for=\"tool-search_file_content\">Search Text (search_file_content)</label>\n                </div>\n                <div class=\"form-check form-switch mb-2\">\n                    <input class=\"form-check-input tool-toggle\" type=\"checkbox\" id=\"tool-google_web_search\" value=\"google_web_search\">\n                    <label class=\"form-check-label\" for=\"tool-google_web_search\">Google Search (google_web_search)</label>\n                </div>\n                <div class=\"form-check form-switch mb-2\">\n                    <input class=\"form-check-input tool-toggle\" type=\"checkbox\" id=\"tool-web_fetch\" value=\"web_fetch\">\n                    <label class=\"form-check-label\" for=\"tool-web_fetch\">Web Fetch (web_fetch)</label>\n                </div>\n            </div>\n        </div>\n\n        <div class=\"mb-4\">\n            <h6 class=\"text-danger small mb-2 text-uppercase fw-bold\">Modification / High-Risk Tools</h6>\n            <div class=\"list-group list-group-flush bg-transparent\">\n                <div class=\"form-check form-switch mb-2\">\n                    <input class=\"form-check-input tool-toggle\" type=\"checkbox\" id=\"tool-replace\" value=\"replace\">\n                    <label class=\"form-check-label\" for=\"tool-replace\">Edit (replace)</label>\n                </div>\n                <div class=\"form-check form-switch mb-2\">\n                    <input class=\"form-check-input tool-toggle\" type=\"checkbox\" id=\"tool-write_file\" value=\"write_file\">\n                    <label class=\"form-check-label\" for=\"tool-write_file\">Write File (write_file)</label>\n                </div>\n                <div class=\"form-check form-switch mb-2\">\n                    <input class=\"form-check-input tool-toggle\" type=\"checkbox\" id=\"tool-run_shell_command\" value=\"run_shell_command\">\n                    <label class=\"form-check-label\" for=\"tool-run_shell_command\">Shell (run_shell_command)</label>\n                </div>\n                <div class=\"form-check form-switch mb-2\">\n                    <input class=\"form-check-input tool-toggle\" type=\"checkbox\" id=\"tool-save_memory\" value=\"save_memory\">\n                    <label class=\"form-check-label\" for=\"tool-save_memory\">Save Memory (save_memory)</label>\n                </div>\n                <div class=\"form-check form-switch mb-2\">\n                    <input class=\"form-check-input tool-toggle\" type=\"checkbox\" id=\"tool-delegate_to_agent\" value=\"delegate_to_agent\">\n                    <label class=\"form-check-label\" for=\"tool-delegate_to_agent\">Delegate to Agent (delegate_to_agent)</label>\n                </div>\n            </div>\n        </div>\n\n        <div class=\"d-flex justify-content-between gap-2 mt-4\">\n            <button type=\"button\" class=\"btn btn-outline-danger btn-sm\" id=\"btn-deselect-all-tools\">Deselect All</button>\n            <button type=\"button\" class=\"btn btn-primary btn-sm\" id=\"btn-apply-tools\">Apply Settings</button>\n        </div>\n        <div id=\"tools-status\" class=\"mt-2 small text-center\"></div>\n      </div>\n    </div>\n  </div>\n</div>\n\n<script src=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js\"></script>\n<script src=\"https://cdn.jsdelivr.net/npm/marked/marked.min.js\"></script>\n<script src=\"https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/highlight.min.js\"></script>\n<script>\n    // Security Modal Logic\n    document.addEventListener('DOMContentLoaded', () => {\n        const btnLinkWallet = document.getElementById('btn-link-wallet');\n        const walletStatus = document.getElementById('wallet-link-status');\n        const btnRegisterPasskey = document.getElementById('btn-register-passkey');\n        const passkeyStatus = document.getElementById('passkey-reg-status');\n        \n        // --- Pattern Update Logic ---\n        const svgSec = document.getElementById('pattern-svg-security');\n        const patternInputSec = document.getElementById('pattern-input-security');\n        const btnUpdatePattern = document.getElementById('btn-update-pattern');\n        const patternStatus = document.getElementById('pattern-update-status');\n        const dotsSec = [];\n        const selectedDotsSec = [];\n        let isDrawingSec = false;\n        let currentLineSec = null;\n\n        // Create 3x3 grid for security modal\n        for (let y = 0; y < 3; y++) {\n            for (let x = 0; x < 3; x++) {\n                const cx = 40 + x * 60;\n                const cy = 40 + y * 60;\n                const index = y * 3 + x + 1;\n                \n                const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');\n                dot.setAttribute('cx', cx);\n                dot.setAttribute('cy', cy);\n                dot.setAttribute('r', 8);\n                dot.setAttribute('fill', '#555');\n                dot.setAttribute('data-index', index);\n                svgSec.appendChild(dot);\n                dotsSec.push({ cx, cy, index, element: dot });\n            }\n        }\n\n        function getMousePosSec(e) {\n            const rect = svgSec.getBoundingClientRect();\n            const clientX = e.touches ? e.touches[0].clientX : e.clientX;\n            const clientY = e.touches ? e.touches[0].clientY : e.clientY;\n            return {\n                x: clientX - rect.left,\n                y: clientY - rect.top\n            };\n        }\n\n        function startDrawingSec(e) {\n            isDrawingSec = true;\n            resetPatternSec();\n            handleMoveSec(e);\n        }\n\n        function handleMoveSec(e) {\n            if (!isDrawingSec) return;\n            const pos = getMousePosSec(e);\n            \n            dotsSec.forEach(dot => {\n                const dist = Math.hypot(pos.x - dot.cx, pos.y - dot.cy);\n                if (dist < 20 && !selectedDotsSec.includes(dot)) {\n                    selectedDotsSec.push(dot);\n                    dot.element.setAttribute('fill', '#ffc107');\n                    dot.element.setAttribute('r', 12);\n                    \n                    if (selectedDotsSec.length > 1) {\n                        const prevDot = selectedDotsSec[selectedDotsSec.length - 2];\n                        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');\n                        line.setAttribute('x1', prevDot.cx);\n                        line.setAttribute('y1', prevDot.cy);\n                        line.setAttribute('x2', dot.cx);\n                        line.setAttribute('y2', dot.cy);\n                        line.setAttribute('stroke', '#ffc107');\n                        line.setAttribute('stroke-width', 3);\n                        svgSec.insertBefore(line, svgSec.firstChild);\n                    }\n                }\n            });\n\n            if (selectedDotsSec.length > 0) {\n                if (currentLineSec) currentLineSec.remove();\n                const lastDot = selectedDotsSec[selectedDotsSec.length - 1];\n                currentLineSec = document.createElementNS('http://www.w3.org/2000/svg', 'line');\n                currentLineSec.setAttribute('x1', lastDot.cx);\n                currentLineSec.setAttribute('y1', lastDot.cy);\n                currentLineSec.setAttribute('x2', pos.x);\n                currentLineSec.setAttribute('y2', pos.y);\n                currentLineSec.setAttribute('stroke', '#ffc107');\n                currentLineSec.setAttribute('stroke-width', 2);\n                currentLineSec.setAttribute('stroke-dasharray', '5,5');\n                svgSec.appendChild(currentLineSec);\n            }\n        }\n\n        function stopDrawingSec() {\n            if (!isDrawingSec) return;\n            isDrawingSec = false;\n            if (currentLineSec) currentLineSec.remove();\n            patternInputSec.value = selectedDotsSec.map(d => d.index).join('');\n        }\n\n        function resetPatternSec() {\n            selectedDotsSec.length = 0;\n            svgSec.querySelectorAll('line').forEach(l => l.remove());\n            dotsSec.forEach(dot => {\n                dot.element.setAttribute('fill', '#555');\n                dot.element.setAttribute('r', 8);\n            });\n            patternInputSec.value = '';\n        }\n\n        svgSec.addEventListener('mousedown', startDrawingSec);\n        window.addEventListener('mousemove', handleMoveSec);\n        window.addEventListener('mouseup', stopDrawingSec);\n\n        svgSec.addEventListener('touchstart', (e) => { e.preventDefault(); startDrawingSec(e); });\n        svgSec.addEventListener('touchmove', (e) => { e.preventDefault(); handleMoveSec(e); });\n        svgSec.addEventListener('touchend', stopDrawingSec);\n\n        btnUpdatePattern.addEventListener('click', async () => {\n            const pattern = patternInputSec.value;\n            if (!pattern) {\n                patternStatus.textContent = 'Please draw a pattern first.';\n                patternStatus.className = 'mt-2 small text-danger';\n                return;\n            }\n\n            try {\n                const formData = new FormData();\n                formData.append('pattern', pattern);\n                const res = await fetch('/user/update-pattern', {\n                    method: 'POST',\n                    body: formData\n                });\n                const result = await res.json();\n                if (result.success) {\n                    patternStatus.textContent = 'Pattern updated successfully!';\n                    patternStatus.className = 'mt-2 small text-success';\n                } else {\n                    patternStatus.textContent = result.error || 'Update failed';\n                    patternStatus.className = 'mt-2 small text-danger';\n                }\n            } catch (err) {\n                patternStatus.textContent = err.message;\n                patternStatus.className = 'mt-2 small text-danger';\n            }\n        });\n\n        btnLinkWallet.addEventListener('click', async () => {\n            if (typeof window.ethereum === 'undefined') {\n                walletStatus.textContent = 'Ethereum wallet not found.';\n                walletStatus.className = 'mt-2 small text-danger';\n                return;\n            }\n\n            try {\n                const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });\n                const address = accounts[0];\n\n                const challengeRes = await fetch('/login/web3/challenge');\n                const { challenge } = await challengeRes.json();\n\n                const provider = new ethers.providers.Web3Provider(window.ethereum);\n                const signer = provider.getSigner();\n                const signature = await signer.signMessage(challenge);\n\n                const formData = new FormData();\n                formData.append('address', address);\n                formData.append('signature', signature);\n\n                const res = await fetch('/user/link-wallet', {\n                    method: 'POST',\n                    body: formData\n                });\n\n                const result = await res.json();\n                if (result.success) {\n                    walletStatus.textContent = 'Wallet linked successfully!';\n                    walletStatus.className = 'mt-2 small text-success';\n                    document.getElementById('wallet-address-input').value = address;\n                } else {\n                    walletStatus.textContent = result.error || 'Linking failed';\n                    walletStatus.className = 'mt-2 small text-danger';\n                }\n            } catch (err) {\n                walletStatus.textContent = err.message;\n                walletStatus.className = 'mt-2 small text-danger';\n            }\n        });\n\n        btnRegisterPasskey.addEventListener('click', async () => {\n            try {\n                const optionsRes = await fetch('/register/passkey/options');\n                const options = await optionsRes.json();\n\n                options.challenge = base64urlToUint8Array(options.challenge);\n                options.user.id = base64urlToUint8Array(options.user.id);\n                if (options.excludeCredentials) {\n                    options.excludeCredentials.forEach(cred => {\n                        cred.id = base64urlToUint8Array(cred.id);\n                    });\n                }\n\n                const credential = await navigator.credentials.create({\n                    publicKey: options\n                });\n\n                const regData = {\n                    id: credential.id,\n                    rawId: bufferToBase64Url(credential.rawId),\n                    type: credential.type,\n                    response: {\n                        attestationObject: bufferToBase64Url(credential.response.attestationObject),\n                        clientDataJSON: bufferToBase64Url(credential.response.clientDataJSON),\n                    }\n                };\n\n                const verifyRes = await fetch('/register/passkey/verify', {\n                    method: 'POST',\n                    headers: { 'Content-Type': 'application/json' },\n                    body: JSON.stringify(regData)\n                });\n\n                const result = await verifyRes.json();\n                if (result.success) {\n                    passkeyStatus.textContent = 'Passkey registered successfully!';\n                    passkeyStatus.className = 'mt-2 small text-success';\n                } else {\n                    passkeyStatus.textContent = result.error || 'Registration failed';\n                    passkeyStatus.className = 'mt-2 small text-danger';\n                }\n            } catch (err) {\n                passkeyStatus.textContent = err.message;\n                passkeyStatus.className = 'mt-2 small text-danger';\n            }\n        });\n\n        function base64urlToUint8Array(base64url) {\n            const padding = '='.repeat((4 - base64url.length % 4) % 4);\n            const base64 = (base64url + padding).replace(/\\-/g, '+').replace(/_/g, '/');\n            const rawData = window.atob(base64);\n            const outputArray = new Uint8Array(rawData.length);\n            for (let i = 0; i < rawData.length; ++i) {\n                outputArray[i] = rawData.charCodeAt(i);\n            }\n            return outputArray;\n        }\n\n        function bufferToBase64Url(buffer) {\n            const bytes = new Uint8Array(buffer);\n            let binary = '';\n            for (let i = 0; i < bytes.byteLength; i++) {\n                binary += String.fromCharCode(bytes[i]);\n            }\n            const base64 = window.btoa(binary);\n            return base64.replace(/\\+/g, '-').replace(/\\//g, '_').replace(/=/g, '');\n        }\n    });\n</script>\n<script src=\"/static/compression.js?v={{ range(1, 999999) | random }}\"></script>\n<script src=\"/static/script.js?v={{ range(1, 999999) | random }}\"></script>\n<script>\n    /*\n    if ('serviceWorker' in navigator) {\n        window.addEventListener('load', () => {\n            navigator.serviceWorker.register('/sw.js')\n                .then(reg => console.log('SW Registered', reg))\n                .catch(err => console.log('SW Reg Error', err));\n        });\n    }\n    */\n</script>\n</body>\n</html>\n",
    "login.html": "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n    <meta charset=\"UTF-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n    <title>Login - Gemini Agent</title>\n    <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css\" rel=\"stylesheet\">\n    <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css\">\n    <link rel=\"icon\" type=\"image/svg+xml\" href=\"/static/icon.svg?v=2\">\n    <link rel=\"manifest\" href=\"/manifest.json?v=3\">\n    <link rel=\"stylesheet\" href=\"/static/style.css\">\n    <style>\n        body {\n            height: 100vh;\n            display: flex;\n            align-items: center;\n            justify-content: center;\n            background-color: #121212;\n        }\n        .login-card {\n            width: 100%;\n            max-width: 400px;\n            padding: 2rem;\n            border-radius: 1rem;\n            background-color: #1e1e1e;\n            border: 1px solid #333;\n            box-shadow: 0 10px 30px rgba(0,0,0,0.5);\n        }\n    </style>\n    <script src=\"https://cdnjs.cloudflare.com/ajax/libs/ethers/5.7.2/ethers.umd.min.js\"></script>\n</head>\n<body class=\"text-light\">\n\n<div class=\"login-card\">\n    <div class=\"text-center mb-4\">\n        <h1 class=\"h3 mb-3\"><i class=\"bi bi-robot text-primary\"></i> Gemini Agent</h1>\n        <p class=\"text-muted\">Please sign in to continue</p>\n    </div>\n\n    {% if error %}\n    <div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">\n        {{ error }}\n        <button type=\"button\" class=\"btn-close\" data-bs-dismiss=\"alert\" aria-label=\"Close\"></button>\n    </div>\n    {% endif %}\n\n    <ul class=\"nav nav-pills nav-fill mb-4\" id=\"loginTabs\" role=\"tablist\">\n        <li class=\"nav-item\" role=\"presentation\">\n            <button class=\"nav-link active\" id=\"passkey-tab\" data-bs-toggle=\"pill\" data-bs-target=\"#passkey-login\" type=\"button\" role=\"tab\" aria-controls=\"passkey-login\" aria-selected=\"true\">Passkey</button>\n        </li>\n        <li class=\"nav-item\" role=\"presentation\">\n            <button class=\"nav-link\" id=\"password-tab\" data-bs-toggle=\"pill\" data-bs-target=\"#password-login\" type=\"button\" role=\"tab\" aria-controls=\"password-login\" aria-selected=\"false\">Password</button>\n        </li>\n        <li class=\"nav-item\" role=\"presentation\">\n            <button class=\"nav-link\" id=\"wallet-tab\" data-bs-toggle=\"pill\" data-bs-target=\"#wallet-login\" type=\"button\" role=\"tab\" aria-controls=\"wallet-login\" aria-selected=\"false\">Wallet</button>\n        </li>\n        <li class=\"nav-item\" role=\"presentation\">\n            <button class=\"nav-link\" id=\"pattern-tab\" data-bs-toggle=\"pill\" data-bs-target=\"#pattern-login\" type=\"button\" role=\"tab\" aria-controls=\"pattern-login\" aria-selected=\"false\">Pattern</button>\n        </li>\n    </ul>\n\n    <div class=\"tab-content\" id=\"loginTabsContent\">\n        <!-- Passkey Login -->\n        <div class=\"tab-pane fade show active\" id=\"passkey-login\" role=\"tabpanel\" aria-labelledby=\"passkey-tab\">\n            <div class=\"text-center py-4\">\n                <i class=\"bi bi-key display-1 text-info mb-3\"></i>\n                <div class=\"mb-3\">\n                    <label for=\"username-passkey\" class=\"form-label\">Username (Optional)</label>\n                    <input type=\"text\" class=\"form-control bg-dark text-light border-secondary\" id=\"username-passkey\" placeholder=\"Leave empty for auto-login\">\n                </div>\n                <button id=\"btn-passkey-login\" class=\"btn btn-info w-100 py-2 text-white\">\n                    Sign In with Passkey\n                </button>\n                <div id=\"passkey-error\" class=\"text-danger small mt-2\"></div>\n            </div>\n        </div>\n\n        <!-- Password Login -->\n        <div class=\"tab-pane fade\" id=\"password-login\" role=\"tabpanel\" aria-labelledby=\"password-tab\">\n            <form action=\"/login\" method=\"post\">\n                <div class=\"mb-3\">\n                    <label for=\"username\" class=\"form-label\">Username</label>\n                    <input type=\"text\" class=\"form-control bg-dark text-light border-secondary\" id=\"username\" name=\"username\" required autofocus>\n                </div>\n                <div class=\"mb-4\">\n                    <label for=\"password\" class=\"form-label\">Password</label>\n                    <input type=\"password\" class=\"form-control bg-dark text-light border-secondary\" id=\"password\" name=\"password\" required>\n                </div>\n                <button type=\"submit\" class=\"btn btn-primary w-100 py-2\">Sign In</button>\n            </form>\n        </div>\n\n        <!-- Wallet Login -->\n        <div class=\"tab-pane fade\" id=\"wallet-login\" role=\"tabpanel\" aria-labelledby=\"wallet-tab\">\n            <div class=\"text-center py-4\">\n                <i class=\"bi bi-wallet2 display-1 text-primary mb-3\"></i>\n                <p>Connect your MetaMask or Brave wallet to sign in.</p>\n                <button id=\"btn-wallet-login\" class=\"btn btn-outline-primary w-100 py-2\">\n                    <img src=\"data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAzMTguNiAzMTguNiI+PHBhdGggZmlsbD0iI0UyN0MxMSIgZD0iTTEyOC42IDYuOGwtMjIuNSAzNi4zIDM0LjYgMjIuM3oiLz48cGF0aCBmaWxsPSIjRTI3QzExIiBkPSJNMTkwIDYuOGwyMi41IDM2LjMtMzQuNiAyMi4zeiIvPjxwYXRoIGZpbGw9IiNFNDc2MTkiIGQ9Ik05OC4zIDY5LjFsLTI5LjEtNCA1MS42IDM4LjV6Ii8+PHBhdGggZmlsbD0iI0U0NzYxOSIgZD0iTTcyMC4zIDY5LjFsMjkuMS00LTUxLjYgMzguNXoiLz48cGF0aCBmaWxsPSIjRTRDMTMzIiBkPSJNOTguNSAxOTMuOGwtMjkuNyA0LjUgMjUuNiA1NnoiLz48cGF0aCBmaWxsPSIjRTRDMjMyIiBkPSJNOTQuNCAyMjMuN2wzOC4zIDE3LjMtMjQuOC00Ny4zeiIvPjxwYXRoIGZpbGw9IiNFNUMxMzMiIGQ9Ik0yMjQuMiAyMjMuN2wtMzguMyAxNy4zIDI0LjgtNDcuM3oiLz48cGF0aCBmaWxsPSIjRTRDMjMyIiBkPSJNMjIwLjEgMTk4LjhsMjkuNyA0LjUtMjUuNiA1NnoiLz48cGF0aCBmaWxsPSIjRTRDMjMyIiBkPSJNMTU5LjMgMTI0LjNsLTI3LjIgOTEuNCAyNy4yIDE0LjIgMjcuMi0xNC4yLTExLjYtOTEuNHoiLz48cGF0aCBmaWxsPSIjRTRDMjMyIiBkPSJNMTU5LjMgMjMwLjFsLTI3LjIgMTQuMkwxNTkuMyAzMTBsMjcuMi02NS43eiIvPjxwYXRoIGZpbGw9IiNGNjhCMTgiIGQ9Ik02OC44IDY1LjFsMTAwLjUgMTguNkwxNTkuMyA2LjhsLTMwLjcgNTguM3oiLz48cGF0aCBmaWxsPSIjRjY4QjE4IiBkPSJNMjQ5LjggNjUuMWwtMTAwLjUgMTguNkwxNTkuMyA2LjhsMzAuNyA1OC4zeiIvPjxwYXRoIGZpbGw9IiNGNjhCMTgiIGQ9Ik02OS4xIDE5OC4zbDU0LjIgMzIuN0wxNTkuMyAxODdsLTM0LjgtNDYuM3oiLz48cGF0aCBmaWxsPSIjRjY4QjE4IiBkPSJNMjQ5LjUgMTk4LjNsLTU0LjIgMzIuN0wxNTkuMyAxODdsMzQuOC00Ni4zeiIvPjxwYXRoIGZpbGw9IiNGNjhCMTgiIGQ9Ik02OS4xIDE5OC4zbDI1LjYgNTZMMTU5LjMgMzEwbC0yNy4yLTY1Ljd6Ii8+PHBhdGggZmlsbD0iI0Y2OEIxOCIgZD0iTTI0OS41IDE5OC4zbC0yNS42IDU2TDE1OS4zIDMxMGwyNy4yLTY1Ljd6Ii8+PC9zdmc+\" alt=\"MetaMask\" style=\"height: 20px; margin-right: 10px;\">\n                    Sign In with Wallet\n                </button>\n                <div id=\"wallet-error\" class=\"text-danger small mt-2\"></div>\n            </div>\n        </div>\n\n        <!-- Pattern Login -->\n        <div class=\"tab-pane fade\" id=\"pattern-login\" role=\"tabpanel\" aria-labelledby=\"pattern-tab\">\n            <form id=\"pattern-form\" action=\"/login/pattern\" method=\"post\">\n                <div class=\"mb-3\">\n                    <label for=\"username-pattern\" class=\"form-label\">Username (Optional)</label>\n                    <input type=\"text\" class=\"form-control bg-dark text-light border-secondary\" id=\"username-pattern\" name=\"username\" placeholder=\"Leave empty for auto-login\">\n                </div>\n                <div class=\"mb-3 text-center\">\n                    <label class=\"form-label d-block\">Draw Pattern</label>\n                    <div id=\"pattern-container\" class=\"mx-auto\" style=\"width: 250px; height: 250px; position: relative; touch-action: none;\">\n                        <svg id=\"pattern-svg\" width=\"250\" height=\"250\" style=\"background: #252525; border-radius: 10px;\"></svg>\n                    </div>\n                    <input type=\"hidden\" id=\"pattern-input\" name=\"pattern\">\n                </div>\n                <button type=\"submit\" class=\"btn btn-primary w-100 py-2\">Sign In with Pattern</button>\n            </form>\n        </div>\n    </div>\n    \n    <div class=\"text-center mt-4\">\n    </div>\n</div>\n\n<script src=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js\"></script>\n<script>\n    document.addEventListener('DOMContentLoaded', () => {\n        // ... (existing pattern logic)\n        const svg = document.getElementById('pattern-svg');\n        // ...\n        const patternInput = document.getElementById('pattern-input');\n        const container = document.getElementById('pattern-container');\n        const dots = [];\n        const selectedDots = [];\n        let isDrawing = false;\n        let currentLine = null;\n\n        // Create 3x3 grid\n        for (let y = 0; y < 3; y++) {\n            for (let x = 0; x < 3; x++) {\n                const cx = 50 + x * 75;\n                const cy = 50 + y * 75;\n                const index = y * 3 + x + 1;\n                \n                const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');\n                dot.setAttribute('cx', cx);\n                dot.setAttribute('cy', cy);\n                dot.setAttribute('r', 10);\n                dot.setAttribute('fill', '#555');\n                dot.setAttribute('data-index', index);\n                svg.appendChild(dot);\n                dots.push({ cx, cy, index, element: dot });\n            }\n        }\n\n        function getMousePos(e) {\n            const rect = svg.getBoundingClientRect();\n            const clientX = e.touches ? e.touches[0].clientX : e.clientX;\n            const clientY = e.touches ? e.touches[0].clientY : e.clientY;\n            return {\n                x: clientX - rect.left,\n                y: clientY - rect.top\n            };\n        }\n\n        function startDrawing(e) {\n            isDrawing = true;\n            resetPattern();\n            handleMove(e);\n        }\n\n        function handleMove(e) {\n            if (!isDrawing) return;\n            const pos = getMousePos(e);\n            \n            // Check if near a dot\n            dots.forEach(dot => {\n                const dist = Math.hypot(pos.x - dot.cx, pos.y - dot.cy);\n                if (dist < 25 && !selectedDots.includes(dot)) {\n                    selectedDots.push(dot);\n                    dot.element.setAttribute('fill', '#0d6efd');\n                    dot.element.setAttribute('r', 15);\n                    \n                    if (selectedDots.length > 1) {\n                        const prevDot = selectedDots[selectedDots.length - 2];\n                        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');\n                        line.setAttribute('x1', prevDot.cx);\n                        line.setAttribute('y1', prevDot.cy);\n                        line.setAttribute('x2', dot.cx);\n                        line.setAttribute('y2', dot.cy);\n                        line.setAttribute('stroke', '#0d6efd');\n                        line.setAttribute('stroke-width', 4);\n                        svg.insertBefore(line, svg.firstChild);\n                    }\n                }\n            });\n\n            // Update floating line\n            if (selectedDots.length > 0) {\n                if (currentLine) currentLine.remove();\n                const lastDot = selectedDots[selectedDots.length - 1];\n                currentLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');\n                currentLine.setAttribute('x1', lastDot.cx);\n                currentLine.setAttribute('y1', lastDot.cy);\n                currentLine.setAttribute('x2', pos.x);\n                currentLine.setAttribute('y2', pos.y);\n                currentLine.setAttribute('stroke', '#0d6efd');\n                currentLine.setAttribute('stroke-width', 2);\n                currentLine.setAttribute('stroke-dasharray', '5,5');\n                svg.appendChild(currentLine);\n            }\n        }\n\n        function stopDrawing() {\n            if (!isDrawing) return;\n            isDrawing = false;\n            if (currentLine) currentLine.remove();\n            patternInput.value = selectedDots.map(d => d.index).join('');\n        }\n\n        function resetPattern() {\n            selectedDots.length = 0;\n            svg.querySelectorAll('line').forEach(l => l.remove());\n            dots.forEach(dot => {\n                dot.element.setAttribute('fill', '#555');\n                dot.element.setAttribute('r', 10);\n            });\n            patternInput.value = '';\n        }\n\n        svg.addEventListener('mousedown', startDrawing);\n        window.addEventListener('mousemove', handleMove);\n        window.addEventListener('mouseup', stopDrawing);\n\n        svg.addEventListener('touchstart', (e) => { e.preventDefault(); startDrawing(e); });\n        svg.addEventListener('touchmove', (e) => { e.preventDefault(); handleMove(e); });\n        svg.addEventListener('touchend', stopDrawing);\n\n        // --- Wallet Login ---\n        const btnWalletLogin = document.getElementById('btn-wallet-login');\n        const walletError = document.getElementById('wallet-error');\n\n        btnWalletLogin.addEventListener('click', async () => {\n            if (typeof window.ethereum === 'undefined') {\n                walletError.textContent = 'Ethereum wallet not found. Please install MetaMask.';\n                return;\n            }\n\n            try {\n                // Request account access\n                const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });\n                const address = accounts[0];\n\n                // Get challenge from server\n                const challengeRes = await fetch('/login/web3/challenge');\n                const { challenge } = await challengeRes.json();\n\n                // Request signature\n                const provider = new ethers.providers.Web3Provider(window.ethereum);\n                const signer = provider.getSigner();\n                const signature = await signer.signMessage(challenge);\n\n                // Verify signature on server\n                const formData = new FormData();\n                formData.append('address', address);\n                formData.append('signature', signature);\n\n                const verifyRes = await fetch('/login/web3/verify', {\n                    method: 'POST',\n                    body: formData\n                });\n\n                const result = await verifyRes.json();\n                if (result.success) {\n                    window.location.href = '/';\n                } else {\n                    walletError.textContent = result.error || 'Login failed';\n                }\n            } catch (err) {\n                console.error(err);\n                walletError.textContent = err.message || 'An error occurred during wallet login';\n            }\n        });\n\n        // --- Passkey Login ---\n        const btnPasskeyLogin = document.getElementById('btn-passkey-login');\n        const passkeyError = document.getElementById('passkey-error');\n        const usernamePasskey = document.getElementById('username-passkey');\n\n        btnPasskeyLogin.addEventListener('click', async () => {\n            const username = usernamePasskey.value;\n            \n            try {\n                // Get authentication options from server\n                const formData = new FormData();\n                if (username) {\n                    formData.append('username', username);\n                }\n                \n                const optionsRes = await fetch('/login/passkey/options', {\n                    method: 'POST',\n                    body: formData\n                });\n\n                if (!optionsRes.ok) {\n                    const errData = await optionsRes.json();\n                    throw new Error(errData.error || 'User not found or no passkeys registered');\n                }\n\n                const options = await optionsRes.json();\n\n                // Convert base64url to Uint8Array for the browser\n                options.challenge = base64urlToUint8Array(options.challenge);\n                if (options.allowCredentials) {\n                    options.allowCredentials.forEach(cred => {\n                        cred.id = base64urlToUint8Array(cred.id);\n                    });\n                }\n\n                // Call the browser's credential API\n                const credential = await navigator.credentials.get({\n                    publicKey: options\n                });\n\n                // Prepare data for verification\n                const authData = {\n                    id: credential.id,\n                    rawId: bufferToBase64Url(credential.rawId),\n                    type: credential.type,\n                    response: {\n                        authenticatorData: bufferToBase64Url(credential.response.authenticatorData),\n                        clientDataJSON: bufferToBase64Url(credential.response.clientDataJSON),\n                        signature: bufferToBase64Url(credential.response.signature),\n                        userHandle: credential.response.userHandle ? bufferToBase64Url(credential.response.userHandle) : null\n                    }\n                };\n\n                // Verify authentication on server\n                const verifyRes = await fetch('/login/passkey/verify', {\n                    method: 'POST',\n                    headers: {\n                        'Content-Type': 'application/json'\n                    },\n                    body: JSON.stringify(authData)\n                });\n\n                const result = await verifyRes.json();\n                if (result.success) {\n                    window.location.href = '/';\n                } else {\n                    passkeyError.textContent = result.error || 'Passkey authentication failed';\n                }\n            } catch (err) {\n                console.error(err);\n                passkeyError.textContent = err.message || 'An error occurred during passkey login';\n            }\n        });\n\n        // Helper functions for WebAuthn\n        function base64urlToUint8Array(base64url) {\n            const padding = '='.repeat((4 - base64url.length % 4) % 4);\n            const base64 = (base64url + padding).replace(/\\-/g, '+').replace(/_/g, '/');\n            const rawData = window.atob(base64);\n            const outputArray = new Uint8Array(rawData.length);\n            for (let i = 0; i < rawData.length; ++i) {\n                outputArray[i] = rawData.charCodeAt(i);\n            }\n            return outputArray;\n        }\n\n        function bufferToBase64Url(buffer) {\n            const bytes = new Uint8Array(buffer);\n            let binary = '';\n            for (let i = 0; i < bytes.byteLength; i++) {\n                binary += String.fromCharCode(bytes[i]);\n            }\n            const base64 = window.btoa(binary);\n            return base64.replace(/\\+/g, '-').replace(/\\//g, '_').replace(/=/g, '');\n        }\n    });\n</script>\n<script>\n    /*\n    if ('serviceWorker' in navigator) {\n        window.addEventListener('load', () => {\n            navigator.serviceWorker.register('/sw.js')\n                .then(reg => console.log('SW Registered', reg))\n                .catch(err => console.log('SW Reg Error', err));\n        });\n    }\n    */\n</script>\n</body>\n</html>\n",
    "setup.html": "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n    <meta charset=\"UTF-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n    <title>Setup - Gemini Agent</title>\n    <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css\" rel=\"stylesheet\">\n    <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css\">\n    <link rel=\"icon\" type=\"image/svg+xml\" href=\"/static/icon.svg?v=2\">\n    <link rel=\"stylesheet\" href=\"/static/style.css\">\n    <style>\n        body {\n            height: 100vh;\n            display: flex;\n            align-items: center;\n            justify-content: center;\n            background-color: #121212;\n        }\n        .setup-card {\n            width: 100%;\n            max-width: 450px;\n            padding: 2.5rem;\n            border-radius: 1rem;\n            background-color: #1e1e1e;\n            border: 1px solid #333;\n            box-shadow: 0 10px 30px rgba(0,0,0,0.5);\n        }\n    </style>\n</head>\n<body class=\"text-light\">\n\n<div class=\"setup-card\">\n    <div class=\"text-center mb-4\">\n        <h1 class=\"h3 mb-3\"><i class=\"bi bi-robot text-primary\"></i> Initial Setup</h1>\n        <p class=\"text-muted\">Create your administrator account to begin.</p>\n    </div>\n\n    <form action=\"/setup\" method=\"post\">\n        <div class=\"mb-3\">\n            <label class=\"form-label\">Username</label>\n            <input type=\"text\" class=\"form-control bg-dark text-light border-secondary\" value=\"admin\" disabled>\n            <div class=\"form-text\">The default administrator username is 'admin'.</div>\n        </div>\n        <div class=\"mb-3\">\n            <label for=\"origin\" class=\"form-label\">Application Origin (URL)</label>\n            <input type=\"url\" class=\"form-control bg-dark text-light border-secondary\" id=\"origin\" name=\"origin\" value=\"http://localhost:8000\" required>\n            <div class=\"form-text\">The full URL where this app is hosted (e.g., https://myapp.example.com).</div>\n        </div>\n        <div class=\"mb-3\">\n            <label for=\"rp_id\" class=\"form-label\">RP ID (Domain)</label>\n            <input type=\"text\" class=\"form-control bg-dark text-light border-secondary\" id=\"rp_id\" name=\"rp_id\" value=\"localhost\" required>\n            <div class=\"form-text\">The domain for WebAuthn/Passkeys (e.g., myapp.example.com). Usually the domain part of the Origin.</div>\n        </div>\n        <div class=\"mb-4\">\n            <label for=\"password\" class=\"form-label\">Admin Password</label>\n            <input type=\"password\" class=\"form-control bg-dark text-light border-secondary\" id=\"password\" name=\"password\" required autofocus>\n            <div class=\"form-text\">Choose a strong password for your local agent.</div>\n        </div>\n        <button type=\"submit\" class=\"btn btn-info w-100 py-2 text-white\">Complete Setup</button>\n    </form>\n</div>\n\n<script src=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js\"></script>\n<script>\n    document.addEventListener('DOMContentLoaded', () => {\n        const originInput = document.getElementById('origin');\n        const rpIdInput = document.getElementById('rp_id');\n        \n        // Auto-fill based on current URL\n        if (window.location.origin) {\n            originInput.value = window.location.origin;\n        }\n        if (window.location.hostname) {\n            rpIdInput.value = window.location.hostname;\n        }\n    });\n</script>\n</body>\n</html>\n"
}


STATIC = {
    "compression.js": {
        "content": "/**\n * Compresses an image file client-side.\n * @param {File} file - The original image file.\n * @returns {Promise<File>} - A promise that resolves to the compressed WebP File.\n */\nasync function compressImage(file) {\n    // Only compress images\n    if (!file.type.startsWith('image/')) {\n        return file;\n    }\n\n    return new Promise((resolve, reject) => {\n        const reader = new FileReader();\n        reader.onload = (e) => {\n            const img = new Image();\n            img.onload = () => {\n                const canvas = document.createElement('canvas');\n                let width = img.width;\n                let height = img.height;\n                const maxDim = 1536;\n\n                // Calculate new dimensions\n                if (width > maxDim || height > maxDim) {\n                    if (width > height) {\n                        height = Math.round((height * maxDim) / width);\n                        width = maxDim;\n                    } else {\n                        width = Math.round((width * maxDim) / height);\n                        height = maxDim;\n                    }\n                }\n\n                canvas.width = width;\n                canvas.height = height;\n                const ctx = canvas.getContext('2d');\n                \n                // Use better image scaling if supported\n                ctx.imageSmoothingEnabled = true;\n                ctx.imageSmoothingQuality = 'high';\n                \n                ctx.drawImage(img, 0, 0, width, height);\n\n                // Convert to WebP with 0.8 quality\n                canvas.toBlob((blob) => {\n                    if (blob) {\n                        // Create a new File object with .webp extension\n                        const newFileName = file.name.replace(/\\.[^/.]+$/, \"\") + \".webp\";\n                        const compressedFile = new File([blob], newFileName, {\n                            type: 'image/webp',\n                            lastModified: Date.now()\n                        });\n                        resolve(compressedFile);\n                    } else {\n                        // Fallback to original if compression fails\n                        resolve(file);\n                    }\n                }, 'image/webp', 0.8);\n            };\n            img.onerror = () => reject(new Error('Failed to load image for compression.'));\n            img.src = e.target.result;\n        };\n        reader.onerror = () => reject(new Error('Failed to read file for compression.'));\n        reader.readAsDataURL(file);\n    });\n}",
        "encoding": "text"
    },
    "favicon.ico": {
        "content": "AAABAAMAEBAAAAAAIAD4AQAANgAAABgYAAAAACAAkwIAAC4CAAAgIAAAAAAgAMAAAADBBAAAiVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAABv0lEQVR4nKWTv2sUURDHP2/3ZXezd5e7pBEFQcQyjYJFwD6FEGyFFP4FNnaiTaorLEQstLMOJKQJmMIUqUWEiI1NCFoJAZPLunt770Zm357ZHIKEfOHtj5md78x8Z9Z0HjvhEgi4JOzkwZiLBYpMEZTuzPg/aLKgPrYyAPMphIE/6hi580FBw66q5SUUJdjRGHopfHwaVMy/MigcLNSEWpXaT3IoRtCOoTsLr3aFtS3B6gc2gMjCUn/M3RuGe7fg5QfhdAgzAeRDWF40LN2E5xvCi4eGaz0Q12hBP9ZMb1dNleUog2frQtqGVgxvVg2Jhf0fcHgEV7t1a6ii+Ewq5N43YVDA50NIWz5YGvb97zCXwHh6CiPnme/3hbAjuGMgguwUcLDcF+K2UBzAgzsGN54iuL4A7x4ZBrnvKQrPskyqVL2KHFZuG95/8U6rSmdDWNsWrnS88kqgijfXIjTeFyWw+UnY+SpEs2D0X1DmQeZLraJ0QdTZIChLvdSKqz+GNJ5MwcD8nL+rFjrnvScBrcS/2xBe7wr9baHXAd0d1UBbrCr416p2kzpbDd283/Wom/grYhPa0s/BedtkxafxB4ttpx3tGBmIAAAAAElFTkSuQmCCiVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAACWklEQVR4nO2Vu2sUURTGf/fO7Ntslv0HRLDzD4hKwEoUbEQLC0WwsEmRxkIRtBAEy6jFIoJYKZY2EmQFFVtBxOCjEQ0GRFlEEzWzO3Pl3DvrPHaWBJd0fjAw98655zvfedxRU/OhYQuht9K54D/BhvDTi5IHin+HwZ2PgEGYI5CPvW/xy6TwodkAY2ICeSn5cOmosip0LMPTji+SkIqgwFOJTWTc+3IPbj0zVCsxgXwoabhwaJIEJXj7GTqPDPVqKkVB6J6FruH8XcN0G2Z2uFx238B0zSlVyuVZbEXp7E5n8/gdRH14flFnspwpctlzEsMQrh7TnJhx+3N3DDeeGOoVp1ZIxGnnuOLUXqd6/p7h+n1jUy2BjB00e3E0sM5/BbA+gHMHFdEAyr6ri5C0G1jnf20OCCv4OY8jBFI0AlhagVoZKj4sLhm0lxRbbNYCeLFsMjaITa4LMymyGxq8ARzuRJyeVTa6yw8MU/WkayT3PwOxMcztcwquLBq8BoTRBgRyMOzD+69w9rYkHHTTOUlD6vDhS2JTbkG45hTYLOQJ5EAwgO1t2L0LWs1k5vrxVGYQF9v33FLS930VqiVY/V1AIAMmRTy5R9lnErxayRFoDet92L/gEmiLmeIoxVGOiDDxnRPb2qvBcwrqNVcPS2AvKAPd10VegB9jQpXLcVu27+22hkYldRcN0ZJOSUFIZfjOHHF3VHpfOuljD24+NdTiAUwrG64zBPkWk7X0uAxaEV5+gmsPDdXy6Nkh1GZ++t6YH2s60nEYmYMiSPsWRhcP3cQE4xRsBn8A0V/jWKXcSNMAAAAASUVORK5CYIKJUE5HDQoaCgAAAA1JSERSAAAAIAAAACAIBgAAAHN6evQAAACHSURBVHic7VbLCoAwDOtKr+5T9Vv8Ve8+2HVU1jI1E5rbWNqFtISlad5PAoKRj4eAcCAcCAcKpA6GbX0/m/JyDOyApvIpaO6Kt9AizMNnTzPt3MtnAoOHF5CrGbZm6uVLS4ClSQ+fCQxGC5C7iy8iuQDuQIpvOYEh3gLLcv4qB1IsIYEBF3ABjJonKrc/GToAAAAASUVORK5CYII=",
        "encoding": "base64"
    },
    "icon-192.png": {
        "content": "iVBORw0KGgoAAAANSUhEUgAAAMAAAADACAYAAABS3GwHAAAEJUlEQVR4nO3dS44bNxiFUbXhqWup9lqy1ZrbDgwkQAbpRC3X47+850wNA2ySH0uPkvT25ev3nw8o9enuAcCdBEA1AVBNAFQTANUEQDUBUE0AVBMA1QRANQFQTQBUEwDVBEA1AVBNAFQTANUEQDUBUE0AVBMA1QRANQFQTQBUEwDVBEA1AVDt890DaLT/8e/nzvbtx+Vjaffmy3Hv3fTvEcM1PAQauPlf/T98nCvAiY7axK4G53HMnOTIE9zV4DwCoJoATnDGie0qcA4BBG1UERxPAFQTANUEEPYQxcOgYwmAagKgmgCoJgCqCYBqAqCaAA50xV2b7gw9lgCoJgCqCSDoIYqHP8cTQMhGtfnPIQCqCeAkR57YTv/z+FD8BV69g9PGP58rwAVe2cg2/zVcAYZdDWz8a7kCUE0AVBMA1QRANQFQTQBUEwDVlnkfwPflXG9b4BdtogOw6efYQmP4lLrxbf5Z9tBftIkbdepEN9gDD6ao0aZNbqs9aJ1iRpo0qTxi1itilCmTSd66jR9hwiSSu36jXwb149Jz7Yv88PfnxwKmTu7Ktr/mfPoJ/3/Gjv7ZibX577U9efhMDWXmqJ5k88+wBV+BYwNInvQVbaHrMTKAqZdL1lvXeSNa+LRZ3Ra4LpEBwFEEQDUBUE0AVBMA1QRANQFQTQBUEwDVBEC1JT4PcOV9K9Pf7k8d910E8MEbtv7+92kbKnXcdxPAi3cqTtlQqeOewnOA37xN985bfFPHPUn9LByxEe7YTKnjnsYMUK06gCNPwCtP09RxT9T911OvNoAzTr4rTtPUcU/V+5eDAGjnCkA1AVBNAFSrDeCMe2GuuL8mddxT1QYAj/YAjjz5rjxFU8c9UXUAUB/AESfgHado6rinqQ/gdzfCnZsoddyT+ETYi795NWUDpY57CgF8cENN3UCp476bAN6RumFSx30XzwGoJgCqCYBqAqCaAKgmAKoJgGoCoJoAqCYAqgmAagKgmgCoJgCqCYBqAqCaD8Qs8LXiPgTzuhkrCDcRANUEQDUBUE0AVBMA1SIDmPLyI/nrMvJ9gF+vaydMptff8+dr/i57R0IgTfbQ9cgcdfikr2Z/Yh0mnv6/jN1Bz06YCO61hx9Cb1++fv/5WGSCp54yK9oXWZeRT4JbTyOuN37HTD49yF+/8QEkTCK56xYRQMpkkrdeMQEkTWq7LWidogJIm9w227cfcesz/mXQ/+JVnxm2sE2/TAD/JIbrbcEbf7kAoOI5ABxJAFQTANUEQDUBUE0AVBMA1QRANQFQTQBUEwDVBEA1AVBNAFQTANUEQDUBUE0AVBMA1QRANQFQTQBUEwDVBEA1AVBNAFQTANUEQDUBUE0AVBMA1QRANQFQTQBUEwDVBEA1AVBNAFQTANUEQDUBUE0AVBMA1QTAo9mfe7MWsxDnphoAAAAASUVORK5CYII=",
        "encoding": "base64"
    },
    "icon-512.png": {
        "content": "iVBORw0KGgoAAAANSUhEUgAAAgAAAAIACAYAAAD0eNT6AAANU0lEQVR4nO3dQW4cRxJAUWugrXRU8Sy6KveiBoLHhkY2QVIkuzLiv7cyPBgzq7oz43exZX/49OXb9z8AgJT/XL0AAOD2BAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAj6ePUCgPd3//Vlrf/57uHd1gKc4cOnL9++X70I4NqB/xRBAPsIAFjirYf+Y8QA7CAAYLhbDf5fCQGYTQDAUFcN/l8JAZjpjBMEGDn8T1sL8HyeAMAgpw9bTwNgjrNPE2DM8J+yRuBPdisMMGmwTlorlNmpcLiJA3XimqHGLoWDTR6kk9cOBXYoHGrDAN1wDbCV3QkH2jQ4N10LbGJnwmE2DsyN1wTT2ZVwkM2DcvO1wUR2JAAECQA4ROETcuEaYQq7EQ5QGoyla4WT2YkAECQA4GLFT8TFa4bT2IUAECQAACBIAMCFyo/Cy9cOJ7ADASBIAMBFfAJ2D+BKAgAAggQAAAQJAAAIEgAAECQA4AK+AOhewNUEAAAECQAACBIAABAkAAAgSAAAQJAAAIAgAQAAQQIAAIIEAAAECQAACBIAcIHPdw/uu3sBlxIAABAkAAAgSAAAQJAAAIAgAQAX8UVA9wCuJAAAIEgAwIXKTwHK1w4nEAAAECQAACBIAMDFio/Ci9cMpxEAABAkAOAApU/EpWuFkwkAOERhMBauEaYQAAAQJADgIJs/IW++NphIAMBhNg7KjdcE0wkAONCmgbnpWmATAQCH2jA4N1wDbCUA4GCTB+jktUOBAIDDTRykE9cMNQIABpg0UCetFcoEAAwxYbBOWCPwpw+fvnz7/r+/Boa4/3pWuxv8MM9ZpwgwbuCetBbg+TwBgOGuehpg8MNsAgCWuFUIGPywgwCAZd4rBAx+2MV3AAAgSAAAQJAAAIAgAQAAQQIAAIIEAAAECQAACBIAABAkAAAgSAAAQJAAAIAgAQAAQQIAAIIEAAAECQAACBIAABAkAAAgSAAAQJAAAIAgAQAAQQIAAIIEAAAEffj05dv3qxfB2e6/6kSY5vPdw9VL4HACgH8w8GEnUcDPBAAGPgSJAQRAmE/6wA9ioEkABBn8wL8RAi0CIMTgB55DCDQIgACDH/gdQmA3f75r+eA3/IHXnCHs5dVdysYF3uoscZ7sJAAWslkB5wpP8R2ARQx+4BZ8N2AHTwCWMPwB5w0vIQAWMPwB5w4vJQCGM/wB5w+/QwAMZvgDV3MOzSUAhrLpgFM4j2YSAAPZbMBpnEvzCAAACBIAw6hs4FTOp1kEwCA2F3A659QcAmAImwqYwnk1gwAAgCD/LYABTqlp//5vON8p58UPzoyzfbx6AZzNBobZe/akIOAsngAc7orNa+jDPleFgPPkXNKQ/2Ozwt69bX/zM08ADnbLYncwQIvzBU8AMPwhSPQjAOJ17hCArlvtf19EPJMACDP8AedAlwA40C1q2aYHbnkeeApwHgEQZPgDzgUEAAAECYAYn/4B5wM/CIDDvOfvyQx/4Eq+B3AWAQDA33xQ6BAAABAkACJUPeC84GcC4CB+PwZs55w7hwAAgCABEODxP+Dc4FcCAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABH28egFwa/dfn9+9n+8e3nUtvC+vNTxOALDeS4bAU/9fQXA2rzU8nwBgrdcMg6f+mULgLF5reDkBwDrvMQwe+xlC4Fpea/h9AoA1bjEMHvuZQuCa+37Fz/Ras4U/BcAKVwyEk35+ydX3+uqfD2/FO5nxTjmQT1nHZqfc41PWAa/hVwCMdeIh7DHx+97Xk3itme68XQVDB8Kk9U1y+r08fX3wGO9cxply4E5Z58mm3MMp64SfedcCQJAAYJRpn7Smrfck0+7dtPWCdyxjTD1gp677SlPv2dR10+TdygjTD9bp67+l6fdq+vrp8E4FgCABwPG2fKLach3vacs92nId7OZdCgBBAoCjbfskte163tK2e7PtetjHOxQAggQAx9r6CWrrdb3G1nuy9brYwbsTAIIEAAAECQAACBIAHGn77063X99LbL8X26+PubwzASBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkADgSJ/vHv7YbPv1vcT2e7H9+phLAABAkAAAgCABAABBAoBjbf3d6dbreo2t92TrdbGDAACAIAHA0bZ9gtp2PW9p273Zdj3sIwAAIEgAcLwtn6S2XMd72nKPtlwHuwkAAAgSAIww/RPV9PXf0vR7NX39dAgAxph6sE5d95Wm3rOp66ZJADDKtAN22npPMu3eTVsvCAAACBIAjDPlk9aUdZ5syj2csk74mQBgpNMP3NPXN8np9/L09cFjPj76v8Dh/jp477+e07GGwfveV681vJ1zTk4YPnRPWcdmp9zjU9YBryEAWOHqA/nqn19y9b2++ufDW/ErANa44jGxYXANrzW8ngBgnVsMB4P/DF5r+H0CgLXeYzgY/GfyWsPLCQDW+3VovyQIDPxZvNbwfAKAHEO9w2sNj/OnAAAgSAAAQJAAAIAgAQAAQQIAAIIEAAAECQAACBIAABAkAAAgSAAAQJAAAIAgAQAAQQIAAIIEAAAECQAACBIAABAkAAAgSAAAQJAAAIAgAQAAQQIAAIIEAAAECQAACBIAABAkAAAgSAAAQJAAAIAgAQAAQQIAAIIEAAAECQAACBIAABAkAAAgSAAAQJAAAIAgAQAAQQIAAIIEAAAECQAACBIAABAkAAAgSAAAQJAAAIAgAQAAQR+vXgBscf9VT9/C57uHm/wc2M6JBQBBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAAT4z9QCzg1+JQAAIEgAHOTz3cPVSwB4V865cwgAAAgSABG+BwA4L/iZAACAIAEQ4ikA4JzgLx///iuO+YKMQT2TLzeBPTKJJwAx4gJwPvCDAADAh4MgARB8lOwpAHBrfkV2HgEQJQIA50GbAAgTAYBzoEsAxB+X2fzQdav97/H/mQQAIgCCg1/8IwAOdstqdiBAw60Hv0//5/IvAuJfDwebFnbxiZ9fffj05dv3f/xdjnLlxhUCMJvzg8d4AsCzDw8xAOfzSZ/n8gRgCJsamMQHhvP5EuAQNhMwhfNqBgEAAEECYBBVDZzOOTWHABjG5gJO5XyaRQAA8GqG/zwCYCAbDYDXEgBDiQDgFM6jmQTAYDYdcDXn0FwCYDibD3D+8DsEwAIiAHDu8FICYAkRANzqrHHe7CAAFrExgfc+Y9hDACxkkwLOFZ4iAJYSAcBbnSXOk50EwGI2LvDaM4S9Pnz68u371YvgNu6/6j3gaQZ/gwAIEgLAvzH4WwRAmBAAfjD4mwQAQgCCDH0EAP/gyQDsZOjzMwHAkwQBzGPY8xQBAABB/lwYAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAA/uj5L6LqtPlW5pLRAAAAAElFTkSuQmCC",
        "encoding": "base64"
    },
    "icon.svg": {
        "content": "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"100\" height=\"100\" viewBox=\"0 0 16 16\">\n  <rect width=\"16\" height=\"16\" rx=\"2\" fill=\"#0d6efd\"/>\n  <path d=\"M6 12.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 0 1h-3a.5.5 0 0 1-.5-.5M3 8.062C3 6.76 4.235 5.765 5.53 5.886a26.6 26.6 0 0 0 4.94 0C11.765 5.765 13 6.76 13 8.062v1.157a.93.93 0 0 1-.765.935c-.845.147-2.34.346-4.235.346s-3.39-.2-4.235-.346A.93.93 0 0 1 3 9.219zm4.542-.827a.25.25 0 0 0-.217.068l-.92.9a25 25 0 0 1-1.871-.183.25.25 0 0 0-.068.495c.55.076 1.232.149 2.02.193a.25.25 0 0 0 .189-.071l.754-.736.847 1.71a.25.25 0 0 0 .404.062l.932-.97a25 25 0 0 0 1.922-.188.25.25 0 0 0-.068-.495c-.538.074-1.207.145-1.98.189a.25.25 0 0 0-.166.076l-.754.785-.842-1.7a.25.25 0 0 0-.182-.135\" fill=\"white\"/>\n  <path d=\"M8.5 1.866a1 1 0 1 0-1 0V3h-2A4.5 4.5 0 0 0 1 7.5V8a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1v1a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-1a1 1 0 0 0 1-1V9a1 1 0 0 0-1-1v-.5A4.5 4.5 0 0 0 10.5 3h-2zM14 7.5V13a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V7.5A3.5 3.5 0 0 1 5.5 4h5A3.5 3.5 0 0 1 14 7.5\" fill=\"white\"/>\n</svg>\n",
        "encoding": "text"
    },
    "manifest.json": {
        "content": "{\n  \"name\": \"Gemini Termux Agent\",\n  \"short_name\": \"Gemini Agent\",\n  \"description\": \"Mobile-first web interface for Gemini AI in Termux.\",\n  \"start_url\": \"/\",\n  \"scope\": \"/\",\n  \"display\": \"standalone\",\n  \"orientation\": \"portrait\",\n  \"background_color\": \"#121212\",\n  \"theme_color\": \"#0d6efd\",\n  \"icons\": [\n    {\n      \"src\": \"/static/icon-192.png\",\n      \"sizes\": \"192x192\",\n      \"type\": \"image/png\",\n      \"purpose\": \"any\"\n    },\n    {\n      \"src\": \"/static/icon-512.png\",\n      \"sizes\": \"512x512\",\n      \"type\": \"image/png\",\n      \"purpose\": \"any\"\n    },\n    {\n      \"src\": \"/static/maskable-icon-512.png\",\n      \"sizes\": \"512x512\",\n      \"type\": \"image/png\",\n      \"purpose\": \"maskable\"\n    }\n  ]\n}\n",
        "encoding": "text"
    },
    "maskable-icon-512.png": {
        "content": "iVBORw0KGgoAAAANSUhEUgAAAgAAAAIACAYAAAD0eNT6AAALQUlEQVR4nO3dwVIbRxRAUUixhU8138KvsgdnRRWJAwEhafr1PWfnKsdMplr97rQA3d7/evl9AwCk/HX0BQAA1ycAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIEgAAECQAACBIAABAkAAAgCABAABBAgAAggQAAAQJAAAIujv6AoDreX76vPkfHl+vdi3AsW7vf738PvgagAOH/kfEAOxNAMCGTh36HxEDsB/fAwCbOffwv9S/CRzLqxo2cslBLQJgL94CgA1cezh7SwDmcwIAwx3xZO40AOYTAAAQJABgsCOfxJ0CwGwCAIZaYQCvcA3Aabx6YaCVBu9K1wJ8nVcuAAQJAAAIEgAwzIpH7iteE/A5r1oACBIAABAkAGCQlY/aV7424E9esQAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAGOTh8fVmVStfG/AnAQAAQQIAAIIEAAyz4lH7itcEfE4AAECQAACAIAEAA6105L7StQBfJwBgqBUG7wrXAJxGAMBgRw5gwx9mEwAAECQAYLgjnsQ9/cN8t/e/Xn4ffRHAeTw/XbbpDX7YhxMA2MglB7ThD3sRALCZSwxqwx/24y0A2NypbwsY+rA3JwCwuVMGueEP+xMAABAkAAAgSAAAQJAAAIAgAQAAQQIAAIIEAAAECQAACBIAABAkAAAgSAAAQJAAAIAgnwZIxqmfikePD0OiQACwLQOfcxAD7EoAsB2Dn0sRA+xEALANg59rEQLswJuibMHwx3qD73ECwGgGP0dzGsBUTgAYy/BnBdYhUwkARrLpshLrkYkEAOPYbFmRdck0AoBRbLKszPpkEgHAGDZXJrBOmUIAAECQHwMk9VTlR7a4xjqz1phAAJDYlA1+rDv4p7t//Rm2YvDz07XjPX125XsAWNpPNl/Dn3P4yToSD6xMALAlwx/rCT4nAFjWqU9Phj+XcOq6cgrAqgQAWzH8sb7gawQAAAQJALbh6R/rDL5OALAk75uyE+uZFQkAtuDpH+sNvkcAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQdHf0BcDunp8+7uyHx9ebMvcGjiMA4MqD7aO/V4kB9wbWIADggOH22X+7awi4N7AW3wMACwy4S/w7K3FvYD1OAGDBgb3LaYB7A+va71EDrujST+uTTwPcG1jb3N0FADiZAIDFn84nngK4N7C+eTsLLODaQ3lSBLg3MMOcXQUAOBsBAEOexiecArg3MMf6OwoAcHYCAACCBAAMOoY/+uuvfG1Hf32YxisGAIIEAAAECQAACBIAABAkAAAgSAAAQJAAgG94eHxNf/2Vr+3orw/TCAAACBIAABAkAGDIUfOEI273BuYQAAAQJABgwJPuhKf/N+4NzCAAYPFBN2n4v3FvYH0CAACCBAAs/KQ78en/jXsDa7s7+gJgurdBd87Po588+N9zb2BdTgBgsaG9y/B/z72B9TgBgEWeeHcc/O+5N7AWAQAX8H6YfxYDuw/9/+LewBoEAFxYcch/lXsDx/E9AAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQdHf0BQB/en7aq80fHl+PvgTgX/baZQCALxEAABAkAAAgSAAAQJAAAIAgAQAAQQIAAIIEAAAECQC2sNsvzmFt1hs7sGsCQJAAYEl+dSw7sZ5Zkc8CYKtj2V022l3+P3bk+J9dOAEAgCABwFZPwZ7OuKRT1pfTHFYlANiOCMC6gv8nANiSCMB6gs8JAJb2k+NTEcA5/GQdOf5nZX4KgMTmbSPm1LUDu7q9//Xy++iLgGttxkKAa6wza40JBABjeCJjCqHJBM64AM7I8GcKAcAYNlaA8xEAjCICWJn1ySQCgHFssqzIumQaAcBINltWYj0ykQBgLJsuK6xB65CpBACj2YA5cu3BZAKALdiMsd7ge/wiILbjFwZxKUKTnQgAtiUEOAdDn10JADIEAV9l6FMgAAAgyDcBAkCQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAECQAACAIAEAAEECAACCBAAABAkAAAgSAAAQJAAAIEgAAMBNz9+hLpq6WlNDBQAAAABJRU5ErkJggg==",
        "encoding": "base64"
    },
    "script.js": {
        "content": "document.addEventListener('DOMContentLoaded', () => {\n    const chatForm = document.getElementById('chat-form');\n    const messageInput = document.getElementById('message-input');\n    const chatContainer = document.getElementById('chat-container');\n    const fileUpload = document.getElementById('file-upload');\n    const filePreviewArea = document.getElementById('file-preview-area');\n    const fileNameDisplay = document.getElementById('file-name');\n    const clearFileBtn = document.getElementById('clear-file-btn');\n    const resetBtn = document.getElementById('reset-btn');\n    const exportBtn = document.getElementById('export-btn');\n    const modelLinks = document.querySelectorAll('[data-model]');\n    const modelInput = document.getElementById('model-input');\n    const modelLabel = document.getElementById('model-label');\n    const patternsList = document.getElementById('patterns-list');\n    const patternSearch = document.getElementById('pattern-search');\n    const patternsModal = document.getElementById('patternsModal');\n    const sessionsList = document.getElementById('sessions-list');\n    const newChatBtn = document.getElementById('new-chat-btn');\n    const historySidebar = document.getElementById('historySidebar');\n    const toolsModal = document.getElementById('toolsModal');\n    const toolsStatus = document.getElementById('tools-status');\n    const btnApplyTools = document.getElementById('btn-apply-tools');\n    const btnDeselectAllTools = document.getElementById('btn-deselect-all-tools');\n    const toolToggles = document.querySelectorAll('.tool-toggle');\n    \n    const liveToast = document.getElementById('liveToast');\n    const toastBody = document.getElementById('toast-body');\n    const loadMoreContainer = document.getElementById('load-more-container');\n    const loadMoreBtn = document.getElementById('load-more-btn');\n    const chatWelcome = document.getElementById('chat-welcome');\n\n    let currentFile = null;\n    let allPatterns = [];\n    let currentOffset = 0;\n    const PAGE_LIMIT = 20;\n    let isLoadingHistory = false;\n\n    function showToast(message) {\n        if (!liveToast) return;\n        toastBody.textContent = message;\n        const toast = new bootstrap.Toast(liveToast);\n        toast.show();\n    }\n\n    // Handle Tools Modal show\n    toolsModal.addEventListener('show.bs.modal', async () => {\n        // Find the active session UUID\n        const activeSessionItem = document.querySelector('.session-item.active-session');\n        let uuid = \"pending\";\n        if (activeSessionItem) {\n            uuid = activeSessionItem.dataset.uuid;\n        }\n\n        toolsStatus.textContent = 'Loading settings...';\n        toolsStatus.className = 'mt-2 small text-muted';\n\n        // Reset toggles first\n        toolToggles.forEach(t => t.checked = false);\n\n        try {\n            const response = await fetch(`/sessions/${uuid}/tools`);\n            if (!response.ok) throw new Error(`HTTP ${response.status}`);\n            const data = await response.json();\n            \n            if (data.tools) {\n                data.tools.forEach(toolName => {\n                    const toggle = document.querySelector(`.tool-toggle[value=\"${toolName}\"]`);\n                    if (toggle) toggle.checked = true;\n                });\n            }\n            toolsStatus.textContent = '';\n        } catch (error) {\n            console.error('Error loading tool settings:', error);\n            toolsStatus.textContent = 'Failed to load settings.';\n            toolsStatus.className = 'mt-2 small text-danger';\n        }\n    });\n\n    btnApplyTools.addEventListener('click', async () => {\n        const activeSessionItem = document.querySelector('.session-item.active-session');\n        let uuid = \"pending\";\n        if (activeSessionItem) {\n            uuid = activeSessionItem.dataset.uuid;\n        }\n\n        const selectedTools = Array.from(toolToggles)\n            .filter(t => t.checked)\n            .map(t => t.value);\n\n        toolsStatus.textContent = 'Saving settings...';\n        toolsStatus.className = 'mt-2 small text-muted';\n\n        try {\n            const response = await fetch(`/sessions/${uuid}/tools`, {\n                method: 'POST',\n                headers: { 'Content-Type': 'application/json' },\n                body: JSON.stringify({ tools: selectedTools })\n            });\n            if (!response.ok) throw new Error(`HTTP ${response.status}`);\n            const data = await response.json();\n            if (data.success) {\n                toolsStatus.textContent = 'Settings applied successfully!';\n                toolsStatus.className = 'mt-2 small text-success';\n                setTimeout(() => {\n                    const modal = bootstrap.Modal.getInstance(toolsModal);\n                    if (modal) modal.hide();\n                }, 1000);\n            }\n        } catch (error) {\n            console.error('Error saving tool settings:', error);\n            toolsStatus.textContent = 'Failed to save settings.';\n            toolsStatus.className = 'mt-2 small text-danger';\n        }\n    });\n\n    btnDeselectAllTools.addEventListener('click', () => {\n        toolToggles.forEach(t => t.checked = false);\n    });\n\n    if (loadMoreBtn) {\n        loadMoreBtn.addEventListener('click', () => {\n            const activeSessionItem = document.querySelector('.session-item.active-session');\n            if (activeSessionItem) {\n                loadMessages(activeSessionItem.dataset.uuid, PAGE_LIMIT, currentOffset);\n            }\n        });\n    }\n\n    // Load sessions when sidebar is shown\n    historySidebar.addEventListener('show.bs.offcanvas', loadSessions);\n\n    // Load sessions on page load\n    loadSessions();\n\n    // Initial Math/Style for server-rendered messages\n    if (window.HAS_INITIAL_MESSAGES) {\n        document.querySelectorAll('.message').forEach(m => {\n            // Apply Math rendering to initial messages\n            if (typeof renderMathInElement === 'function') {\n                renderMathInElement(m, {\n                    delimiters: [\n                        {left: '$$', right: '$$', display: true},\n                        {left: '$', right: '$', display: false},\n                        {left: '\\\\(', right: '\\\\)', display: false},\n                        {left: '\\\\[', right: '\\\\]', display: true}\n                    ],\n                    throwOnError: false\n                });\n            }\n            // Setup copy buttons for initial messages\n            const btn = m.querySelector('.copy-btn');\n            if (btn) {\n                const text = m.querySelector('.message-content').textContent;\n                btn.onclick = (e) => {\n                    e.stopPropagation();\n                    navigator.clipboard.writeText(text).then(() => {\n                        const icon = btn.querySelector('i');\n                        icon.className = 'bi bi-check2';\n                        setTimeout(() => { icon.className = 'bi bi-clipboard'; }, 2000);\n                    });\n                };\n            }\n        });\n        chatContainer.scrollTop = chatContainer.scrollHeight;\n        // Update currentOffset to match initial load\n        currentOffset = document.querySelectorAll('.message').length;\n    }\n\n    \n    async function loadMessages(uuid, limit = PAGE_LIMIT, offset = 0, isAutoRestore = false) {\n        if (isLoadingHistory) return;\n        if (offset > 0) isLoadingHistory = true;\n\n        try {\n            const response = await fetch(`/sessions/${uuid}/messages?limit=${limit}&offset=${offset}`);\n            if (!response.ok) throw new Error(`HTTP ${response.status}`);\n            const messages = await response.json();\n            \n            if (offset === 0) {\n                // Clear existing messages only if it's the first page\n                chatContainer.innerHTML = '<div id=\"scroll-sentinel\" style=\"height: 10px; width: 100%;\"></div>';\n                currentOffset = 0;\n                if (chatWelcome) chatWelcome.classList.add('d-none');\n            }\n\n            if (messages.length > 0) {\n                if (offset === 0) {\n                    messages.forEach(msg => {\n                        const msgDiv = createMessageDiv(msg.role, msg.content);\n                        if (msgDiv) chatContainer.appendChild(msgDiv);\n                    });\n                    chatContainer.scrollTop = chatContainer.scrollHeight;\n                } else {\n                    // Prepend for \"Load More\"\n                    // We need to maintain scroll position\n                    const scrollHeightBefore = chatContainer.scrollHeight;\n                    const firstMessage = chatContainer.querySelector('.message');\n                    \n                    // Messages are in chronological order for the range.\n                    // To prepend correctly, we reverse and prepend.\n                    [...messages].reverse().forEach(msg => {\n                        const msgDiv = createMessageDiv(msg.role, msg.content);\n                        if (msgDiv) {\n                            if (firstMessage) {\n                                chatContainer.insertBefore(msgDiv, firstMessage);\n                            } else {\n                                chatContainer.appendChild(msgDiv);\n                            }\n                        }\n                    });\n                    \n                    chatContainer.scrollTop = chatContainer.scrollHeight - scrollHeightBefore;\n                }\n                \n                currentOffset += messages.length;\n                \n                // Show/Hide Load More (Still useful for fallback/logic)\n                if (messages.length === limit) {\n                    if (loadMoreContainer) loadMoreContainer.classList.remove('d-none');\n                } else {\n                    if (loadMoreContainer) loadMoreContainer.classList.add('d-none');\n                }\n\n                if (isAutoRestore) {\n                    showToast('Resumed last session');\n                }\n            } else {\n                if (offset === 0) {\n                    if (chatWelcome) chatWelcome.classList.remove('d-none');\n                }\n                if (loadMoreContainer) loadMoreContainer.classList.add('d-none');\n            }\n        } catch (error) {\n            console.error('Error loading messages:', error);\n        } finally {\n            isLoadingHistory = false;\n        }\n    }\n\n    async function loadSessions() {\n        try {\n            const response = await fetch('/sessions');\n            if (!response.ok) throw new Error(`HTTP ${response.status}`);\n            const sessions = await response.json();\n            \n            // Auto-create if none\n            if (sessions.length === 0) {\n                const newRes = await fetch('/sessions/new', { method: 'POST' });\n                if (newRes.ok) {\n                    loadSessions();\n                    return;\n                }\n            }\n\n            renderSessions(sessions);\n            const activeSession = sessions.find(s => s.active);\n            \n            // Check if we need to auto-load\n            const hasMessages = chatContainer.querySelectorAll('.message').length > 0;\n            if (activeSession && !hasMessages && !window.HAS_INITIAL_MESSAGES) {\n                 loadMessages(activeSession.uuid, PAGE_LIMIT, 0, true);\n            }\n        } catch (error) {\n            console.error('Error loading sessions:', error);\n            if (sessionsList) sessionsList.innerHTML = `<div class=\"alert alert-danger mx-3 mt-3\">Failed to load history: ${error.message}</div>`;\n        }\n    }\n\n    // Load patterns when modal is shown\n    patternsModal.addEventListener('show.bs.modal', async () => {\n        if (allPatterns.length === 0) {\n            try {\n                const response = await fetch('/patterns');\n                if (!response.ok) throw new Error(`HTTP ${response.status}`);\n                const data = await response.json();\n                allPatterns = data; // data is already the list\n                renderPatterns(allPatterns);\n            } catch (error) {\n                console.error('Error loading patterns:', error);\n                patternsList.innerHTML = `<div class=\"alert alert-danger\">Failed to load patterns: ${error.message}</div>`;\n            }\n        }\n    });\n\n    function renderSessions(sessions) {\n        if (sessions.length === 0) {\n            sessionsList.innerHTML = '<div class=\"text-center p-3 text-muted\">No history found.</div>';\n            return;\n        }\n        sessionsList.innerHTML = sessions.map(s => `\n            <div class=\"list-group-item list-group-item-action bg-dark text-light session-item ${s.active ? 'active-session' : ''}\" data-uuid=\"${s.uuid}\">\n                <div class=\"d-flex justify-content-between align-items-start\">\n                    <div class=\"flex-grow-1 overflow-hidden\">\n                        <span class=\"session-title text-truncate\">${s.title || 'Untitled Chat'}</span>\n                        <span class=\"session-time\">${s.time || ''}</span>\n                    </div>\n                    <div class=\"d-flex align-items-center gap-2\">\n                        ${s.active ? '<span class=\"badge bg-primary rounded-pill small\">Active</span>' : ''}\n                        <button class=\"btn btn-sm btn-outline-danger border-0 delete-session-btn\" data-uuid=\"${s.uuid}\" title=\"Delete Chat\">\n                            <i class=\"bi bi-trash\"></i>\n                        </button>\n                    </div>\n                </div>\n            </div>\n        `).join('');\n\n        // Add click listeners to items\n        document.querySelectorAll('.session-item').forEach(item => {\n            item.addEventListener('click', async (e) => {\n                // If clicked on delete button, don't switch session\n                if (e.target.closest('.delete-session-btn')) return;\n\n                const uuid = item.dataset.uuid;\n                if (item.classList.contains('active-session')) {\n                    bootstrap.Offcanvas.getInstance(historySidebar).hide();\n                    return;\n                }\n                \n                try {\n                    const formData = new FormData();\n                    formData.append('session_uuid', uuid);\n                    const response = await fetch('/sessions/switch', {\n                        method: 'POST',\n                        body: formData\n                    });\n                    const data = await response.json();\n                    if (data.success) {\n                        chatContainer.innerHTML = '<div class=\"text-center text-muted mt-5\"><p>Loading conversation...</p></div>';\n                        await loadMessages(uuid);\n                        bootstrap.Offcanvas.getInstance(historySidebar).hide();\n                        loadSessions();\n                    }\n                } catch (error) {\n                    console.error('Error switching session:', error);\n                    alert('Failed to switch session.');\n                }\n            });\n        });\n\n        // Delete buttons\n        document.querySelectorAll('.delete-session-btn').forEach(btn => {\n            btn.addEventListener('click', async (e) => {\n                e.stopPropagation();\n                const uuid = btn.dataset.uuid;\n                if (confirm('Are you sure you want to delete this conversation?')) {\n                    try {\n                        const formData = new FormData();\n                        formData.append('session_uuid', uuid);\n                        const response = await fetch('/sessions/delete', {\n                            method: 'POST',\n                            body: formData\n                        });\n                        const data = await response.json();\n                        if (data.success) {\n                            loadSessions();\n                            // If deleted the active one, clear the chat\n                            const item = btn.closest('.session-item');\n                            if (item.classList.contains('active-session')) {\n                                chatContainer.innerHTML = '<div class=\"text-center text-muted mt-5\"><p>Conversation deleted. Start a new one!</p></div>';\n                            }\n                        }\n                    } catch (error) {\n                        console.error('Error deleting session:', error);\n                        alert('Failed to delete session.');\n                    }\n                }\n            });\n        });\n    }\n\n    // New Chat\n    newChatBtn.addEventListener('click', async () => {\n        try {\n            const response = await fetch('/sessions/new', { method: 'POST' });\n            const data = await response.json();\n            if (data.success) {\n                chatContainer.innerHTML = '<div class=\"text-center text-muted mt-5\"><p>New conversation started.</p></div>';\n                bootstrap.Offcanvas.getInstance(historySidebar).hide();\n                loadSessions();\n            }\n        } catch (error) {\n            console.error('Error starting new chat:', error);\n            alert('Failed to start new chat.');\n        }\n    });\n\n    // Load patterns when modal is shown\n    patternsModal.addEventListener('show.bs.modal', async () => {\n        if (allPatterns.length === 0) {\n            try {\n                const response = await fetch('/patterns');\n                const data = await response.json();\n                allPatterns = data; // data is already the list\n                renderPatterns(allPatterns);\n            } catch (error) {\n                console.error('Error loading patterns:', error);\n                patternsList.innerHTML = '<div class=\"alert alert-danger\">Failed to load patterns.</div>';\n            }\n        }\n    });\n\n    // Search patterns\n    patternSearch.addEventListener('input', (e) => {\n        const query = e.target.value.toLowerCase();\n        const filtered = allPatterns.filter(p => \n            (p.name && p.name.toLowerCase().includes(query)) || \n            (p.description && p.description.toLowerCase().includes(query))\n        );\n        renderPatterns(filtered);\n    });\n\n    function renderPatterns(patterns) {\n        if (patterns.length === 0) {\n            patternsList.innerHTML = '<div class=\"text-center p-3 text-muted\">No patterns found.</div>';\n            return;\n        }\n        patternsList.innerHTML = patterns.map(p => `\n            <button type=\"button\" class=\"list-group-item list-group-item-action bg-dark text-light border-secondary pattern-item\" data-pattern=\"${p.name}\">\n                <div class=\"d-flex w-100 justify-content-between\">\n                    <h6 class=\"mb-1\"><i class=\"bi bi-magic\"></i> ${p.name}</h6>\n                </div>\n                <small class=\"text-muted\">${p.description || ''}</small>\n            </button>\n        `).join('');\n\n        // Add click listeners to items\n        document.querySelectorAll('.pattern-item').forEach(item => {\n            item.addEventListener('click', () => {\n                const pattern = item.dataset.pattern;\n                messageInput.value = `/p ${pattern} ${messageInput.value}`;\n                bootstrap.Modal.getInstance(patternsModal).hide();\n                messageInput.focus();\n                // Trigger auto-resize\n                messageInput.dispatchEvent(new Event('input'));\n            });\n        });\n    }\n\n    // Auto-resize textarea\n    messageInput.addEventListener('keydown', function(event) {\n        if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {\n            event.preventDefault();\n            chatForm.dispatchEvent(new Event('submit'));\n        }\n    });\n\n    messageInput.addEventListener('input', function() {\n        this.style.height = 'auto';\n        this.style.height = (this.scrollHeight) + 'px';\n        if (this.value === '') {\n            this.style.height = '';\n        }\n    });\n\n    // Model selection\n    modelLinks.forEach(link => {\n        link.addEventListener('click', (e) => {\n            e.preventDefault();\n            const targetLink = e.currentTarget; // The <a> tag\n            const model = targetLink.dataset.model;\n            \n            modelInput.value = model;\n            // Get text without the badge if possible, or just full text\n            let modelName = targetLink.innerText;\n            // Clean up \"Fast\"/\"Smart\" badges from text if present (simple hack)\n            modelName = modelName.replace('Fast', '').replace('Smart', '').trim();\n            \n            modelLabel.textContent = modelName;\n            \n            modelLinks.forEach(l => l.classList.remove('active'));\n            targetLink.classList.add('active');\n        });\n    });\n\n    // File handling\n    fileUpload.addEventListener('change', (e) => {\n        if (e.target.files.length > 0) {\n            currentFile = e.target.files[0];\n            fileNameDisplay.textContent = currentFile.name;\n            filePreviewArea.classList.remove('d-none');\n            \n            // Auto-switch to Gemini 3 Flash Preview for better vision support\n            const flashModel = \"gemini-3-flash-preview\";\n            modelInput.value = flashModel;\n            \n            // Update UI label and active state\n            modelLinks.forEach(link => {\n                if (link.dataset.model === flashModel) {\n                    link.classList.add('active');\n                    let modelName = link.innerText;\n                    modelName = modelName.replace('Fast', '').replace('Smart', '').trim();\n                    modelLabel.textContent = modelName + \" (Auto-switched)\";\n                } else {\n                    link.classList.remove('active');\n                }\n            });\n        }\n    });\n\n    clearFileBtn.addEventListener('click', () => {\n        fileUpload.value = '';\n        currentFile = null;\n        filePreviewArea.classList.add('d-none');\n    });\n\n    // Reset Chat\n    if (resetBtn) {\n        resetBtn.addEventListener('click', async () => {\n            if (confirm('Are you sure you want to clear the conversation history?')) {\n                try {\n                    const response = await fetch('/reset', { method: 'POST' });\n                    const data = await response.json();\n                    chatContainer.innerHTML = `<div class=\"text-center text-muted mt-5\"><p>${data.response}</p></div>`;\n                } catch (error) {\n                    console.error('Error resetting chat:', error);\n                    alert('Failed to reset chat.');\n                }\n            }\n        });\n    }\n\n    // Export Chat\n    if (exportBtn) {\n        exportBtn.addEventListener('click', async () => {\n            const activeSessionItem = document.querySelector('.session-item.active-session');\n            if (!activeSessionItem) {\n                alert('No active session to export.');\n                return;\n            }\n            const uuid = activeSessionItem.dataset.uuid;\n            // Get title, cleanup whitespace\n            let title = activeSessionItem.querySelector('.session-title').textContent.trim();\n            if (!title) title = \"chat_export\";\n\n            try {\n                // Fetch all messages (no limit)\n                const response = await fetch(`/sessions/${uuid}/messages`);\n                if (!response.ok) throw new Error('Network response was not ok');\n                const messages = await response.json();\n                \n                let markdown = `# Chat Export: ${title}\\n\\n`;\n                messages.forEach(msg => {\n                    const role = msg.role === 'user' ? 'User' : 'Gemini';\n                    markdown += `## ${role}\\n\\n${msg.content}\\n\\n---\\n\\n`;\n                });\n                \n                const blob = new Blob([markdown], { type: 'text/markdown' });\n                const url = URL.createObjectURL(blob);\n                const a = document.createElement('a');\n                a.href = url;\n                // Sanitize filename\n                const safeTitle = title.replace(/[^a-z0-9]/gi, '_').substring(0, 50);\n                a.download = `${safeTitle}.md`;\n                document.body.appendChild(a);\n                a.click();\n                document.body.removeChild(a);\n                URL.revokeObjectURL(url);\n            } catch (e) {\n                console.error('Export failed:', e);\n                alert('Failed to export chat.');\n            }\n        });\n    }\n\n    // Send Message\n    chatForm.addEventListener('submit', async (e) => {\n        e.preventDefault();\n        const message = messageInput.value.trim();\n        if (!message && !currentFile) return;\n\n        // Add user message to chat\n        appendMessage('user', message, currentFile ? `[Attachment: ${currentFile.name}]` : null, currentFile);\n        \n        // Clear inputs immediately\n        messageInput.value = '';\n        messageInput.style.height = '';\n        fileUpload.value = '';\n        filePreviewArea.classList.add('d-none');\n        const fileToSend = currentFile; // Keep ref for sending\n        currentFile = null;\n\n        // Show loading state\n        const loadingId = appendLoading();\n\n        try {\n            const formData = new FormData();\n            formData.append('message', message);\n            if (fileToSend) {\n                let finalFile = fileToSend;\n                // Compress if it's an image\n                if (fileToSend.type.startsWith('image/') && typeof compressImage === 'function') {\n                    try {\n                        finalFile = await compressImage(fileToSend);\n                    } catch (compressError) {\n                        console.error('Compression failed, sending original:', compressError);\n                    }\n                }\n                formData.append('file', finalFile);\n            }\n            formData.append('model', modelInput.value);\n\n            const response = await fetch('/chat', {\n                method: 'POST',\n                body: formData\n            });\n\n            if (!response.ok) {\n                let errorMessage = `Server Error: ${response.status}`;\n                try {\n                    const text = await response.text();\n                    try {\n                        const errorData = JSON.parse(text);\n                        if (errorData.error) {\n                            errorMessage = `Error: ${errorData.error}`;\n                        } else if (errorData.response) {\n                            errorMessage = errorData.response;\n                        }\n                    } catch (parseError) {\n                        if (text && text.length < 100) {\n                            errorMessage = `Error ${response.status}: ${text}`;\n                        } else {\n                            errorMessage = `Error ${response.status}: Failed to get valid response from server.`;\n                        }\n                    }\n                } catch (e) {\n                    console.error('Could not read error response:', e);\n                }\n                throw new Error(errorMessage);\n            }\n\n            const contentType = response.headers.get('content-type');\n            if (contentType && contentType.includes('text/event-stream')) {\n                await processStream(response, loadingId);\n            } else {\n                const data = await response.json();\n                removeLoading(loadingId);\n                appendMessage('bot', data.response);\n            }\n\n        } catch (error) {\n            removeLoading(loadingId);\n            console.error('Detailed Chat Error:', error);\n            let displayError = error.message || 'Unknown Error';\n            if (error instanceof TypeError && error.message === 'Failed to fetch') {\n                displayError = 'Network Error: Could not connect to the server. Check if the service is running and accessible.';\n            }\n            appendMessage('bot', `Error: ${displayError}`);\n        }\n    });\n\n    async function processStream(response, loadingId) {\n        const reader = response.body.getReader();\n        const decoder = new TextDecoder();\n        let messageDiv = null;\n        \n        let fullText = \"\";\n        let toolLogs = [];\n        let buffer = \"\";\n        let errorYielded = false;\n        \n        const renderInterval = 100; // ms\n        let lastRenderTime = 0;\n\n        try {\n            while (true) {\n                const { done, value } = await reader.read();\n                if (done) break;\n                \n                buffer += decoder.decode(value, { stream: true });\n                const lines = buffer.split('\\n');\n                buffer = lines.pop();\n\n                for (const line of lines) {\n                    const trimmedLine = line.trim();\n                    if (!trimmedLine || trimmedLine.startsWith(':')) continue; // Skip empty or heartbeats\n\n                    if (trimmedLine.startsWith('data: ')) {\n                        const dataStr = trimmedLine.substring(6).trim();\n                        if (dataStr === '[DONE]') continue;\n                        \n                        try {\n                            const data = JSON.parse(dataStr);\n                            if (data.type === 'message' && data.role === 'assistant') {\n                                fullText += data.content;\n                            } else if (data.type === 'model_switch') {\n                                // Update footer label\n                                const label = document.getElementById('model-label');\n                                if (label) {\n                                    // Make it look nice, e.g. \"Gemini 3 Flash (Auto-switched)\"\n                                    let cleanName = data.new_model.replace(/-/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase());\n                                    // Remove 'Preview' etc if redundant, but keep it clear\n                                    label.textContent = cleanName + \" (Auto-switched)\";\n                                    label.classList.add('text-warning'); // Highlight the change\n                                }\n                            } else if (data.type === 'tool_use') {\n                                toolLogs.push({ type: 'call', name: data.tool_name, input: data.parameters });\n                            } else if (data.type === 'tool_result') {\n                                if (data.output && data.output.trim() !== \"\") {\n                                    toolLogs.push({ type: 'output', output: data.output });\n                                }\n                            } else if (data.type === 'error') {\n                                fullText += `\\n\\n[Error: ${data.content}]\\n\\n`;\n                                errorYielded = true;\n                            }\n                            \n                            if (!messageDiv && (fullText.trim().length > 0 || toolLogs.length > 0)) {\n                                messageDiv = createStreamingMessage('bot');\n                                removeLoading(loadingId);\n                                if (chatWelcome) chatWelcome.classList.add('d-none');\n                            }\n\n                            if (messageDiv) {\n                                const now = Date.now();\n                                if (now - lastRenderTime > renderInterval) {\n                                    updateStreamingMessage(messageDiv, fullText, toolLogs);\n                                    lastRenderTime = now;\n                                }\n                            }\n                        } catch (e) {\n                            console.error('Error parsing stream chunk:', e, dataStr);\n                        }\n                    }\n                }\n            }\n            if (messageDiv) {\n                updateStreamingMessage(messageDiv, fullText, toolLogs, true);\n            } else {\n                removeLoading(loadingId);\n            }\n        } catch (error) {\n            console.error('Stream processing error:', error);\n            if (!errorYielded) {\n                if (!messageDiv) {\n                    messageDiv = createStreamingMessage('bot');\n                    removeLoading(loadingId);\n                }\n                const errorDiv = document.createElement('div');\n                errorDiv.className = 'text-danger small mt-2';\n                errorDiv.textContent = 'Connection lost. Message may be incomplete.';\n                messageDiv.appendChild(errorDiv);\n            }\n        }\n    }\n\n    function createStreamingMessage(sender) {\n        const messageDiv = document.createElement('div');\n        messageDiv.classList.add('message', sender);\n        \n        const contentArea = document.createElement('div');\n        contentArea.className = 'message-content';\n        messageDiv.appendChild(contentArea);\n        \n        const logsArea = document.createElement('div');\n        logsArea.className = 'tool-logs mt-2 d-none';\n        messageDiv.appendChild(logsArea);\n        \n        chatContainer.appendChild(messageDiv);\n        chatContainer.scrollTop = chatContainer.scrollHeight;\n        return messageDiv;\n    }\n\n    function updateStreamingMessage(messageDiv, text, toolLogs, isFinal = false) {\n        const contentArea = messageDiv.querySelector('.message-content');\n        const logsArea = messageDiv.querySelector('.tool-logs');\n        \n        // Render Text\n        if (text.trim().length > 0) {\n            if (typeof marked !== 'undefined') {\n                contentArea.innerHTML = marked.parse(text);\n            } else {\n                contentArea.textContent = text;\n            }\n        }\n        \n        // Render Logs\n        if (toolLogs.length > 0) {\n            logsArea.classList.remove('d-none');\n            logsArea.innerHTML = toolLogs.map(log => {\n                if (log.type === 'call') {\n                    return `<div class=\"small text-info border-start border-info ps-2 mb-1\" style=\"font-family: monospace;\">\n                        <strong>Tool Call:</strong> ${log.name}<br>\n                        <span class=\"text-muted\" style=\"word-break: break-all; font-size: 0.7rem;\">${JSON.stringify(log.input)}</span>\n                    </div>`;\n                } else {\n                    if (!log.output || log.output.trim() === \"\") return \"\";\n                    return `<div class=\"small text-success border-start border-success ps-2 mb-2\" style=\"font-family: monospace;\">\n                        <strong>Tool Output:</strong><br>\n                        <pre class=\"m-0\" style=\"font-size: 0.7rem; max-height: 150px; overflow: auto; background: #1a1a1a; padding: 5px; border-radius: 4px;\">${log.output}</pre>\n                    </div>`;\n                }\n            }).join('');\n        }\n        \n        if (isFinal) {\n            // Add copy button\n            const copyBtn = document.createElement('button');\n            copyBtn.className = 'copy-btn';\n            copyBtn.innerHTML = '<i class=\"bi bi-clipboard\"></i>';\n            copyBtn.onclick = (e) => {\n                e.stopPropagation();\n                navigator.clipboard.writeText(text).then(() => {\n                    const icon = copyBtn.querySelector('i');\n                    icon.className = 'bi bi-check2';\n                    setTimeout(() => { icon.className = 'bi bi-clipboard'; }, 2000);\n                });\n            };\n            messageDiv.prepend(copyBtn);\n            \n            // Highlight code\n            if (typeof hljs !== 'undefined') {\n                messageDiv.querySelectorAll('pre code').forEach((block) => {\n                    hljs.highlightElement(block);\n                });\n            }\n\n            // Render Math\n            try {\n                if (typeof renderMathInElement === 'function') {\n                    renderMathInElement(messageDiv, {\n                        delimiters: [\n                            {left: '$$', right: '$$', display: true},\n                            {left: '$', right: '$', display: false},\n                            {left: '\\\\(', right: '\\\\)', display: false},\n                            {left: '\\\\[', right: '\\\\]', display: true}\n                        ],\n                        throwOnError: false\n                    });\n                }\n            } catch (e) {\n                console.error('Error rendering math:', e);\n            }\n        }\n        \n        chatContainer.scrollTop = chatContainer.scrollHeight;\n    }\n\n    function createMessageDiv(sender, text, attachmentInfo = null, file = null) {\n        if (!text && !attachmentInfo) return null;\n        if (text && text.trim() === \"\" && !attachmentInfo) return null;\n\n        const messageDiv = document.createElement('div');\n        messageDiv.classList.add('message', sender);\n        \n        let contentHtml = '';\n\n        // Image Preview Logic\n        let imageUrl = null;\n        if (file && file.type.startsWith('image/')) {\n            imageUrl = URL.createObjectURL(file);\n        } else if (text && sender === 'user') {\n            // Regex to find attachment path: matches both / and \\ \n            const match = text.match(/@tmp[\\\\\\/]user_attachments[\\\\\\/]([^\\s]+)/);\n            if (match) {\n                const filename = match[1];\n                imageUrl = `/uploads/${filename}`;\n            }\n        }\n\n        if (imageUrl) {\n            contentHtml += `<img src=\"${imageUrl}\" class=\"message-thumbnail mb-2\" style=\"max-width: 150px; border-radius: 8px; cursor: pointer; display: block;\" onclick=\"window.open('${imageUrl}', '_blank')\">`;\n        }\n\n        if (attachmentInfo) {\n            contentHtml += `<div class=\"text-muted small mb-1\"><i class=\"bi bi-paperclip\"></i> ${attachmentInfo}</div>`;\n        }\n        \n        // Use marked to parse markdown safely\n        let parsedText = text;\n        try {\n            if (typeof marked !== 'undefined') {\n                if (typeof marked.parse === 'function') {\n                    parsedText = marked.parse(text);\n                } else if (typeof marked === 'function') {\n                    parsedText = marked(text);\n                }\n            }\n        } catch (e) {\n            console.error('Error parsing markdown:', e);\n        }\n        \n        contentHtml += `<div class=\"message-content\">${parsedText}</div>`;\n\n        messageDiv.innerHTML = contentHtml;\n        // Add copy button\n        const copyBtn = document.createElement('button');\n        copyBtn.className = 'copy-btn';\n        copyBtn.innerHTML = '<i class=\"bi bi-clipboard\"></i>';\n        copyBtn.onclick = (e) => {\n            e.stopPropagation();\n            navigator.clipboard.writeText(text).then(() => {\n                const icon = copyBtn.querySelector('i');\n                icon.className = 'bi bi-check2';\n                setTimeout(() => { icon.className = 'bi bi-clipboard'; }, 2000);\n            });\n        };\n        messageDiv.prepend(copyBtn);\n\n        // Highlight code blocks safely\n        try {\n            if (typeof hljs !== 'undefined') {\n                messageDiv.querySelectorAll('pre code').forEach((block) => {\n                    hljs.highlightElement(block);\n                });\n            }\n        } catch (e) {\n            console.error('Error highlighting code:', e);\n        }\n\n        // Render Math\n        try {\n            if (typeof renderMathInElement === 'function') {\n                renderMathInElement(messageDiv, {\n                    delimiters: [\n                        {left: '$$', right: '$$', display: true},\n                        {left: '$', right: '$', display: false},\n                        {left: '\\\\(', right: '\\\\)', display: false},\n                        {left: '\\\\[', right: '\\\\]', display: true}\n                    ],\n                    throwOnError: false\n                });\n            }\n        } catch (e) {\n            console.error('Error rendering math:', e);\n        }\n        \n        return messageDiv;\n    }\n\n    function appendMessage(sender, text, attachmentInfo = null, file = null) {\n        try {\n            const messageDiv = createMessageDiv(sender, text, attachmentInfo, file);\n            chatContainer.appendChild(messageDiv);\n            chatContainer.scrollTop = chatContainer.scrollHeight;\n        } catch (e) {\n            console.error('Error in appendMessage:', e);\n        }\n    }\n\n    function appendLoading() {\n        const id = 'loading-' + Date.now();\n        const messageDiv = document.createElement('div');\n        messageDiv.classList.add('message', 'bot');\n        messageDiv.id = id;\n        messageDiv.innerHTML = '<div class=\"spinner-border spinner-border-sm text-light\" role=\"status\"><span class=\"visually-hidden\">Loading...</span></div> Thinking...';\n        chatContainer.appendChild(messageDiv);\n        chatContainer.scrollTop = chatContainer.scrollHeight;\n        return id;\n    }\n\n    function removeLoading(id) {\n        const element = document.getElementById(id);\n        if (element) {\n            element.remove();\n        }\n    }\n\n    // Infinite Scroll Observer\n    const scrollSentinel = document.getElementById('scroll-sentinel');\n    if (scrollSentinel) {\n        const observer = new IntersectionObserver((entries) => {\n            if (entries[0].isIntersecting && !isLoadingHistory) {\n                const activeSessionItem = document.querySelector('.session-item.active-session');\n                const hasMore = !loadMoreContainer.classList.contains('d-none');\n                \n                if (activeSessionItem && hasMore && currentOffset > 0) {\n                    loadMessages(activeSessionItem.dataset.uuid, PAGE_LIMIT, currentOffset);\n                }\n            }\n        }, {\n            root: chatContainer,\n            threshold: 0.1\n        });\n        observer.observe(scrollSentinel);\n    }\n});\n",
        "encoding": "text"
    },
    "style.css": {
        "content": ":root {\n    --bg-color: #121212;\n    --chat-bg: #0b0b0b;\n    --sidebar-bg: #1e1e1e;\n    --message-user-bg: #3c6e71; /* Teal muted */\n    --message-bot-bg: #2b2d42; /* Dark blue/grey */\n    --text-color: #e0e0e0;\n    --input-bg: #2d2d2d;\n    --border-color: #444;\n}\n\nbody {\n    background-color: var(--bg-color) !important;\n    color: var(--text-color) !important;\n    font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;\n}\n\n/* Header Styling */\nheader {\n    background-color: var(--sidebar-bg) !important;\n    box-shadow: 0 2px 10px rgba(0,0,0,0.3);\n    z-index: 1000;\n}\n\n/* Chat Container */\n#chat-container {\n    background-color: var(--chat-bg);\n    padding-bottom: 2rem;\n    display: flex;\n    flex-direction: column;\n}\n\n/* Messages */\n.message {\n    max-width: 85%;\n    margin-bottom: 1.2rem;\n    padding: 1rem 1.2rem;\n    border-radius: 1.2rem;\n    position: relative;\n    word-wrap: break-word;\n    box-shadow: 0 1px 2px rgba(0,0,0,0.2);\n    font-size: 0.95rem;\n    line-height: 1.5;\n}\n\n.message.user {\n    background-color: var(--message-user-bg);\n    color: #ffffff;\n    align-self: flex-end;\n    margin-left: auto;\n    border-bottom-right-radius: 0.2rem;\n}\n\n.message.bot {\n    background-color: #2d2d2d; /* Dark Grey */\n    color: #ffffff; /* Brighter white */\n    align-self: flex-start;\n    margin-right: auto;\n    border-bottom-left-radius: 0.2rem;\n}\n\n.text-muted {\n    color: #b0b0b0 !important; /* Brighter muted text */\n}\n\n/* Code Blocks */\n.message pre {\n    background-color: #1a1a1a !important;\n    padding: 1rem;\n    border-radius: 0.5rem;\n    overflow-x: auto;\n    margin-top: 0.5rem;\n    border: 1px solid #333;\n}\n\n/* Footer / Input Area */\nfooter {\n    background-color: var(--sidebar-bg) !important;\n    box-shadow: 0 -2px 10px rgba(0,0,0,0.2);\n}\n\n/* Custom Scrollbar */\n::-webkit-scrollbar {\n    width: 6px;\n}\n\n::-webkit-scrollbar-track {\n    background: var(--chat-bg);\n}\n\n::-webkit-scrollbar-thumb {\n    background: #555;\n    border-radius: 3px;\n}\n\n::-webkit-scrollbar-thumb:hover {\n    background: #777;\n}\n\n/* Input Field Styling */\ntextarea#message-input {\n    resize: none;\n    max-height: 200px;\n    min-height: 50px; /* Enforce a minimum height */\n    background-color: var(--input-bg);\n    color: white;\n    border: 1px solid var(--border-color);\n    border-radius: 1.5rem !important; /* Pill shape */\n    padding: 0.8rem 1.2rem;\n    font-size: 1rem;\n}\n\ntextarea#message-input:focus {\n    background-color: #333;\n    border-color: #666;\n    box-shadow: none;\n    color: white;\n}\n\n/* Buttons in Input Area */\n.btn-circle {\n    width: 40px;\n    height: 40px;\n    padding: 0;\n    border-radius: 50%;\n    display: flex;\n    align-items: center;\n    justify-content: center;\n}\n\n/* Dropdown Menu */\n.dropdown-menu {\n    background-color: var(--input-bg);\n    border-color: var(--border-color);\n}\n.dropdown-item {\n    color: var(--text-color);\n}\n.dropdown-item:hover {\n    background-color: #444;\n    color: white;\n}\n\n/* Session List Items */\n#sessions-list .list-group-item {\n    cursor: pointer;\n    transition: background-color 0.2s;\n    border-color: #333;\n    padding: 0.75rem 1.25rem;\n}\n\n#sessions-list .list-group-item:hover {\n    background-color: #333 !important;\n}\n\n#sessions-list .list-group-item.active-session {\n    background-color: #2b2d42 !important;\n    border-left: 4px solid #3c6e71;\n}\n\n#sessions-list .session-title {\n    font-weight: 500;\n    font-size: 0.9rem;\n    display: block;\n}\n\n#sessions-list .session-time {\n    font-size: 0.75rem;\n    color: #888;\n}\n/* Mobile Safe Area Fixes */\nhtml, body { height: 100%; margin: 0; padding: 0; }\n.container-fluid { height: 100vh; display: flex; flex-direction: column; }\n#chat-container { flex-grow: 1; overflow-y: auto; }\nfooter { \n    flex-shrink: 0; \n    padding-bottom: calc(1rem + env(safe-area-inset-bottom)) !important; \n}\n@supports (height: 100dvh) {\n    .container-fluid { height: 100dvh; }\n}\n\n/* Copy Button */\n.message { \n    position: relative; \n    padding-right: 40px !important; \n    display: flex;\n    flex-direction: column;\n}\n.copy-btn {\n    position: sticky; \n    top: 0; \n    align-self: flex-end;\n    margin-top: -5px;\n    margin-right: -30px;\n    background: rgba(0,0,0,0.2); \n    border: 1px solid rgba(255,255,255,0.1);\n    color: rgba(255, 255, 255, 0.5); \n    cursor: pointer;\n    padding: 4px; \n    border-radius: 4px;\n    transition: all 0.2s; \n    font-size: 1rem;\n    display: flex; \n    align-items: center; \n    justify-content: center; \n    z-index: 10;\n}\n.copy-btn:hover { \n    color: #fff; \n    background: rgba(255, 255, 255, 0.2); \n}\n\n/* Image Thumbnails */\n.message-thumbnail {\n    max-width: 150px;\n    max-height: 150px;\n    border-radius: 8px;\n    cursor: pointer;\n    display: block;\n    transition: transform 0.2s;\n}\n.message-thumbnail:hover {\n    transform: scale(1.02);\n}\n",
        "encoding": "text"
    },
    "sw.js": {
        "content": "const CACHE_NAME = 'gemini-agent-v6'; // Bump version for fresh install\n\nself.addEventListener('install', (event) => {\n  console.log('Service Worker v6 installing...');\n  event.waitUntil(\n    caches.open(CACHE_NAME).then((cache) => {\n      // Pre-cache only essential, non-dynamic assets\n      // (Root path '/' removed to avoid caching redirects)\n      return cache.addAll([\n        '/static/style.css',\n        '/static/script.js',\n        '/static/icon.svg',\n        '/static/icon-192.png',\n        '/static/icon-512.png',\n        '/static/maskable-icon-512.png',\n        '/manifest.json'\n      ]);\n    }).catch((error) => {\n      console.error('Service Worker install failed:', error);\n    })\n  );\n});\n\nself.addEventListener('activate', (event) => {\n  console.log('Service Worker v6 activating...');\n  event.waitUntil(\n    caches.keys().then((cacheNames) => {\n      return Promise.all(\n        cacheNames.filter((cacheName) => {\n          return cacheName !== CACHE_NAME;\n        }).map((cacheName) => {\n          console.log(`[SW] Deleting old cache: ${cacheName}`);\n          return caches.delete(cacheName);\n        })\n      );\n    })\n  );\n  event.waitUntil(self.clients.claim()); // Take control of un-controlled clients\n});\n\nself.addEventListener('fetch', (event) => {\n  console.log('[SW] Fetching:', event.request.url);\n\n  // Network-first strategy for all requests\n  event.respondWith(\n    fetch(event.request)\n      .then((networkResponse) => {\n        // If the network response is good, cache it and return it\n        if (networkResponse.ok && networkResponse.type === 'basic' && event.request.method === 'GET') {\n          const clonedResponse = networkResponse.clone();\n          caches.open(CACHE_NAME).then((cache) => {\n            // Only cache requests for paths that typically don't change often and are not main HTML docs\n            const urlWithoutQuery = event.request.url.split('?')[0].replace(self.location.origin, '');\n            if (urlWithoutQuery.startsWith('/static/') || urlWithoutQuery === '/manifest.json') {\n                 console.log(`[SW] Caching network response for: ${event.request.url}`);\n                cache.put(event.request, clonedResponse);\n            }\n          });\n        }\n        return networkResponse;\n      })\n      .catch((error) => {\n        console.warn(`[SW] Network request failed for: ${event.request.url}. Trying cache.`, error);\n        // Fallback to cache if network fails\n        return caches.match(event.request).then((cachedResponse) => {\n          if (cachedResponse) {\n            console.log(`[SW] Serving from cache: ${event.request.url}`);\n            return cachedResponse;\n          }\n          // If neither network nor cache has a response, return a generic offline page or error\n          console.error(`[SW] No cache match for offline: ${event.request.url}`);\n          // For navigation requests, can show an offline page\n          if (event.request.mode === 'navigate') {\n            return new Response('<h1>Offline</h1><p>You are offline and this page is not available.</p>', { headers: { 'Content-Type': 'text/html' } });\n          }\n          // For other requests, return a network error\n          return new Response(null, { status: 503, statusText: 'Service Unavailable (Offline)' });\n        });\n      })\n  );\n});\n",
        "encoding": "text"
    }
}


# --- SERVICES ---
import os
import json
import hashlib
import bcrypt
from typing import Optional, Tuple, Dict, List
from webauthn.helpers import bytes_to_base64url

class UserManager:
    def __init__(self, working_dir: Optional[str] = None):
        self.working_dir = working_dir or os.getcwd()
        self.users_file = os.getenv("USERS_FILE", os.path.join(self.working_dir, "users.json"))
        self.users = self._load_users()
        self._ensure_admin()

    def _load_users(self) -> Dict:
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, "r") as f: return json.load(f)
            except: return {}
        return {}

    def _save_users(self):
        with open(self.users_file, "w") as f: json.dump(self.users, f, indent=2)

    def has_users(self) -> bool:
        return len(self.users) > 0

    def clear_all_users(self):
        self.users = {}
        self._save_users()

    def _ensure_admin(self):
        # We no longer auto-create admin with a default password for security and anonymity.
        # The first-run setup should be handled by the application logic.
        pass

    def _pre_hash(self, password: str) -> str:
        if not password: return ""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    def get_password_hash(self, password: str) -> str:
        return bcrypt.hashpw(self._pre_hash(password).encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def verify_password(self, plain: str, hashed: str) -> bool:
        try: return bcrypt.checkpw(self._pre_hash(plain).encode('utf-8'), hashed.encode('utf-8'))
        except: return False

    def register_user(self, username: str, password: str, pattern: Optional[str] = None, wallet: Optional[str] = None, role: str = "user") -> Tuple[bool, str]:
        if username in self.users: return False, "Exists"
        self.users[username] = {
            "password": self.get_password_hash(password),
            "pattern": self.get_password_hash(pattern) if pattern else None,
            "wallet_address": wallet.lower() if wallet else None,
            "role": role,
            "passkeys": []
        }
        self._save_users()
        return True, "Success"

    def get_all_users(self) -> List[Dict]:
        return [{"username": u, "role": d.get("role", "user"), "pattern_disabled": d.get("pattern_disabled", False)} for u, d in self.users.items()]

    def remove_user(self, username: str) -> bool:
        if username in self.users:
            del self.users[username]
            self._save_users()
            return True
        return False

    def update_password(self, username: str, password: str) -> bool:
        if username in self.users:
            self.users[username]["password"] = self.get_password_hash(password)
            self._save_users()
            return True
        return False

    def get_role(self, username: str) -> Optional[str]:
        return self.users.get(username, {}).get("role")

    def add_passkey(self, username: str, cred_id, pub_key, sign_count: int = 0) -> bool:
        if username not in self.users: return False
        if isinstance(cred_id, bytes): cred_id = bytes_to_base64url(cred_id)
        if isinstance(pub_key, bytes): pub_key = bytes_to_base64url(pub_key)
        self.users[username].setdefault("passkeys", []).append({
            "credential_id": cred_id, "public_key": pub_key, "sign_count": sign_count
        })
        self._save_users()
        return True

    def get_passkeys(self, username: str) -> List[Dict]:
        return self.users.get(username, {}).get("passkeys", [])

    def update_passkey_sign_count(self, username: str, cred_id: str, count: int) -> bool:
        if username not in self.users: return False
        for pk in self.users[username].get("passkeys", []):
            if pk["credential_id"] == cred_id:
                pk["sign_count"] = count
                self._save_users()
                return True
        return False

    def set_pattern_disabled(self, username: str, disabled: bool) -> bool:
        if username not in self.users: return False
        self.users[username]["pattern_disabled"] = disabled
        self._save_users()
        return True

    def is_pattern_disabled(self, username: str) -> bool:
        return self.users.get(username, {}).get("pattern_disabled", False)

    def authenticate_with_pattern(self, username: str, pattern: str) -> bool:
        user = self.users.get(username)
        if not user or user.get("pattern_disabled", False): return False
        return user.get("pattern") and self.verify_password(pattern, user["pattern"])

    def set_pattern(self, username: str, pattern: str) -> bool:
        if username not in self.users: return False
        self.users[username]["pattern"] = self.get_password_hash(pattern)
        self._save_users()
        return True

    def set_wallet_address(self, username: str, addr: str) -> bool:
        if username not in self.users: return False
        self.users[username]["wallet_address"] = addr.lower()
        self._save_users()
        return True

    def authenticate_user(self, username: str, password: str) -> bool:
        user = self.users.get(username)
        return user and self.verify_password(password, user["password"])

    def get_user_by_wallet(self, addr: str) -> Optional[str]:
        addr = addr.lower()
        for u, d in self.users.items():
            if d.get("wallet_address") == addr: return u
        return None

    def get_user_by_credential_id(self, cred_id) -> Tuple[Optional[str], Optional[Dict]]:
        if isinstance(cred_id, bytes): cred_id = bytes_to_base64url(cred_id)
        for u, d in self.users.items():
            for pk in d.get("passkeys", []):
                if pk["credential_id"] == cred_id: return u, pk
        return None, None

    def get_user_by_pattern(self, pattern: str) -> Optional[str]:
        for u, d in self.users.items():
            if not d.get("pattern_disabled", False) and d.get("pattern") and self.verify_password(pattern, d["pattern"]): return u
        return None


from webauthn import (
    generate_registration_options, 
    verify_registration_response, 
    generate_authentication_options, 
    verify_authentication_response, 
    options_to_json, 
    base64url_to_bytes
)
from webauthn.helpers import bytes_to_base64url
from webauthn.helpers.structs import (
    PublicKeyCredentialDescriptor, 
    AuthenticatorSelectionCriteria, 
    UserVerificationRequirement,
    ResidentKeyRequirement
)
from typing import List, Optional

class AuthService:
    def __init__(self, rp_id: str, rp_name: str, origin: str):
        self.rp_id = rp_id
        self.rp_name = rp_name
        self.origin = origin

    def generate_registration_options(self, user_id: str, user_name: str):
        return generate_registration_options(
            rp_id=self.rp_id,
            rp_name=self.rp_name,
            user_id=user_id.encode(),
            user_name=user_name,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.PREFERRED
            )
        )

    def verify_registration_response(self, credential, challenge):
        return verify_registration_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(challenge),
            expected_origin=self.origin,
            expected_rp_id=self.rp_id
        )

    def generate_authentication_options(self, credential_ids: List[str] = []):
        creds = [PublicKeyCredentialDescriptor(id=base64url_to_bytes(cid)) for cid in credential_ids]
        return generate_authentication_options(
            rp_id=self.rp_id,
            allow_credentials=creds,
            user_verification=UserVerificationRequirement.PREFERRED
        )

    def verify_authentication_response(self, credential, challenge, public_key, sign_count):
        return verify_authentication_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(challenge),
            expected_origin=self.origin,
            expected_rp_id=self.rp_id,
            credential_public_key=base64url_to_bytes(public_key),
            credential_current_sign_count=sign_count
        )
    
    def options_to_json(self, options):
        return options_to_json(options)
    
    def bytes_to_base64url(self, b):
        return bytes_to_base64url(b)


import json
import os
import re
import asyncio
import shutil
from typing import Optional, List, Dict, AsyncGenerator

FALLBACK_MODELS = {
    "gemini-3-pro-preview": "gemini-3-flash-preview",
    "gemini-2.5-pro": "gemini-2.5-flash",
    "gemini-1.5-pro": "gemini-1.5-flash"
}

def global_log(msg):
    try:
        with open("agent_debug.log", "a", encoding="utf-8") as f:
            f.write(f"{msg}\n")
    except: pass

class GeminiAgent:
    def __init__(self, model: str = "gemini-2.5-flash", working_dir: Optional[str] = None):
        self.model_name = model
        self.working_dir = working_dir or os.getcwd()
        self.session_file = os.path.join(self.working_dir, "user_sessions.json")
        self.gemini_cmd = shutil.which("gemini") or "gemini"
        self.user_data = self._load_user_data()
        self.yolo_mode = False

    def _load_user_data(self) -> Dict:
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, "r") as f:
                    data = json.load(f)
                    if not data: return {}
                    # Migration for old flat format
                    if isinstance(next(iter(data.values())), str):
                        return {uid: {"active_session": suid, "sessions": [suid], "session_tools": {}} for uid, suid in data.items()}
                    # Ensure all entries have the expected keys
                    for uid in data:
                        if "sessions" not in data[uid]:
                            data[uid]["sessions"] = []
                        if "active_session" not in data[uid]:
                            data[uid]["active_session"] = None
                        if "session_tools" not in data[uid]:
                            data[uid]["session_tools"] = {}
                        if "pending_tools" not in data[uid]:
                            data[uid]["pending_tools"] = []
                    return data
            except: return {}
        return {}

    def _save_user_data(self):
        with open(self.session_file, "w") as f: json.dump(self.user_data, f, indent=2)

    def get_session_tools(self, user_id: str, session_uuid: str) -> List[str]:
        user_info = self.user_data.get(user_id)
        if not user_info: return []
        if session_uuid == "pending":
            return user_info.get("pending_tools", [])
        return user_info.get("session_tools", {}).get(session_uuid, [])

    def set_session_tools(self, user_id: str, session_uuid: str, tools: List[str]):
        if user_id not in self.user_data:
            self.user_data[user_id] = {"active_session": None, "sessions": [], "session_tools": {}, "pending_tools": []}
        
        if session_uuid == "pending":
            self.user_data[user_id]["pending_tools"] = tools
        else:
            if "session_tools" not in self.user_data[user_id]:
                self.user_data[user_id]["session_tools"] = {}
            self.user_data[user_id]["session_tools"][session_uuid] = tools
        self._save_user_data()

    def list_patterns(self) -> List[str]:
        return sorted([k for k in PATTERNS.keys() if k != "__explanations__"])

    async def apply_pattern(self, user_id: str, pattern_name: str, input_text: str, model: Optional[str] = None, file_path: Optional[str] = None) -> str:
        system = PATTERNS.get(pattern_name)
        if not system: return f"Error: Pattern '{pattern_name}' not found."
        return await self.generate_response(user_id, f"{system}\n\nUSER INPUT:\n{input_text}", model=model, file_path=file_path)

    def _filter_errors(self, err: str) -> str:
        err = re.sub(r".*?\[DEP0151\] DeprecationWarning:.*?(\n|$)", "", err)
        err = re.sub(r".*?Default \"index\" lookups for the main are deprecated for ES modules..*?(\n|$)", "", err)
        return "\n".join([s for s in err.splitlines() if s.strip()]).strip()

    async def _get_latest_session_uuid(self) -> Optional[str]:
        try:
            global_log("Executing --list-sessions...")
            proc = await asyncio.create_subprocess_exec(self.gemini_cmd, "--list-sessions", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=self.working_dir)
            stdout, stderr = await proc.communicate()
            content = (stdout.decode() + stderr.decode())
            matches = re.findall(r"\<([a-fA-F0-9-]{36})\>", content)
            res = matches[-1] if matches else None
            global_log(f"Latest session ID found: {res}")
            return res
        except Exception as e:
            global_log(f"Error in _get_latest_session_uuid: {str(e)}")
            return None

    async def generate_response_stream(self, user_id: str, prompt: str, model: Optional[str] = None, file_path: Optional[str] = None) -> AsyncGenerator[Dict, None]:
        def log_debug(msg):
            global_log(f"[{user_id}] {msg}")

        if user_id not in self.user_data:
            self.user_data[user_id] = {"active_session": None, "sessions": [], "session_tools": {}, "pending_tools": []}
        else:
            if "sessions" not in self.user_data[user_id]:
                self.user_data[user_id]["sessions"] = []
            if "active_session" not in self.user_data[user_id]:
                self.user_data[user_id]["active_session"] = None
            if "session_tools" not in self.user_data[user_id]:
                self.user_data[user_id]["session_tools"] = {}
            if "pending_tools" not in self.user_data[user_id]:
                self.user_data[user_id]["pending_tools"] = []

        session_uuid = self.user_data[user_id].get("active_session")
        current_model = model or self.model_name
        
        attempt = 0
        max_attempts = 2
        
        while attempt < max_attempts:
            attempt += 1
            enabled_tools = []
            if session_uuid:
                enabled_tools = self.get_session_tools(user_id, session_uuid)
            else:
                enabled_tools = self.get_session_tools(user_id, "pending")
            
            args = [self.gemini_cmd]
            args.extend(["--output-format", "stream-json"])
            
            if enabled_tools:
                args.extend(["--allowed-tools", ",".join(enabled_tools)])
            else:
                args.extend(["--allowed-tools", "none"])
            
            args.extend(["--approval-mode", "default"])

            if self.yolo_mode: args.append("--yolo")
            if session_uuid: args.extend(["--resume", session_uuid])
            if current_model: args.extend(["--model", current_model])
            args.extend(["--include-directories", self.working_dir])
            if file_path: args.append(f"@{file_path}")
            
            log_debug(f"Attempt {attempt}: Running command {" ".join(args)}")
            
            should_fallback = False
            proc = None
            try:
                proc = await asyncio.create_subprocess_exec(
                    *args, 
                    stdin=asyncio.subprocess.PIPE, 
                    stdout=asyncio.subprocess.PIPE, 
                    stderr=asyncio.subprocess.PIPE, 
                    cwd=self.working_dir
                )
                
                if prompt:
                    log_debug("Writing prompt to stdin...")
                    proc.stdin.write(prompt.encode('utf-8'))
                    await proc.stdin.drain()
                    proc.stdin.close()
                
                async def read_stderr(stderr_pipe):
                    try:
                        data = await stderr_pipe.read()
                        return data.decode()
                    except Exception as e: 
                        log_debug(f"Error reading stderr: {str(e)}")
                        return ""

                stderr_task = asyncio.create_task(read_stderr(proc.stderr))

                log_debug("Starting to read stdout")
                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        log_debug("Stdout closed (EOF)")
                        break
                    line_str = line.decode().strip()
                    if not line_str: continue
                    
                    log_debug(f"Received line: {line_str[:100]}...")
                    if ("429" in line_str or "No capacity available" in line_str) and attempt < max_attempts:
                        fallback = FALLBACK_MODELS.get(current_model)
                        if fallback:
                            log_debug(f"Capacity error detected, falling back to {fallback}")
                            yield {"type": "model_switch", "old_model": current_model, "new_model": fallback}
                            yield {"type": "message", "role": "assistant", "content": f"\n\n[Model {current_model} is currently busy. Switching to {fallback} for a faster response...]\n\n"}
                            current_model = fallback
                            should_fallback = True
                            break
                    
                    try:
                        data = json.loads(line_str)
                        yield data
                    except json.JSONDecodeError:
                        yield {"type": "raw", "content": line_str}
                
                if should_fallback:
                    try:
                        if proc.returncode is None:
                            proc.terminate()
                            await proc.wait()
                    except: pass
                    continue 

                await proc.wait()
                stderr_output = await stderr_task
                log_debug(f"Process exited with code {proc.returncode}")
                
                if proc.returncode != 0:
                    err = self._filter_errors(stderr_output.strip())
                    log_debug(f"Error output: {err}")
                    if ("429" in err or "No capacity available" in err) and attempt < max_attempts:
                        fallback = FALLBACK_MODELS.get(current_model)
                        if fallback:
                            yield {"type": "message", "role": "assistant", "content": f"\n\n[Model {current_model} is currently busy. Switching to {fallback}...]\n\n"}
                            current_model = fallback
                            continue

                    if session_uuid and any(x in err.lower() for x in ["no session", "not found", "invalid session"]):
                        self.user_data[user_id]["active_session"] = None
                        yield {"type": "error", "content": f"Session error: {err}"}
                    else:
                        yield {"type": "error", "content": f"Error: {err}"}
                
                break 

            except Exception as e:
                log_debug(f"Exception in stream: {str(e)}")
                yield {"type": "error", "content": f"Exception: {str(e)}"}
                break
            finally:
                if not session_uuid:
                    log_debug("New session detected, attempting to capture ID")
                    await asyncio.sleep(0.5)
                    new_uuid = await self._get_latest_session_uuid()
                    if new_uuid:
                        log_debug(f"Captured new session ID: {new_uuid}")
                        self.user_data[user_id]["active_session"] = new_uuid
                        if new_uuid not in self.user_data[user_id]["sessions"]:
                            self.user_data[user_id]["sessions"].append(new_uuid)
                        
                        pending = self.user_data[user_id].get("pending_tools", [])
                        if pending:
                            if "session_tools" not in self.user_data[user_id]:
                                self.user_data[user_id]["session_tools"] = {}
                            self.user_data[user_id]["session_tools"][new_uuid] = pending
                            self.user_data[user_id]["pending_tools"] = []
                            
                        self._save_user_data()
                
                if proc and proc.returncode is None:
                    try:
                        proc.terminate()
                        await proc.wait()
                    except: pass

    async def generate_response(self, user_id: str, prompt: str, model: Optional[str] = None, file_path: Optional[str] = None) -> str:
        full_response = ""
        async for chunk in self.generate_response_stream(user_id, prompt, model, file_path):
            if chunk.get("type") == "message":
                full_response += chunk.get("content", "")
            elif chunk.get("type") == "error":
                full_response += f"\n[Error: {chunk.get('content')}]"
            elif chunk.get("type") == "raw":
                 full_response += chunk.get("content", "") + "\n"
        return full_response.strip()

    async def get_user_sessions(self, user_id: str) -> List[Dict]:
        if user_id not in self.user_data:
            self.user_data[user_id] = {"active_session": None, "sessions": [], "session_tools": {}, "pending_tools": []}
            self._save_user_data()
            
        user_info = self.user_data[user_id]
        uuids = user_info.get("sessions", [])
        if not uuids: return []
        
        try:
            proc = await asyncio.create_subprocess_exec(self.gemini_cmd, "--list-sessions", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=self.working_dir)
            stdout, stderr = await proc.communicate()
            content = self._filter_errors(stdout.decode() + stderr.decode())
            pattern = r"^\s+\d+\.\s+(?P<title>.*?)\s+\((?P<time>.*?)\)\s+\[(?P<uuid>[a-fA-F0-9-]{36})\]"
            matches = re.finditer(pattern, content, re.MULTILINE)
            sessions = []
            for m in matches:
                info = m.groupdict()
                if info["uuid"] in uuids:
                    info["active"] = (info["uuid"] == user_info.get("active_session"))
                    sessions.append(info)
            
            return sessions[::-1]
        except: 
            return [{"uuid": u, "title": "Unknown", "time": "Unknown", "active": (u == user_info.get("active_session"))} for u in uuids]

    async def get_session_messages(self, session_uuid: str, limit: Optional[int] = None, offset: int = 0) -> List[Dict]:
        try:
            uuid_start = session_uuid.split('-')[0]
            home = os.path.expanduser("~")
            gemini_tmp_base = os.path.join(home, ".gemini", "tmp")
            if not os.path.exists(gemini_tmp_base): return []
            import glob
            search_path = os.path.join(gemini_tmp_base, "*", "chats", f"*{uuid_start}*.json")
            files = glob.glob(search_path)
            if not files: return []
            files.sort(key=os.path.getmtime, reverse=True)
            with open(files[0], 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_messages = data.get("messages", [])
                total = len(all_messages)
                if limit is not None:
                    start = max(0, total - offset - limit)
                    end = max(0, total - offset)
                    messages_to_process = all_messages[start:end]
                else:
                    messages_to_process = all_messages
                
                messages = []
                for msg in messages_to_process:
                    content = msg.get("content", "")
                    if not content or content.strip() == "": continue
                    messages.append({
                        "role": "user" if msg.get("type") == "user" else "bot",
                        "content": content
                    })
                return messages
        except Exception as e:
            print(f"Error loading session messages for {session_uuid}: {str(e)}")
            return []

    async def switch_session(self, user_id: str, uuid: str) -> bool:
        if user_id in self.user_data and uuid in self.user_data[user_id]["sessions"]:
            self.user_data[user_id]["active_session"] = uuid
            self._save_user_data()
            return True
        return False

    async def new_session(self, user_id: str):
        self.user_data.setdefault(user_id, {})["active_session"] = None
        self._save_user_data()

    async def delete_specific_session(self, user_id: str, uuid: str) -> bool:
        if user_id in self.user_data and uuid in self.user_data[user_id]["sessions"]:
            try:
                await (await asyncio.create_subprocess_exec(self.gemini_cmd, "--delete-session", uuid, cwd=self.working_dir)).communicate()
                self.user_data[user_id]["sessions"].remove(uuid)
                if self.user_data[user_id]["active_session"] == uuid: self.user_data[user_id]["active_session"] = None
                self._save_user_data()
                return True
            except: return False
        return False

    async def reset_chat(self, user_id: str) -> str:
        uuid = self.user_data.get(user_id, {}).get("active_session")
        if uuid:
            if await self.delete_specific_session(user_id, uuid): return "Conversation reset."
            return "Error resetting."
        return "No active session."


import httpx
import json
import os
import re
import asyncio
from typing import Dict, List, Any

class PatternSyncService:
    GITHUB_API_URL = "https://api.github.com/repos/danielmiessler/Fabric/contents/data/patterns"
    RAW_URL_BASE = "https://raw.githubusercontent.com/danielmiessler/Fabric/main/data/patterns"

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)

    async def fetch_pattern_list(self) -> List[str]:
        response = await self.client.get(self.GITHUB_API_URL)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch pattern list: {response.status_code}")
        
        items = response.json()
        return [item["name"] for item in items if item["type"] == "dir"]

    async def fetch_pattern_content(self, pattern_name: str) -> str:
        url = f"{self.RAW_URL_BASE}/{pattern_name}/system.md"
        response = await self.client.get(url)
        if response.status_code != 200:
            return ""
        return response.text

    def sanitize_content(self, content: str) -> str:
        # Remove instructions that mention running fabric commands
        content = re.sub(r'fabric\s+--pattern\s+\S+', 'the current pattern', content, flags=re.IGNORECASE)
        content = re.sub(r'run\s+the\s+pattern', 'use the prompt', content, flags=re.IGNORECASE)
        # Remove any other specific fabric CLI mentions
        content = re.sub(r'fabric\s+', 'Gemini ', content, flags=re.IGNORECASE)
        return content

    async def sync_all(self):
        pattern_names = await self.fetch_pattern_list()
        new_patterns = {}
        explanations = []

        # Limit to first 50 for now to avoid hitting rate limits or taking too long
        # The user said "include the rest", but there are hundreds.
        # I'll try to get them all but maybe in batches if needed.
        # Actually, I'll just go for it and see.
        
        tasks = []
        for name in pattern_names:
            tasks.append(self.fetch_pattern_content(name))
        
        contents = await asyncio.gather(*tasks)

        for name, content in zip(pattern_names, contents):
            if content:
                sanitized = self.sanitize_content(content)
                new_patterns[name] = sanitized
                # Try to extract a short description (first sentence of IDENTITY and PURPOSE or similar)
                desc = self.extract_description(sanitized)
                explanations.append(f"{len(explanations)+1}. **{name}**: {desc}")

        new_patterns["__explanations__"] = "\n".join(explanations)

        with open(PATTERNS_FILE, "w", encoding="utf-8") as f:
            json.dump(new_patterns, f, indent=4)
        
        reload_patterns()
        return len(new_patterns) - 1 # exclude __explanations__

    def extract_description(self, content: str) -> str:
        # Look for the section between # IDENTITY and PURPOSE and the next header
        match = re.search(r'# IDENTITY and PURPOSE\n\n(.*?)(?=\n# |\Z)', content, re.DOTALL)
        if match:
            desc = match.group(1).strip()
            # Clean up: remove internal markdown headers if they exist in the desc
            desc = re.sub(r'^#+ .*?\n', '', desc, flags=re.MULTILINE)
            # Replace multiple newlines with a single space for a compact preview
            desc = re.sub(r'\n+', ' ', desc)
            # Limit length but provide much more than before
            if len(desc) > 300:
                return desc[:297] + "..."
            return desc
        return "No description available."

    async def close(self):
        await self.client.aclose()


# --- ROUTERS ---
auth_router = APIRouter()
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional
import secrets
from eth_account import Account
from eth_account.messages import encode_defunct

# We will import the global instances from main later, or use dependencies.
# For now, we assume they are accessible via request.app.state.



@auth_router.get("/setup", response_class=HTMLResponse)
async def setup_pg(request: Request):
    user_manager = request.app.state.user_manager
    if user_manager.has_users():
        return RedirectResponse("/login")
    return request.app.state.render("setup.html", request=request)

@auth_router.post("/setup")
async def setup(request: Request, password: str = Form(...), origin: str = Form("http://localhost:8000"), rp_id: str = Form("localhost")):
    user_manager = request.app.state.user_manager
    if user_manager.has_users():
        raise HTTPException(status_code=403, detail="Setup already complete")
    
    # Save to .env
    update_env("ORIGIN", origin)
    update_env("RP_ID", rp_id)
    
    # Update config in memory
    ORIGIN = origin
    RP_ID = rp_id
    request.app.state.auth_service = AuthService(rp_id, RP_NAME, origin)
    
    user_manager.register_user("admin", password, role="admin")
    return RedirectResponse("/login", status_code=303)

@auth_router.get("/login", response_class=HTMLResponse)
async def login_pg(request: Request):
    return request.app.state.render("login.html", request=request)

@auth_router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    user_manager = request.app.state.user_manager
    if user_manager.authenticate_user(username, password):
        request.session["user"] = username
        # Use absolute URL for redirect to avoid potential issues with Service Worker or proxies
        return RedirectResponse(str(request.url_for("index")), status_code=303)
    return request.app.state.render("login.html", request=request, error="Invalid credentials")

@auth_router.post("/login/pattern")
async def login_pat(request: Request, pattern: str = Form(...), username: Optional[str] = Form(None)):
    user_manager = request.app.state.user_manager
    u = username if username else user_manager.get_user_by_pattern(pattern)
    if u and (not username or user_manager.authenticate_with_pattern(u, pattern)):
        request.session["user"] = u
        # Use absolute URL for redirect to avoid potential issues with Service Worker or proxies
        return RedirectResponse(str(request.url_for("index")), status_code=303)
    return request.app.state.render("login.html", request=request, error="Invalid pattern")

@auth_router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login")

@auth_router.get("/login/web3/challenge")
async def w3_ch(request: Request):
    c = f"Sign this: {secrets.token_hex(16)}"
    request.session["web3_challenge"] = c
    return {"challenge": c}

@auth_router.post("/login/web3/verify")
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

@auth_router.post("/user/update-pattern")
async def upd_pat(request: Request, pattern: str = Form(...)):
    user_manager = request.app.state.user_manager
    user = request.session.get("user")
    if user: return {"success": user_manager.set_pattern(user, pattern)}
    return {"success": False}

@auth_router.post("/user/link-wallet")
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

@auth_router.get("/register/passkey/options")
async def pk_reg_opt(request: Request):
    auth_service = request.app.state.auth_service
    user = request.session.get("user")
    if not user: raise HTTPException(401)
    opts = auth_service.generate_registration_options(user, user)
    request.session["registration_challenge"] = auth_service.bytes_to_base64url(opts.challenge)
    return HTMLResponse(auth_service.options_to_json(opts), media_type="application/json")

@auth_router.post("/register/passkey/verify")
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

@auth_router.post("/login/passkey/options")
async def pk_log_opt(request: Request, username: Optional[str] = Form(None)):
    user_manager = request.app.state.user_manager
    auth_service = request.app.state.auth_service
    credential_ids = [pk["credential_id"] for pk in user_manager.get_passkeys(username)] if username else []
    opts = auth_service.generate_authentication_options(credential_ids)
    request.session["authentication_challenge"] = auth_service.bytes_to_base64url(opts.challenge)
    if username: request.session["authentication_username"] = username
    return HTMLResponse(auth_service.options_to_json(opts), media_type="application/json")

@auth_router.post("/login/passkey/verify")
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


chat_router = APIRouter()
from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from typing import Optional
import os
import shutil
import json



async def get_user(request: Request):
    return request.session.get("user")

@chat_router.get("/", response_class=HTMLResponse)
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

@chat_router.get("/sessions")
async def get_sess(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    return await agent.get_user_sessions(user)

@chat_router.get("/sessions/{session_uuid}/messages")
async def get_sess_messages(session_uuid: str, request: Request, limit: Optional[int] = None, offset: int = 0, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    # Security: check if this session belongs to the user
    user_sessions = await agent.get_user_sessions(user)
    if not any(s['uuid'] == session_uuid for s in user_sessions):
        raise HTTPException(403, "Access denied")
    return await agent.get_session_messages(session_uuid, limit=limit, offset=offset)

@chat_router.post("/sessions/switch")
async def sw_sess(request: Request, session_uuid: str = Form(...), user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    return {"success": await agent.switch_session(user, session_uuid)}

@chat_router.post("/sessions/new")
async def nw_sess(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    await agent.new_session(user)
    return {"success": True}

@chat_router.post("/sessions/delete")
async def dl_sess(request: Request, session_uuid: str = Form(...), user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    return {"success": await agent.delete_specific_session(user, session_uuid)}

@chat_router.get("/sessions/{session_uuid}/tools")
async def get_sess_tools(session_uuid: str, request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    if session_uuid != "pending":
        user_sessions = await agent.get_user_sessions(user)
        if not any(s['uuid'] == session_uuid for s in user_sessions):
            raise HTTPException(403, "Access denied")
    return {"tools": agent.get_session_tools(user, session_uuid)}

@chat_router.post("/sessions/{session_uuid}/tools")
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

@chat_router.get("/patterns")
async def get_pats(request: Request):
    agent = request.app.state.agent
    # This logic was a bit involved in original_app.py
    # I'll simplify or copy it.
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

@chat_router.post("/chat")
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
        try:
            stream = agent.generate_response_stream(user, message, model=m_override, file_path=fpath)
            it = stream.__aiter__()
            while True:
                try:
                    # Wait for next chunk or timeout for heartbeat
                    chunk = await asyncio.wait_for(it.__anext__(), timeout=15.0)
                    yield f"data: {json.dumps(chunk)}\n\n"
                except asyncio.TimeoutError:
                    # Send SSE comment as heartbeat to keep connection alive
                    yield ": heartbeat\n\n"
                except StopAsyncIteration:
                    break
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
                    break
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@chat_router.post("/reset")
async def reset(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    return {"response": await agent.reset_chat(user)}


admin_router = APIRouter()
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional




async def get_user(request: Request):
    return request.session.get("user")

@admin_router.post("/admin/patterns/sync")
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

@admin_router.post("/admin/system/restart-setup")
async def restart_setup(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    user_manager.clear_all_users()
    request.session.clear()
    return {"success": True}

@admin_router.get("/admin", response_class=HTMLResponse)
async def admin_db(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin": return RedirectResponse("/")
    return request.app.state.render("admin.html", request=request, users=user_manager.get_all_users())

@admin_router.post("/admin/user/add")
async def adm_add(request: Request, username: str = Form(...), password: str = Form(...), role: str = Form(...), user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) == "admin": user_manager.register_user(username, password, role=role)
    return RedirectResponse("/admin", status_code=303)

@admin_router.post("/admin/user/remove")
async def adm_rem(request: Request, username: str = Form(...), user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) == "admin" and username != "admin": user_manager.remove_user(username)
    return {"success": True}

@admin_router.post("/admin/user/toggle-pattern")
async def adm_tog_pat(request: Request, username: str = Form(...), disabled: str = Form(...), user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) == "admin":
        is_disabled = disabled.lower() == 'true'
        user_manager.set_pattern_disabled(username, is_disabled)
        return {"success": True}
    return {"success": False}

@admin_router.post("/admin/user/update-password")
async def adm_upd(request: Request, username: str = Form(...), new_password: str = Form(...), user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) == "admin": user_manager.update_password(username, new_password)
    return RedirectResponse("/admin", status_code=303)


# --- MAIN ---
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

app = FastAPI()

# Session Middleware
# We enable https_only if the origin starts with https
https_only = ORIGIN.startswith("https")
app.add_middleware(
    SessionMiddleware, 
    secret_key=SESSION_SECRET,
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
UPLOAD_DIR = UPLOAD_DIR
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Templates
templates_dir = None


def render(name, **ctx):
    return HTMLResponse(Template(TEMPLATES[name]).render(**ctx))

# Services
user_manager = UserManager()
auth_service = AuthService(RP_ID, RP_NAME, ORIGIN)
agent = GeminiAgent()

# App State
app.state.user_manager = user_manager
app.state.auth_service = auth_service
app.state.agent = agent
app.state.render = render
app.state.UPLOAD_DIR = UPLOAD_DIR

# Static Files
static_dir = os.path.join(os.path.dirname(__file__), "static")


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
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(admin_router)



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


if __name__ == "__main__":
    import uvicorn
    import argparse
    
    parser = argparse.ArgumentParser(description="Run the Gemini Agent")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the service on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    args = parser.parse_args()
    
    uvicorn.run(app, host=args.host, port=args.port)