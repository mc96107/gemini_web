import json, os, mimetypes, hashlib, asyncio, re, secrets, shutil, uvicorn, bcrypt, subprocess, sys, base64, httpx, pypandoc, pandas as pd
from typing import Dict, Optional, List, Tuple, Any
from pydantic import BaseModel
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
RP_ID = os.getenv("RP_ID")
RP_NAME = os.getenv("RP_NAME", "Gemini Agent")
ORIGIN = os.getenv("ORIGIN")

# Security Configuration
SESSION_SECRET = os.getenv("SESSION_SECRET", secrets.token_hex(32))

# Application Configuration
UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(os.getcwd(), "tmp", "user_attachments"))
AGENT_BASE_DIR = os.getenv("AGENT_BASE_DIR", os.path.join(os.getcwd(), "data", "agents"))
SKILLS_BASE_DIR = os.path.join(os.getcwd(), ".gemini", "skills")
SETTINGS_FILE = os.path.join(os.getcwd(), "data", "settings.json")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-3-pro-preview")
LOG_LEVEL = os.getenv("LOG_LEVEL", "NONE").upper()
GEMINI_CMD = os.getenv("GEMINI_CMD", "gemini")

import json
import logging

def get_all_global_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading settings: {e}")
    return {}

def get_global_setting(key: str, default=None):
    settings = get_all_global_settings()
    return settings.get(key, default)

def update_global_setting(key: str, value: str):
    settings = get_all_global_settings()
    settings[key] = value
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        logging.error(f"Error saving settings: {e}")

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
    "admin.html": "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n    <meta charset=\"UTF-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n    <title>Admin Dashboard - Gemini Agent</title>\n    <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css\" rel=\"stylesheet\">\n    <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css\">\n    <link rel=\"icon\" type=\"image/svg+xml\" href=\"/static/icon.svg?v=2\">\n    <style>\n        body { background-color: #121212; color: #e0e0e0; }\n        .card { background-color: #1e1e1e; border: 1px solid #333; }\n        .table { color: #e0e0e0; }\n        .table-hover tbody tr:hover { background-color: #2c2c2c; }\n        h2, h5, .card-title { color: #fff !important; }\n        .text-muted { color: #aaa !important; }\n        .form-label { color: #ccc !important; }\n    </style>\n</head>\n<body>\n    <nav class=\"navbar navbar-expand-lg navbar-dark bg-dark border-bottom border-secondary\">\n        <div class=\"container\">\n            <a class=\"navbar-brand\" href=\"/\"><i class=\"bi bi-robot text-primary me-2\"></i>Gemini Agent Admin</a>\n            <div class=\"navbar-nav ms-auto\">\n                <a class=\"nav-link\" href=\"/\">Back to Chat</a>\n                <a class=\"nav-link\" href=\"/logout\">Logout</a>\n            </div>\n        </div>\n    </nav>\n\n    <div class=\"container mt-4\">\n        <h2 class=\"mb-4\">User Management</h2>\n\n        <div class=\"row\">\n            <div class=\"col-md-8\">\n                <div class=\"card shadow-sm\">\n                    <div class=\"card-body\">\n                        <h5 class=\"card-title\">Users</h5>\n                        <div class=\"table-responsive\">\n                            <table class=\"table table-dark table-hover\">\n                                <thead>\n                                    <tr>\n                                        <th>Username</th>\n                                        <th>Role</th>\n                                        <th>Pattern Login</th>\n                                        <th>Actions</th>\n                                    </tr>\n                                </thead>\n                                <tbody>\n                                    {% for user in users %}\n                                    <tr>\n                                        <td>{{ user.username }}</td>\n                                        <td>\n                                            <div class=\"dropdown\">\n                                                <button class=\"btn btn-sm {{ 'btn-primary' if user.role == 'admin' else 'btn-secondary' }} dropdown-toggle py-0\" type=\"button\" data-bs-toggle=\"dropdown\" aria-expanded=\"false\" style=\"font-size: 0.75rem;\">\n                                                    {{ user.role }}\n                                                </button>\n                                                <ul class=\"dropdown-menu dropdown-menu-dark shadow\">\n                                                    <li><a class=\"dropdown-item small\" href=\"#\" onclick=\"changeRole('{{ user.username }}', 'user')\">User</a></li>\n                                                    <li><a class=\"dropdown-item small\" href=\"#\" onclick=\"changeRole('{{ user.username }}', 'admin')\">Admin</a></li>\n                                                </ul>\n                                            </div>\n                                        </td>\n                                        <td>\n                                            <div class=\"form-check form-switch\">\n                                                <input class=\"form-check-input\" type=\"checkbox\" role=\"switch\" \n                                                    id=\"patternSwitch_{{ user.username }}\" \n                                                    {% if not user.pattern_disabled %}checked{% endif %}\n                                                    onchange=\"togglePattern('{{ user.username }}', this.checked)\">\n                                                <label class=\"form-check-label\" for=\"patternSwitch_{{ user.username }}\">\n                                                    {{ 'Enabled' if not user.pattern_disabled else 'Disabled' }}\n                                                </label>\n                                            </div>\n                                        </td>\n                                        <td>\n                                            {% if user.username != 'admin' %}\n                                            <button class=\"btn btn-sm btn-outline-danger\" onclick=\"deleteUser('{{ user.username }}')\">Delete</button>\n                                            {% endif %}\n                                            <button class=\"btn btn-sm btn-outline-info\" onclick=\"showChangePassword('{{ user.username }}')\">Change Password</button>\n                                        </td>\n                                    </tr>\n                                    {% endfor %}\n                                </tbody>\n                            </table>\n                        </div>\n                    </div>\n                </div>\n            </div>\n\n            <div class=\"col-md-4\">\n                <div class=\"card shadow-sm mb-4\">\n                    <div class=\"card-body\">\n                        <h5 class=\"card-title\">System Actions</h5>\n                        <button class=\"btn btn-info w-100 mb-2\" onclick=\"syncPatterns()\">\n                            <i class=\"bi bi-arrow-repeat me-1\"></i> Sync Fabric Patterns\n                        </button>\n                        <button class=\"btn btn-outline-danger w-100 mb-2\" onclick=\"clearAllTags()\">\n                            <i class=\"bi bi-trash me-1\"></i> Clear All Chat Tags\n                        </button>\n                        <button class=\"btn btn-warning w-100 mb-2\" onclick=\"restartSetup()\">\n                            <i class=\"bi bi-exclamation-triangle me-1\"></i> Restart Setup\n                        </button>\n                        <div class=\"mt-3\">\n                            <label class=\"form-label small text-muted\">Logging Level</label>\n                            <select id=\"log-level-select\" class=\"form-select form-select-sm bg-dark text-light border-secondary\" onchange=\"updateLogLevel(this.value)\">\n                                <option value=\"NONE\">NONE (Silent)</option>\n                                <option value=\"INFO\">INFO (Normal)</option>\n                                <option value=\"DEBUG\">DEBUG (Verbose)</option>\n                            </select>\n                        </div>\n                        <div id=\"sync-status\" class=\"small mt-2\"></div>\n                    </div>\n                </div>\n\n                <div class=\"card shadow-sm mb-4\">\n                    <div class=\"card-body\">\n                        <h5 class=\"card-title\">Global Settings</h5>\n                        <div class=\"mb-3\">\n                            <div class=\"d-flex justify-content-between align-items-center mb-1\">\n                                <label class=\"form-label small text-muted mb-0\">Interactive Mode Instructions</label>\n                                <button class=\"btn btn-link btn-sm text-warning p-0\" style=\"text-decoration: none; font-size: 0.7rem;\" onclick=\"resetInteractiveModeInstructions()\">\n                                    <i class=\"bi bi-arrow-counterclockwise\"></i> Reset\n                                </button>\n                            </div>\n                            <textarea id=\"interactive-mode-instructions\" class=\"form-control form-control-sm bg-dark text-light border-secondary\" rows=\"4\"></textarea>\n                        </div>\n                        <button class=\"btn btn-primary btn-sm w-100\" onclick=\"saveGlobalSettings()\">\n                            Save All Settings\n                        </button>\n                        <div id=\"settings-status\" class=\"small mt-2\"></div>\n                    </div>\n                </div>\n\n                <div class=\"card shadow-sm mb-4\">\n                    <div class=\"card-body\">\n                        <h5 class=\"card-title\">Add User</h5>\n                        <form action=\"/admin/user/add\" method=\"post\">\n                            <div class=\"mb-3\">\n                                <label class=\"form-label\">Username</label>\n                                <input type=\"text\" name=\"username\" class=\"form-control bg-dark text-light border-secondary\" required>\n                            </div>\n                            <div class=\"mb-3\">\n                                <label class=\"form-label\">Password</label>\n                                <input type=\"password\" name=\"password\" class=\"form-control bg-dark text-light border-secondary\" required>\n                            </div>\n                            <div class=\"mb-3\">\n                                <label class=\"form-label\">Role</label>\n                                <select name=\"role\" class=\"form-select bg-dark text-light border-secondary\">\n                                    <option value=\"user\">User</option>\n                                    <option value=\"admin\">Admin</option>\n                                </select>\n                            </div>\n                            <button type=\"submit\" class=\"btn btn-success w-100\">Add User</button>\n                        </form>\n                    </div>\n                </div>\n            </div>\n        </div>\n\n        <hr class=\"border-secondary my-5\">\n\n        <h2 class=\"mb-4\">Agent Management</h2>\n        \n        <div id=\"orchestration-warnings\" class=\"mb-3\"></div>\n\n        <div class=\"row\">\n            <div class=\"col-md-12\">\n                <div class=\"card shadow-sm\">\n                    <div class=\"card-body\">\n                        <div class=\"d-flex justify-content-between align-items-center mb-3\">\n                            <h5 class=\"card-title mb-0\">Agents</h5>\n                            <div class=\"d-flex gap-2\">\n                                <select id=\"categoryFilter\" class=\"form-select form-select-sm bg-dark text-light border-secondary\" style=\"width: auto;\" onchange=\"renderAgents()\">\n                                    <option value=\"all\">All Categories</option>\n                                </select>\n                                <button class=\"btn btn-sm btn-outline-info\" onclick=\"editRootAgent()\">\n                                    <i class=\"bi bi-gear-fill me-1\"></i> Root Orchestrator\n                                </button>\n                                <button class=\"btn btn-sm btn-primary\" onclick=\"showAgentEditor()\">\n                                    <i class=\"bi bi-plus-lg me-1\"></i> New Agent\n                                </button>\n                            </div>\n                        </div>\n                        <div class=\"table-responsive\">\n                            <table class=\"table table-dark table-hover\">\n                                <thead>\n                                    <tr>\n                                        <th>Category</th>\n                                        <th>Enabled</th>\n                                        <th>Name</th>\n                                        <th>Folder</th>\n                                        <th>Description</th>\n                                        <th>Actions</th>\n                                    </tr>\n                                </thead>\n                                <tbody id=\"agentsTableBody\">\n                                    <!-- Loaded via JS -->\n                                </tbody>\n                            </table>\n                        </div>\n                    </div>\n                </div>\n            </div>\n        </div>\n\n        </div>\n    </div>\n\n    <!-- Agent Editor Modal -->\n    <div class=\"modal fade\" id=\"agentModal\" tabindex=\"-1\" aria-hidden=\"true\">\n        <div class=\"modal-dialog modal-lg\">\n            <div class=\"modal-content bg-dark text-light border-secondary\">\n                <div class=\"modal-header border-secondary\">\n                    <h5 class=\"modal-title\" id=\"agentModalTitle\">New Agent</h5>\n                    <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>\n                </div>\n                <div class=\"modal-body\">\n                    <form id=\"agentForm\">\n                        <div class=\"row mb-3\">\n                            <div class=\"col-md-6\">\n                                <label class=\"form-label\">Category</label>\n                                <input type=\"text\" id=\"agentCategory\" class=\"form-control bg-dark text-light border-secondary\" placeholder=\"e.g., functions, projects\" required>\n                            </div>\n                            <div class=\"col-md-6\">\n                                <label class=\"form-label\">Folder Name</label>\n                                <input type=\"text\" id=\"agentFolder\" class=\"form-control bg-dark text-light border-secondary\" placeholder=\"e.g., team_manager\" required>\n                            </div>\n                        </div>\n                        <div class=\"mb-3\">\n                            <label class=\"form-label\">Name</label>\n                            <input type=\"text\" id=\"agentName\" class=\"form-control bg-dark text-light border-secondary\" placeholder=\"Display Name\" required>\n                        </div>\n                        <div class=\"mb-3\">\n                            <label class=\"form-label\">Description</label>\n                            <input type=\"text\" id=\"agentDescription\" class=\"form-control bg-dark text-light border-secondary\" placeholder=\"Brief description\">\n                        </div>\n                        <div class=\"mb-3\">\n                            <label class=\"form-label\">System Prompt (Markdown)</label>\n                            <textarea id=\"agentPrompt\" class=\"form-control bg-dark text-light border-secondary\" rows=\"10\" placeholder=\"Agent instructions...\" required></textarea>\n                        </div>\n                        <div class=\"mb-3\">\n                            <label class=\"form-label\">Associated Skills</label>\n                            <div id=\"skillsContainer\" class=\"d-flex flex-wrap gap-2\">\n                                <!-- Loaded via JS -->\n                            </div>\n                        </div>\n                    </form>\n                </div>\n                <div class=\"modal-footer border-secondary\">\n                    <button type=\"button\" class=\"btn btn-secondary\" data-bs-dismiss=\"modal\">Cancel</button>\n                    <button type=\"button\" class=\"btn btn-primary\" onclick=\"saveAgent()\">Save Agent</button>\n                </div>\n            </div>\n        </div>\n    </div>\n\n    <!-- Change Password Modal -->\n    <div class=\"modal fade\" id=\"passwordModal\" tabindex=\"-1\" aria-hidden=\"true\">\n        <div class=\"modal-dialog\">\n            <div class=\"modal-content bg-dark text-light border-secondary\">\n                <div class=\"modal-header border-secondary\">\n                    <h5 class=\"modal-title\">Change Password for <span id=\"targetUsername\"></span></h5>\n                    <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>\n                </div>\n                <form action=\"/admin/user/update-password\" method=\"post\">\n                    <div class=\"modal-body\">\n                        <input type=\"hidden\" name=\"username\" id=\"modalUsername\">\n                        <div class=\"mb-3\">\n                            <label class=\"form-label\">New Password</label>\n                            <input type=\"password\" name=\"new_password\" class=\"form-control bg-dark text-light border-secondary\" required>\n                        </div>\n                    </div>\n                    <div class=\"modal-footer border-secondary\">\n                        <button type=\"button\" class=\"btn btn-secondary\" data-bs-dismiss=\"modal\">Cancel</button>\n                        <button type=\"submit\" class=\"btn btn-primary\">Update Password</button>\n                    </div>\n                </form>\n            </div>\n        </div>\n    </div>\n\n    <div class=\"row mt-4\">\n        <div class=\"col-md-6\">\n            <div class=\"card shadow-sm\">\n                <div class=\"card-body\">\n                    <div class=\"d-flex justify-content-between align-items-center mb-3\">\n                        <h5 class=\"card-title mb-0\">Available Skills</h5>\n                        <button class=\"btn btn-primary btn-sm\" onclick=\"showNewSkill()\">\n                            <i class=\"bi bi-plus-lg me-1\"></i> Add Skill\n                        </button>\n                    </div>\n                    <p class=\"text-muted small\">Managed in <code>.gemini/skills/</code></p>\n                    <div id=\"dashboardSkillsList\" class=\"list-group list-group-flush bg-dark\">\n                        <!-- Loaded via JS -->\n                    </div>\n                </div>\n            </div>\n        </div>\n        <div class=\"col-md-6\">\n            <div class=\"card shadow-sm\">\n                <div class=\"card-body\">\n                    <div class=\"d-flex justify-content-between align-items-center mb-3\">\n                        <h5 class=\"card-title mb-0\">MCP Servers</h5>\n                        <button class=\"btn btn-primary btn-sm\" onclick=\"showNewMCP()\">\n                            <i class=\"bi bi-plus-lg me-1\"></i> Add MCP Server\n                        </button>\n                    </div>\n                    <div class=\"table-responsive\">\n                        <table class=\"table table-dark table-hover\">\n                            <thead>\n                                <tr>\n                                    <th>Status</th>\n                                    <th>Name</th>\n                                    <th>Command</th>\n                                    <th>Actions</th>\n                                </tr>\n                            </thead>\n                            <tbody id=\"mcpTableBody\">\n                                <!-- Loaded via JS -->\n                            </tbody>\n                        </table>\n                    </div>\n                </div>\n            </div>\n        </div>\n    </div>\n\n    <!-- MCP Modal -->\n    <div class=\"modal fade\" id=\"mcpModal\" tabindex=\"-1\" aria-hidden=\"true\">\n        <div class=\"modal-dialog\">\n            <div class=\"modal-content bg-dark text-light border-secondary\">\n                <div class=\"modal-header border-secondary\">\n                    <h5 class=\"modal-title\" id=\"mcpModalTitle\">Add MCP Server</h5>\n                    <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>\n                </div>\n                <div class=\"modal-body\">\n                    <form id=\"mcpForm\">\n                        <div class=\"mb-3\">\n                            <label class=\"form-label\">Name</label>\n                            <input type=\"text\" id=\"mcpName\" class=\"form-control bg-dark text-light border-secondary\" placeholder=\"e.g., sqlite-server\" required>\n                        </div>\n                        <div class=\"mb-3\">\n                            <label class=\"form-label\">Command</label>\n                            <input type=\"text\" id=\"mcpCommand\" class=\"form-control bg-dark text-light border-secondary\" placeholder=\"e.g., npx\" required>\n                        </div>\n                        <div class=\"mb-3\">\n                            <label class=\"form-label\">Arguments (Space separated)</label>\n                            <input type=\"text\" id=\"mcpArgs\" class=\"form-control bg-dark text-light border-secondary\" placeholder=\"e.g., -y @modelcontextprotocol/server-sqlite --db /path/to/db\">\n                        </div>\n                    </form>\n                </div>\n                <div class=\"modal-footer border-secondary\">\n                    <button type=\"button\" class=\"btn btn-secondary\" data-bs-dismiss=\"modal\">Cancel</button>\n                    <button type=\"button\" class=\"btn btn-primary\" onclick=\"saveMCP()\">Add Server</button>\n                </div>\n            </div>\n        </div>\n    </div>\n\n    <!-- Skill Modal -->\n    <div class=\"modal fade\" id=\"skillModal\" tabindex=\"-1\" aria-hidden=\"true\">\n        <div class=\"modal-dialog modal-lg\">\n            <div class=\"modal-content bg-dark text-light border-secondary\">\n                <div class=\"modal-header border-secondary\">\n                    <h5 class=\"modal-title\" id=\"skillModalTitle\">New Skill</h5>\n                    <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>\n                </div>\n                <div class=\"modal-body\">\n                    <form id=\"skillForm\">\n                        <div class=\"mb-3\">\n                            <label class=\"form-label\">Skill Name (Filename)</label>\n                            <input type=\"text\" id=\"skillName\" class=\"form-control bg-dark text-light border-secondary\" placeholder=\"e.g., code-reviewer\" required>\n                        </div>\n                        <div class=\"mb-3\">\n                            <label class=\"form-label\">Description</label>\n                            <input type=\"text\" id=\"skillDescription\" class=\"form-control bg-dark text-light border-secondary\" placeholder=\"Short summary of what this skill does\">\n                        </div>\n                        <div class=\"mb-3\">\n                            <label class=\"form-label\">Instructions (Markdown)</label>\n                            <textarea id=\"skillContent\" class=\"form-control bg-dark text-light border-secondary\" rows=\"15\" placeholder=\"## Instructions\\n...\" required></textarea>\n                        </div>\n                    </form>\n                </div>\n                <div class=\"modal-footer border-secondary\">\n                    <button type=\"button\" class=\"btn btn-secondary\" data-bs-dismiss=\"modal\">Cancel</button>\n                    <button type=\"button\" class=\"btn btn-primary\" onclick=\"saveSkill()\">Save Skill</button>\n                </div>\n            </div>\n        </div>\n    </div>\n\n    <script src=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js\"></script>\n    <script>\n        const passwordModal = new bootstrap.Modal(document.getElementById('passwordModal'));\n        const agentModal = new bootstrap.Modal(document.getElementById('agentModal'));\n        const mcpModal = new bootstrap.Modal(document.getElementById('mcpModal'));\n        const skillModal = new bootstrap.Modal(document.getElementById('skillModal'));\n        let allAgents = [];\n        let allSkills = [];\n\n        document.addEventListener('DOMContentLoaded', () => {\n            const logLevel = \"{{ log_level }}\";\n            const select = document.getElementById('log-level-select');\n            if (select) select.value = logLevel;\n            fetchAgents();\n            fetchMCP();\n            fetchSkills();\n            fetchGlobalSettings();\n        });\n\n        async function fetchSkills() {\n            try {\n                const res = await fetch('/admin/skills');\n                allSkills = await res.json();\n                \n                const list = document.getElementById('dashboardSkillsList');\n                if (list) {\n                    list.innerHTML = '';\n                    allSkills.forEach(skill => {\n                        const item = document.createElement('div');\n                        item.className = 'list-group-item bg-dark text-light border-secondary d-flex justify-content-between align-items-center py-1';\n                        item.innerHTML = `\n                            <span><i class=\"bi bi-magic me-2 text-info\"></i>${skill}</span>\n                            <div>\n                                <button class=\"btn btn-sm btn-link text-info p-0 me-2\" onclick=\"editSkill('${skill}')\"><i class=\"bi bi-pencil\"></i></button>\n                                <button class=\"btn btn-sm btn-link text-danger p-0\" onclick=\"deleteSkill('${skill}')\"><i class=\"bi bi-trash\"></i></button>\n                            </div>\n                        `;\n                        list.appendChild(item);\n                    });\n                    if (allSkills.length === 0) {\n                        list.innerHTML = '<div class=\"text-muted small p-2\">No skills found.</div>';\n                    }\n                }\n            } catch (err) { console.error('Error fetching skills:', err); }\n        }\n\n            function showNewSkill() {\n                document.getElementById('skillModalTitle').textContent = 'New Skill';\n                document.getElementById('skillName').value = '';\n                document.getElementById('skillName').disabled = false;\n                document.getElementById('skillDescription').value = '';\n                document.getElementById('skillContent').value = '# Skill Title\\n\\n## Instructions\\n...';\n                skillModal.show();\n            }\n        async function editSkill(name) {\n            try {\n                const res = await fetch(`/admin/skills/${name}`);\n                const skill = await res.json();\n                document.getElementById('skillModalTitle').textContent = 'Edit Skill';\n                document.getElementById('skillName').value = skill.name;\n                document.getElementById('skillName').disabled = true;\n                document.getElementById('skillDescription').value = skill.description || '';\n                document.getElementById('skillContent').value = skill.content;\n                skillModal.show();\n            } catch (err) { alert('Error loading skill'); }\n        }\n\n        async function saveSkill() {\n            const name = document.getElementById('skillName').value.trim();\n            const description = document.getElementById('skillDescription').value.trim();\n            const content = document.getElementById('skillContent').value.trim();\n            if (!name || !content) return;\n\n            try {\n                const res = await fetch('/admin/skills', {\n                    method: 'POST',\n                    headers: {'Content-Type': 'application/json'},\n                    body: JSON.stringify({name, description, content})\n                });\n                const data = await res.json();\n                if (data.success) {\n                    skillModal.hide();\n                    fetchSkills();\n                } else { alert('Error saving skill'); }\n            } catch (err) { alert('Request failed'); }\n        }\n\n        async function deleteSkill(name) {\n            if (!confirm(`Are you sure you want to delete skill \"${name}\"?`)) return;\n            try {\n                const res = await fetch(`/admin/skills/${name}`, { method: 'DELETE' });\n                const data = await res.json();\n                if (data.success) {\n                    fetchSkills();\n                } else { alert('Error deleting skill'); }\n            } catch (err) { alert('Request failed'); }\n        }\n\n        function renderSkillsCheckboxes(selectedSkills = []) {\n            const container = document.getElementById('skillsContainer');\n            container.innerHTML = '';\n            \n            if (allSkills.length === 0) {\n                container.innerHTML = '<span class=\"text-muted small\">No skills found in .gemini/skills/</span>';\n                return;\n            }\n\n            allSkills.forEach(skill => {\n                const div = document.createElement('div');\n                div.className = 'form-check form-check-inline';\n                const checked = selectedSkills.includes(skill) ? 'checked' : '';\n                div.innerHTML = `\n                    <input class=\"form-check-input skill-checkbox\" type=\"checkbox\" value=\"${skill}\" id=\"skill_${skill}\" ${checked}>\n                    <label class=\"form-check-label small\" for=\"skill_${skill}\">${skill}</label>\n                `;\n                container.appendChild(div);\n            });\n        }\n\n        async function fetchMCP() {\n            try {\n                const res = await fetch('/admin/mcp');\n                const servers = await res.json();\n                const tbody = document.getElementById('mcpTableBody');\n                tbody.innerHTML = '';\n                \n                servers.forEach(s => {\n                    const tr = document.createElement('tr');\n                    tr.innerHTML = `\n                        <td>\n                            <div class=\"form-check form-switch\">\n                                <input class=\"form-check-input\" type=\"checkbox\" role=\"switch\" ${s.enabled ? 'checked' : ''} \n                                    onchange=\"toggleMCP('${s.name}', this.checked)\">\n                                <span class=\"badge ${s.status === 'Connected' ? 'bg-success' : 'bg-secondary'} ms-1\" style=\"font-size: 0.6rem;\">${s.status}</span>\n                            </div>\n                        </td>\n                        <td><strong>${s.name}</strong></td>\n                        <td><code>${s.command}</code></td>\n                        <td>\n                            <button class=\"btn btn-sm btn-outline-danger\" onclick=\"removeMCP('${s.name}')\"><i class=\"bi bi-trash\"></i></button>\n                        </td>\n                    `;\n                    tbody.appendChild(tr);\n                });\n            } catch (err) {\n                console.error('Error fetching MCP servers:', err);\n            }\n        }\n\n        function showNewMCP() {\n            document.getElementById('mcpForm').reset();\n            mcpModal.show();\n        }\n\n        async function saveMCP() {\n            const name = document.getElementById('mcpName').value;\n            const command = document.getElementById('mcpCommand').value;\n            const args = document.getElementById('mcpArgs').value;\n            \n            if (!name || !command) return;\n            \n            try {\n                const res = await fetch('/admin/mcp/add', {\n                    method: 'POST',\n                    headers: {'Content-Type': 'application/json'},\n                    body: JSON.stringify({name, command, args})\n                });\n                const data = await res.json();\n                if (data.success) {\n                    mcpModal.hide();\n                    fetchMCP();\n                } else {\n                    alert('Error adding MCP: ' + data.output);\n                }\n            } catch (err) {\n                alert('Request failed');\n            }\n        }\n\n        async function removeMCP(name) {\n            if (!confirm(`Are you sure you want to remove MCP server \"${name}\"?`)) return;\n            try {\n                const res = await fetch('/admin/mcp/remove', {\n                    method: 'POST',\n                    headers: {'Content-Type': 'application/json'},\n                    body: JSON.stringify({name})\n                });\n                const data = await res.json();\n                if (data.success) {\n                    fetchMCP();\n                } else {\n                    alert('Error removing MCP: ' + data.output);\n                }\n            } catch (err) {\n                alert('Request failed');\n            }\n        }\n\n        async function toggleMCP(name, enabled) {\n            try {\n                const res = await fetch('/admin/mcp/toggle', {\n                    method: 'POST',\n                    headers: {'Content-Type': 'application/json'},\n                    body: JSON.stringify({name, enabled})\n                });\n                const data = await res.json();\n                if (!data.success) {\n                    alert('Error toggling MCP: ' + data.output);\n                    fetchMCP(); // Revert UI\n                }\n            } catch (err) {\n                alert('Request failed');\n                fetchMCP();\n            }\n        }\n\n        async function fetchAgents() {\n            try {\n                const res = await fetch('/admin/agents');\n                allAgents = await res.json();\n                updateCategoryFilter();\n                renderAgents();\n                validateOrchestration();\n            } catch (e) { console.error('Error fetching agents:', e); }\n        }\n\n        async function fetchGlobalSettings() {\n            try {\n                const res = await fetch('/admin/settings');\n                const data = await res.json();\n                if (data.interactive_mode_instructions) {\n                    document.getElementById('interactive-mode-instructions').value = data.interactive_mode_instructions;\n                }\n            } catch (e) { console.error('Error fetching settings:', e); }\n        }\n\n        async function saveGlobalSettings() {\n            const status = document.getElementById('settings-status');\n            const interactiveInstructions = document.getElementById('interactive-mode-instructions').value;\n            \n            status.textContent = 'Saving...';\n            status.className = 'small mt-2 text-info';\n\n            try {\n                const res = await fetch('/admin/settings', {\n                    method: 'POST',\n                    headers: { 'Content-Type': 'application/json' },\n                    body: JSON.stringify({ \n                        interactive_mode_instructions: interactiveInstructions\n                    })\n                });\n                const data = await res.json();\n                if (data.success) {\n                    status.textContent = 'Settings saved successfully!';\n                    status.className = 'small mt-2 text-success';\n                    setTimeout(() => { status.textContent = ''; }, 3000);\n                } else {\n                    status.textContent = 'Error saving settings';\n                    status.className = 'small mt-2 text-danger';\n                }\n            } catch (e) {\n                status.textContent = 'Error: ' + e.message;\n                status.className = 'small mt-2 text-danger';\n            }\n        }\n\n        function resetInteractiveModeInstructions() {\n            const defaultInstructions = `You can ask interactive multiple-choice or open-ended questions to the user in their preferred language (e.g., Greek).\nTo trigger a question card, include a JSON block in your response using this format:\n{\"type\": \"question\", \"question\": \"Your question text here\", \"options\": [\"Option 1\", \"Option 2\"], \"allow_multiple\": false}\n- The 'question' and 'options' values should match the language of the conversation.\n- If 'allow_multiple' is true, users can select several options.\n- If 'options' is empty [], it is an open-ended question.\nThe user's response will be sent back to you as a normal message.`;\n            \n            document.getElementById('interactive-mode-instructions').value = defaultInstructions;\n        }\n\n        function updateCategoryFilter() {\n            const filter = document.getElementById('categoryFilter');\n            const categories = [...new Set(allAgents.map(a => a.category))].sort();\n            \n            // Keep \"All Categories\"\n            filter.innerHTML = '<option value=\"all\">All Categories</option>';\n            categories.forEach(cat => {\n                const opt = document.createElement('option');\n                opt.value = cat;\n                opt.textContent = cat;\n                filter.appendChild(opt);\n            });\n        }\n\n        function renderAgents() {\n            const filter = document.getElementById('categoryFilter').value;\n            const tbody = document.getElementById('agentsTableBody');\n            tbody.innerHTML = '';\n\n            const filtered = filter === 'all' ? allAgents : allAgents.filter(a => a.category === filter);\n\n            filtered.forEach(agent => {\n                const tr = document.createElement('tr');\n                const isEnabled = agent.parent !== null && agent.parent !== undefined;\n                const isRoot = agent.category === 'root';\n                \n                tr.innerHTML = `\n                    <td><span class=\"badge bg-secondary\">${agent.category}</span></td>\n                    <td>\n                        <div class=\"form-check form-switch\">\n                            <input class=\"form-check-input\" type=\"checkbox\" role=\"switch\" \n                                id=\"agentEnabled_${agent.category}_${agent.folder_name}\" \n                                ${isEnabled ? 'checked' : ''}\n                                ${isRoot ? 'disabled' : ''}\n                                onchange=\"toggleAgentEnabled('${agent.category}', '${agent.folder_name}', this.checked)\">\n                        </div>\n                    </td>\n                    <td><strong>${agent.name}</strong></td>\n                    <td><code>${agent.folder_name}</code></td>\n                    <td class=\"small text-muted\">${agent.description || ''}</td>\n                    <td>\n                        <button class=\"btn btn-sm btn-outline-info me-1\" onclick=\"editAgent('${agent.category}', '${agent.folder_name}')\">Edit</button>\n                        <button class=\"btn btn-sm btn-outline-danger\" onclick=\"deleteAgent('${agent.category}', '${agent.folder_name}')\">Delete</button>\n                    </td>\n                `;\n                tbody.appendChild(tr);\n            });\n        }\n\n        async function toggleAgentEnabled(category, name, enabled) {\n            try {\n                const res = await fetch(`/admin/agents/${category}/${name}/toggle-enabled`, {\n                    method: 'POST',\n                    headers: { 'Content-Type': 'application/json' },\n                    body: JSON.stringify({ enabled })\n                });\n                const result = await res.json();\n                if (result.success) {\n                    validateOrchestration();\n                } else {\n                    alert('Error toggling agent status');\n                    document.getElementById(`agentEnabled_${category}_${name}`).checked = !enabled;\n                }\n            } catch (e) {\n                console.error(e);\n                alert('Error');\n                document.getElementById(`agentEnabled_${category}_${name}`).checked = !enabled;\n            }\n        }\n\n        async function validateOrchestration() {\n            try {\n                const res = await fetch('/admin/agents/validate');\n                const data = await res.json();\n                const container = document.getElementById('orchestration-warnings');\n                container.innerHTML = '';\n                \n                if (data.warnings && data.warnings.length > 0) {\n                    const alert = document.createElement('div');\n                    alert.className = 'alert alert-warning border-warning bg-dark-subtle py-2 mb-0';\n                    alert.innerHTML = `\n                        <div class=\"d-flex align-items-center\">\n                            <i class=\"bi bi-exclamation-triangle-fill me-2 text-warning\"></i>\n                            <div>\n                                <h6 class=\"alert-heading mb-1 small fw-bold\">Orchestration Warnings</h6>\n                                <ul class=\"mb-0 small ps-3\">\n                                    ${data.warnings.map(w => `<li>${w}</li>`).join('')}\n                                </ul>\n                            </div>\n                        </div>\n                    `;\n                    container.appendChild(alert);\n                }\n            } catch (e) { console.error('Validation error:', e); }\n        }\n\n        function showAgentEditor(agent = null) {\n            const isEdit = !!agent;\n            document.getElementById('agentModalTitle').textContent = isEdit ? 'Edit Agent' : 'New Agent';\n            document.getElementById('agentCategory').value = agent ? agent.category : '';\n            document.getElementById('agentFolder').value = agent ? agent.folder_name : '';\n            document.getElementById('agentName').value = agent ? agent.name : '';\n            document.getElementById('agentDescription').value = agent ? agent.description : '';\n            document.getElementById('agentPrompt').value = agent ? agent.prompt : '';\n            \n            // Disable folder/category edit if editing\n            document.getElementById('agentCategory').disabled = isEdit;\n            document.getElementById('agentFolder').disabled = isEdit;\n            \n            renderSkillsCheckboxes(agent ? (agent.skills || []) : []);\n            \n            agentModal.show();\n        }\n\n        async function editAgent(category, name) {\n            try {\n                const res = await fetch(`/admin/agents/${category}/${name}`);\n                const agent = await res.json();\n                showAgentEditor(agent);\n            } catch (e) { console.error(e); alert('Error fetching agent details'); }\n        }\n\n        async function editRootAgent() {\n            try {\n                const res = await fetch('/admin/agents/root');\n                const agent = await res.json();\n                showAgentEditor(agent);\n            } catch (e) { console.error(e); alert('Error fetching root agent'); }\n        }\n\n        async function saveAgent() {\n            const skillChecks = document.querySelectorAll('.skill-checkbox:checked');\n            const skills = Array.from(skillChecks).map(c => c.value);\n\n            const agentData = {\n                category: document.getElementById('agentCategory').value.trim(),\n                folder_name: document.getElementById('agentFolder').value.trim(),\n                name: document.getElementById('agentName').value.trim(),\n                description: document.getElementById('agentDescription').value.trim(),\n                prompt: document.getElementById('agentPrompt').value.trim(),\n                skills: skills\n            };\n\n            if (!agentData.category || !agentData.folder_name || !agentData.name || !agentData.prompt) {\n                alert('Please fill in all required fields');\n                return;\n            }\n\n            const url = agentData.category === 'root' ? '/admin/agents/root' : '/admin/agents';\n\n            try {\n                const res = await fetch(url, {\n                    method: 'POST',\n                    headers: { 'Content-Type': 'application/json' },\n                    body: JSON.stringify(agentData)\n                });\n                const result = await res.json();\n                if (result.success) {\n                    agentModal.hide();\n                    fetchAgents();\n                } else {\n                    alert('Error saving agent');\n                }\n            } catch (e) { console.error(e); alert('Error saving agent'); }\n        }\n\n        async function deleteAgent(category, name) {\n            if (!confirm(`Are you sure you want to delete agent \"${name}\" in category \"${category}\"?`)) return;\n\n            try {\n                const res = await fetch(`/admin/agents/${category}/${name}`, { method: 'DELETE' });\n                const result = await res.json();\n                if (result.success) {\n                    fetchAgents();\n                } else {\n                    alert('Error deleting agent');\n                }\n            } catch (e) { console.error(e); alert('Error deleting agent'); }\n        }\n\n        function showChangePassword(username) {\n            document.getElementById('targetUsername').innerText = username;\n            document.getElementById('modalUsername').value = username;\n            passwordModal.show();\n        }\n\n        \n        async function togglePattern(username, enabled) {\n            try {\n                const formData = new FormData();\n                formData.append('username', username);\n                formData.append('disabled', !enabled);\n                const res = await fetch('/admin/user/toggle-pattern', { method: 'POST', body: formData });\n                const data = await res.json();\n                if (data.success) {\n                    const label = document.querySelector(`label[for=\"patternSwitch_${username}\"]`);\n                    if (label) label.textContent = enabled ? 'Enabled' : 'Disabled';\n                } else {\n                    alert('Failed to update');\n                    document.getElementById(`patternSwitch_${username}`).checked = !enabled;\n                }\n            } catch (e) { console.error(e); alert('Error'); }\n        }\n\n        async function changeRole(username, newRole) {\n            if (username === 'admin' && newRole === 'user') {\n                alert('Cannot demote primary admin.');\n                return;\n            }\n            if (!confirm(`Change role of user \"${username}\" to \"${newRole}\"?`)) return;\n\n            try {\n                const formData = new FormData();\n                formData.append('username', username);\n                formData.append('role', newRole);\n                const res = await fetch('/admin/user/toggle-role', { method: 'POST', body: formData });\n                const data = await res.json();\n                if (data.success) {\n                    location.reload();\n                } else {\n                    alert('Failed to update role');\n                }\n            } catch (e) { console.error(e); alert('Error'); }\n        }\n\n        async function deleteUser(username) {\n            if (confirm(`Are you sure you want to delete user ${username}?`)) {\n                const formData = new FormData();\n                formData.append('username', username);\n                const res = await fetch('/admin/user/remove', {\n                    method: 'POST',\n                    body: formData\n                });\n                if (res.ok) {\n                    location.reload();\n                } else {\n                    alert('Error deleting user');\n                }\n            }\n        }\n\n        async function syncPatterns() {\n            const status = document.getElementById('sync-status');\n            status.textContent = 'Syncing... Please wait.';\n            status.className = 'small mt-2 text-info';\n            \n            try {\n                const res = await fetch('/admin/patterns/sync', { method: 'POST' });\n                const data = await res.json();\n                if (data.success) {\n                    status.textContent = `Successfully synced ${data.count} patterns!`;\n                    status.className = 'small mt-2 text-success';\n                } else {\n                    status.textContent = 'Error: ' + (data.error || 'Unknown error');\n                    status.className = 'small mt-2 text-danger';\n                }\n            } catch (e) {\n                status.textContent = 'Error: ' + e.message;\n                status.className = 'small mt-2 text-danger';\n            }\n        }\n\n        async function clearAllTags() {\n            if (!confirm('Are you sure you want to CLEAR ALL chat tags? This cannot be undone.')) return;\n\n            const status = document.getElementById('sync-status');\n            status.textContent = 'Clearing tags...';\n            status.className = 'small mt-2 text-info';\n            \n            try {\n                const res = await fetch('/admin/sessions/cleartags', { method: 'POST' });\n                if (!res.ok) throw new Error(`Server error ${res.status}`);\n                const data = await res.json();\n                if (data.success) {\n                    status.textContent = `Successfully cleared tags from ${data.count} sessions!`;\n                    status.className = 'small mt-2 text-success';\n                } else {\n                    status.textContent = 'Error: ' + (data.error || 'Unknown error');\n                    status.className = 'small mt-2 text-danger';\n                }\n            } catch (e) {\n                status.textContent = 'Error: ' + e.message;\n                status.className = 'small mt-2 text-danger';\n            }\n        }\n\n        async function updateLogLevel(level) {\n            const status = document.getElementById('sync-status');\n            try {\n                const res = await fetch('/admin/system/log-level', {\n                    method: 'POST',\n                    headers: { 'Content-Type': 'application/json' },\n                    body: JSON.stringify({ level })\n                });\n                if (res.ok) {\n                    status.textContent = `Logging level updated to ${level}`;\n                    status.className = 'small mt-2 text-success';\n                    setTimeout(() => { status.textContent = ''; }, 3000);\n                }\n            } catch (e) { console.error(e); }\n        }\n\n        async function restartSetup() {\n            if (confirm('Are you sure you want to RESTART SETUP? This will DELETE ALL USERS and you will need to re-configure the admin account.')) {\n                try {\n                    const res = await fetch('/admin/system/restart-setup', { method: 'POST' });\n                    const data = await res.json();\n                    if (data.success) {\n                        window.location.href = '/setup';\n                    } else {\n                        alert('Failed to restart setup');\n                    }\n                } catch (e) {\n                    console.error(e);\n                    alert('Error');\n                }\n            }\n        }\n    </script>\n</body>\n</html>\n",
    "index.html": "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n    <meta charset=\"UTF-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n    <title>Gemini Termux Agent</title>\n    <link rel=\"manifest\" href=\"/manifest.json?v=3\">\n    <link rel=\"icon\" type=\"image/svg+xml\" href=\"/static/icon.svg?v=2\">\n    <meta name=\"theme-color\" content=\"#0d6efd\">\n    <meta name=\"mobile-web-app-capable\" content=\"yes\">\n    <meta name=\"apple-mobile-web-app-status-bar-style\" content=\"black-translucent\">\n    <link rel=\"apple-touch-icon\" href=\"/static/icon.svg?v=2\">\n    <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css\" rel=\"stylesheet\">\n    <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css\">\n    <link rel=\"stylesheet\" href=\"https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/styles/github-dark.min.css\">\n    <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css\">\n    <link rel=\"stylesheet\" href=\"/static/style.css?v={{ range(1, 999999) | random }}\">\n    <script src=\"https://cdnjs.cloudflare.com/ajax/libs/ethers/5.7.2/ethers.umd.min.js\"></script>\n    <script defer src=\"https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js\"></script>\n    <script defer src=\"https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js\"></script>\n</head>\n<body class=\"bg-dark text-light\">\n\n<div class=\"container-fluid d-flex flex-column vh-100 p-0\">\n    <!-- Header -->\n    <!-- Header -->\n    <header class=\"p-2 border-bottom border-secondary bg-black d-flex justify-content-between align-items-center\">\n        <div class=\"d-flex align-items-center\">\n            <button class=\"btn btn-outline-secondary btn-sm me-2\" type=\"button\" data-bs-toggle=\"offcanvas\" data-bs-target=\"#historySidebar\" aria-controls=\"historySidebar\">\n                <i class=\"bi bi-layout-sidebar-inset\"></i>\n            </button>\n            <div class=\"d-flex align-items-center gap-2\">\n                <i class=\"bi bi-robot text-primary h4 m-0\"></i>\n                <span class=\"small fw-bold d-md-none text-truncate\" style=\"max-width: 100px;\">{{ user }}</span>\n            </div>\n            <div id=\"chat-tags-header\" class=\"d-none d-md-flex align-items-center gap-2 ms-3 overflow-auto\" style=\"max-width: 40vw;\">\n                <!-- Desktop tags -->\n            </div>\n        </div>\n\n        <div class=\"d-flex align-items-center gap-2\">\n            <span class=\"badge bg-secondary d-none d-md-inline-block\"><i class=\"bi bi-person\"></i> {{ user }}</span>\n            \n            <!-- Mobile Actions Button -->\n            <div class=\"d-md-none\">\n                <button class=\"btn btn-outline-light btn-sm\" type=\"button\" data-bs-toggle=\"offcanvas\" data-bs-target=\"#actionsSidebar\" aria-controls=\"actionsSidebar\" id=\"mobile-actions-toggle\">\n                    <i class=\"bi bi-three-dots-vertical\"></i>\n                </button>\n            </div>\n\n            <!-- Desktop Actions -->\n            <div class=\"d-none d-md-flex gap-2\">\n                {% if is_admin %}\n                <a href=\"/admin\" class=\"btn btn-outline-info btn-sm\" title=\"Admin\"><i class=\"bi bi-gear\"></i> <span class=\"d-none d-lg-inline\">Admin</span></a>\n                {% endif %}\n                <button id=\"tree-view-btn\" class=\"btn btn-outline-info btn-sm\" data-bs-toggle=\"modal\" data-bs-target=\"#treeViewModal\" title=\"View Conversation Tree\"><svg width=\"16\" height=\"16\" fill=\"currentColor\" viewBox=\"0 0 16 16\" class=\"bi\"><path d=\"M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 2.25 0 1 1 1.5 0v.878a2.25 2.25 0 0 1-2.25 2.25h-1.5v2.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25v-.878a2.25 2.25 0 1 1 1.5 0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z\"></path></svg> <span class=\"d-none d-lg-inline\">Tree</span></button>\n                <button id=\"security-btn\" class=\"btn btn-outline-light btn-sm\" data-bs-toggle=\"modal\" data-bs-target=\"#securityModal\" title=\"Security\"><i class=\"bi bi-shield-lock\"></i> <span class=\"d-none d-lg-inline\">Security</span></button>\n                <button id=\"share-btn\" class=\"btn btn-outline-primary btn-sm\" data-bs-toggle=\"modal\" data-bs-target=\"#shareModal\" title=\"Share Chat\"><i class=\"bi bi-share\"></i> <span class=\"d-none d-lg-inline\">Share</span></button>\n                <button id=\"export-btn\" class=\"btn btn-outline-success btn-sm\" title=\"Export Chat\"><i class=\"bi bi-download\"></i> <span class=\"d-none d-lg-inline\">Export</span></button>\n                <button id=\"reset-btn\" class=\"btn btn-outline-warning btn-sm\" title=\"Reset Chat\"><i class=\"bi bi-trash\"></i> <span class=\"d-none d-lg-inline\">Reset</span></button>\n                <button id=\"patterns-btn\" class=\"btn btn-outline-info btn-sm\" data-bs-toggle=\"modal\" data-bs-target=\"#patternsModal\" title=\"Patterns\"><i class=\"bi bi-collection\"></i> <span class=\"d-none d-lg-inline\">Patterns</span></button>\n                <a href=\"/logout\" class=\"btn btn-outline-danger btn-sm\" title=\"Logout\"><i class=\"bi bi-box-arrow-right\"></i> <span class=\"d-none d-lg-inline\">Logout</span></a>\n            </div>\n        </div>\n    </header>\n\n    <!-- History Sidebar (Offcanvas) -->\n    <div class=\"offcanvas offcanvas-start bg-dark text-light border-end border-secondary\" tabindex=\"-1\" id=\"historySidebar\" aria-labelledby=\"historySidebarLabel\">\n      <div class=\"offcanvas-header border-bottom border-secondary\">\n        <h5 class=\"offcanvas-title\" id=\"historySidebarLabel\"><i class=\"bi bi-clock-history\"></i> Chat History</h5>\n        <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"offcanvas\" aria-label=\"Close\"></button>\n      </div>\n      <div class=\"offcanvas-body p-0 d-flex flex-column\">\n        <div class=\"p-3 border-bottom border-secondary\">\n            <button id=\"new-chat-btn\" class=\"btn btn-primary w-100 mb-2\"><i class=\"bi bi-plus-lg\"></i> New Chat</button>\n            <div class=\"mt-2\">\n                <div class=\"input-group input-group-sm\">\n                    <span class=\"input-group-text bg-dark border-secondary text-secondary\"><i class=\"bi bi-search\"></i></span>\n                    <input type=\"text\" id=\"session-search\" class=\"form-control bg-dark text-light border-secondary shadow-none\" placeholder=\"Search history...\">\n                </div>\n            </div>\n            <div id=\"tag-filter-container\" class=\"mt-2 d-flex flex-wrap gap-1\">\n                <!-- Tags will be loaded here -->\n            </div>\n        </div>\n        <div class=\"flex-grow-1 overflow-auto\">\n            <div id=\"sessions-list\" class=\"list-group list-group-flush\">\n                <!-- Pinned Section -->\n                <div id=\"pinned-sessions-header\" class=\"sidebar-section-header d-none px-3 py-2 small text-uppercase fw-bold text-muted bg-black bg-opacity-25 border-bottom border-secondary border-opacity-25\">\n                    <i class=\"bi bi-pin-angle-fill me-1\"></i> Pinned\n                </div>\n                <div id=\"pinned-sessions-list\"></div>\n\n                <!-- Recent Section -->\n                <div id=\"history-sessions-header\" class=\"sidebar-section-header d-none px-3 py-2 small text-uppercase fw-bold text-muted bg-black bg-opacity-25 border-bottom border-secondary border-opacity-25\">\n                    <i class=\"bi bi-clock-history me-1\"></i> Recent\n                </div>\n                <div id=\"history-sessions-list\">\n                    <!-- Sessions will be loaded here -->\n                    <div id=\"sidebar-initial-loader\" class=\"text-center p-3\">\n                        <div class=\"spinner-border text-info spinner-border-sm\" role=\"status\"></div>\n                    </div>\n                </div>\n            </div>\n            <div id=\"sidebar-load-more-container\" class=\"p-3 text-center d-none\">\n                <button id=\"sidebar-load-more-btn\" class=\"btn btn-outline-secondary btn-sm w-100\">Load More</button>\n            </div>\n        </div>\n      </div>\n    </div>\n\n    <!-- Actions Sidebar (Right Offcanvas) -->\n    <div class=\"offcanvas offcanvas-end bg-dark text-light border-start border-secondary\" tabindex=\"-1\" id=\"actionsSidebar\" aria-labelledby=\"actionsSidebarLabel\">\n      <div class=\"offcanvas-header border-bottom border-secondary\">\n        <h5 class=\"offcanvas-title\" id=\"actionsSidebarLabel\"><i class=\"bi bi-gear\"></i> Actions</h5>\n        <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"offcanvas\" aria-label=\"Close\"></button>\n      </div>\n      <div class=\"offcanvas-body p-0\">\n        <div class=\"list-group list-group-flush\">\n            <div class=\"p-3 border-bottom border-secondary bg-black d-flex align-items-center gap-2\">\n                <i class=\"bi bi-person-circle h4 m-0 text-primary\"></i>\n                <span class=\"text-truncate\">{{ user }}</span>\n                {% if is_admin %}<span class=\"badge bg-info ms-auto\">Admin</span>{% endif %}\n            </div>\n            \n            <!-- Mobile Tags Section -->\n            <div class=\"p-3 border-bottom border-secondary d-md-none\">\n                <h6 class=\"small text-muted text-uppercase fw-bold mb-2\">Chat Tags</h6>\n                <div id=\"chat-tags-sidebar\" class=\"d-flex flex-wrap gap-2\">\n                    <!-- Mobile tags will render here -->\n                </div>\n            </div>\n\n            {% if is_admin %}\n            <a href=\"/admin\" class=\"list-group-item list-group-item-action bg-dark text-light border-secondary\"><i class=\"bi bi-gear me-2\"></i> Admin Maintenance</a>\n            {% endif %}\n            <button id=\"tree-view-btn-mobile\" class=\"list-group-item list-group-item-action bg-dark text-info border-secondary\" data-bs-toggle=\"modal\" data-bs-target=\"#treeViewModal\" data-bs-dismiss=\"offcanvas\"><svg width=\"16\" height=\"16\" fill=\"currentColor\" viewBox=\"0 0 16 16\" class=\"bi me-2\"><path d=\"M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 2.25 0 1 1 1.5 0v.878a2.25 2.25 0 0 1-2.25 2.25h-1.5v2.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25v-.878a2.25 2.25 0 1 1 1.5 0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z\"></path></svg> Conversation Tree</button>\n            <button class=\"list-group-item list-group-item-action bg-dark text-primary border-secondary\" data-bs-toggle=\"modal\" data-bs-target=\"#shareModal\" data-bs-dismiss=\"offcanvas\"><i class=\"bi bi-share me-2\"></i> Share Chat</button>\n            <button class=\"list-group-item list-group-item-action bg-dark text-light border-secondary\" data-bs-toggle=\"modal\" data-bs-target=\"#securityModal\" data-bs-dismiss=\"offcanvas\"><i class=\"bi bi-shield-lock me-2\"></i> Security Settings</button>\n            <button class=\"list-group-item list-group-item-action bg-dark text-light border-secondary\" data-bs-toggle=\"modal\" data-bs-target=\"#patternsModal\" data-bs-dismiss=\"offcanvas\"><i class=\"bi bi-collection me-2\"></i> Available Patterns</button>\n            <button id=\"export-btn-mobile\" class=\"list-group-item list-group-item-action bg-dark text-light border-secondary\" data-bs-dismiss=\"offcanvas\"><i class=\"bi bi-download me-2\"></i> Export Conversation</button>\n            <button id=\"reset-btn-mobile\" class=\"list-group-item list-group-item-action bg-dark text-warning border-secondary\" data-bs-dismiss=\"offcanvas\"><i class=\"bi bi-trash me-2\"></i> Reset History</button>\n            <a href=\"/logout\" class=\"list-group-item list-group-item-action bg-dark text-danger border-secondary\"><i class=\"bi bi-box-arrow-right me-2\"></i> Logout</a>\n        </div>\n      </div>\n    </div>\n\n    <!-- Chat Area -->\n    <div id=\"chat-container\" class=\"flex-grow-1 overflow-auto p-3 position-relative\">\n        <div id=\"drag-drop-overlay\" class=\"d-none position-absolute top-0 start-0 w-100 h-100 d-flex flex-column align-items-center justify-content-center bg-dark bg-opacity-75\" style=\"z-index: 1000; pointer-events: none;\">\n            <div class=\"border border-primary border-3 border-dashed rounded-3 p-5 d-flex flex-column align-items-center\">\n                <i class=\"bi bi-cloud-arrow-up text-primary\" style=\"font-size: 4rem;\"></i>\n                <h4 class=\"text-primary mt-3\">Drop files to attach</h4>\n            </div>\n        </div>\n        <div id=\"scroll-sentinel\" style=\"height: 10px; width: 100%;\"></div>\n        <div id=\"load-more-container\" class=\"text-center {{ 'd-none' if not has_more else '' }} mb-3\">\n            <button id=\"load-more-btn\" class=\"btn btn-outline-secondary btn-sm\">Load Older Messages</button>\n        </div>\n        <div id=\"chat-welcome\" class=\"text-center text-muted mt-3\">\n            <p>Start a conversation with Gemini.</p>\n            <p class=\"small\">Try <code>/help</code> to see available commands.</p>\n        </div>\n    </div>\n\n    <!-- Input Area -->\n    <footer class=\"py-3 px-3 border-top border-secondary bg-black\">\n        <form id=\"chat-form\" class=\"d-flex flex-column gap-1\">\n            \n            <div id=\"attachment-queue\" class=\"d-flex flex-wrap gap-2\">\n                <!-- Attachment items will be injected here -->\n            </div>\n\n            <div class=\"d-flex align-items-end gap-2\">\n                <!-- Left Actions: Model & Attach -->\n                <div class=\"d-flex gap-1 pb-1\">\n                    <div class=\"btn-group dropup\">\n                        <button class=\"btn btn-secondary btn-sm rounded-circle\" type=\"button\" data-bs-toggle=\"dropdown\" aria-expanded=\"false\" title=\"Select Model\">\n                            <i class=\"bi bi-cpu\"></i>\n                        </button>\n                        <ul class=\"dropdown-menu\">\n                            <li><h6 class=\"dropdown-header\">Model Selection</h6></li>\n                            <li><a class=\"dropdown-item active\" href=\"#\" data-model=\"gemini-3-pro-preview\">Gemini 3 Pro <span class=\"badge bg-warning text-dark ms-1\">Preview</span></a></li>\n                            <li><a class=\"dropdown-item\" href=\"#\" data-model=\"gemini-3-flash-preview\">Gemini 3 Flash <span class=\"badge bg-secondary ms-1\">Preview</span></a></li>\n                            <li><hr class=\"dropdown-divider\"></li>\n                            <li><a class=\"dropdown-item\" href=\"#\" data-model=\"gemini-3-pro\">Gemini 3 Pro <span class=\"badge bg-info ms-1\">Stable (v0.28+)</span></a></li>\n                            <li><a class=\"dropdown-item\" href=\"#\" data-model=\"gemini-3-flash\">Gemini 3 Flash <span class=\"badge bg-info ms-1\">Stable (v0.28+)</span></a></li>\n                            <li><hr class=\"dropdown-divider\"></li>\n                            <li><a class=\"dropdown-item\" href=\"#\" data-model=\"gemini-2.5-pro\">Gemini 2.5 Pro</a></li>\n                            <li><a class=\"dropdown-item\" href=\"#\" data-model=\"gemini-2.5-flash\">Gemini 2.5 Flash</a></li>\n                        </ul>\n                    </div>\n                    <input type=\"hidden\" name=\"model\" id=\"model-input\" value=\"gemini-3-pro-preview\">\n                    \n                    <label class=\"btn btn-outline-secondary btn-sm rounded-circle\" for=\"file-upload\" title=\"Attach Files\">\n                        <i class=\"bi bi-paperclip\"></i>\n                    </label>\n                    <input type=\"file\" id=\"file-upload\" name=\"file\" class=\"d-none\" multiple>\n                    \n                    <button class=\"btn btn-outline-secondary btn-sm rounded-circle\" type=\"button\" id=\"tools-config-btn\" data-bs-toggle=\"modal\" data-bs-target=\"#toolsModal\" title=\"Tools Settings\">\n                        <i class=\"bi bi-wrench\"></i>\n                    </button>\n                    \n                    <button class=\"btn btn-outline-info btn-sm rounded-circle d-none\" type=\"button\" id=\"drive-mode-btn\" title=\"Drive Mode (Voice Loop)\">\n                        <i class=\"bi bi-mic-fill\"></i>\n                    </button>\n\n                    <button class=\"btn btn-outline-warning btn-sm rounded-circle d-none\" type=\"button\" id=\"plan-mode-btn\" title=\"Toggle Plan Mode (Experimental)\">\n                        <i class=\"bi bi-journal-text\"></i>\n                    </button>\n                </div>\n\n                <!-- Text Input -->\n                <div class=\"flex-grow-1\">\n                    <textarea class=\"form-control bg-dark text-light border-secondary shadow-none\" id=\"message-input\" name=\"message\" rows=\"2\" placeholder=\"Message Gemini...\" required style=\"border-radius: 20px;\"></textarea>\n                </div>\n                \n                <!-- Send Button -->\n                <button class=\"btn btn-primary rounded-circle p-2\" type=\"submit\" id=\"send-btn\" style=\"width: 45px; height: 45px;\">\n                    <i class=\"bi bi-send-fill\"></i>\n                </button>\n                \n                <!-- Stop Button (Hidden by default) -->\n                <button class=\"btn btn-danger rounded-circle p-2 d-none\" type=\"button\" id=\"stop-btn\" style=\"width: 45px; height: 45px;\" title=\"Stop Response\">\n                    <i class=\"bi bi-stop-fill\"></i>\n                </button>\n            </div>\n            \n            <div class=\"text-center\">\n                <small class=\"text-muted\" style=\"font-size: 0.7rem;\">Currently using: <span id=\"model-label\">Gemini 3 Pro</span></small>\n            </div>\n        </form>\n    </footer>\n</div>\n\n<!-- Toast Container -->\n<div class=\"toast-container position-fixed bottom-0 end-0 p-3\">\n    <div id=\"liveToast\" class=\"toast align-items-center text-white bg-primary border-0\" role=\"alert\" aria-live=\"assertive\" aria-atomic=\"true\">\n        <div class=\"d-flex\">\n            <div class=\"toast-body\" id=\"toast-body\">\n                Notification message\n            </div>\n            <button type=\"button\" class=\"btn-close btn-close-white me-2 m-auto\" data-bs-dismiss=\"toast\" aria-label=\"Close\"></button>\n        </div>\n    </div>\n</div>\n\n<!-- Patterns Modal -->\n<div class=\"modal fade\" id=\"patternsModal\" tabindex=\"-1\" aria-labelledby=\"patternsModalLabel\">\n  <div class=\"modal-dialog modal-lg modal-dialog-scrollable\">\n    <div class=\"modal-content bg-dark text-light border-secondary\">\n      <div class=\"modal-header border-secondary\">\n        <h5 class=\"modal-title\" id=\"patternsModalLabel\"><i class=\"bi bi-collection\"></i> Available Patterns</h5>\n        <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>\n      </div>\n      <div class=\"modal-body\">\n        <div class=\"mb-3\">\n            <input type=\"text\" id=\"pattern-search\" class=\"form-control bg-dark text-light border-secondary\" placeholder=\"Search patterns...\">\n        </div>\n        <div class=\"list-group\" id=\"patterns-list\">\n            <!-- Patterns will be loaded here -->\n            <div class=\"text-center p-3\">\n                <div class=\"spinner-border text-info\" role=\"status\"></div>\n            </div>\n        </div>\n      </div>\n    </div>\n  </div>\n</div>\n\n<!-- Security Modal -->\n<div class=\"modal fade\" id=\"securityModal\" tabindex=\"-1\" aria-labelledby=\"securityModalLabel\">\n  <div class=\"modal-dialog\">\n    <div class=\"modal-content bg-dark text-light border-secondary\">\n      <div class=\"modal-header border-secondary\">\n        <h5 class=\"modal-title\" id=\"securityModalLabel\"><i class=\"bi bi-shield-lock\"></i> Security Settings</h5>\n        <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>\n      </div>\n      <div class=\"modal-body\">\n        <div class=\"mb-4\">\n            <h6><i class=\"bi bi-key\"></i> Passkeys</h6>\n            <p class=\"small text-muted\">Register a Passkey for faster, more secure login without a password.</p>\n            <button id=\"btn-register-passkey\" class=\"btn btn-outline-info w-100\"><i class=\"bi bi-plus-lg\"></i> Register New Passkey</button>\n            <div id=\"passkey-reg-status\" class=\"mt-2 small\"></div>\n        </div>\n        <hr class=\"border-secondary\">\n        <div class=\"mb-4\">\n            <h6><i class=\"bi bi-grid-3x3\"></i> Login Pattern</h6>\n            <p class=\"small text-muted\">Change your pattern-based login.</p>\n            <div class=\"text-center mb-3\">\n                <div id=\"pattern-container-security\" class=\"mx-auto\" style=\"width: 200px; height: 200px; position: relative; touch-action: none;\">\n                    <svg id=\"pattern-svg-security\" width=\"200\" height=\"200\" style=\"background: #252525; border-radius: 10px;\"></svg>\n                </div>\n                <input type=\"hidden\" id=\"pattern-input-security\">\n            </div>\n            <button id=\"btn-update-pattern\" class=\"btn btn-outline-warning w-100\">Update Pattern</button>\n            <div id=\"pattern-update-status\" class=\"mt-2 small\"></div>\n        </div>\n        <hr class=\"border-secondary\">\n        <div class=\"mb-3\">\n            <h6><i class=\"bi bi-wallet2\"></i> Crypto Wallet</h6>\n            <p class=\"small text-muted\">Link your Ethereum wallet (MetaMask/Brave) to sign in using your wallet.</p>\n            <div class=\"input-group mb-2\">\n                <input type=\"text\" id=\"wallet-address-input\" class=\"form-control bg-dark text-light border-secondary\" placeholder=\"0x...\" readonly>\n                <button id=\"btn-link-wallet\" class=\"btn btn-outline-primary\">Link Wallet</button>\n            </div>\n            <div id=\"wallet-link-status\" class=\"mt-2 small\"></div>\n        </div>\n        <hr class=\"border-secondary\">\n        <div class=\"mb-3\">\n            <h6><i class=\"bi bi-sliders\"></i> Preferences</h6>\n            <div class=\"form-check form-switch mb-2\">\n                <input class=\"form-check-input\" type=\"checkbox\" role=\"switch\" id=\"setting-show-mic\">\n                <label class=\"form-check-label\" for=\"setting-show-mic\">Show Drive Mode (Mic)</label>\n            </div>\n            <div class=\"form-check form-switch mb-2\">\n                <input class=\"form-check-input\" type=\"checkbox\" role=\"switch\" id=\"setting-show-plan\">\n                <label class=\"form-check-label\" for=\"setting-show-plan\">Show Plan Mode</label>\n            </div>\n            <div class=\"form-check form-switch mb-2\">\n                <input class=\"form-check-input\" type=\"checkbox\" role=\"switch\" id=\"setting-interactive-mode\">\n                <label class=\"form-check-label\" for=\"setting-interactive-mode\">Interactive Mode (AI Questions)</label>\n            </div>\n            <div class=\"form-check form-switch\">\n                <input class=\"form-check-input\" type=\"checkbox\" role=\"switch\" id=\"setting-copy-formatted\">\n                <label class=\"form-check-label\" for=\"setting-copy-formatted\">Copy Formatted Text</label>\n            </div>\n        </div>\n      </div>\n    </div>\n  </div>\n</div>\n\n<!-- Rename Session Modal -->\n<div class=\"modal fade\" id=\"renameSessionModal\" tabindex=\"-1\" aria-labelledby=\"renameSessionModalLabel\">\n  <div class=\"modal-dialog\">\n    <div class=\"modal-content bg-dark text-light border-secondary\">\n      <div class=\"modal-header border-secondary\">\n        <h5 class=\"modal-title\" id=\"renameSessionModalLabel\"><i class=\"bi bi-pencil-square\"></i> Rename Chat</h5>\n        <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>\n      </div>\n      <div class=\"modal-body\">\n        <div class=\"mb-3\">\n            <label for=\"rename-input\" class=\"form-label\">Chat Title</label>\n            <input type=\"text\" class=\"form-control bg-dark text-light border-secondary\" id=\"rename-input\">\n        </div>\n      </div>\n      <div class=\"modal-footer border-secondary justify-content-end\">\n        <div>\n            <button type=\"button\" class=\"btn btn-secondary me-2\" data-bs-dismiss=\"modal\">Cancel</button>\n            <button type=\"button\" class=\"btn btn-primary\" id=\"btn-save-rename\">Save</button>\n        </div>\n      </div>\n    </div>\n  </div>\n</div>\n\n<!-- Edit Prompt Modal -->\n<div class=\"modal fade\" id=\"editPromptModal\" tabindex=\"-1\" aria-labelledby=\"editPromptModalLabel\">\n  <div class=\"modal-dialog modal-lg\">\n    <div class=\"modal-content bg-dark text-light border-secondary\">\n      <div class=\"modal-header border-secondary\">\n        <h5 class=\"modal-title\" id=\"editPromptModalLabel\"><i class=\"bi bi-pencil\"></i> Edit Custom Prompt</h5>\n        <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>\n      </div>\n      <div class=\"modal-body\">\n        <div class=\"mb-3\">\n            <label for=\"edit-prompt-filename\" class=\"form-label small text-muted\">Filename</label>\n            <input type=\"text\" class=\"form-control bg-dark text-light border-secondary\" id=\"edit-prompt-filename\" readonly>\n        </div>\n        <div class=\"mb-3\">\n            <label for=\"edit-prompt-content\" class=\"form-label small text-muted\">Content</label>\n            <textarea class=\"form-control bg-dark text-light border-secondary\" id=\"edit-prompt-content\" rows=\"15\" style=\"font-family: monospace;\"></textarea>\n        </div>\n      </div>\n      <div class=\"modal-footer border-secondary\">\n        <button type=\"button\" class=\"btn btn-secondary btn-sm\" data-bs-dismiss=\"modal\">Cancel</button>\n        <button type=\"button\" id=\"btn-save-prompt-edit\" class=\"btn btn-primary btn-sm\">Save Changes</button>\n      </div>\n    </div>\n  </div>\n</div>\n\n<!-- Tools Modal -->\n<div class=\"modal fade\" id=\"toolsModal\" tabindex=\"-1\" aria-labelledby=\"toolsModalLabel\">\n  <div class=\"modal-dialog\">\n    <div class=\"modal-content bg-dark text-light border-secondary\">\n      <div class=\"modal-header border-secondary\">\n        <h5 class=\"modal-title\" id=\"toolsModalLabel\"><i class=\"bi bi-wrench\"></i> Tools Settings</h5>\n        <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>\n      </div>\n      <div class=\"modal-body\">\n        <p class=\"small text-muted mb-3\">Enable or disable tools for the current session. All tools are disabled by default for security.</p>\n        \n        <div class=\"mb-4\">\n            <h6 class=\"text-info small mb-2 text-uppercase fw-bold\">Read-Only / Safe Tools</h6>\n            <div class=\"list-group list-group-flush bg-transparent\">\n                <div class=\"form-check form-switch mb-2\">\n                    <input class=\"form-check-input tool-toggle\" type=\"checkbox\" id=\"tool-list_directory\" value=\"list_directory\">\n                    <label class=\"form-check-label\" for=\"tool-list_directory\">Read Folder (list_directory)</label>\n                </div>\n                <div class=\"form-check form-switch mb-2\">\n                    <input class=\"form-check-input tool-toggle\" type=\"checkbox\" id=\"tool-read_file\" value=\"read_file\">\n                    <label class=\"form-check-label\" for=\"tool-read_file\">Read File (read_file)</label>\n                </div>\n                <div class=\"form-check form-switch mb-2\">\n                    <input class=\"form-check-input tool-toggle\" type=\"checkbox\" id=\"tool-glob\" value=\"glob\">\n                    <label class=\"form-check-label\" for=\"tool-glob\">Find Files (glob)</label>\n                </div>\n                <div class=\"form-check form-switch mb-2\">\n                    <input class=\"form-check-input tool-toggle\" type=\"checkbox\" id=\"tool-grep_search\" value=\"grep_search\">\n                    <label class=\"form-check-label\" for=\"tool-grep_search\">Search Text (grep_search)</label>\n                </div>\n                <div class=\"form-check form-switch mb-2\">\n                    <input class=\"form-check-input tool-toggle\" type=\"checkbox\" id=\"tool-google_web_search\" value=\"google_web_search\">\n                    <label class=\"form-check-label\" for=\"tool-google_web_search\">Google Search (google_web_search)</label>\n                </div>\n                <div class=\"form-check form-switch mb-2\">\n                    <input class=\"form-check-input tool-toggle\" type=\"checkbox\" id=\"tool-web_fetch\" value=\"web_fetch\">\n                    <label class=\"form-check-label\" for=\"tool-web_fetch\">Web Fetch (web_fetch)</label>\n                </div>\n                <div class=\"form-check form-switch mb-2\">\n                    <input class=\"form-check-input tool-toggle\" type=\"checkbox\" id=\"tool-cli_help\" value=\"cli_help\">\n                    <label class=\"form-check-label\" for=\"tool-cli_help\">CLI Help (cli_help)</label>\n                </div>\n                <div class=\"form-check form-switch mb-2\">\n                    <input class=\"form-check-input tool-toggle\" type=\"checkbox\" id=\"tool-ask_user\" value=\"ask_user\">\n                    <label class=\"form-check-label\" for=\"tool-ask_user\">Ask User (ask_user)</label>\n                </div>\n                <div class=\"form-check form-switch mb-2\">\n                    <input class=\"form-check-input tool-toggle\" type=\"checkbox\" id=\"tool-confirm_output\" value=\"confirm_output\">\n                    <label class=\"form-check-label\" for=\"tool-confirm_output\">Confirm Output (confirm_output)</label>\n                </div>\n            </div>\n        </div>\n\n        <div class=\"mb-4\">\n            <h6 class=\"text-danger small mb-2 text-uppercase fw-bold\">Modification / High-Risk Tools</h6>\n            <div class=\"list-group list-group-flush bg-transparent\">\n                <div class=\"form-check form-switch mb-2\">\n                    <input class=\"form-check-input tool-toggle\" type=\"checkbox\" id=\"tool-replace\" value=\"replace\">\n                    <label class=\"form-check-label\" for=\"tool-replace\">Edit (replace)</label>\n                </div>\n                <div class=\"form-check form-switch mb-2\">\n                    <input class=\"form-check-input tool-toggle\" type=\"checkbox\" id=\"tool-write_file\" value=\"write_file\">\n                    <label class=\"form-check-label\" for=\"tool-write_file\">Write File (write_file)</label>\n                </div>\n                <div class=\"form-check form-switch mb-2\">\n                    <input class=\"form-check-input tool-toggle\" type=\"checkbox\" id=\"tool-run_shell_command\" value=\"run_shell_command\">\n                    <label class=\"form-check-label\" for=\"tool-run_shell_command\">Shell (run_shell_command)</label>\n                </div>\n                <div class=\"form-check form-switch mb-2\">\n                    <input class=\"form-check-input tool-toggle\" type=\"checkbox\" id=\"tool-save_memory\" value=\"save_memory\">\n                    <label class=\"form-check-label\" for=\"tool-save_memory\">Save Memory (save_memory)</label>\n                </div>\n                <div class=\"form-check form-switch mb-2\">\n                    <input class=\"form-check-input tool-toggle\" type=\"checkbox\" id=\"tool-delegate_to_agent\" value=\"delegate_to_agent\">\n                    <label class=\"form-check-label\" for=\"tool-delegate_to_agent\">Delegate to Agent (delegate_to_agent)</label>\n                </div>\n                <div class=\"form-check form-switch mb-2\">\n                    <input class=\"form-check-input tool-toggle\" type=\"checkbox\" id=\"tool-activate_skill\" value=\"activate_skill\">\n                    <label class=\"form-check-label\" for=\"tool-activate_skill\">Activate Skill (activate_skill)</label>\n                </div>\n                <div class=\"form-check form-switch mb-2\">\n                    <input class=\"form-check-input tool-toggle\" type=\"checkbox\" id=\"tool-codebase_investigator\" value=\"codebase_investigator\">\n                    <label class=\"form-check-label\" for=\"tool-codebase_investigator\">Codebase Investigator (codebase_investigator)</label>\n                </div>\n            </div>\n        </div>\n\n        <div class=\"d-flex flex-wrap justify-content-between gap-2 mt-4\">\n            <div class=\"d-flex gap-2\">\n                <button type=\"button\" class=\"btn btn-outline-info btn-sm\" id=\"btn-safe-tools-only\">Safe Tools Only</button>\n                <button type=\"button\" class=\"btn btn-outline-warning btn-sm\" id=\"btn-all-except-memory\">All Except Memory</button>\n            </div>\n            <div class=\"d-flex gap-2\">\n                <button type=\"button\" class=\"btn btn-outline-danger btn-sm\" id=\"btn-deselect-all-tools\">Deselect All</button>\n                <button type=\"button\" class=\"btn btn-primary btn-sm\" id=\"btn-apply-tools\">Apply Settings</button>\n            </div>\n        </div>\n        <div id=\"tools-status\" class=\"mt-2 small text-center\"></div>\n      </div>\n    </div>\n  </div>\n</div>\n\n<!-- Tagging Modal -->\n<div class=\"modal fade\" id=\"taggingModal\" tabindex=\"-1\" aria-labelledby=\"taggingModalLabel\">\n  <div class=\"modal-dialog\">\n    <div class=\"modal-content bg-dark text-light border-secondary\">\n      <div class=\"modal-header border-secondary\">\n        <h5 class=\"modal-title\" id=\"taggingModalLabel\"><i class=\"bi bi-tags\"></i> Edit Chat Tags</h5>\n        <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>\n      </div>\n      <div class=\"modal-body\">\n        <div class=\"mb-3\">\n            <label class=\"form-label small text-muted\">Current Tags</label>\n            <div id=\"modal-current-tags\" class=\"d-flex flex-wrap gap-1 mb-2\"></div>\n            <div class=\"input-group input-group-sm\">\n                <input type=\"text\" id=\"tag-input\" class=\"form-control bg-dark text-light border-secondary\" placeholder=\"New tag...\">\n                <button class=\"btn btn-outline-secondary\" type=\"button\" id=\"btn-add-tag\">Add</button>\n            </div>\n            <small class=\"text-muted\" style=\"font-size: 0.6rem;\">Press Enter or use comma to add multiple tags.</small>\n        </div>\n        <div class=\"mb-3\">\n            <label class=\"form-label small text-muted\">Pick from existing tags</label>\n            <div id=\"modal-existing-tags\" class=\"d-flex flex-wrap gap-1\">\n                <!-- Existing tags will be loaded here -->\n            </div>\n        </div>\n      </div>\n      <div class=\"modal-footer border-secondary\">\n        <button type=\"button\" class=\"btn btn-secondary btn-sm\" data-bs-dismiss=\"modal\">Cancel</button>\n        <button type=\"button\" id=\"btn-save-tags\" class=\"btn btn-primary btn-sm\">Save Changes</button>\n      </div>\n    </div>\n  </div>\n</div>\n\n<!-- Tree View Modal -->\n<div class=\"modal fade\" id=\"treeViewModal\" tabindex=\"-1\" aria-labelledby=\"treeViewModalLabel\">\n  <div class=\"modal-dialog modal-xl modal-dialog-scrollable\">\n    <div class=\"modal-content bg-dark text-light border-secondary\">\n      <div class=\"modal-header border-secondary\">\n        <h5 class=\"modal-title\" id=\"treeViewModalLabel\"><svg width=\"20\" height=\"20\" fill=\"currentColor\" viewBox=\"0 0 16 16\" class=\"bi me-2\" style=\"margin-top: -4px;\"><path d=\"M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 2.25 0 1 1 1.5 0v.878a2.25 2.25 0 0 1-2.25 2.25h-1.5v2.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25v-.878a2.25 2.25 0 1 1 1.5 0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z\"></path></svg> Conversation Tree</h5>\n        <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>\n      </div>\n      <div class=\"modal-body\">\n        <div id=\"tree-container\" class=\"p-3 overflow-auto\" style=\"min-height: 400px;\">\n            <!-- Tree will be rendered here -->\n            <div class=\"text-center p-5\">\n                <div class=\"spinner-border text-info\" role=\"status\"></div>\n                <p class=\"mt-2\">Building conversation tree...</p>\n            </div>\n        </div>\n      </div>\n    </div>\n  </div>\n</div>\n\n<!-- Share Modal -->\n<div class=\"modal fade\" id=\"shareModal\" tabindex=\"-1\" aria-labelledby=\"shareModalLabel\">\n  <div class=\"modal-dialog\">\n    <div class=\"modal-content bg-dark text-light border-secondary\">\n      <div class=\"modal-header border-secondary\">\n        <h5 class=\"modal-title\" id=\"shareModalLabel\"><i class=\"bi bi-share\"></i> Share Chat</h5>\n        <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>\n      </div>\n      <div class=\"modal-body\">\n        <p class=\"small text-muted\">Enter the username of the person you want to share this chat with. They will be able to read and participate in the conversation.</p>\n        <div class=\"mb-3\">\n            <label for=\"share-username-input\" class=\"form-label\">Username</label>\n            <input type=\"text\" class=\"form-control bg-dark text-light border-secondary\" id=\"share-username-input\" placeholder=\"e.g. bob\">\n        </div>\n        <div id=\"share-status\" class=\"small mt-2\"></div>\n      </div>\n      <div class=\"modal-footer border-secondary\">\n        <button type=\"button\" class=\"btn btn-secondary btn-sm\" data-bs-dismiss=\"modal\">Cancel</button>\n        <button type=\"button\" id=\"btn-confirm-share\" class=\"btn btn-primary btn-sm\">Share</button>\n      </div>\n    </div>\n  </div>\n</div>\n\n<script src=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js\"></script>\n<script src=\"https://cdn.jsdelivr.net/npm/marked/marked.min.js\"></script>\n<script src=\"https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/highlight.min.js\"></script>\n<script>\n    // Security Modal Logic\n    document.addEventListener('DOMContentLoaded', () => {\n        const btnLinkWallet = document.getElementById('btn-link-wallet');\n        const walletStatus = document.getElementById('wallet-link-status');\n        const btnRegisterPasskey = document.getElementById('btn-register-passkey');\n        const passkeyStatus = document.getElementById('passkey-reg-status');\n        \n        // --- Pattern Update Logic ---\n        const svgSec = document.getElementById('pattern-svg-security');\n        const patternInputSec = document.getElementById('pattern-input-security');\n        const btnUpdatePattern = document.getElementById('btn-update-pattern');\n        const patternStatus = document.getElementById('pattern-update-status');\n        const dotsSec = [];\n        const selectedDotsSec = [];\n        let isDrawingSec = false;\n        let currentLineSec = null;\n\n        // Create 3x3 grid for security modal\n        for (let y = 0; y < 3; y++) {\n            for (let x = 0; x < 3; x++) {\n                const cx = 40 + x * 60;\n                const cy = 40 + y * 60;\n                const index = y * 3 + x + 1;\n                \n                const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');\n                dot.setAttribute('cx', cx);\n                dot.setAttribute('cy', cy);\n                dot.setAttribute('r', 8);\n                dot.setAttribute('fill', '#555');\n                dot.setAttribute('data-index', index);\n                svgSec.appendChild(dot);\n                dotsSec.push({ cx, cy, index, element: dot });\n            }\n        }\n\n        function getMousePosSec(e) {\n            const rect = svgSec.getBoundingClientRect();\n            const clientX = e.touches ? e.touches[0].clientX : e.clientX;\n            const clientY = e.touches ? e.touches[0].clientY : e.clientY;\n            return {\n                x: clientX - rect.left,\n                y: clientY - rect.top\n            };\n        }\n\n        function startDrawingSec(e) {\n            isDrawingSec = true;\n            resetPatternSec();\n            handleMoveSec(e);\n        }\n\n        function handleMoveSec(e) {\n            if (!isDrawingSec) return;\n            const pos = getMousePosSec(e);\n            \n            dotsSec.forEach(dot => {\n                const dist = Math.hypot(pos.x - dot.cx, pos.y - dot.cy);\n                if (dist < 20 && !selectedDotsSec.includes(dot)) {\n                    selectedDotsSec.push(dot);\n                    dot.element.setAttribute('fill', '#ffc107');\n                    dot.element.setAttribute('r', 12);\n                    \n                    if (selectedDotsSec.length > 1) {\n                        const prevDot = selectedDotsSec[selectedDotsSec.length - 2];\n                        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');\n                        line.setAttribute('x1', prevDot.cx);\n                        line.setAttribute('y1', prevDot.cy);\n                        line.setAttribute('x2', dot.cx);\n                        line.setAttribute('y2', dot.cy);\n                        line.setAttribute('stroke', '#ffc107');\n                        line.setAttribute('stroke-width', 3);\n                        svgSec.insertBefore(line, svgSec.firstChild);\n                    }\n                }\n            });\n\n            if (selectedDotsSec.length > 0) {\n                if (currentLineSec) currentLineSec.remove();\n                const lastDot = selectedDotsSec[selectedDotsSec.length - 1];\n                currentLineSec = document.createElementNS('http://www.w3.org/2000/svg', 'line');\n                currentLineSec.setAttribute('x1', lastDot.cx);\n                currentLineSec.setAttribute('y1', lastDot.cy);\n                currentLineSec.setAttribute('x2', pos.x);\n                currentLineSec.setAttribute('y2', pos.y);\n                currentLineSec.setAttribute('stroke', '#ffc107');\n                currentLineSec.setAttribute('stroke-width', 2);\n                currentLineSec.setAttribute('stroke-dasharray', '5,5');\n                svgSec.appendChild(currentLineSec);\n            }\n        }\n\n        function stopDrawingSec() {\n            if (!isDrawingSec) return;\n            isDrawingSec = false;\n            if (currentLineSec) currentLineSec.remove();\n            patternInputSec.value = selectedDotsSec.map(d => d.index).join('');\n        }\n\n        function resetPatternSec() {\n            selectedDotsSec.length = 0;\n            svgSec.querySelectorAll('line').forEach(l => l.remove());\n            dotsSec.forEach(dot => {\n                dot.element.setAttribute('fill', '#555');\n                dot.element.setAttribute('r', 8);\n            });\n            patternInputSec.value = '';\n        }\n\n        const showMicSetting = document.getElementById('setting-show-mic');\n        const interactiveModeSetting = document.getElementById('setting-interactive-mode');\n        const copyFormattedSetting = document.getElementById('setting-copy-formatted');\n\n        if (showMicSetting && window.USER_SETTINGS) {\n            showMicSetting.checked = window.USER_SETTINGS.show_mic !== false;\n            \n            showMicSetting.onchange = async () => {\n                const enabled = showMicSetting.checked;\n                try {\n                    await fetch('/settings', {\n                        method: 'POST',\n                        headers: { 'Content-Type': 'application/json' },\n                        body: JSON.stringify({ show_mic: enabled })\n                    });\n                    window.USER_SETTINGS.show_mic = enabled;\n                    // Trigger visibility update if DriveModeManager is available\n                    if (window.updateDriveModeVisibility) window.updateDriveModeVisibility();\n                } catch (err) { console.error(err); }\n            };\n        }\n\n        if (interactiveModeSetting && window.USER_SETTINGS) {\n            interactiveModeSetting.checked = window.USER_SETTINGS.interactive_mode !== false;\n            \n            interactiveModeSetting.onchange = async () => {\n                const enabled = interactiveModeSetting.checked;\n                try {\n                    await fetch('/settings', {\n                        method: 'POST',\n                        headers: { 'Content-Type': 'application/json' },\n                        body: JSON.stringify({ interactive_mode: enabled })\n                    });\n                    window.USER_SETTINGS.interactive_mode = enabled;\n                } catch (err) { console.error(err); }\n            };\n        }\n\n        if (copyFormattedSetting && window.USER_SETTINGS) {\n            copyFormattedSetting.checked = window.USER_SETTINGS.copy_formatted === true;\n            \n            copyFormattedSetting.onchange = async () => {\n                const enabled = copyFormattedSetting.checked;\n                try {\n                    await fetch('/settings', {\n                        method: 'POST',\n                        headers: { 'Content-Type': 'application/json' },\n                        body: JSON.stringify({ copy_formatted: enabled })\n                    });\n                    window.USER_SETTINGS.copy_formatted = enabled;\n                } catch (err) { console.error(err); }\n            };\n        }\n\n        svgSec.addEventListener('mousedown', startDrawingSec);\n        window.addEventListener('mousemove', handleMoveSec);\n        window.addEventListener('mouseup', stopDrawingSec);\n\n        svgSec.addEventListener('touchstart', (e) => { e.preventDefault(); startDrawingSec(e); });\n        svgSec.addEventListener('touchmove', (e) => { e.preventDefault(); handleMoveSec(e); });\n        svgSec.addEventListener('touchend', stopDrawingSec);\n\n        btnUpdatePattern.addEventListener('click', async () => {\n            const pattern = patternInputSec.value;\n            if (!pattern) {\n                patternStatus.textContent = 'Please draw a pattern first.';\n                patternStatus.className = 'mt-2 small text-danger';\n                return;\n            }\n\n            try {\n                const formData = new FormData();\n                formData.append('pattern', pattern);\n                const res = await fetch('/user/update-pattern', {\n                    method: 'POST',\n                    body: formData\n                });\n                const result = await res.json();\n                if (result.success) {\n                    patternStatus.textContent = 'Pattern updated successfully!';\n                    patternStatus.className = 'mt-2 small text-success';\n                } else {\n                    patternStatus.textContent = result.error || 'Update failed';\n                    patternStatus.className = 'mt-2 small text-danger';\n                }\n            } catch (err) {\n                patternStatus.textContent = err.message;\n                patternStatus.className = 'mt-2 small text-danger';\n            }\n        });\n\n        btnLinkWallet.addEventListener('click', async () => {\n            if (typeof window.ethereum === 'undefined') {\n                walletStatus.textContent = 'Ethereum wallet not found.';\n                walletStatus.className = 'mt-2 small text-danger';\n                return;\n            }\n\n            try {\n                const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });\n                const address = accounts[0];\n\n                const challengeRes = await fetch('/login/web3/challenge');\n                const { challenge } = await challengeRes.json();\n\n                const provider = new ethers.providers.Web3Provider(window.ethereum);\n                const signer = provider.getSigner();\n                const signature = await signer.signMessage(challenge);\n\n                const formData = new FormData();\n                formData.append('address', address);\n                formData.append('signature', signature);\n\n                const res = await fetch('/user/link-wallet', {\n                    method: 'POST',\n                    body: formData\n                });\n\n                const result = await res.json();\n                if (result.success) {\n                    walletStatus.textContent = 'Wallet linked successfully!';\n                    walletStatus.className = 'mt-2 small text-success';\n                    document.getElementById('wallet-address-input').value = address;\n                } else {\n                    walletStatus.textContent = result.error || 'Linking failed';\n                    walletStatus.className = 'mt-2 small text-danger';\n                }\n            } catch (err) {\n                walletStatus.textContent = err.message;\n                walletStatus.className = 'mt-2 small text-danger';\n            }\n        });\n\n        btnRegisterPasskey.addEventListener('click', async () => {\n            try {\n                const optionsRes = await fetch('/register/passkey/options');\n                const options = await optionsRes.json();\n\n                options.challenge = base64urlToUint8Array(options.challenge);\n                options.user.id = base64urlToUint8Array(options.user.id);\n                if (options.excludeCredentials) {\n                    options.excludeCredentials.forEach(cred => {\n                        cred.id = base64urlToUint8Array(cred.id);\n                    });\n                }\n\n                const credential = await navigator.credentials.create({\n                    publicKey: options\n                });\n\n                const regData = {\n                    id: credential.id,\n                    rawId: bufferToBase64Url(credential.rawId),\n                    type: credential.type,\n                    response: {\n                        attestationObject: bufferToBase64Url(credential.response.attestationObject),\n                        clientDataJSON: bufferToBase64Url(credential.response.clientDataJSON),\n                    }\n                };\n\n                const verifyRes = await fetch('/register/passkey/verify', {\n                    method: 'POST',\n                    headers: { 'Content-Type': 'application/json' },\n                    body: JSON.stringify(regData)\n                });\n\n                const result = await verifyRes.json();\n                if (result.success) {\n                    passkeyStatus.textContent = 'Passkey registered successfully!';\n                    passkeyStatus.className = 'mt-2 small text-success';\n                } else {\n                    passkeyStatus.textContent = result.error || 'Registration failed';\n                    passkeyStatus.className = 'mt-2 small text-danger';\n                }\n            } catch (err) {\n                passkeyStatus.textContent = err.message;\n                passkeyStatus.className = 'mt-2 small text-danger';\n            }\n        });\n\n        function base64urlToUint8Array(base64url) {\n            const padding = '='.repeat((4 - base64url.length % 4) % 4);\n            const base64 = (base64url + padding).replace(/\\-/g, '+').replace(/_/g, '/');\n            const rawData = window.atob(base64);\n            const outputArray = new Uint8Array(rawData.length);\n            for (let i = 0; i < rawData.length; ++i) {\n                outputArray[i] = rawData.charCodeAt(i);\n            }\n            return outputArray;\n        }\n\n        function bufferToBase64Url(buffer) {\n            const bytes = new Uint8Array(buffer);\n            let binary = '';\n            for (let i = 0; i < bytes.byteLength; i++) {\n                binary += String.fromCharCode(bytes[i]);\n            }\n            const base64 = window.btoa(binary);\n            return base64.replace(/\\+/g, '-').replace(/\\//g, '_').replace(/=/g, '');\n        }\n    });\n</script>\n<script src=\"/static/compression.js?v={{ range(1, 999999) | random }}\"></script>\n<script src=\"/static/drive_mode.js?v={{ range(1, 999999) | random }}\"></script>\n<script src=\"/static/attachment_manager.js?v={{ range(1, 999999) | random }}\"></script>\n<script>\n    window.INITIAL_MESSAGES = {{ initial_messages | tojson }};\n    window.TOTAL_MESSAGES = {{ total_messages }};\n    window.ACTIVE_SESSION_UUID = \"{{ active_session.uuid if active_session else '' }}\";\n    window.USER_SETTINGS = {{ user_settings | tojson }};\n\n    // Mobile Height Fix\n\n</script>\n<script src=\"/static/script.js?v={{ range(1, 999999) | random }}\"></script>\n<script>\n    /*\n    if ('serviceWorker' in navigator) {\n        window.addEventListener('load', () => {\n            navigator.serviceWorker.register('/sw.js')\n                .then(reg => console.log('SW Registered', reg))\n                .catch(err => console.log('SW Reg Error', err));\n        });\n    }\n    */\n</script>\n</body>\n</html>\n",
    "login.html": "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n    <meta charset=\"UTF-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n    <title>Login - Gemini Agent</title>\n    <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css\" rel=\"stylesheet\">\n    <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css\">\n    <link rel=\"icon\" type=\"image/svg+xml\" href=\"/static/icon.svg?v=2\">\n    <link rel=\"manifest\" href=\"/manifest.json?v=3\">\n    <link rel=\"stylesheet\" href=\"/static/style.css\">\n    <style>\n        body {\n            height: 100vh;\n            display: flex;\n            align-items: center;\n            justify-content: center;\n            background-color: #121212;\n        }\n        .login-card {\n            width: 100%;\n            max-width: 400px;\n            padding: 2rem;\n            border-radius: 1rem;\n            background-color: #1e1e1e;\n            border: 1px solid #333;\n            box-shadow: 0 10px 30px rgba(0,0,0,0.5);\n        }\n    </style>\n    <script src=\"https://cdnjs.cloudflare.com/ajax/libs/ethers/5.7.2/ethers.umd.min.js\"></script>\n</head>\n<body class=\"text-light\">\n\n<div class=\"login-card\">\n    <div class=\"text-center mb-4\">\n        <h1 class=\"h3 mb-3\"><i class=\"bi bi-robot text-primary\"></i> Gemini Agent</h1>\n        <p class=\"text-muted\">Please sign in to continue</p>\n    </div>\n\n    {% if error %}\n    <div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">\n        {{ error }}\n        <button type=\"button\" class=\"btn-close\" data-bs-dismiss=\"alert\" aria-label=\"Close\"></button>\n    </div>\n    {% endif %}\n\n    <ul class=\"nav nav-pills nav-fill mb-4\" id=\"loginTabs\" role=\"tablist\">\n        <li class=\"nav-item\" role=\"presentation\">\n            <button class=\"nav-link active\" id=\"passkey-tab\" data-bs-toggle=\"pill\" data-bs-target=\"#passkey-login\" type=\"button\" role=\"tab\" aria-controls=\"passkey-login\" aria-selected=\"true\">Passkey</button>\n        </li>\n        <li class=\"nav-item\" role=\"presentation\">\n            <button class=\"nav-link\" id=\"password-tab\" data-bs-toggle=\"pill\" data-bs-target=\"#password-login\" type=\"button\" role=\"tab\" aria-controls=\"password-login\" aria-selected=\"false\">Password</button>\n        </li>\n        <li class=\"nav-item\" role=\"presentation\">\n            <button class=\"nav-link\" id=\"wallet-tab\" data-bs-toggle=\"pill\" data-bs-target=\"#wallet-login\" type=\"button\" role=\"tab\" aria-controls=\"wallet-login\" aria-selected=\"false\">Wallet</button>\n        </li>\n        <li class=\"nav-item\" role=\"presentation\">\n            <button class=\"nav-link\" id=\"pattern-tab\" data-bs-toggle=\"pill\" data-bs-target=\"#pattern-login\" type=\"button\" role=\"tab\" aria-controls=\"pattern-login\" aria-selected=\"false\">Pattern</button>\n        </li>\n    </ul>\n\n    <div class=\"tab-content\" id=\"loginTabsContent\">\n        <!-- Passkey Login -->\n        <div class=\"tab-pane fade show active\" id=\"passkey-login\" role=\"tabpanel\" aria-labelledby=\"passkey-tab\">\n            <div class=\"text-center py-4\">\n                <i class=\"bi bi-key display-1 text-info mb-3\"></i>\n                <div class=\"mb-3\">\n                    <label for=\"username-passkey\" class=\"form-label\">Username (Optional)</label>\n                    <input type=\"text\" class=\"form-control bg-dark text-light border-secondary\" id=\"username-passkey\" placeholder=\"Leave empty for auto-login\">\n                </div>\n                <button id=\"btn-passkey-login\" class=\"btn btn-info w-100 py-2 text-white\">\n                    Sign In with Passkey\n                </button>\n                <div id=\"passkey-error\" class=\"text-danger small mt-2\"></div>\n            </div>\n        </div>\n\n        <!-- Password Login -->\n        <div class=\"tab-pane fade\" id=\"password-login\" role=\"tabpanel\" aria-labelledby=\"password-tab\">\n            <form action=\"/login\" method=\"post\">\n                <div class=\"mb-3\">\n                    <label for=\"username\" class=\"form-label\">Username</label>\n                    <input type=\"text\" class=\"form-control bg-dark text-light border-secondary\" id=\"username\" name=\"username\" required autofocus>\n                </div>\n                <div class=\"mb-4\">\n                    <label for=\"password\" class=\"form-label\">Password</label>\n                    <input type=\"password\" class=\"form-control bg-dark text-light border-secondary\" id=\"password\" name=\"password\" required>\n                </div>\n                <button type=\"submit\" class=\"btn btn-primary w-100 py-2\">Sign In</button>\n            </form>\n        </div>\n\n        <!-- Wallet Login -->\n        <div class=\"tab-pane fade\" id=\"wallet-login\" role=\"tabpanel\" aria-labelledby=\"wallet-tab\">\n            <div class=\"text-center py-4\">\n                <i class=\"bi bi-wallet2 display-1 text-primary mb-3\"></i>\n                <p>Connect your MetaMask or Brave wallet to sign in.</p>\n                <button id=\"btn-wallet-login\" class=\"btn btn-outline-primary w-100 py-2\">\n                    <img src=\"data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAzMTguNiAzMTguNiI+PHBhdGggZmlsbD0iI0UyN0MxMSIgZD0iTTEyOC42IDYuOGwtMjIuNSAzNi4zIDM0LjYgMjIuM3oiLz48cGF0aCBmaWxsPSIjRTI3QzExIiBkPSJNMTkwIDYuOGwyMi41IDM2LjMtMzQuNiAyMi4zeiIvPjxwYXRoIGZpbGw9IiNFNDc2MTkiIGQ9Ik05OC4zIDY5LjFsLTI5LjEtNCA1MS42IDM4LjV6Ii8+PHBhdGggZmlsbD0iI0U0NzYxOSIgZD0iTTcyMC4zIDY5LjFsMjkuMS00LTUxLjYgMzguNXoiLz48cGF0aCBmaWxsPSIjRTRDMTMzIiBkPSJNOTguNSAxOTMuOGwtMjkuNyA0LjUgMjUuNiA1NnoiLz48cGF0aCBmaWxsPSIjRTRDMjMyIiBkPSJNOTQuNCAyMjMuN2wzOC4zIDE3LjMtMjQuOC00Ny4zeiIvPjxwYXRoIGZpbGw9IiNFNUMxMzMiIGQ9Ik0yMjQuMiAyMjMuN2wtMzguMyAxNy4zIDI0LjgtNDcuM3oiLz48cGF0aCBmaWxsPSIjRTRDMjMyIiBkPSJNMjIwLjEgMTk4LjhsMjkuNyA0LjUtMjUuNiA1NnoiLz48cGF0aCBmaWxsPSIjRTRDMjMyIiBkPSJNMTU5LjMgMTI0LjNsLTI3LjIgOTEuNCAyNy4yIDE0LjIgMjcuMi0xNC4yLTExLjYtOTEuNHoiLz48cGF0aCBmaWxsPSIjRTRDMjMyIiBkPSJNMTU5LjMgMjMwLjFsLTI3LjIgMTQuMkwxNTkuMyAzMTBsMjcuMi02NS43eiIvPjxwYXRoIGZpbGw9IiNGNjhCMTgiIGQ9Ik02OC44IDY1LjFsMTAwLjUgMTguNkwxNTkuMyA2LjhsLTMwLjcgNTguM3oiLz48cGF0aCBmaWxsPSIjRjY4QjE4IiBkPSJNMjQ5LjggNjUuMWwtMTAwLjUgMTguNkwxNTkuMyA2LjhsMzAuNyA1OC4zeiIvPjxwYXRoIGZpbGw9IiNGNjhCMTgiIGQ9Ik02OS4xIDE5OC4zbDU0LjIgMzIuN0wxNTkuMyAxODdsLTM0LjgtNDYuM3oiLz48cGF0aCBmaWxsPSIjRjY4QjE4IiBkPSJNMjQ5LjUgMTk4LjNsLTU0LjIgMzIuN0wxNTkuMyAxODdsMzQuOC00Ni4zeiIvPjxwYXRoIGZpbGw9IiNGNjhCMTgiIGQ9Ik02OS4xIDE5OC4zbDI1LjYgNTZMMTU5LjMgMzEwbC0yNy4yLTY1Ljd6Ii8+PHBhdGggZmlsbD0iI0Y2OEIxOCIgZD0iTTI0OS41IDE5OC4zbC0yNS42IDU2TDE1OS4zIDMxMGwyNy4yLTY1Ljd6Ii8+PC9zdmc+\" alt=\"MetaMask\" style=\"height: 20px; margin-right: 10px;\">\n                    Sign In with Wallet\n                </button>\n                <div id=\"wallet-error\" class=\"text-danger small mt-2\"></div>\n            </div>\n        </div>\n\n        <!-- Pattern Login -->\n        <div class=\"tab-pane fade\" id=\"pattern-login\" role=\"tabpanel\" aria-labelledby=\"pattern-tab\">\n            <form id=\"pattern-form\" action=\"/login/pattern\" method=\"post\">\n                <div class=\"mb-3\">\n                    <label for=\"username-pattern\" class=\"form-label\">Username (Optional)</label>\n                    <input type=\"text\" class=\"form-control bg-dark text-light border-secondary\" id=\"username-pattern\" name=\"username\" placeholder=\"Leave empty for auto-login\">\n                </div>\n                <div class=\"mb-3 text-center\">\n                    <label class=\"form-label d-block\">Draw Pattern</label>\n                    <div id=\"pattern-container\" class=\"mx-auto\" style=\"width: 250px; height: 250px; position: relative; touch-action: none;\">\n                        <svg id=\"pattern-svg\" width=\"250\" height=\"250\" style=\"background: #252525; border-radius: 10px;\"></svg>\n                    </div>\n                    <input type=\"hidden\" id=\"pattern-input\" name=\"pattern\">\n                </div>\n                <button type=\"submit\" class=\"btn btn-primary w-100 py-2\">Sign In with Pattern</button>\n            </form>\n        </div>\n    </div>\n    \n    <div class=\"text-center mt-4\">\n    </div>\n</div>\n\n<script src=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js\"></script>\n<script>\n    document.addEventListener('DOMContentLoaded', () => {\n        // ... (existing pattern logic)\n        const svg = document.getElementById('pattern-svg');\n        // ...\n        const patternInput = document.getElementById('pattern-input');\n        const container = document.getElementById('pattern-container');\n        const dots = [];\n        const selectedDots = [];\n        let isDrawing = false;\n        let currentLine = null;\n\n        // Create 3x3 grid\n        for (let y = 0; y < 3; y++) {\n            for (let x = 0; x < 3; x++) {\n                const cx = 50 + x * 75;\n                const cy = 50 + y * 75;\n                const index = y * 3 + x + 1;\n                \n                const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');\n                dot.setAttribute('cx', cx);\n                dot.setAttribute('cy', cy);\n                dot.setAttribute('r', 10);\n                dot.setAttribute('fill', '#555');\n                dot.setAttribute('data-index', index);\n                svg.appendChild(dot);\n                dots.push({ cx, cy, index, element: dot });\n            }\n        }\n\n        function getMousePos(e) {\n            const rect = svg.getBoundingClientRect();\n            const clientX = e.touches ? e.touches[0].clientX : e.clientX;\n            const clientY = e.touches ? e.touches[0].clientY : e.clientY;\n            return {\n                x: clientX - rect.left,\n                y: clientY - rect.top\n            };\n        }\n\n        function startDrawing(e) {\n            isDrawing = true;\n            resetPattern();\n            handleMove(e);\n        }\n\n        function handleMove(e) {\n            if (!isDrawing) return;\n            const pos = getMousePos(e);\n            \n            // Check if near a dot\n            dots.forEach(dot => {\n                const dist = Math.hypot(pos.x - dot.cx, pos.y - dot.cy);\n                if (dist < 25 && !selectedDots.includes(dot)) {\n                    selectedDots.push(dot);\n                    dot.element.setAttribute('fill', '#0d6efd');\n                    dot.element.setAttribute('r', 15);\n                    \n                    if (selectedDots.length > 1) {\n                        const prevDot = selectedDots[selectedDots.length - 2];\n                        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');\n                        line.setAttribute('x1', prevDot.cx);\n                        line.setAttribute('y1', prevDot.cy);\n                        line.setAttribute('x2', dot.cx);\n                        line.setAttribute('y2', dot.cy);\n                        line.setAttribute('stroke', '#0d6efd');\n                        line.setAttribute('stroke-width', 4);\n                        svg.insertBefore(line, svg.firstChild);\n                    }\n                }\n            });\n\n            // Update floating line\n            if (selectedDots.length > 0) {\n                if (currentLine) currentLine.remove();\n                const lastDot = selectedDots[selectedDots.length - 1];\n                currentLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');\n                currentLine.setAttribute('x1', lastDot.cx);\n                currentLine.setAttribute('y1', lastDot.cy);\n                currentLine.setAttribute('x2', pos.x);\n                currentLine.setAttribute('y2', pos.y);\n                currentLine.setAttribute('stroke', '#0d6efd');\n                currentLine.setAttribute('stroke-width', 2);\n                currentLine.setAttribute('stroke-dasharray', '5,5');\n                svg.appendChild(currentLine);\n            }\n        }\n\n        function stopDrawing() {\n            if (!isDrawing) return;\n            isDrawing = false;\n            if (currentLine) currentLine.remove();\n            patternInput.value = selectedDots.map(d => d.index).join('');\n        }\n\n        function resetPattern() {\n            selectedDots.length = 0;\n            svg.querySelectorAll('line').forEach(l => l.remove());\n            dots.forEach(dot => {\n                dot.element.setAttribute('fill', '#555');\n                dot.element.setAttribute('r', 10);\n            });\n            patternInput.value = '';\n        }\n\n        svg.addEventListener('mousedown', startDrawing);\n        window.addEventListener('mousemove', handleMove);\n        window.addEventListener('mouseup', stopDrawing);\n\n        svg.addEventListener('touchstart', (e) => { e.preventDefault(); startDrawing(e); });\n        svg.addEventListener('touchmove', (e) => { e.preventDefault(); handleMove(e); });\n        svg.addEventListener('touchend', stopDrawing);\n\n        // --- Wallet Login ---\n        const btnWalletLogin = document.getElementById('btn-wallet-login');\n        const walletError = document.getElementById('wallet-error');\n\n        btnWalletLogin.addEventListener('click', async () => {\n            if (typeof window.ethereum === 'undefined') {\n                walletError.textContent = 'Ethereum wallet not found. Please install MetaMask.';\n                return;\n            }\n\n            try {\n                // Request account access\n                const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });\n                const address = accounts[0];\n\n                // Get challenge from server\n                const challengeRes = await fetch('/login/web3/challenge');\n                const { challenge } = await challengeRes.json();\n\n                // Request signature\n                const provider = new ethers.providers.Web3Provider(window.ethereum);\n                const signer = provider.getSigner();\n                const signature = await signer.signMessage(challenge);\n\n                // Verify signature on server\n                const formData = new FormData();\n                formData.append('address', address);\n                formData.append('signature', signature);\n\n                const verifyRes = await fetch('/login/web3/verify', {\n                    method: 'POST',\n                    body: formData\n                });\n\n                const result = await verifyRes.json();\n                if (result.success) {\n                    window.location.href = '/';\n                } else {\n                    walletError.textContent = result.error || 'Login failed';\n                }\n            } catch (err) {\n                console.error(err);\n                walletError.textContent = err.message || 'An error occurred during wallet login';\n            }\n        });\n\n        // --- Passkey Login ---\n        const btnPasskeyLogin = document.getElementById('btn-passkey-login');\n        const passkeyError = document.getElementById('passkey-error');\n        const usernamePasskey = document.getElementById('username-passkey');\n\n        btnPasskeyLogin.addEventListener('click', async () => {\n            const username = usernamePasskey.value;\n            \n            try {\n                // Get authentication options from server\n                const formData = new FormData();\n                if (username) {\n                    formData.append('username', username);\n                }\n                \n                const optionsRes = await fetch('/login/passkey/options', {\n                    method: 'POST',\n                    body: formData\n                });\n\n                if (!optionsRes.ok) {\n                    const errData = await optionsRes.json();\n                    throw new Error(errData.error || 'User not found or no passkeys registered');\n                }\n\n                const options = await optionsRes.json();\n\n                // Convert base64url to Uint8Array for the browser\n                options.challenge = base64urlToUint8Array(options.challenge);\n                if (options.allowCredentials) {\n                    options.allowCredentials.forEach(cred => {\n                        cred.id = base64urlToUint8Array(cred.id);\n                    });\n                }\n\n                // Call the browser's credential API\n                const credential = await navigator.credentials.get({\n                    publicKey: options\n                });\n\n                // Prepare data for verification\n                const authData = {\n                    id: credential.id,\n                    rawId: bufferToBase64Url(credential.rawId),\n                    type: credential.type,\n                    response: {\n                        authenticatorData: bufferToBase64Url(credential.response.authenticatorData),\n                        clientDataJSON: bufferToBase64Url(credential.response.clientDataJSON),\n                        signature: bufferToBase64Url(credential.response.signature),\n                        userHandle: credential.response.userHandle ? bufferToBase64Url(credential.response.userHandle) : null\n                    }\n                };\n\n                // Verify authentication on server\n                const verifyRes = await fetch('/login/passkey/verify', {\n                    method: 'POST',\n                    headers: {\n                        'Content-Type': 'application/json'\n                    },\n                    body: JSON.stringify(authData)\n                });\n\n                const result = await verifyRes.json();\n                if (result.success) {\n                    window.location.href = '/';\n                } else {\n                    passkeyError.textContent = result.error || 'Passkey authentication failed';\n                }\n            } catch (err) {\n                console.error(err);\n                passkeyError.textContent = err.message || 'An error occurred during passkey login';\n            }\n        });\n\n        // Helper functions for WebAuthn\n        function base64urlToUint8Array(base64url) {\n            const padding = '='.repeat((4 - base64url.length % 4) % 4);\n            const base64 = (base64url + padding).replace(/\\-/g, '+').replace(/_/g, '/');\n            const rawData = window.atob(base64);\n            const outputArray = new Uint8Array(rawData.length);\n            for (let i = 0; i < rawData.length; ++i) {\n                outputArray[i] = rawData.charCodeAt(i);\n            }\n            return outputArray;\n        }\n\n        function bufferToBase64Url(buffer) {\n            const bytes = new Uint8Array(buffer);\n            let binary = '';\n            for (let i = 0; i < bytes.byteLength; i++) {\n                binary += String.fromCharCode(bytes[i]);\n            }\n            const base64 = window.btoa(binary);\n            return base64.replace(/\\+/g, '-').replace(/\\//g, '_').replace(/=/g, '');\n        }\n    });\n</script>\n<script>\n    /*\n    if ('serviceWorker' in navigator) {\n        window.addEventListener('load', () => {\n            navigator.serviceWorker.register('/sw.js')\n                .then(reg => console.log('SW Registered', reg))\n                .catch(err => console.log('SW Reg Error', err));\n        });\n    }\n    */\n</script>\n</body>\n</html>\n",
    "setup.html": "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n    <meta charset=\"UTF-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n    <title>Setup - Gemini Agent</title>\n    <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css\" rel=\"stylesheet\">\n    <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css\">\n    <link rel=\"icon\" type=\"image/svg+xml\" href=\"/static/icon.svg?v=2\">\n    <link rel=\"stylesheet\" href=\"/static/style.css\">\n    <style>\n        body {\n            height: 100vh;\n            display: flex;\n            align-items: center;\n            justify-content: center;\n            background-color: #121212;\n        }\n        .setup-card {\n            width: 100%;\n            max-width: 450px;\n            padding: 2.5rem;\n            border-radius: 1rem;\n            background-color: #1e1e1e;\n            border: 1px solid #333;\n            box-shadow: 0 10px 30px rgba(0,0,0,0.5);\n        }\n    </style>\n</head>\n<body class=\"text-light\">\n\n<div class=\"setup-card\">\n    <div class=\"text-center mb-4\">\n        <h1 class=\"h3 mb-3\"><i class=\"bi bi-robot text-primary\"></i> Initial Setup</h1>\n        <p class=\"text-muted\">Create your administrator account to begin.</p>\n    </div>\n\n    <form action=\"/setup\" method=\"post\">\n        <div class=\"mb-3\">\n            <label class=\"form-label\">Username</label>\n            <input type=\"text\" class=\"form-control bg-dark text-light border-secondary\" value=\"admin\" disabled>\n            <div class=\"form-text\">The default administrator username is 'admin'.</div>\n        </div>\n        <div class=\"mb-3\">\n            <label for=\"origin\" class=\"form-label\">Application Origin (URL)</label>\n            <input type=\"url\" class=\"form-control bg-dark text-light border-secondary\" id=\"origin\" name=\"origin\" value=\"http://localhost:8000\" required>\n            <div class=\"form-text\">The full URL where this app is hosted (e.g., https://myapp.example.com).</div>\n        </div>\n        <div class=\"mb-3\">\n            <label for=\"rp_id\" class=\"form-label\">RP ID (Domain)</label>\n            <input type=\"text\" class=\"form-control bg-dark text-light border-secondary\" id=\"rp_id\" name=\"rp_id\" value=\"localhost\" required>\n            <div class=\"form-text\">The domain for WebAuthn/Passkeys (e.g., myapp.example.com). Usually the domain part of the Origin.</div>\n        </div>\n        <div class=\"mb-4\">\n            <label for=\"password\" class=\"form-label\">Admin Password</label>\n            <input type=\"password\" class=\"form-control bg-dark text-light border-secondary\" id=\"password\" name=\"password\" required autofocus>\n            <div class=\"form-text\">Choose a strong password for your local agent.</div>\n        </div>\n        <button type=\"submit\" class=\"btn btn-info w-100 py-2 text-white\">Complete Setup</button>\n    </form>\n</div>\n\n<script src=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js\"></script>\n<script>\n    document.addEventListener('DOMContentLoaded', () => {\n        const originInput = document.getElementById('origin');\n        const rpIdInput = document.getElementById('rp_id');\n        \n        // Auto-fill based on current URL to handle non-LAN access\n        originInput.value = window.location.origin;\n        rpIdInput.value = window.location.hostname;\n    });\n</script>\n</body>\n</html>\n"
}


STATIC = {
    "attachment_manager.js": {
        "content": "class AttachmentManager {\n    constructor(options = {}) {\n        this.attachments = []; // Array of objects: { file, id, compressedFile, previewUrl, size }\n        this.maxTotalSize = options.maxTotalSize || 20 * 1024 * 1024; // Default 20MB\n        this.onQueueChange = options.onQueueChange || (() => {});\n        this.onSizeLimitExceeded = options.onSizeLimitExceeded || (() => {});\n    }\n\n    /**\n     * Adds files to the queue.\n     * @param {FileList|File[]} files \n     */\n    async addFiles(files) {\n        for (const file of Array.from(files)) {\n            const id = Math.random().toString(36).substring(2, 9);\n            let processedFile = file;\n            let previewUrl = null;\n\n            if (file.type.startsWith('image/')) {\n                try {\n                    // Assume compressImage is available globally or we'll inject it\n                    if (typeof compressImage === 'function') {\n                        processedFile = await compressImage(file);\n                    }\n                    previewUrl = URL.createObjectURL(processedFile);\n                } catch (e) {\n                    console.error(\"Compression failed for\", file.name, e);\n                }\n            }\n\n            const attachmentSize = processedFile.size;\n            if (this.getTotalSize() + attachmentSize > this.maxTotalSize) {\n                this.onSizeLimitExceeded(file.name);\n                continue;\n            }\n\n            this.attachments.push({\n                id,\n                originalFile: file,\n                file: processedFile,\n                previewUrl,\n                name: processedFile.name,\n                size: attachmentSize,\n                type: file.type\n            });\n        }\n        this.onQueueChange(this.attachments);\n    }\n\n    removeAttachment(id) {\n        const index = this.attachments.findIndex(a => a.id === id);\n        if (index !== -1) {\n            const attachment = this.attachments[index];\n            if (attachment.previewUrl) {\n                URL.revokeObjectURL(attachment.previewUrl);\n            }\n            this.attachments.splice(index, 1);\n            this.onQueueChange(this.attachments);\n        }\n    }\n\n    clear() {\n        this.attachments.forEach(a => {\n            if (a.previewUrl) URL.revokeObjectURL(a.previewUrl);\n        });\n        this.attachments = [];\n        this.onQueueChange(this.attachments);\n    }\n\n    getTotalSize() {\n        return this.attachments.reduce((sum, a) => sum + a.size, 0);\n    }\n\n    getFiles() {\n        return this.attachments.map(a => a.file);\n    }\n}\n\nif (typeof module !== 'undefined' && module.exports) {\n    module.exports = AttachmentManager;\n}\n",
        "encoding": "text"
    },
    "compression.js": {
        "content": "/**\n * Compresses an image file client-side.\n * @param {File} file - The original image file.\n * @returns {Promise<File>} - A promise that resolves to the compressed WebP File.\n */\nasync function compressImage(file) {\n    // Only compress images\n    if (!file.type.startsWith('image/')) {\n        return file;\n    }\n\n    return new Promise((resolve, reject) => {\n        const reader = new FileReader();\n        reader.onload = (e) => {\n            const img = new Image();\n            img.onload = () => {\n                const canvas = document.createElement('canvas');\n                let width = img.width;\n                let height = img.height;\n                const maxDim = 1536;\n\n                // Calculate new dimensions\n                if (width > maxDim || height > maxDim) {\n                    if (width > height) {\n                        height = Math.round((height * maxDim) / width);\n                        width = maxDim;\n                    } else {\n                        width = Math.round((width * maxDim) / height);\n                        height = maxDim;\n                    }\n                }\n\n                canvas.width = width;\n                canvas.height = height;\n                const ctx = canvas.getContext('2d');\n                \n                // Use better image scaling if supported\n                ctx.imageSmoothingEnabled = true;\n                ctx.imageSmoothingQuality = 'high';\n                \n                ctx.drawImage(img, 0, 0, width, height);\n\n                // Convert to WebP with 0.8 quality\n                canvas.toBlob((blob) => {\n                    if (blob) {\n                        // Create a new File object with .webp extension\n                        const newFileName = file.name.replace(/\\.[^/.]+$/, \"\") + \".webp\";\n                        const compressedFile = new File([blob], newFileName, {\n                            type: 'image/webp',\n                            lastModified: Date.now()\n                        });\n                        resolve(compressedFile);\n                    } else {\n                        // Fallback to original if compression fails\n                        resolve(file);\n                    }\n                }, 'image/webp', 0.8);\n            };\n            img.onerror = () => reject(new Error('Failed to load image for compression.'));\n            img.src = e.target.result;\n        };\n        reader.onerror = () => reject(new Error('Failed to read file for compression.'));\n        reader.readAsDataURL(file);\n    });\n}",
        "encoding": "text"
    },
    "drive_mode.js": {
        "content": "/**\n * Manages the \"Drive Mode\" voice-only conversation loop.\n * Handles speech recognition (STT) and speech synthesis (TTS).\n */\nclass DriveModeManager {\n    constructor() {\n        this.isActive = false;\n        this.state = 'idle'; // idle, listening, processing, speaking\n        this.wakeLock = null;\n        \n        // Pre-load voices for Chrome/Android\n        if (typeof window !== 'undefined' && window.speechSynthesis) {\n            window.speechSynthesis.getVoices();\n            window.speechSynthesis.onvoiceschanged = () => {\n                window.speechSynthesis.getVoices();\n            };\n        }\n    }\n\n    /**\n     * Checks if the browser supports the necessary Web Speech APIs and Wake Lock API.\n     * @returns {boolean}\n     */\n    isSupported() {\n        const hasSTT = 'webkitSpeechRecognition' in window || 'speechRecognition' in window;\n        const hasTTS = 'speechSynthesis' in window;\n        return hasSTT && hasTTS;\n    }\n\n    /**\n     * Requests a screen wake lock to prevent the device from sleeping.\n     */\n    async requestWakeLock() {\n        if ('wakeLock' in navigator) {\n            try {\n                this.wakeLock = await navigator.wakeLock.request('screen');\n                console.log('Wake Lock acquired');\n            } catch (err) {\n                console.error(`${err.name}, ${err.message}`);\n            }\n        }\n    }\n\n    /**\n     * Releases the acquired wake lock.\n     */\n    async releaseWakeLock() {\n        if (this.wakeLock) {\n            await this.wakeLock.release();\n            this.wakeLock = null;\n            console.log('Wake Lock released');\n        }\n    }\n\n    /**\n     * Starts the Speech-to-Text (STT) recognition.\n     * @param {Function} onResult - Callback called with transcribed text.\n     * @param {Function} onError - Callback called on recognition error.\n     */\n    startListening(onResult, onError) {\n        const SpeechRecognition = window.webkitSpeechRecognition || window.SpeechRecognition;\n        if (!SpeechRecognition) {\n            if (onError) onError('Speech Recognition not supported');\n            return;\n        }\n\n        const recognition = new SpeechRecognition();\n        \n        // Using el-GR generally allows for better recognition of Greek + English\n        // mixed together than using en-US on an English device.\n        recognition.lang = 'el-GR'; \n        recognition.interimResults = false;\n        recognition.maxAlternatives = 1;\n        recognition.continuous = false; // We want automatic end-of-speech detection\n\n        recognition.onstart = () => {\n            this.state = 'listening';\n            console.log('STT: Started listening...');\n        };\n\n        recognition.onresult = (event) => {\n            const transcript = event.results[0][0].transcript;\n            console.log('STT Result:', transcript);\n            this.state = 'idle';\n            if (onResult) onResult(transcript);\n        };\n\n        recognition.onerror = (event) => {\n            console.error('STT Error:', event.error);\n            this.state = 'idle';\n            if (onError) onError(event.error);\n        };\n\n        recognition.onend = () => {\n            console.log('STT: Stopped listening.');\n            if (this.state === 'listening') {\n                this.state = 'idle';\n            }\n        };\n\n        try {\n            recognition.start();\n            this.recognition = recognition;\n        } catch (e) {\n            console.error('STT Start Error:', e);\n            this.state = 'idle';\n            if (onError) onError(e.message);\n        }\n    }\n\n    /**\n     * Stops current recognition.\n     */\n    stopListening() {\n        if (this.recognition) {\n            try {\n                this.recognition.stop();\n            } catch (e) {\n                // Ignore if already stopped\n            }\n            this.recognition = null;\n        }\n    }\n\n    /**\n     * Reads text aloud using Speech Synthesis (TTS).\n     * @param {string} text - The text to speak.\n     * @param {Function} onEnd - Callback called when speaking finishes.\n     */\n    speak(text, onEnd) {\n        if (!window.speechSynthesis) {\n            if (onEnd) onEnd();\n            return;\n        }\n\n        // Cancel any ongoing speech\n        window.speechSynthesis.cancel();\n\n        const utterance = new SpeechSynthesisUtterance(text);\n        \n        // Smarter Voice Selection\n        const voices = window.speechSynthesis.getVoices();\n        if (voices.length > 0) {\n            // Detect if text is mostly Greek or English (simplified)\n            const isGreek = /[\\u0370-\\u03FF]/.test(text);\n            const targetLang = isGreek ? 'el' : 'en';\n            \n            // Find a voice that matches the language\n            const voice = voices.find(v => v.lang.startsWith(targetLang)) || \n                          voices.find(v => v.lang.startsWith(document.documentElement.lang)) ||\n                          voices[0];\n            \n            if (voice) {\n                utterance.voice = voice;\n                utterance.lang = voice.lang;\n            }\n        } else {\n            utterance.lang = document.documentElement.lang || window.navigator.language || 'el-GR';\n        }\n        \n        utterance.onstart = () => {\n            this.state = 'speaking';\n            console.log('TTS: Started speaking...');\n        };\n\n        utterance.onend = () => {\n            this.state = 'idle';\n            console.log('TTS: Finished speaking.');\n            if (onEnd) onEnd();\n        };\n\n        utterance.onerror = (event) => {\n            console.error('TTS Error:', event.error);\n            this.state = 'idle';\n            if (onEnd) onEnd();\n        };\n\n        window.speechSynthesis.speak(utterance);\n    }\n\n    /**\n     * Stops current speaking.\n     */\n    stopSpeaking() {\n        if (window.speechSynthesis) {\n            window.speechSynthesis.cancel();\n        }\n    }\n}\n\nif (typeof module !== 'undefined' && module.exports) {\n    module.exports = DriveModeManager;\n}\n",
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
        "content": "document.addEventListener('DOMContentLoaded', () => {\n    const chatForm = document.getElementById('chat-form');\n    const messageInput = document.getElementById('message-input');\n    const chatContainer = document.getElementById('chat-container');\n    const fileUpload = document.getElementById('file-upload');\n    const filePreviewArea = document.getElementById('file-preview-area');\n    const fileNameDisplay = document.getElementById('file-name');\n    const clearFileBtn = document.getElementById('clear-file-btn');\n    const exportBtn = document.getElementById('export-btn');\n    const exportBtnMobile = document.getElementById('export-btn-mobile');\n    const resetBtn = document.getElementById('reset-btn');\n    const resetBtnMobile = document.getElementById('reset-btn-mobile');\n\n    const shareModalEl = document.getElementById('shareModal');\n    const shareUsernameInput = document.getElementById('share-username-input');\n    const shareStatus = document.getElementById('share-status');\n    const btnConfirmShare = document.getElementById('btn-confirm-share');\n    let shareModal = null;\n\n    if (shareModalEl) {\n        shareModal = new bootstrap.Modal(shareModalEl);\n        \n        shareModalEl.addEventListener('shown.bs.modal', () => {\n            shareUsernameInput.focus();\n            shareStatus.textContent = '';\n        });\n\n        if (btnConfirmShare) {\n            btnConfirmShare.addEventListener('click', async () => {\n                const username = shareUsernameInput.value.trim();\n                if (!username) return;\n                \n                const uuid = currentActiveUUID;\n                if (!uuid) return;\n\n                shareStatus.textContent = 'Sharing...';\n                shareStatus.className = 'small mt-2 text-muted';\n                \n                try {\n                    const response = await fetch(`/sessions/${uuid}/share`, {\n                        method: 'POST',\n                        headers: { 'Content-Type': 'application/json' },\n                        body: JSON.stringify({ username })\n                    });\n                    const data = await response.json();\n                    \n                    // Fail silently or with simple success per spec\n                    if (data.success) {\n                        shareStatus.textContent = 'Chat shared successfully!';\n                        shareStatus.className = 'small mt-2 text-success';\n                        setTimeout(() => {\n                            shareModal.hide();\n                            shareUsernameInput.value = '';\n                        }, 1000);\n                    } else {\n                        // Per spec: fail silently if target does not exist.\n                        // We close the modal as if nothing happened or show a subtle message.\n                        shareModal.hide();\n                        shareUsernameInput.value = '';\n                        showToast('Sharing operation finished.');\n                    }\n                } catch (error) {\n                    console.error('Error sharing session:', error);\n                    shareStatus.textContent = 'Network error. Try again.';\n                    shareStatus.className = 'small mt-2 text-danger';\n                }\n            });\n        }\n    }\n\n    async function handleReset() {\n        if (confirm('Are you sure you want to clear the conversation history?')) {\n            try {\n                const response = await fetch('/reset', { method: 'POST' });\n                const data = await response.json();\n                chatContainer.innerHTML = `<div class=\"text-center text-muted mt-5\"><p>${data.response}</p></div>`;\n            } catch (error) {\n                console.error('Error resetting chat:', error);\n                alert('Failed to reset chat.');\n            }\n        }\n    }\n\n    async function handleClone(uuid, messageIndex, showAlert = true) {\n        try {\n            const response = await fetch(`/sessions/${uuid}/clone`, {\n                method: 'POST',\n                headers: { 'Content-Type': 'application/json' },\n                body: JSON.stringify({ message_index: messageIndex })\n            });\n            const data = await response.json();\n            if (data.success) {\n                if (showAlert) showToast('Conversation forked!');\n                \n                if (data.new_uuid === \"pending\") {\n                    // For -1 forks, the next message sent will establish the session.\n                    // We just need to clear the current chat display.\n                    chatContainer.innerHTML = '<div class=\"text-center text-muted mt-5\"><p>Type your edited question to start the branch.</p></div>';\n                    currentOffset = 0;\n                    window.TOTAL_MESSAGES = 0;\n                    loadSessions();\n                } else {\n                    // The backend sets the new session as active, so we just need to reload.\n                    chatContainer.innerHTML = '<div class=\"text-center text-muted mt-5\"><p>Loading forked conversation...</p></div>';\n                    await loadMessages(data.new_uuid);\n                    loadSessions();\n                }\n            } else {\n                alert('Failed to fork conversation.');\n            }\n        } catch (error) {\n            console.error('Error cloning chat:', error);\n            alert('Failed to fork chat.');\n        }\n    }\n\n    async function handleExport() {\n        const uuid = currentActiveUUID;\n        if (!uuid) {\n            alert('No active session to export.');\n            return;\n        }\n\n        let title = \"chat_export\";\n        const activeSessionItem = document.querySelector(`.session-item[data-uuid=\"${uuid}\"]`);\n        if (activeSessionItem) {\n            const titleEl = activeSessionItem.querySelector('.session-title');\n            if (titleEl) title = titleEl.textContent.trim();\n        }\n\n        try {\n            const response = await fetch(`/sessions/${uuid}/messages`);\n            if (!response.ok) throw new Error('Network response was not ok');\n            const data = await response.json();\n            const messages = data.messages || [];\n\n            let markdown = `# Chat Export: ${title}\\n\\n`;\n            messages.forEach(msg => {\n                const role = msg.role === 'user' ? 'User' : 'Gemini';\n                markdown += `## ${role}\\n\\n${msg.content}\\n\\n---\\n\\n`;\n            });\n\n            const blob = new Blob([markdown], { type: 'text/markdown' });\n            const url = URL.createObjectURL(blob);\n            const a = document.createElement('a');\n            a.href = url;\n            const safeTitle = title.replace(/[^a-z0-9]/gi, '_').substring(0, 50);\n            a.download = `${safeTitle}.md`;\n            document.body.appendChild(a);\n            a.click();\n            document.body.removeChild(a);\n            URL.revokeObjectURL(url);\n        } catch (e) {\n            console.error('Export failed:', e);\n            alert('Failed to export chat.');\n        }\n    }\n\n    if (exportBtn) exportBtn.onclick = handleExport;\n    if (exportBtnMobile) exportBtnMobile.onclick = handleExport;\n    if (resetBtn) resetBtn.onclick = handleReset;\n    if (resetBtnMobile) resetBtnMobile.onclick = handleReset;\n    const modelLinks = document.querySelectorAll('[data-model]');\n    const modelInput = document.getElementById('model-input');\n    const modelLabel = document.getElementById('model-label');\n    const patternsList = document.getElementById('patterns-list');\n    const patternSearch = document.getElementById('pattern-search');\n    const patternsModal = document.getElementById('patternsModal');\n    const sessionsList = document.getElementById('sessions-list');\n    const newChatBtn = document.getElementById('new-chat-btn');\n    const historySidebar = document.getElementById('historySidebar');\n    const toolsModal = document.getElementById('toolsModal');\n    const toolsStatus = document.getElementById('tools-status');\n    const btnApplyTools = document.getElementById('btn-apply-tools');\n    const btnDeselectAllTools = document.getElementById('btn-deselect-all-tools');\n    const toolToggles = document.querySelectorAll('.tool-toggle');\n    \n    const liveToast = document.getElementById('liveToast');\n    const toastBody = document.getElementById('toast-body');\n    const loadMoreContainer = document.getElementById('load-more-container');\n    const loadMoreBtn = document.getElementById('load-more-btn');\n    const chatWelcome = document.getElementById('chat-welcome');\n    const sessionSearch = document.getElementById('session-search');\n    const sidebarLoadMoreContainer = document.getElementById('sidebar-load-more-container');\n    const sidebarLoadMoreBtn = document.getElementById('sidebar-load-more-btn');\n    const sendBtn = document.getElementById('send-btn');\n    const stopBtn = document.getElementById('stop-btn');\n    const tagFilterContainer = document.getElementById('tag-filter-container');\n    const chatTagsHeader = document.getElementById('chat-tags-header');\n\n    // --- Plan Mode ---\n    const planModeBtn = document.getElementById('plan-mode-btn');\n    let planModeActive = false;\n\n    planModeBtn?.addEventListener('click', () => {\n        planModeActive = !planModeActive;\n        if (planModeActive) {\n            planModeBtn.classList.replace('btn-outline-warning', 'btn-warning');\n            messageInput.placeholder = \"Message Gemini in Plan Mode...\";\n            messageInput.classList.add('border-warning');\n        } else {\n            planModeBtn.classList.replace('btn-warning', 'btn-outline-warning');\n            messageInput.placeholder = \"Message Gemini...\";\n            messageInput.classList.remove('border-warning');\n        }\n    });\n\n    const taggingModal = document.getElementById('taggingModal');\n    const modalCurrentTags = document.getElementById('modal-current-tags');\n    const modalExistingTags = document.getElementById('modal-existing-tags');\n    const tagInput = document.getElementById('tag-input');\n    const btnAddTag = document.getElementById('btn-add-tag');\n    const btnSaveTags = document.getElementById('btn-save-tags');\n\n    const renameModalEl = document.getElementById('renameSessionModal');\n    const renameInput = document.getElementById('rename-input');\n    const btnSaveRename = document.getElementById('btn-save-rename');\n    let renameModal = null;\n    let currentRenameUUID = null;\n    let currentRenameTitleEl = null; // To update UI immediately\n\n    const treeViewModalEl = document.getElementById('treeViewModal');\n    const treeContainer = document.getElementById('tree-container');\n    const treeViewBtn = document.getElementById('tree-view-btn');\n    const treeViewBtnMobile = document.getElementById('tree-view-btn-mobile');\n    let treeViewModal = null;\n\n    // --- Attachment Management ---\n    const attachmentQueue = document.getElementById('attachment-queue');\n    const dragDropOverlay = document.getElementById('drag-drop-overlay');\n    \n    // --- Drive Mode ---\n    const driveModeBtn = document.getElementById('drive-mode-btn');\n    const driveMode = new DriveModeManager();\n\n    const showMicSetting = document.getElementById('setting-show-mic');\n    if (showMicSetting && window.USER_SETTINGS) {\n        showMicSetting.checked = window.USER_SETTINGS.show_mic !== false;\n        \n        showMicSetting.onchange = async () => {\n            const enabled = showMicSetting.checked;\n            try {\n                const response = await fetch('/settings', {\n                    method: 'POST',\n                    headers: { 'Content-Type': 'application/json' },\n                    body: JSON.stringify({ show_mic: enabled })\n                });\n                if (response.ok) {\n                    window.USER_SETTINGS.show_mic = enabled;\n                    updateDriveModeVisibility();\n                }\n            } catch (err) {\n                console.error('Error saving setting:', err);\n            }\n        };\n    }\n\n    const showPlanSetting = document.getElementById('setting-show-plan');\n    if (showPlanSetting && window.USER_SETTINGS) {\n        showPlanSetting.checked = window.USER_SETTINGS.show_plan === true;\n        \n        showPlanSetting.onchange = async () => {\n            const enabled = showPlanSetting.checked;\n            try {\n                const response = await fetch('/settings', {\n                    method: 'POST',\n                    headers: { 'Content-Type': 'application/json' },\n                    body: JSON.stringify({ show_plan: enabled })\n                });\n                if (response.ok) {\n                    window.USER_SETTINGS.show_plan = enabled;\n                    updatePlanModeVisibility();\n                }\n            } catch (err) {\n                console.error('Error saving setting:', err);\n            }\n        };\n    }\n\n    const copyFormattedSetting = document.getElementById('setting-copy-formatted');\n    if (copyFormattedSetting && window.USER_SETTINGS) {\n        copyFormattedSetting.checked = window.USER_SETTINGS.copy_formatted === true;\n        \n        copyFormattedSetting.onchange = async () => {\n            const enabled = copyFormattedSetting.checked;\n            try {\n                const response = await fetch('/settings', {\n                    method: 'POST',\n                    headers: { 'Content-Type': 'application/json' },\n                    body: JSON.stringify({ copy_formatted: enabled })\n                });\n                if (response.ok) {\n                    window.USER_SETTINGS.copy_formatted = enabled;\n                }\n            } catch (err) {\n                console.error('Error saving setting:', err);\n            }\n        };\n    }\n\n    function updateDriveModeVisibility() {\n        if (!driveModeBtn) return;\n        const isEnabled = window.USER_SETTINGS && window.USER_SETTINGS.show_mic !== false;\n        if (driveMode.isSupported() && isEnabled) {\n            driveModeBtn.classList.remove('d-none');\n        } else {\n            driveModeBtn.classList.add('d-none');\n        }\n    }\n    window.updateDriveModeVisibility = updateDriveModeVisibility;\n\n    function updatePlanModeVisibility() {\n        if (!planModeBtn) return;\n        const isEnabled = window.USER_SETTINGS && window.USER_SETTINGS.show_plan === true;\n        if (isEnabled) {\n            planModeBtn.classList.remove('d-none');\n        } else {\n            planModeBtn.classList.add('d-none');\n        }\n    }\n    window.updatePlanModeVisibility = updatePlanModeVisibility;\n\n    updateDriveModeVisibility();\n    updatePlanModeVisibility();\n\n    driveModeBtn?.addEventListener('click', () => {\n        if (!driveMode.isActive) {\n            startDriveMode();\n        } else {\n            stopDriveMode();\n        }\n    });\n\n    async function startDriveMode() {\n        driveMode.isActive = true;\n        driveModeBtn.classList.replace('btn-outline-info', 'btn-info');\n        driveModeBtn.innerHTML = '<i class=\"bi bi-stop-circle-fill\"></i>';\n        await driveMode.requestWakeLock();\n        runDriveModeLoop();\n    }\n\n    function stopDriveMode() {\n        driveMode.isActive = false;\n        driveMode.stopListening();\n        driveMode.stopSpeaking();\n        driveMode.releaseWakeLock();\n        driveModeBtn.classList.replace('btn-info', 'btn-outline-info');\n        driveModeBtn.innerHTML = '<i class=\"bi bi-mic-fill\"></i>';\n        driveMode.state = 'idle';\n        updateDriveModeUI();\n    }\n\n    function updateDriveModeUI() {\n        const state = driveMode.state;\n        const btn = document.getElementById('drive-mode-btn');\n        if (!btn) return;\n\n        // Reset icon and animation\n        btn.innerHTML = driveMode.isActive ? '<i class=\"bi bi-stop-circle-fill\"></i>' : '<i class=\"bi bi-mic-fill\"></i>';\n        btn.classList.remove('pulse-animation');\n\n        if (driveMode.isActive) {\n            if (state === 'listening') {\n                btn.classList.add('pulse-animation');\n                btn.style.color = '#fff';\n            } else if (state === 'processing') {\n                btn.innerHTML = '<span class=\"spinner-border spinner-border-sm\" role=\"status\" aria-hidden=\"true\"></span>';\n            } else if (state === 'speaking') {\n                btn.innerHTML = '<i class=\"bi bi-volume-up-fill\"></i>';\n            }\n        }\n    }\n\n    function runDriveModeLoop() {\n        if (!driveMode.isActive) return;\n\n        updateDriveModeUI();\n        driveMode.state = 'listening';\n        updateDriveModeUI();\n\n        driveMode.startListening(\n            async (transcript) => {\n                const cmd = transcript.toLowerCase().trim();\n                // Check for stop words\n                if (cmd === 'stop' || cmd === '\u03c3\u03c4\u03b1\u03bc\u03ac\u03c4\u03b1' || cmd === '\u03c3\u03c4\u03b1\u03bc\u03ac\u03c4\u03b1.') {\n                    console.log('Voice Command: Stop detected.');\n                    stopDriveMode();\n                    driveMode.speak(cmd === 'stop' ? 'Stopping drive mode.' : '\u03a4\u03b5\u03c1\u03bc\u03b1\u03c4\u03b9\u03c3\u03bc\u03cc\u03c2 drive mode.');\n                    return;\n                }\n\n                // onResult\n                driveMode.state = 'processing';\n                updateDriveModeUI();\n                \n                // Add user message to chat UI using standard method\n                const userMsgIndex = window.TOTAL_MESSAGES || 0;\n                appendMessage('user', transcript, null, null, userMsgIndex);\n                window.TOTAL_MESSAGES = userMsgIndex + 1;\n\n                // Send to AI\n                try {\n                    const loadingObj = appendLoading();\n                    toggleStopButton(true);\n\n                    const formData = new FormData();\n                    formData.append('message', transcript);\n                    formData.append('model', document.getElementById('model-input').value);\n\n                    const response = await fetch('/chat', {\n                        method: 'POST',\n                        body: formData\n                    });\n\n                    if (!response.ok) throw new Error('Chat request failed');\n\n                    // Process stream using NATIVE function for reliability\n                    await processStream(response, loadingObj.id);\n                    \n                    if (!driveMode.isActive) return;\n\n                    // Capture the text from the message we just created\n                    const lastBotMsg = chatContainer.querySelector('.message.bot:last-child .message-content');\n                    const aiResponse = lastBotMsg ? lastBotMsg.innerText : \"\";\n\n                    driveMode.state = 'speaking';\n                    updateDriveModeUI();\n\n                    driveMode.speak(aiResponse, () => {\n                        // onEnd\n                        if (driveMode.isActive) {\n                            setTimeout(runDriveModeLoop, 500); // Small delay before restart\n                        }\n                    });\n                } catch (err) {\n                    console.error('Drive Mode AI Error:', err);\n                    if (driveMode.isActive) {\n                        driveMode.speak('\u03a3\u03c6\u03ac\u03bb\u03bc\u03b1 \u03b5\u03c0\u03b9\u03ba\u03bf\u03b9\u03bd\u03c9\u03bd\u03af\u03b1\u03c2. \u039e\u03b1\u03bd\u03b1\u03c0\u03c1\u03bf\u03c3\u03c0\u03b1\u03b8\u03ce.', () => {\n                            setTimeout(runDriveModeLoop, 2000);\n                        });\n                    }\n                } finally {\n                    toggleStopButton(false);\n                }\n            },\n            (error) => {\n                // onError\n                console.warn('Drive Mode STT Error:', error);\n                if (driveMode.isActive) {\n                    if (error === 'no-speech') {\n                        // Silent retry\n                        setTimeout(runDriveModeLoop, 1000);\n                    } else {\n                        driveMode.state = 'idle';\n                        updateDriveModeUI();\n                        // Possible permanent error, but let's try to recover once\n                        setTimeout(runDriveModeLoop, 3000);\n                    }\n                }\n            }\n        );\n    }\n\n    // Remove the redundant processStreamWithCapture to prevent scope issues\n    async function sendToAI(text) {\n        // Prepare data\n        const formData = new FormData();\n        formData.append('message', text);\n        formData.append('model', document.getElementById('model-input').value);\n\n        const response = await fetch('/chat', {\n            method: 'POST',\n            body: formData\n        });\n\n        if (!response.ok) throw new Error('Chat request failed');\n\n        // Since it's a streaming response usually, we need to handle it.\n        // For Drive Mode, we want the FULL text to speak it.\n        // We'll use a modified logic or wait for completion.\n        const reader = response.body.getReader();\n        const decoder = new TextDecoder();\n        let fullText = '';\n\n        while (true) {\n            const { done, value } = await reader.read();\n            if (done) break;\n            const chunk = decoder.decode(value, { stream: true });\n            \n            // Extract text from SSE format \"data: ...\"\n            const lines = chunk.split('\\n');\n            for (const line of lines) {\n                if (line.startsWith('data: ')) {\n                    try {\n                        const data = JSON.parse(line.substring(6));\n                        if (data.type === 'text') {\n                            fullText += data.content;\n                        } else if (data.type === 'error') {\n                            throw new Error(data.content);\n                        }\n                    } catch (e) {\n                        // Ignore partial JSON or other types\n                    }\n                }\n            }\n        }\n        return fullText;\n    }\n\n    const attachments = new AttachmentManager({\n        maxTotalSize: 20 * 1024 * 1024, // 20MB\n        onQueueChange: (items) => renderAttachmentQueue(items),\n        onSizeLimitExceeded: (fileName) => {\n            showToast(`Size limit exceeded: ${fileName} was not added.`);\n        }\n    });\n\n    function renderAttachmentQueue(items) {\n        if (!attachmentQueue) return;\n        attachmentQueue.innerHTML = items.map(item => {\n            const isImage = item.type.startsWith('image/');\n            return `\n                <div class=\"attachment-item position-relative bg-secondary bg-opacity-25 rounded p-1 d-flex align-items-center gap-2\" style=\"max-width: 200px; border: 1px solid rgba(255,255,255,0.1);\">\n                    ${isImage ? \n                        `<img src=\"${item.previewUrl}\" class=\"rounded\" style=\"width: 40px; height: 40px; object-fit: cover;\">` :\n                        `<div class=\"bg-dark rounded d-flex align-items-center justify-content-center\" style=\"width: 40px; height: 40px;\"><i class=\"bi bi-file-earmark\"></i></div>`\n                    }\n                    <div class=\"flex-grow-1 overflow-hidden\">\n                        <div class=\"small text-truncate\" title=\"${item.name}\">${item.name}</div>\n                        <div class=\"text-muted\" style=\"font-size: 0.6rem;\">${(item.size / 1024).toFixed(1)} KB</div>\n                    </div>\n                    <button type=\"button\" class=\"btn-close btn-close-white small p-1\" style=\"font-size: 0.5rem;\" onclick=\"window.removeAttachment('${item.id}')\"></button>\n                </div>\n            `;\n        }).join('');\n    }\n\n    window.removeAttachment = (id) => {\n        attachments.removeAttachment(id);\n    };\n\n    // --- Drag and Drop ---\n    if (chatContainer && dragDropOverlay) {\n        let dragCounter = 0;\n\n        window.addEventListener('dragenter', (e) => {\n            e.preventDefault();\n            dragCounter++;\n            dragDropOverlay.classList.remove('d-none');\n        });\n\n        window.addEventListener('dragleave', (e) => {\n            e.preventDefault();\n            dragCounter--;\n            if (dragCounter === 0) {\n                dragDropOverlay.classList.add('d-none');\n            }\n        });\n\n        window.addEventListener('dragover', (e) => {\n            e.preventDefault();\n        });\n\n        window.addEventListener('drop', async (e) => {\n            e.preventDefault();\n            dragCounter = 0;\n            dragDropOverlay.classList.add('d-none');\n            \n            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {\n                await attachments.addFiles(e.dataTransfer.files);\n                // Auto-switch to Gemini 3 Flash Preview for better vision support\n                switchToFlashModel();\n            }\n        });\n    }\n\n    function switchToFlashModel() {\n        const flashModel = \"gemini-3-flash-preview\";\n        modelInput.value = flashModel;\n        modelLinks.forEach(link => {\n            if (link.dataset.model === flashModel) {\n                link.classList.add('active');\n                let modelName = link.innerText;\n                modelName = modelName.replace('Fast', '').replace('Smart', '').trim();\n                modelLabel.textContent = modelName + \" (Auto-switched)\";\n            } else {\n                link.classList.remove('active');\n            }\n        });\n    }\n\n    if (treeViewModalEl) {\n        treeViewModal = new bootstrap.Modal(treeViewModalEl);\n        \n        const openTree = async () => {\n            treeContainer.innerHTML = '<div class=\"text-center p-5\"><div class=\"spinner-border text-info\" role=\"status\"></div><p class=\"mt-2\">Building conversation tree...</p></div>';\n            treeViewModal.show();\n            \n            try {\n                // Fetch full fork graph for the user\n                const graphRes = await fetch(`/sessions/fork-graph`);\n                const graphData = await graphRes.json();\n                const graph = graphData.graph; // { uuid: { parent, fork_point, title } }\n\n                renderGraph(graph, currentActiveUUID);\n\n            } catch (error) {\n                console.error('Error building tree:', error);\n                treeContainer.innerHTML = `<div class=\"alert alert-danger\">Failed to build tree: ${error.message}</div>`;\n            }\n        };\n\n        if (treeViewBtn) treeViewBtn.onclick = openTree;\n        if (treeViewBtnMobile) treeViewBtnMobile.onclick = openTree;\n    }\n\n    function renderGraph(graph, activeUUID) {\n        treeContainer.innerHTML = '';\n        \n        if (!activeUUID || !graph[activeUUID]) {\n            treeContainer.innerHTML = '<div class=\"alert alert-info\">No related forks found for this conversation.</div>';\n            return;\n        }\n\n        // Find the root of the current session's tree\n        let rootUUID = activeUUID;\n        let visited = new Set();\n        while (graph[rootUUID] && graph[rootUUID].parent && !visited.has(rootUUID)) {\n            visited.add(rootUUID);\n            rootUUID = graph[rootUUID].parent;\n        }\n\n        const treeRoot = document.createElement('div');\n        treeRoot.className = 'tree-view';\n        treeRoot.appendChild(createTreeNode(rootUUID, graph, activeUUID));\n\n        treeContainer.appendChild(treeRoot);\n    }\n\n    function createTreeNode(uuid, graph, activeUUID) {\n        const node = graph[uuid];\n        const div = document.createElement('div');\n        div.className = 'tree-node-wrapper';\n        \n        const content = document.createElement('div');\n        content.className = `tree-node p-2 mb-3 rounded border ${uuid === activeUUID ? 'bg-primary text-white shadow-lg border-light' : 'bg-dark text-light border-secondary'}`;\n        content.style.cursor = 'pointer';\n        content.style.maxWidth = '280px';\n        content.style.transition = 'all 0.2s';\n        content.style.borderRadius = '15px';\n        \n        const header = document.createElement('div');\n        header.className = 'tree-node-header mb-1 small text-info d-flex align-items-center gap-1';\n        \n        const forkIcon = `<svg width=\"14\" height=\"14\" fill=\"currentColor\" viewBox=\"0 0 16 16\" style=\"margin-top: -2px;\"><path d=\"M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 2.25 0 1 1 1.5 0v.878a2.25 2.25 0 0 1-2.25 2.25h-1.5v2.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25v-.878a2.25 2.25 0 1 1 1.5 0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z\"></path></svg>`;\n        header.innerHTML = node.parent ? forkIcon : `<i class=\"bi bi-chat-left-text\"></i>`;\n        \n        const title = document.createElement('div');\n        title.className = 'fw-bold text-truncate flex-grow-1';\n        title.style.fontSize = '0.85rem';\n        title.textContent = node.title || 'Untitled Chat';\n        header.appendChild(title);\n        \n        const meta = document.createElement('div');\n        meta.className = `small ${uuid === activeUUID ? 'text-white-50' : 'text-muted'}`;\n        meta.style.fontSize = '0.7rem';\n        if (node.parent) {\n            meta.textContent = `Forked at msg #${node.fork_point + 1}`;\n        } else {\n            meta.textContent = 'Root Conversation';\n        }\n        \n        content.appendChild(header);\n        content.appendChild(meta);\n        \n        content.onclick = () => {\n            if (uuid !== activeUUID) {\n                switchSession(uuid);\n                treeViewModal.hide();\n            }\n        };\n\n        // Hover effect\n        content.onmouseover = () => { \n            content.style.transform = 'scale(1.02)';\n            if (uuid !== activeUUID) content.classList.add('border-primary'); \n        };\n        content.onmouseout = () => { \n            content.style.transform = 'scale(1)';\n            if (uuid !== activeUUID) content.classList.remove('border-primary'); \n        };\n\n        div.appendChild(content);\n\n        // Children - sort them by fork point\n        const children = Object.keys(graph).filter(u => graph[u].parent === uuid);\n        children.sort((a, b) => (graph[a].fork_point || 0) - (graph[b].fork_point || 0));\n\n        if (children.length > 0) {\n            const childrenContainer = document.createElement('div');\n            childrenContainer.className = 'tree-children ms-4 ps-3 border-start border-secondary';\n            children.forEach(childUUID => {\n                childrenContainer.appendChild(createTreeNode(childUUID, graph, activeUUID));\n            });\n            div.appendChild(childrenContainer);\n        }\n\n        return div;\n    }\n\n    if (renameModalEl) {\n        renameModal = new bootstrap.Modal(renameModalEl);\n        \n        renameModalEl.addEventListener('shown.bs.modal', () => {\n            renameInput.focus();\n        });\n\n        if (btnSaveRename) {\n            btnSaveRename.addEventListener('click', async () => {\n                const newTitle = renameInput.value.trim();\n                if (!newTitle || !currentRenameUUID) return;\n                \n                try {\n                    const response = await fetch(`/sessions/${currentRenameUUID}/title`, {\n                        method: 'POST',\n                        headers: { 'Content-Type': 'application/json' },\n                        body: JSON.stringify({ title: newTitle })\n                    });\n                    const data = await response.json();\n                    if (data.success) {\n                        if (currentRenameTitleEl) currentRenameTitleEl.textContent = newTitle;\n                        showToast('Chat renamed');\n                        renameModal.hide();\n                    } else {\n                        alert('Failed to rename chat: ' + (data.error || 'Unknown error'));\n                    }\n                } catch (error) {\n                    console.error('Error renaming session:', error);\n                    alert('Failed to rename chat.');\n                }\n            });\n        }\n    }\n\n    let currentFile = null;\n    let allPatterns = [];\n    let currentOffset = 0;\n    let sidebarOffset = 0;\n    const PAGE_LIMIT = 20;\n    const SIDEBAR_PAGE_LIMIT = 10;\n    let isLoadingHistory = false;\n    let isLoadingSidebar = false;\n\n    let activeTags = new Set();\n    let allUniqueTags = [];\n    let currentForkMap = {}; // index -> [uuids]\n    let currentActiveUUID = window.ACTIVE_SESSION_UUID || null;\n\n    function toggleStopButton(show) {\n        if (show) {\n            sendBtn.classList.add('d-none');\n            stopBtn.classList.remove('d-none');\n        } else {\n            sendBtn.classList.remove('d-none');\n            stopBtn.classList.add('d-none');\n        }\n    }\n\n    if (stopBtn) {\n        stopBtn.addEventListener('click', async () => {\n            if (driveMode.isActive) {\n                stopDriveMode();\n            }\n            try {\n                const response = await fetch('/stop', { method: 'POST' });\n                if (response.ok) {\n                    toggleStopButton(false);\n                }\n            } catch (error) {\n                console.error('Error stopping chat:', error);\n            }\n        });\n    }\n\n    function showToast(message) {\n        if (!liveToast) return;\n        toastBody.textContent = message;\n        const toast = new bootstrap.Toast(liveToast);\n        toast.show();\n    }\n\n    async function fetchUniqueTags() {\n        try {\n            const response = await fetch('/sessions/tags');\n            const data = await response.json();\n            allUniqueTags = data.tags || [];\n            renderTagFilters();\n        } catch (error) {\n            console.error('Error fetching tags:', error);\n        }\n    }\n\n    async function fetchForks(uuid) {\n        try {\n            const response = await fetch(`/sessions/${uuid}/forks`);\n            const data = await response.json();\n            currentForkMap = data.forks || {};\n        } catch (error) {\n            console.error('Error fetching forks:', error);\n            currentForkMap = {};\n        }\n    }\n\n    function renderTagFilters() {\n        if (!tagFilterContainer) return;\n        if (!allUniqueTags || allUniqueTags.length === 0) {\n            tagFilterContainer.innerHTML = '';\n            return;\n        }\n\n        tagFilterContainer.innerHTML = allUniqueTags.map(tag => `\n            <span class=\"tag-badge ${activeTags.has(tag) ? 'selected' : ''}\" data-tag=\"${tag}\">${tag}</span>\n        `).join('');\n\n        tagFilterContainer.querySelectorAll('.tag-badge').forEach(badge => {\n            badge.onclick = () => toggleTagFilter(badge.dataset.tag);\n        });\n    }\n\n    function toggleTagFilter(tag) {\n        if (activeTags.has(tag)) {\n            activeTags.delete(tag);\n        } else {\n            activeTags.add(tag);\n        }\n        renderTagFilters();\n        sidebarOffset = 0;\n        loadSessions(false);\n    }\n\n    async function updateSessionTags(uuid, tags) {\n        try {\n            const response = await fetch(`/sessions/${uuid}/tags`, {\n                method: 'POST',\n                headers: { 'Content-Type': 'application/json' },\n                body: JSON.stringify({ tags })\n            });\n            const data = await response.json();\n            if (data.success) {\n                fetchUniqueTags();\n                loadSessions(false);\n                return true;\n            }\n        } catch (error) {\n            console.error('Error updating tags:', error);\n        }\n        return false;\n    }\n\n    function renderChatTags(session) {\n        const headerContainer = document.getElementById('chat-tags-header');\n        const sidebarContainer = document.getElementById('chat-tags-sidebar');\n        if (!headerContainer || !sidebarContainer) return;\n\n        if (!session || !session.uuid) {\n            headerContainer.innerHTML = '';\n            sidebarContainer.innerHTML = '';\n            return;\n        }\n\n        const tags = session.tags || [];\n        const isMobile = window.innerWidth < 768;\n\n        let html = tags.map(tag => `<span class=\"tag-badge selected\">${tag}</span>`).join('');\n        html += `<span class=\"tag-badge add-tag-btn\" title=\"Edit Tags\"><i class=\"bi bi-plus\"></i> Tags</span>`;\n\n        if (isMobile) {\n            headerContainer.innerHTML = '';\n            sidebarContainer.innerHTML = html;\n        } else {\n            sidebarContainer.innerHTML = '';\n            headerContainer.innerHTML = html;\n        }\n\n        // Clicking on tags or the add button opens the modal\n        const targetContainer = isMobile ? sidebarContainer : headerContainer;\n        const allBadges = targetContainer.querySelectorAll('.tag-badge');\n        allBadges.forEach(badge => {\n            badge.onclick = () => {\n                let modalInstance = bootstrap.Modal.getInstance(taggingModal);\n                if (!modalInstance) {\n                    modalInstance = new bootstrap.Modal(taggingModal);\n                }\n\n                let workingTags = [...tags];\n\n                function renderModalTags() {\n                    modalCurrentTags.innerHTML = workingTags.map(t => `\n                        <span class=\"tag-badge selected\" data-tag=\"${t}\">${t} <i class=\"bi bi-x ms-1 remove-tag\"></i></span>\n                    `).join('');\n\n                    modalCurrentTags.querySelectorAll('.remove-tag').forEach(btn => {\n                        btn.onclick = (e) => {\n                            e.stopPropagation();\n                            const tagToRemove = btn.parentElement.dataset.tag;\n                            workingTags = workingTags.filter(t => t !== tagToRemove);\n                            renderModalTags();\n                        };\n                    });\n\n                    // Render existing tags suggestions\n                    modalExistingTags.innerHTML = allUniqueTags\n                        .filter(t => !workingTags.includes(t))\n                        .map(t => `<span class=\"tag-badge\" data-tag=\"${t}\">${t}</span>`)\n                        .join('');\n\n                    modalExistingTags.querySelectorAll('.tag-badge').forEach(badge => {\n                        badge.onclick = () => {\n                            workingTags.push(badge.dataset.tag);\n                            renderModalTags();\n                        };\n                    });\n                }\n\n                renderModalTags();\n                tagInput.value = '';\n\n                function addTagFromInput() {\n                    const rawVal = tagInput.value.trim();\n                    if (!rawVal) return;\n\n                    // Support comma-separated tags\n                    const newTags = rawVal.split(',').map(t => t.trim()).filter(t => t !== '');\n                    let added = false;\n\n                    newTags.forEach(val => {\n                        if (!workingTags.includes(val)) {\n                            workingTags.push(val);\n                            added = true;\n                        }\n                    });\n\n                    if (added) {\n                        tagInput.value = '';\n                        renderModalTags();\n                    }\n                }\n\n                tagInput.onkeydown = (e) => {\n                    if (e.key === 'Enter' || e.key === ',') {\n                        e.preventDefault();\n                        addTagFromInput();\n                    }\n                };\n\n                if (btnAddTag) {\n                    btnAddTag.onclick = (e) => {\n                        e.preventDefault();\n                        addTagFromInput();\n                    };\n                }\n\n                btnSaveTags.onclick = async () => {\n                    if (await updateSessionTags(session.uuid, workingTags)) {\n                        session.tags = workingTags;\n                        renderChatTags(session);\n                        modalInstance.hide();\n                    }\n                };\n\n                modalInstance.show();\n            };\n        });\n    }\n\n    function debounce(func, timeout = 300) {\n        let timer;\n        return (...args) => {\n            clearTimeout(timer);\n            timer = setTimeout(() => { func.apply(this, args); }, timeout);\n        };\n    }\n\n    // Handle Tools Modal show\n    toolsModal.addEventListener('show.bs.modal', async () => {\n        // Find the active session UUID\n        const activeSessionItem = document.querySelector('.session-item.active-session');\n        let uuid = \"pending\";\n        if (activeSessionItem) {\n            uuid = activeSessionItem.dataset.uuid;\n        }\n\n        toolsStatus.textContent = 'Loading settings...';\n        toolsStatus.className = 'mt-2 small text-muted';\n\n        // Reset toggles first\n        toolToggles.forEach(t => t.checked = false);\n\n        try {\n            const response = await fetch(`/sessions/${uuid}/tools`);\n            if (!response.ok) throw new Error(`HTTP ${response.status}`);\n            const data = await response.json();\n            \n            if (data.tools) {\n                data.tools.forEach(toolName => {\n                    const toggle = document.querySelector(`.tool-toggle[value=\"${toolName}\"]`);\n                    if (toggle) toggle.checked = true;\n                });\n            }\n            toolsStatus.textContent = '';\n        } catch (error) {\n            console.error('Error loading tool settings:', error);\n            toolsStatus.textContent = 'Failed to load settings.';\n            toolsStatus.className = 'mt-2 small text-danger';\n        }\n    });\n\n    btnApplyTools.addEventListener('click', async () => {\n        const activeSessionItem = document.querySelector('.session-item.active-session');\n        let uuid = \"pending\";\n        if (activeSessionItem) {\n            uuid = activeSessionItem.dataset.uuid;\n        }\n\n        const selectedTools = Array.from(toolToggles)\n            .filter(t => t.checked)\n            .map(t => t.value);\n\n        toolsStatus.textContent = 'Saving settings...';\n        toolsStatus.className = 'mt-2 small text-muted';\n\n        try {\n            const response = await fetch(`/sessions/${uuid}/tools`, {\n                method: 'POST',\n                headers: { 'Content-Type': 'application/json' },\n                body: JSON.stringify({ tools: selectedTools })\n            });\n            if (!response.ok) throw new Error(`HTTP ${response.status}`);\n            const data = await response.json();\n            if (data.success) {\n                toolsStatus.textContent = 'Settings applied successfully!';\n                toolsStatus.className = 'mt-2 small text-success';\n                setTimeout(() => {\n                    const modalInstance = bootstrap.Modal.getInstance(toolsModal);\n                    if (modalInstance) modalInstance.hide();\n                }, 1000);\n            }\n        } catch (error) {\n            console.error('Error saving tool settings:', error);\n            toolsStatus.textContent = 'Failed to save settings.';\n            toolsStatus.className = 'mt-2 small text-danger';\n        }\n    });\n\n    btnDeselectAllTools.addEventListener('click', () => {\n        toolToggles.forEach(t => t.checked = false);\n    });\n\n    const btnSafeToolsOnly = document.getElementById('btn-safe-tools-only');\n    const btnAllExceptMemory = document.getElementById('btn-all-except-memory');\n\n    const safeToolNames = [\n        'list_directory', 'read_file', 'glob', 'grep_search', \n        'google_web_search', 'web_fetch', 'cli_help', 'ask_user', 'confirm_output'\n    ];\n\n    btnSafeToolsOnly?.addEventListener('click', () => {\n        toolToggles.forEach(t => {\n            t.checked = safeToolNames.includes(t.value);\n        });\n    });\n\n    btnAllExceptMemory?.addEventListener('click', () => {\n        toolToggles.forEach(t => {\n            t.checked = (t.value !== 'save_memory');\n        });\n    });\n\n    if (loadMoreBtn) {\n        loadMoreBtn.addEventListener('click', () => {\n            const activeSessionItem = document.querySelector('.session-item.active-session');\n            if (activeSessionItem) {\n                loadMessages(activeSessionItem.dataset.uuid, PAGE_LIMIT, currentOffset);\n            }\n        });\n    }\n\n    if (sessionSearch) {\n        sessionSearch.addEventListener('input', debounce(() => {\n            if (sessionSearch.value.trim() !== \"\") {\n                activeTags.clear();\n                renderTagFilters();\n            }\n            loadSessions();\n        }, 300));\n    }\n\n    if (sidebarLoadMoreBtn) {\n        sidebarLoadMoreBtn.addEventListener('click', () => {\n            sidebarOffset += SIDEBAR_PAGE_LIMIT;\n            loadSessions(true);\n        });\n    }\n\n    // Load sessions when sidebar is shown\n    historySidebar.addEventListener('show.bs.offcanvas', () => loadSessions());\n\n    // Load sessions on page load\n    fetchUniqueTags();\n    loadSessions();\n\n    // Initial load from server-side messages\n    if (window.INITIAL_MESSAGES && window.INITIAL_MESSAGES.length > 0) {\n        if (chatWelcome) chatWelcome.classList.add('d-none');\n        window.INITIAL_MESSAGES.forEach((msg, idx) => {\n            const index = (msg.raw_index !== undefined) ? msg.raw_index : idx;\n            const msgDiv = createMessageDiv(msg.role, msg.content, null, null, index);\n            if (msgDiv) chatContainer.appendChild(msgDiv);\n        });\n        chatContainer.scrollTop = chatContainer.scrollHeight;\n        currentOffset = 20; // Default limit used in index route\n        window.HAS_INITIAL_MESSAGES = true;\n    }\n\n    \n    async function loadMessages(uuid, limit = PAGE_LIMIT, offset = 0, isAutoRestore = false) {\n        if (isLoadingHistory) return;\n        if (offset > 0) isLoadingHistory = true;\n\n        if (offset === 0) {\n            currentActiveUUID = uuid;\n            await fetchForks(uuid);\n        }\n\n        try {\n            const response = await fetch(`/sessions/${uuid}/messages?limit=${limit}&offset=${offset}`);\n            if (!response.ok) throw new Error(`HTTP ${response.status}`);\n            const data = await response.json();\n            const messages = data.messages || [];\n            const total = data.total || 0;\n            \n            if (offset === 0) {\n                // Clear existing messages only if it's the first page\n                chatContainer.innerHTML = '<div id=\"scroll-sentinel\" style=\"height: 10px; width: 100%;\"></div>';\n                currentOffset = 0;\n                window.TOTAL_MESSAGES = total; // Update global\n                if (chatWelcome) chatWelcome.classList.add('d-none');\n            }\n\n            if (messages.length > 0) {\n                if (offset === 0) {\n                    messages.forEach((msg, idx) => {\n                        const index = (msg.raw_index !== undefined) ? msg.raw_index : idx;\n                        const msgDiv = createMessageDiv(msg.role, msg.content, null, null, index);\n                        if (msgDiv) chatContainer.appendChild(msgDiv);\n                    });\n                    chatContainer.scrollTop = chatContainer.scrollHeight;\n                } else {\n                    // Prepend for \"Load More\"\n                    const scrollHeightBefore = chatContainer.scrollHeight;\n                    \n                    const sentinel = document.getElementById('scroll-sentinel');\n                    const loadMore = document.getElementById('load-more-container');\n                    const originalFirstMessage = loadMore ? loadMore.nextSibling : (sentinel ? sentinel.nextSibling : chatContainer.firstChild);\n\n                    // If total is 100, offset is 20, limit is 20.\n                    // We loaded messages 60 to 79 (total - offset - limit to total - offset)\n                    // The index of the first message in this chunk is total - offset - messages.length\n                    const baseIndex = total - offset - messages.length;\n\n                    messages.forEach((msg, idx) => {\n                        const index = (msg.raw_index !== undefined) ? msg.raw_index : (baseIndex + idx);\n                        const msgDiv = createMessageDiv(msg.role, msg.content, null, null, index); \n                        if (msgDiv) {\n                            chatContainer.insertBefore(msgDiv, originalFirstMessage);\n                        }\n                    });\n                    \n                    chatContainer.scrollTop = chatContainer.scrollHeight - scrollHeightBefore;\n                }\n                \n                currentOffset = offset + limit;\n                \n                // Show/Hide Load More\n                if (currentOffset < total) {\n                    if (loadMoreContainer) loadMoreContainer.classList.remove('d-none');\n                } else {\n                    if (loadMoreContainer) loadMoreContainer.classList.add('d-none');\n                }\n\n                if (isAutoRestore) {\n                    showToast('Resumed last session');\n                }\n            } else {\n                if (offset === 0) {\n                    if (chatWelcome) chatWelcome.classList.remove('d-none');\n                }\n                if (loadMoreContainer) loadMoreContainer.classList.add('d-none');\n            }\n        } catch (error) {\n            console.error('Error loading messages:', error);\n        } finally {\n            isLoadingHistory = false;\n        }\n    }\n\n    async function loadSessions(append = false) {\n        if (isLoadingSidebar) return;\n        if (!append) sidebarOffset = 0;\n        \n        let query = \"\";\n        if (sessionSearch) {\n            query = sessionSearch.value.trim();\n        }\n        \n        let url = `/sessions?limit=${SIDEBAR_PAGE_LIMIT}&offset=${sidebarOffset}`;\n        \n        if (activeTags.size > 0) {\n            url += `&tags=${encodeURIComponent(Array.from(activeTags).join(','))}`;\n        }\n        \n        if (query) {\n            url = `/sessions/search?q=${encodeURIComponent(query)}`;\n        }\n\n        try {\n            isLoadingSidebar = true;\n            const response = await fetch(url);\n            if (!response.ok) throw new Error(`HTTP ${response.status}`);\n            const data = await response.json();\n            \n            let sessions = [];\n            let pinned = [];\n            let history = [];\n            let totalUnpinned = 0;\n\n            if (Array.isArray(data)) {\n                sessions = data;\n                history = data;\n            } else {\n                pinned = data.pinned || [];\n                history = data.history || [];\n                totalUnpinned = data.total_unpinned || 0;\n                sessions = pinned.concat(history);\n            }\n\n            // Auto-create if none and not searching\n            if (!query && !append && sessions.length === 0) {\n                const newRes = await fetch('/sessions/new', { method: 'POST' });\n                if (newRes.ok) {\n                    loadSessions();\n                    return;\n                }\n            }\n\n            try {\n                if (append) {\n                    renderSessions(history, true);\n                } else {\n                    renderSessions(sessions, false);\n                }\n            } catch (renderError) {\n                console.error('Error rendering sessions:', renderError);\n            }\n            \n            // Handle Load More visibility\n            if (query) {\n                if (sidebarLoadMoreContainer) sidebarLoadMoreContainer.classList.add('d-none');\n            } else {\n                if (history.length === SIDEBAR_PAGE_LIMIT && (sidebarOffset + SIDEBAR_PAGE_LIMIT) < totalUnpinned) {\n                    if (sidebarLoadMoreContainer) sidebarLoadMoreContainer.classList.remove('d-none');\n                } else {\n                    if (sidebarLoadMoreContainer) sidebarLoadMoreContainer.classList.add('d-none');\n                }\n            }\n\n            const activeSession = sessions.find(s => s.active);\n            try {\n                renderChatTags(activeSession);\n            } catch (tagError) {\n                console.error('Error rendering chat tags:', tagError);\n            }\n            \n            // Check if we need to auto-load (only on initial load)\n            if (!append && !query) {\n                const hasMessages = chatContainer.querySelectorAll('.message').length > 0;\n                if (activeSession && !hasMessages && !window.HAS_INITIAL_MESSAGES) {\n                     loadMessages(activeSession.uuid, PAGE_LIMIT, 0, true);\n                }\n            }\n        } catch (error) {\n            console.error('Error loading sessions:', error);\n            if (sessionsList && !append) sessionsList.innerHTML = `<div class=\"alert alert-danger mx-3 mt-3\">Failed to load history: ${error.message}</div>`;\n        } finally {\n            isLoadingSidebar = false;\n        }\n    }\n\n    function renderSessions(data, append = false) {\n        const pinnedList = document.getElementById('pinned-sessions-list');\n        const historyList = document.getElementById('history-sessions-list');\n        const pinnedHeader = document.getElementById('pinned-sessions-header');\n        const historyHeader = document.getElementById('history-sessions-header');\n        const initialLoader = document.getElementById('sidebar-initial-loader');\n\n        if (initialLoader) initialLoader.remove();\n\n        let pinned = [];\n        let history = [];\n\n        if (Array.isArray(data)) {\n            // Fallback for search results or legacy\n            history = data;\n        } else {\n            pinned = data.pinned || [];\n            history = data.history || [];\n        }\n\n        const createSessionHTML = (s) => `\n            <div class=\"list-group-item list-group-item-action bg-dark text-light session-item ${(s.active || s.has_active_fork) ? 'active-session' : ''}\" data-uuid=\"${s.uuid}\">\n                <div class=\"d-flex justify-content-between align-items-start\">\n                    <div class=\"flex-grow-1 overflow-hidden\">\n                        <span class=\"session-title text-truncate\">${s.title || 'Untitled Chat'}</span>\n                        <div class=\"session-tags-list\">\n                            ${(s.tags || []).map(t => `<span class=\"session-tag-item\">${t}</span>`).join('')}\n                        </div>\n                        <span class=\"session-time\">${s.time || ''}</span>\n                    </div>\n                    <div class=\"d-flex align-items-center gap-1\">\n                        ${(s.active || s.has_active_fork) ? '<span class=\"badge bg-primary rounded-pill small me-1\">Active</span>' : ''}\n                        <button class=\"btn btn-sm pin-btn border-0 ${s.pinned ? 'pinned' : ''}\" data-uuid=\"${s.uuid}\" title=\"${s.pinned ? 'Unpin Chat' : 'Pin Chat'}\">\n                            <i class=\"bi ${s.pinned ? 'bi-pin-fill' : 'bi-pin'}\"></i>\n                        </button>\n                        <button class=\"btn btn-sm rename-session-btn border-0\" data-uuid=\"${s.uuid}\" title=\"Rename Chat\">\n                            <i class=\"bi bi-pencil\"></i>\n                        </button>\n                        <button class=\"btn btn-sm btn-outline-danger border-0 delete-session-btn\" data-uuid=\"${s.uuid}\" title=\"Delete Chat\">\n                            <i class=\"bi bi-trash\"></i>\n                        </button>\n                    </div>\n                </div>\n            </div>\n        `;\n\n        if (!append) {\n            pinnedList.innerHTML = pinned.map(createSessionHTML).join('');\n            historyList.innerHTML = history.map(createSessionHTML).join('');\n            \n            if (pinned.length > 0) {\n                pinnedHeader.classList.remove('d-none');\n            } else {\n                pinnedHeader.classList.add('d-none');\n            }\n\n            if (history.length > 0 || pinned.length > 0) {\n                historyHeader.classList.remove('d-none');\n            } else {\n                historyHeader.classList.add('d-none');\n                historyList.innerHTML = '<div class=\"text-center p-3 text-muted\">No history found.</div>';\n            }\n        } else {\n            historyList.insertAdjacentHTML('beforeend', history.map(createSessionHTML).join(''));\n        }\n\n        attachSessionListeners();\n    }\n\n    async function renameSession(uuid, newTitle, titleSpan) {\n        try {\n            const response = await fetch(`/sessions/${uuid}/title`, {\n                method: 'POST',\n                headers: { 'Content-Type': 'application/json' },\n                body: JSON.stringify({ title: newTitle })\n            });\n            const data = await response.json();\n            if (data.success) {\n                titleSpan.textContent = newTitle;\n                showToast('Chat renamed');\n            } else {\n                alert('Failed to rename chat: ' + (data.error || 'Unknown error'));\n            }\n        } catch (error) {\n            console.error('Error renaming session:', error);\n            alert('Failed to rename chat.');\n        }\n    }\n\n    async function switchSession(uuid) {\n        try {\n            const formData = new FormData();\n            formData.append('session_uuid', uuid);\n            const response = await fetch('/sessions/switch', {\n                method: 'POST',\n                body: formData\n            });\n            const data = await response.json();\n            if (data.success) {\n                chatContainer.innerHTML = '<div class=\"text-center text-muted mt-5\"><p>Loading conversation...</p></div>';\n                await loadMessages(uuid);\n                const historyEl = document.getElementById('historySidebar');\n                const offcanvas = bootstrap.Offcanvas.getInstance(historyEl);\n                if (offcanvas) offcanvas.hide();\n                loadSessions();\n            }\n        } catch (error) {\n            console.error('Error switching session:', error);\n            alert('Failed to switch session.');\n        }\n    }\n\n    function attachSessionListeners() {\n        document.querySelectorAll('.session-item').forEach(item => {\n            item.onclick = async (e) => {\n                if (e.target.closest('button')) return;\n\n                const uuid = item.dataset.uuid;\n                if (item.classList.contains('active-session')) {\n                    bootstrap.Offcanvas.getInstance(historySidebar).hide();\n                    return;\n                }\n                \n                await switchSession(uuid);\n            };\n        });\n\n        document.querySelectorAll('.pin-btn').forEach(btn => {\n            btn.onclick = async (e) => {\n                e.stopPropagation();\n                const uuid = btn.dataset.uuid;\n                try {\n                    const response = await fetch(`/sessions/${uuid}/pin`, { method: 'POST' });\n                    const data = await response.json();\n                    loadSessions();\n                } catch (error) {\n                    console.error('Error pinning session:', error);\n                }\n            };\n        });\n\n        document.querySelectorAll('.rename-session-btn').forEach(btn => {\n            btn.onclick = (e) => {\n                e.stopPropagation();\n                const uuid = btn.dataset.uuid;\n                const item = btn.closest('.session-item');\n                const titleSpan = item.querySelector('.session-title');\n                const oldTitle = titleSpan.textContent.trim();\n                \n                currentRenameUUID = uuid;\n                currentRenameTitleEl = titleSpan;\n                if (renameInput) renameInput.value = oldTitle;\n                if (renameModal) renameModal.show();\n            };\n        });\n\n        document.querySelectorAll('.delete-session-btn').forEach(btn => {\n            btn.onclick = async (e) => {\n                e.stopPropagation();\n                const uuid = btn.dataset.uuid;\n                if (confirm('Are you sure you want to delete this conversation?')) {\n                    try {\n                        const formData = new FormData();\n                        formData.append('session_uuid', uuid);\n                        const response = await fetch('/sessions/delete', {\n                            method: 'POST',\n                            body: formData\n                        });\n                        const data = await response.json();\n                        if (data.success) {\n                            loadSessions();\n                            const item = btn.closest('.session-item');\n                            if (item.classList.contains('active-session')) {\n                                chatContainer.innerHTML = '<div class=\"text-center text-muted mt-5\"><p>Conversation deleted. Start a new one!</p></div>';\n                            }\n                        }\n                    } catch (error) {\n                        console.error('Error deleting session:', error);\n                        alert('Failed to delete session.');\n                    }\n                }\n            };\n        });\n    }\n\n    // New Chat\n    newChatBtn.addEventListener('click', async () => {\n        try {\n            const response = await fetch('/sessions/new', { method: 'POST' });\n            const data = await response.json();\n            if (data.success) {\n                chatContainer.innerHTML = '<div class=\"text-center text-muted mt-5\"><p>New conversation started.</p></div>';\n                bootstrap.Offcanvas.getInstance(historySidebar).hide();\n                loadSessions();\n            }\n        } catch (error) {\n            console.error('Error starting new chat:', error);\n            alert('Failed to start new chat.');\n        }\n    });\n\n    // Load patterns when modal is shown\n    patternsModal.addEventListener('show.bs.modal', async () => {\n        if (allPatterns.length === 0) {\n            try {\n                const response = await fetch('/patterns');\n                const data = await response.json();\n                allPatterns = data; // data is already the list\n                renderPatterns(allPatterns);\n            } catch (error) {\n                console.error('Error loading patterns:', error);\n                patternsList.innerHTML = '<div class=\"alert alert-danger\">Failed to load patterns.</div>';\n            }\n        }\n    });\n\n    // Search patterns\n    patternSearch.addEventListener('input', (e) => {\n        const query = e.target.value.toLowerCase();\n        const filtered = allPatterns.filter(p => \n            (p.name && p.name.toLowerCase().includes(query)) || \n            (p.description && p.description.toLowerCase().includes(query))\n        );\n        renderPatterns(filtered);\n    });\n\n    function renderPatterns(patterns) {\n        if (patterns.length === 0) {\n            patternsList.innerHTML = '<div class=\"text-center p-3 text-muted\">No patterns found.</div>';\n            return;\n        }\n\n        // Sort: User prompts first, then system patterns\n        patterns.sort((a, b) => {\n            if (a.type === 'user' && b.type !== 'user') return -1;\n            if (a.type !== 'user' && b.type === 'user') return 1;\n            return a.name.localeCompare(b.name);\n        });\n\n        patternsList.innerHTML = patterns.map(p => {\n            if (p.type === 'user') {\n                return `\n                <div class=\"list-group-item bg-dark text-light border-secondary d-flex justify-content-between align-items-center\">\n                    <div class=\"flex-grow-1 cursor-pointer user-prompt-item\" data-name=\"${p.name}\">\n                        <div class=\"d-flex align-items-center\">\n                            <h6 class=\"mb-1 text-info\"><i class=\"bi bi-file-text me-2\"></i>${p.name}</h6>\n                        </div>\n                        <small class=\"text-muted\">${p.description}</small>\n                    </div>\n                    <div class=\"d-flex gap-2\">\n                        <button class=\"btn btn-sm btn-outline-warning edit-prompt-btn\" data-name=\"${p.name}\" title=\"Edit\"><i class=\"bi bi-pencil\"></i></button>\n                        <button class=\"btn btn-sm btn-outline-danger delete-prompt-btn\" data-name=\"${p.name}\" title=\"Delete\"><i class=\"bi bi-trash\"></i></button>\n                    </div>\n                </div>`;\n            } else {\n                return `\n                <button type=\"button\" class=\"list-group-item list-group-item-action bg-dark text-light border-secondary pattern-item\" data-pattern=\"${p.name}\">\n                    <div class=\"d-flex w-100 justify-content-between\">\n                        <h6 class=\"mb-1\"><i class=\"bi bi-magic me-2\"></i>${p.name}</h6>\n                    </div>\n                    <small class=\"text-muted\">${p.description || ''}</small>\n                </button>`;\n            }\n        }).join('');\n\n        // System Pattern Click\n        document.querySelectorAll('.pattern-item').forEach(item => {\n            item.addEventListener('click', () => {\n                const pattern = item.dataset.pattern;\n                messageInput.value = `/p ${pattern} ${messageInput.value}`;\n                bootstrap.Modal.getInstance(patternsModal).hide();\n                messageInput.focus();\n                messageInput.dispatchEvent(new Event('input'));\n            });\n        });\n\n        // User Prompt Click (Load)\n        document.querySelectorAll('.user-prompt-item').forEach(item => {\n            item.addEventListener('click', async () => {\n                const name = item.dataset.name;\n                // Fetch content? Or just assume it was loaded?\n                // The list endpoint didn't return content. We need to fetch or just execute.\n                // Actually, prompts are files. We can't just \"/p name\" them unless the backend supports it.\n                // The backend \"apply_pattern\" reads from PATTERNS dict. It doesn't read files yet.\n                // BUT, the request was \"list prompts... option to edit or delete\".\n                // If I click it, maybe I want to RUN it?\n                // For now, let's load it into the input as text so the user can send it.\n                try {\n                    // We need an endpoint to get the content. \n                    // We can reuse the `get_pats` if we included content, or add a simple get endpoint.\n                    // Or, we can use `read_file` via tool? No, frontend.\n                    // Let's assume for now clicking puts `/p name` and we update backend to handle file prompts.\n                    // WAIT, I updated `get_pats` but didn't update `apply_pattern`.\n                    // Let's implement client-side fetch for content to populate input.\n                    // I'll add a quick fetch logic here.\n                    const res = await fetch(`/api/prompt-helper/prompts/${name}`); // Need this endpoint? No, we have PUT/DELETE.\n                    // We don't have GET content endpoint in prompt_helper.\n                    // I will add GET /api/prompt-helper/prompts/{filename} to the router next.\n                } catch (e) {}\n            });\n        });\n        \n        // Delete Prompt\n        document.querySelectorAll('.delete-prompt-btn').forEach(btn => {\n            btn.addEventListener('click', async (e) => {\n                e.stopPropagation();\n                if (confirm(`Delete prompt \"${btn.dataset.name}\"?`)) {\n                    try {\n                        const res = await fetch(`/api/prompt-helper/prompts/${btn.dataset.name}`, { method: 'DELETE' });\n                        if (res.ok) {\n                            allPatterns = allPatterns.filter(p => p.name !== btn.dataset.name);\n                            renderPatterns(allPatterns);\n                        } else {\n                            alert('Failed to delete prompt.');\n                        }\n                    } catch (err) {\n                        console.error(err);\n                    }\n                }\n            });\n        });\n\n        // Edit Prompt (Open Modal)\n        document.querySelectorAll('.edit-prompt-btn').forEach(btn => {\n            btn.addEventListener('click', async (e) => {\n                e.stopPropagation();\n                const name = btn.dataset.name;\n                const modalEl = document.getElementById('editPromptModal');\n                const editModal = new bootstrap.Modal(modalEl);\n                \n                try {\n                    const res = await fetch(`/api/prompt-helper/prompts/${name}`);\n                    const data = await res.json();\n                    if (data.content) {\n                        document.getElementById('edit-prompt-filename').value = name;\n                        document.getElementById('edit-prompt-content').value = data.content;\n                        editModal.show();\n                    }\n                } catch (err) {\n                    console.error(err);\n                    alert('Failed to load prompt content.');\n                }\n            });\n        });\n\n        // Handle Prompt Save\n        const savePromptBtn = document.getElementById('btn-save-prompt-edit');\n        if (savePromptBtn) {\n            savePromptBtn.onclick = async () => {\n                const filename = document.getElementById('edit-prompt-filename').value;\n                const content = document.getElementById('edit-prompt-content').value;\n                const formData = new FormData();\n                formData.append('content', content);\n\n                try {\n                    const res = await fetch(`/api/prompt-helper/prompts/${filename}`, {\n                        method: 'PUT',\n                        body: formData\n                    });\n                    const data = await res.json();\n                    if (data.success) {\n                        showToast('Prompt updated successfully!');\n                        bootstrap.Modal.getInstance(document.getElementById('editPromptModal')).hide();\n                    } else {\n                        alert('Failed to update prompt.');\n                    }\n                } catch (err) {\n                    console.error(err);\n                    alert('Error saving prompt.');\n                }\n            };\n        }\n        \n        // User Prompt Item Click (Load content into chat input)\n        document.querySelectorAll('.user-prompt-item').forEach(item => {\n            item.addEventListener('click', async () => {\n                const name = item.dataset.name;\n                try {\n                    const res = await fetch(`/api/prompt-helper/prompts/${name}`);\n                    const data = await res.json();\n                    if (data.content) {\n                        messageInput.value = data.content;\n                        bootstrap.Modal.getInstance(patternsModal).hide();\n                        messageInput.focus();\n                        messageInput.dispatchEvent(new Event('input'));\n                    }\n                } catch (err) {\n                    console.error(err);\n                }\n            });\n        });\n    }\n\n    // Auto-resize textarea\n    messageInput.addEventListener('keydown', function(event) {\n        if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {\n            event.preventDefault();\n            chatForm.dispatchEvent(new Event('submit'));\n        }\n    });\n\n    messageInput.addEventListener('input', function() {\n        this.style.height = 'auto';\n        this.style.height = (this.scrollHeight) + 'px';\n        if (this.value === '') {\n            this.style.height = '';\n        }\n    });\n\n    // Model selection\n    modelLinks.forEach(link => {\n        link.addEventListener('click', (e) => {\n            e.preventDefault();\n            const targetLink = e.currentTarget; // The <a> tag\n            const model = targetLink.dataset.model;\n            \n            modelInput.value = model;\n            // Get text without the badge if possible, or just full text\n            let modelName = targetLink.innerText;\n            // Clean up \"Fast\"/\"Smart\" badges from text if present (simple hack)\n            modelName = modelName.replace('Fast', '').replace('Smart', '').trim();\n            \n            modelLabel.textContent = modelName;\n            \n            modelLinks.forEach(l => l.classList.remove('active'));\n            targetLink.classList.add('active');\n        });\n    });\n\n    // File handling\n    fileUpload.addEventListener('change', async (e) => {\n        if (e.target.files.length > 0) {\n            await attachments.addFiles(e.target.files);\n            switchToFlashModel();\n            fileUpload.value = ''; // Reset input to allow re-selecting same file\n        }\n    });\n\n    /*\n    clearFileBtn.addEventListener('click', () => {\n        fileUpload.value = '';\n        currentFile = null;\n        filePreviewArea.classList.add('d-none');\n    });\n    */\n\n        chatForm.addEventListener('submit', async (e) => {\n        e.preventDefault();\n        const message = messageInput.value.trim();\n        const queuedFiles = attachments.getFiles();\n        \n        if (!message && queuedFiles.length === 0) return;\n\n        // Add user message to chat\n        const userMsgIndex = window.TOTAL_MESSAGES || 0;\n        const attachmentText = queuedFiles.length > 0 ? \n            ` [${queuedFiles.length} attachment(s)]` : '';\n            \n        // For local display, we show the first file as a thumbnail if it's an image\n        const firstFile = queuedFiles.length > 0 ? queuedFiles[0] : null;\n        \n        appendMessage('user', message + attachmentText, null, firstFile, userMsgIndex);\n        window.TOTAL_MESSAGES = userMsgIndex + 1;\n\n        // Clear inputs immediately\n        messageInput.value = '';\n        messageInput.style.height = '';\n        const filesToSend = [...queuedFiles]; \n        attachments.clear();\n\n        // Show loading state\n        const loadingId = appendLoading();\n        toggleStopButton(true);\n\n        try {\n            const formData = new FormData();\n            formData.append('message', message);\n            \n            for (const file of filesToSend) {\n                // Files are already compressed by AttachmentManager if they are images\n                formData.append('file', file);\n            }\n            \n            formData.append('model', modelInput.value);\n            if (planModeActive) {\n                formData.append('plan_mode', 'true');\n            }\n\n            const response = await fetch('/chat', {\n                method: 'POST',\n                body: formData\n            });\n\n            if (!response.ok) {\n                let errorMessage = `Server Error: ${response.status}`;\n                try {\n                    const text = await response.text();\n                    try {\n                        const errorData = JSON.parse(text);\n                        if (errorData.error) {\n                            errorMessage = `Error: ${errorData.error}`;\n                        } else if (errorData.response) {\n                            errorMessage = errorData.response;\n                        }\n                    } catch (parseError) {\n                        if (text && text.length < 100) {\n                            errorMessage = `Error ${response.status}: ${text}`;\n                        } else {\n                            errorMessage = `Error ${response.status}: Failed to get valid response from server.`;\n                        }\n                    }\n                } catch (e) {\n                    console.error('Could not read error response:', e);\n                }\n                throw new Error(errorMessage);\n            }\n\n            const contentType = response.headers.get('content-type');\n            if (contentType && contentType.includes('text/event-stream')) {\n                await processStream(response, loadingId);\n            } else {\n                const data = await response.json();\n                removeLoading(loadingId);\n                appendMessage('bot', data.response);\n            }\n\n        } catch (error) {\n            removeLoading(loadingId);\n            console.error('Detailed Chat Error:', error);\n            let displayError = error.message || 'Unknown Error';\n            if (error instanceof TypeError && error.message === 'Failed to fetch') {\n                displayError = 'Network Error: Could not connect to the server. Check if the service is running and accessible.';\n            }\n            appendMessage('bot', `Error: ${displayError}`);\n        } finally {\n            toggleStopButton(false);\n            // Refresh sidebar to ensure new sessions appear without reload\n            loadSessions();\n        }\n    });\n\n    async function processStream(response, loadingId) {\n        const reader = response.body.getReader();\n        const decoder = new TextDecoder();\n        let messageDiv = null;\n        \n        let fullText = \"\";\n        let toolLogs = [];\n        let buffer = \"\";\n        let errorYielded = false;\n        \n        const renderInterval = 100; // ms\n        let lastRenderTime = 0;\n\n        try {\n            while (true) {\n                const { done, value } = await reader.read();\n                if (done) break;\n                \n                buffer += decoder.decode(value, { stream: true });\n                const lines = buffer.split('\\n');\n                buffer = lines.pop();\n\n                for (const line of lines) {\n                    const trimmedLine = line.trim();\n                    if (!trimmedLine || trimmedLine.startsWith(':')) continue; // Skip empty or heartbeats\n\n                    if (trimmedLine.startsWith('data: ')) {\n                        const dataStr = trimmedLine.substring(6).trim();\n                        if (dataStr === '[DONE]') continue;\n                        \n                        try {\n                            const data = JSON.parse(dataStr);\n                            if (data.type === 'message' && data.role === 'assistant') {\n                                fullText += data.content;\n                            } else if (data.type === 'plan_status') {\n                                if (data.status === 'active') {\n                                    fullText += `\\n\\n<div class=\"alert alert-info py-2 px-3 mb-2\"><i class=\"bi bi-journal-text me-2\"></i><strong>Plan Mode Active:</strong> ${data.message}</div>\\n\\n`;\n                                } else if (data.status === 'completed') {\n                                    fullText += `\\n\\n<div class=\"alert alert-success py-2 px-3 mt-2\"><i class=\"bi bi-check-circle me-2\"></i><strong>Plan Complete:</strong> ${data.message}</div>\\n\\n`;\n                                }\n                            } else if (data.type === 'question') {\n                                // Render question card\n                                const card = createQuestionCard(data);\n                                chatContainer.appendChild(card);\n                                chatContainer.scrollTop = chatContainer.scrollHeight;\n                            } else if (data.type === 'model_switch') {\n                                // Update hidden input for subsequent requests\n                                if (modelInput) modelInput.value = data.new_model;\n                                \n                                // Update active state in the dropdown menu\n                                modelLinks.forEach(link => {\n                                    if (link.dataset.model === data.new_model) {\n                                        link.classList.add('active');\n                                    } else {\n                                        link.classList.remove('active');\n                                    }\n                                });\n\n                                // Update footer label\n                                const label = document.getElementById('model-label');\n                                if (label) {\n                                    // Make it look nice, e.g. \"Gemini 3 Flash (Auto-switched)\"\n                                    let cleanName = data.new_model.replace(/-/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase());\n                                    // Remove 'Preview' etc if redundant, but keep it clear\n                                    label.textContent = cleanName + \" (Auto-switched)\";\n                                    label.classList.add('text-warning'); // Highlight the change\n                                }\n                            } else if (data.type === 'tool_use') {\n                                toolLogs.push({ type: 'call', name: data.tool_name, input: data.parameters });\n                            } else if (data.type === 'tool_result') {\n                                if (data.output && data.output.trim() !== \"\") {\n                                    toolLogs.push({ type: 'output', output: data.output, full_path: data.full_output_path });\n                                }\n                            } else if (data.type === 'error') {\n                                fullText += `\\n\\n[Error: ${data.content}]\\n\\n`;\n                                errorYielded = true;\n                            }\n                            \n                            if (!messageDiv && (fullText.trim().length > 0 || toolLogs.length > 0)) {\n                                const botMsgIndex = window.TOTAL_MESSAGES || 0;\n                                messageDiv = createStreamingMessage('bot', botMsgIndex);\n                                window.TOTAL_MESSAGES = botMsgIndex + 1;\n                                removeLoading(loadingId);\n                                if (chatWelcome) chatWelcome.classList.add('d-none');\n                            }\n\n                            if (messageDiv) {\n                                const now = Date.now();\n                                if (now - lastRenderTime > renderInterval) {\n                                    updateStreamingMessage(messageDiv, fullText, toolLogs);\n                                    lastRenderTime = now;\n                                }\n                            }\n                        } catch (e) {\n                            console.error('Error parsing stream chunk:', e, dataStr);\n                        }\n                    }\n                }\n            }\n            if (messageDiv) {\n                updateStreamingMessage(messageDiv, fullText, toolLogs, true);\n            } else {\n                removeLoading(loadingId);\n            }\n            toggleStopButton(false);\n            // Refresh sidebar to ensure new sessions appear without reload\n            loadSessions();\n        } catch (error) {\n            console.error('Stream processing error:', error);\n            if (!errorYielded) {\n                if (!messageDiv) {\n                    messageDiv = createStreamingMessage('bot');\n                    removeLoading(loadingId);\n                }\n                const errorDiv = document.createElement('div');\n                errorDiv.className = 'text-danger small mt-2';\n                errorDiv.textContent = 'Connection lost. Message may be incomplete.';\n                messageDiv.appendChild(errorDiv);\n            }\n        }\n    }\n\n    function createStreamingMessage(sender, index = null) {\n        const messageDiv = document.createElement('div');\n        messageDiv.classList.add('message', sender);\n        if (index !== null) messageDiv.dataset.index = index;\n        \n        const contentArea = document.createElement('div');\n        contentArea.className = 'message-content';\n        messageDiv.appendChild(contentArea);\n        \n        const logsArea = document.createElement('div');\n        logsArea.className = 'tool-logs mt-2 d-none';\n        messageDiv.appendChild(logsArea);\n        \n        chatContainer.appendChild(messageDiv);\n        chatContainer.scrollTop = chatContainer.scrollHeight;\n        return messageDiv;\n    }\n\n    function createQuestionCard(data) {\n        const { question, options, allow_multiple } = data;\n        \n        const card = document.createElement('div');\n        card.className = 'question-card';\n        \n        const qText = document.createElement('div');\n        qText.className = 'question-text';\n        qText.innerText = question;\n        card.appendChild(qText);\n        \n        const optContainer = document.createElement('div');\n        optContainer.className = 'options-container';\n        \n        const dismissCard = () => {\n            card.classList.add('removing');\n            setTimeout(() => card.remove(), 200);\n        };\n\n        if (!options || options.length === 0) {\n            // Open-ended question\n            const input = document.createElement('input');\n            input.type = 'text';\n            input.className = 'form-control bg-dark text-light border-secondary mb-2';\n            input.placeholder = 'Type your answer...';\n            card.appendChild(input);\n            \n            const submit = document.createElement('button');\n            submit.className = 'btn btn-primary btn-sm w-100';\n            submit.innerText = 'Submit';\n            submit.onclick = () => {\n                const val = input.value.trim();\n                if (val) {\n                    submitAnswer(val);\n                    dismissCard();\n                }\n            };\n            card.appendChild(submit);\n            \n            // Allow Enter key\n            input.onkeydown = (e) => {\n                if (e.key === 'Enter') submit.click();\n            };\n        } else {\n            // Multiple choice\n            const selected = new Set();\n            \n            options.forEach(opt => {\n                const btn = document.createElement('button');\n                btn.className = 'option-btn';\n                btn.innerText = opt;\n                btn.onclick = () => {\n                    if (allow_multiple) {\n                        if (selected.has(opt)) {\n                            selected.delete(opt);\n                            btn.classList.remove('active');\n                        } else {\n                            selected.add(opt);\n                            btn.classList.add('active');\n                        }\n                    } else {\n                        submitAnswer(opt);\n                        dismissCard();\n                    }\n                };\n                optContainer.appendChild(btn);\n            });\n            \n            card.appendChild(optContainer);\n            \n            if (allow_multiple) {\n                const submit = document.createElement('button');\n                submit.className = 'btn btn-primary btn-sm submit-btn';\n                submit.innerText = 'Submit Selection';\n                submit.onclick = () => {\n                    if (selected.size > 0) {\n                        submitAnswer(Array.from(selected).join(', '));\n                        dismissCard();\n                    }\n                };\n                card.appendChild(submit);\n            }\n        }\n        \n        return card;\n    }\n\n    async function submitAnswer(text) {\n        // Send answer as a normal user message\n        messageInput.value = text;\n        chatForm.dispatchEvent(new Event('submit'));\n    }\n\n    async function copyMessageToClipboard(text, messageDiv, btn) {\n        try {\n            const icon = btn.querySelector('i');\n            const isFormatted = window.USER_SETTINGS && window.USER_SETTINGS.copy_formatted === true;\n\n            if (isFormatted && typeof ClipboardItem !== 'undefined') {\n                // Get the rendered HTML content, excluding the actions div\n                const contentClone = messageDiv.cloneNode(true);\n                const actions = contentClone.querySelector('.message-actions');\n                if (actions) actions.remove();\n                \n                // Remove question cards\n                contentClone.querySelectorAll('.question-card').forEach(c => c.remove());\n\n                const htmlContent = contentClone.innerHTML;\n                const blobHtml = new Blob([htmlContent], { type: 'text/html' });\n                const blobText = new Blob([text], { type: 'text/plain' });\n                \n                const data = [new ClipboardItem({\n                    'text/html': blobHtml,\n                    'text/plain': blobText\n                })];\n                \n                await navigator.clipboard.write(data);\n            } else {\n                // Default markdown only\n                await navigator.clipboard.writeText(text);\n            }\n\n            icon.className = 'bi bi-check2';\n            setTimeout(() => { icon.className = 'bi bi-clipboard'; }, 2000);\n        } catch (err) {\n            console.error('Failed to copy:', err);\n            // Fallback\n            try {\n                await navigator.clipboard.writeText(text);\n                const icon = btn.querySelector('i');\n                if (icon) {\n                    icon.className = 'bi bi-check2';\n                    setTimeout(() => { icon.className = 'bi bi-clipboard'; }, 2000);\n                }\n            } catch (e) {}\n        }\n    }\n\n    function updateStreamingMessage(messageDiv, text, toolLogs, isFinal = false) {\n        const contentArea = messageDiv.querySelector('.message-content');\n        const logsArea = messageDiv.querySelector('.tool-logs');\n        \n        // Render Text\n        if (text.trim().length > 0) {\n            if (typeof marked !== 'undefined') {\n                contentArea.innerHTML = marked.parse(text);\n            } else {\n                contentArea.textContent = text;\n            }\n        }\n        \n        // Render Logs\n        if (toolLogs.length > 0) {\n            logsArea.classList.remove('d-none');\n            logsArea.innerHTML = toolLogs.map(log => {\n                if (log.type === 'call') {\n                    return `<div class=\"small text-info border-start border-info ps-2 mb-1\" style=\"font-family: monospace;\">\n                        <strong>Tool Call:</strong> ${log.name}<br>\n                        <span class=\"text-muted\" style=\"word-break: break-all; font-size: 0.7rem;\">${JSON.stringify(log.input)}</span>\n                    </div>`;\n                } else {\n                    if (!log.output || log.output.trim() === \"\") return \"\";\n                    let outputHtml = `<div class=\"small text-success border-start border-success ps-2 mb-2\" style=\"font-family: monospace;\">\n                        <strong>Tool Output:</strong><br>\n                        <pre class=\"m-0\" style=\"font-size: 0.7rem; max-height: 150px; overflow: auto; background: #1a1a1a; padding: 5px; border-radius: 4px;\">${log.output}</pre>`;\n                    \n                    if (log.full_path) {\n                        outputHtml += `<div class=\"mt-1\"><a href=\"${log.full_path}\" target=\"_blank\" class=\"btn btn-sm btn-outline-success py-0\" style=\"font-size: 0.6rem;\"><i class=\"bi bi-download\"></i> Download Full Output</a></div>`;\n                    }\n                    \n                    outputHtml += `</div>`;\n                    return outputHtml;\n                }\n            }).join('');\n        }\n        \n        if (isFinal) {\n            // Update Actions\n            let actionsDiv = messageDiv.querySelector('.message-actions');\n            if (!actionsDiv) {\n                actionsDiv = document.createElement('div');\n                actionsDiv.className = 'message-actions';\n                messageDiv.prepend(actionsDiv);\n            }\n            actionsDiv.innerHTML = ''; // Clear\n\n            const copyBtn = document.createElement('button');\n            copyBtn.className = 'copy-btn';\n            copyBtn.title = 'Copy to clipboard';\n            copyBtn.innerHTML = '<i class=\"bi bi-clipboard\"></i>';\n            copyBtn.onclick = (e) => {\n                e.stopPropagation();\n                copyMessageToClipboard(text, messageDiv, copyBtn);\n            };\n            actionsDiv.appendChild(copyBtn);\n\n            const forkBtn = document.createElement('button');\n            forkBtn.className = 'clone-btn';\n            forkBtn.title = 'Fork conversation from this message';\n            forkBtn.innerHTML = `<svg width=\"14\" height=\"14\" fill=\"currentColor\" viewBox=\"0 0 16 16\"><path d=\"M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 2.25 0 1 1 1.5 0v.878a2.25 2.25 0 0 1-2.25 2.25h-1.5v2.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25v-.878a2.25 2.25 0 1 1 1.5 0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z\"></path></svg>`;\n            forkBtn.onclick = (e) => {\n                e.stopPropagation();\n                const activeSessionItem = document.querySelector('.session-item.active-session');\n                if (activeSessionItem) {\n                    handleClone(activeSessionItem.dataset.uuid, parseInt(messageDiv.dataset.index));\n                }\n            };\n            actionsDiv.appendChild(forkBtn);\n\n            // Highlight code\n            if (typeof hljs !== 'undefined') {\n                messageDiv.querySelectorAll('pre code').forEach((block) => {\n                    hljs.highlightElement(block);\n                });\n            }\n\n            // Render Math\n            try {\n                if (typeof renderMathInElement === 'function') {\n                    renderMathInElement(messageDiv, {\n                        delimiters: [\n                            {left: '$$', right: '$$', display: true},\n                            {left: '$', right: '$', display: false},\n                            {left: '\\\\(', right: '\\\\)', display: false},\n                            {left: '\\\\[', right: '\\\\]', display: true}\n                        ],\n                        throwOnError: false\n                    });\n                }\n            } catch (e) {\n                console.error('Error rendering math:', e);\n            }\n        }\n        \n        chatContainer.scrollTop = chatContainer.scrollHeight;\n    }\n\n    function createMessageDiv(sender, text, attachmentInfo = null, file = null, index = null) {\n        if (!text && !attachmentInfo) return null;\n        if (text && text.trim() === \"\" && !attachmentInfo) return null;\n\n        const messageDiv = document.createElement('div');\n        messageDiv.classList.add('message', sender);\n        if (index !== null) messageDiv.dataset.index = index;\n        \n        let contentHtml = '';\n\n        // Image Preview Logic\n        let imageUrl = null;\n        if (file && file.type.startsWith('image/')) {\n            imageUrl = URL.createObjectURL(file);\n        } else if (text && sender === 'user') {\n            // Regex to find attachment path: matches both / and \\ \n            const match = text.match(/@tmp[\\\\\\/]user_attachments[\\\\\\/]([^\\s]+)/);\n            if (match) {\n                const filename = match[1];\n                imageUrl = `/uploads/${filename}`;\n            }\n        }\n\n        if (imageUrl) {\n            contentHtml += `<img src=\"${imageUrl}\" class=\"message-thumbnail mb-2\" style=\"max-width: 150px; border-radius: 8px; cursor: pointer; display: block;\" onclick=\"window.open('${imageUrl}', '_blank')\">`;\n        }\n\n        if (attachmentInfo) {\n            contentHtml += `<div class=\"text-muted small mb-1\"><i class=\"bi bi-paperclip\"></i> ${attachmentInfo}</div>`;\n        }\n        \n        // Use marked to parse markdown safely\n        let parsedText = text;\n        try {\n            if (typeof marked !== 'undefined') {\n                if (typeof marked.parse === 'function') {\n                    parsedText = marked.parse(text);\n                } else if (typeof marked === 'function') {\n                    parsedText = marked(text);\n                }\n            }\n        } catch (e) {\n            console.error('Error parsing markdown:', e);\n        }\n        \n        contentHtml += `<div class=\"message-content\">${parsedText}</div>`;\n\n        messageDiv.innerHTML = contentHtml;\n\n        // Detect and render Question Cards if present in text (Historical Rendering)\n        if (sender === 'bot') {\n            const questionPattern = /(?:```(?:json)?\\s*)?\\{\\s*\"type\"\\s*:\\s*\"question\"[\\s\\S]*?\\}(?:\\s*```)?/g;\n            const matches = text.match(questionPattern);\n            if (matches) {\n                matches.forEach(match => {\n                    try {\n                        // Extract just the JSON part\n                        const jsonMatch = match.match(/\\{[\\s\\S]*\\}/);\n                        if (jsonMatch) {\n                            const questionData = JSON.parse(jsonMatch[0]);\n                            const card = createQuestionCard(questionData);\n                            messageDiv.appendChild(card);\n                            \n                            // Remove the raw JSON from the displayed text if it was successfully rendered\n                            const contentArea = messageDiv.querySelector('.message-content');\n                            if (contentArea) {\n                                // We replace the match in the innerHTML/innerText carefully.\n                                // Since marked might have wrapped it in <pre><code>, we might need a more robust way.\n                                // For now, let's try to remove the <pre><code> block if it contains this JSON.\n                                const preBlocks = contentArea.querySelectorAll('pre');\n                                preBlocks.forEach(pre => {\n                                    if (pre.innerText.includes('\"type\": \"question\"') && pre.innerText.includes(questionData.question)) {\n                                        pre.remove();\n                                    }\n                                });\n                            }\n                        }\n                    } catch (e) {\n                        console.error('Error parsing historical question card:', e);\n                    }\n                });\n            }\n        }\n        \n        // Add Action Buttons\n        const actionsDiv = document.createElement('div');\n        actionsDiv.className = 'message-actions';\n\n        const copyBtn = document.createElement('button');\n        copyBtn.className = 'copy-btn';\n        copyBtn.title = 'Copy to clipboard';\n        copyBtn.innerHTML = '<i class=\"bi bi-clipboard\"></i>';\n        copyBtn.onclick = (e) => {\n            e.stopPropagation();\n            copyMessageToClipboard(text, messageDiv, copyBtn);\n        };\n        actionsDiv.appendChild(copyBtn);\n\n        if (sender === 'bot' && index !== null) {\n            const forkBtn = document.createElement('button');\n            forkBtn.className = 'clone-btn';\n            forkBtn.title = 'Fork conversation from this message';\n            forkBtn.innerHTML = `<svg width=\"14\" height=\"14\" fill=\"currentColor\" viewBox=\"0 0 16 16\"><path d=\"M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 2.25 0 1 1 1.5 0v.878a2.25 2.25 0 0 1-2.25 2.25h-1.5v2.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25v-.878a2.25 2.25 0 1 1 1.5 0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z\"></path></svg>`;\n            forkBtn.onclick = (e) => {\n                e.stopPropagation();\n                const activeSessionItem = document.querySelector('.session-item.active-session');\n                if (activeSessionItem) {\n                    handleClone(activeSessionItem.dataset.uuid, parseInt(index));\n                }\n            };\n            actionsDiv.appendChild(forkBtn);\n        }\n\n        // User Message Actions: Edit and Fork Navigation\n        if (sender === 'user' && index !== null) {\n            // Edit Button\n            const editBtn = document.createElement('button');\n            editBtn.className = 'clone-btn'; // Reuse same style\n            editBtn.title = 'Edit and branch conversation';\n            editBtn.innerHTML = '<i class=\"bi bi-pencil\"></i>';\n            editBtn.onclick = (e) => {\n                e.stopPropagation();\n                if (confirm('Edit this question and branch the conversation?')) {\n                    // 1. Populate input\n                    messageInput.value = text;\n                    messageInput.focus();\n                    messageInput.dispatchEvent(new Event('input'));\n                    \n                    // 2. Clone at the point before this message\n                    const activeSessionItem = document.querySelector('.session-item.active-session');\n                    if (activeSessionItem) {\n                        const msgIndex = parseInt(index);\n                        handleClone(activeSessionItem.dataset.uuid, msgIndex - 1, false); \n                    }\n                }\n            };\n            actionsDiv.appendChild(editBtn);\n\n            // Fork Navigation Arrows (now on the user message that branched)\n            const forkPoint = index - 1;\n            if (currentForkMap[forkPoint]) {\n                const forks = currentForkMap[forkPoint];\n                const totalBranches = forks.length + 1;\n                \n                const navSpan = document.createElement('span');\n                navSpan.className = 'fork-nav-controls d-flex align-items-center bg-dark rounded px-1 me-1';\n                navSpan.style.fontSize = '0.7rem';\n                navSpan.style.border = '1px solid rgba(255,255,255,0.1)';\n\n                const prevBtn = document.createElement('button');\n                prevBtn.className = 'btn btn-link btn-sm p-0 text-secondary border-0';\n                prevBtn.innerHTML = '<i class=\"bi bi-chevron-left\"></i>';\n                \n                const nextBtn = document.createElement('button');\n                nextBtn.className = 'btn btn-link btn-sm p-0 text-secondary border-0';\n                nextBtn.innerHTML = '<i class=\"bi bi-chevron-right\"></i>';\n\n                const branchInfo = document.createElement('span');\n                branchInfo.className = 'mx-1 text-muted';\n                branchInfo.textContent = `${totalBranches} forks`;\n\n                nextBtn.onclick = (e) => { e.stopPropagation(); switchSession(forks[0]); };\n                prevBtn.onclick = (e) => { e.stopPropagation(); switchSession(forks[forks.length - 1]); };\n\n                navSpan.appendChild(prevBtn);\n                navSpan.appendChild(branchInfo);\n                navSpan.appendChild(nextBtn);\n                actionsDiv.appendChild(navSpan);\n            }\n        }\n\n        messageDiv.prepend(actionsDiv);\n\n        // Highlight code blocks safely\n        try {\n            if (typeof hljs !== 'undefined') {\n                messageDiv.querySelectorAll('pre code').forEach((block) => {\n                    hljs.highlightElement(block);\n                });\n            }\n        } catch (e) {\n            console.error('Error highlighting code:', e);\n        }\n\n        // Render Math\n        try {\n            if (typeof renderMathInElement === 'function') {\n                renderMathInElement(messageDiv, {\n                    delimiters: [\n                        {left: '$$', right: '$$', display: true},\n                        {left: '$', right: '$', display: false},\n                        {left: '\\\\(', right: '\\\\)', display: false},\n                        {left: '\\\\[', right: '\\\\]', display: true}\n                    ],\n                    throwOnError: false\n                });\n            }\n        } catch (e) {\n            console.error('Error rendering math:', e);\n        }\n        \n        return messageDiv;\n    }\n\n    function appendMessage(sender, text, attachmentInfo = null, file = null, index = null) {\n        try {\n            const messageDiv = createMessageDiv(sender, text, attachmentInfo, file, index);\n            if (messageDiv) {\n                chatContainer.appendChild(messageDiv);\n                chatContainer.scrollTop = chatContainer.scrollHeight;\n            }\n            return messageDiv;\n        } catch (e) {\n            console.error('Error in appendMessage:', e);\n            return null;\n        }\n    }\n\n    function appendLoading() {\n        const id = 'loading-' + Date.now();\n        const messageDiv = document.createElement('div');\n        messageDiv.classList.add('message', 'bot');\n        messageDiv.id = id;\n        messageDiv.innerHTML = '<div class=\"spinner-border spinner-border-sm text-light\" role=\"status\"><span class=\"visually-hidden\">Loading...</span></div> Thinking...';\n        chatContainer.appendChild(messageDiv);\n        chatContainer.scrollTop = chatContainer.scrollHeight;\n        return { id, element: messageDiv };\n    }\n\n    function removeLoading(id) {\n        const element = document.getElementById(id);\n        if (element) {\n            element.remove();\n        }\n    }\n\n    // Infinite Scroll Observer\n    const scrollSentinel = document.getElementById('scroll-sentinel');\n    if (scrollSentinel) {\n        const observer = new IntersectionObserver((entries) => {\n            if (entries[0].isIntersecting && !isLoadingHistory) {\n                const activeSessionItem = document.querySelector('.session-item.active-session');\n                const hasMore = !loadMoreContainer.classList.contains('d-none');\n                \n                if (activeSessionItem && hasMore && currentOffset > 0) {\n                    loadMessages(activeSessionItem.dataset.uuid, PAGE_LIMIT, currentOffset);\n                }\n            }\n        }, {\n            root: chatContainer,\n            threshold: 0.1\n        });\n        observer.observe(scrollSentinel);\n    }\n\n    // Swipe Gestures for Mobile\n    let touchStartX = 0;\n    let touchStartY = 0;\n    const swipeThreshold = 50;\n    const edgeThreshold = 40;\n\n    document.addEventListener('touchstart', (e) => {\n        // Only track if swipe starts near edges\n        const x = e.touches[0].clientX;\n        if (x < edgeThreshold || x > window.innerWidth - edgeThreshold) {\n            touchStartX = x;\n            touchStartY = e.touches[0].clientY;\n        } else {\n            touchStartX = 0; // Reset\n        }\n    }, { passive: true });\n\n    document.addEventListener('touchend', (e) => {\n        if (touchStartX === 0) return;\n\n        const touchEndX = e.changedTouches[0].clientX;\n        const touchEndY = e.changedTouches[0].clientY;\n        const diffX = touchEndX - touchStartX;\n        const diffY = touchEndY - touchStartY;\n\n        // Must be horizontal and meet threshold\n        if (Math.abs(diffX) > Math.abs(diffY) * 1.5 && Math.abs(diffX) > swipeThreshold) {\n            if (diffX > 0 && touchStartX < edgeThreshold) {\n                // Swipe Left-to-Right from left edge: Open History\n                const historyEl = document.getElementById('historySidebar');\n                const historyOffcanvas = bootstrap.Offcanvas.getInstance(historyEl) || new bootstrap.Offcanvas(historyEl);\n                historyOffcanvas.show();\n            } else if (diffX < 0 && touchStartX > window.innerWidth - edgeThreshold) {\n                // Swipe Right-to-Left from right edge: Open Actions\n                const actionsEl = document.getElementById('actionsSidebar');\n                const actionsOffcanvas = bootstrap.Offcanvas.getInstance(actionsEl) || new bootstrap.Offcanvas(actionsEl);\n                actionsOffcanvas.show();\n            }\n        }\n        touchStartX = 0; // Reset\n    }, { passive: true });\n});\n",
        "encoding": "text"
    },
    "style.css": {
        "content": ":root {\n    --bg-color: #121212;\n    --chat-bg: #0b0b0b;\n    --sidebar-bg: #1e1e1e;\n    --message-user-bg: #3c6e71; /* Teal muted */\n    --message-bot-bg: #2b2d42; /* Dark blue/grey */\n    --text-color: #e0e0e0;\n    --input-bg: #2d2d2d;\n    --border-color: #444;\n}\n\nbody {\n    background-color: var(--bg-color) !important;\n    color: var(--text-color) !important;\n    font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;\n    touch-action: pan-y;\n}\n\n/* Header Styling */\nheader {\n    background-color: var(--sidebar-bg) !important;\n    box-shadow: 0 2px 10px rgba(0,0,0,0.3);\n    z-index: 1000;\n}\n\n/* Chat Container */\n#chat-container {\n    background-color: var(--chat-bg);\n    padding-bottom: 2rem;\n    touch-action: pan-y;\n}\n\n/* Messages */\n.message {\n    max-width: 85%;\n    margin-bottom: 1.2rem;\n    padding: 1rem 1.2rem;\n    border-radius: 1.2rem;\n    position: relative;\n    word-wrap: break-word;\n    box-shadow: 0 1px 2px rgba(0,0,0,0.2);\n    font-size: 0.95rem;\n    line-height: 1.5;\n}\n\n.message.user {\n    background-color: var(--message-user-bg);\n    color: #ffffff;\n    align-self: flex-end;\n    margin-left: auto;\n    border-bottom-right-radius: 0.2rem;\n}\n\n.message.bot {\n    background-color: #2d2d2d; /* Dark Grey */\n    color: #ffffff; /* Brighter white */\n    align-self: flex-start;\n    margin-right: auto;\n    border-bottom-left-radius: 0.2rem;\n}\n\n.text-muted {\n    color: #b0b0b0 !important; /* Brighter muted text */\n}\n\n/* Code Blocks */\n.message pre {\n    background-color: #1a1a1a !important;\n    padding: 1rem;\n    border-radius: 0.5rem;\n    overflow-x: auto;\n    margin-top: 0.5rem;\n    border: 1px solid #333;\n}\n\n/* Footer / Input Area */\nfooter {\n    background-color: var(--sidebar-bg) !important;\n    box-shadow: 0 -2px 10px rgba(0,0,0,0.2);\n}\n\n/* Custom Scrollbar */\n::-webkit-scrollbar {\n    width: 6px;\n}\n\n::-webkit-scrollbar-track {\n    background: var(--chat-bg);\n}\n\n::-webkit-scrollbar-thumb {\n    background: #555;\n    border-radius: 3px;\n}\n\n::-webkit-scrollbar-thumb:hover {\n    background: #777;\n}\n\n/* Input Field Styling */\ntextarea#message-input {\n    resize: none;\n    max-height: 200px;\n    min-height: 50px; /* Enforce a minimum height */\n    background-color: var(--input-bg);\n    color: white;\n    border: 1px solid var(--border-color);\n    border-radius: 1.5rem !important; /* Pill shape */\n    padding: 0.8rem 1.2rem;\n    font-size: 1rem;\n}\n\ntextarea#message-input:focus {\n    background-color: #333;\n    border-color: #666;\n    box-shadow: none;\n    color: white;\n}\n\n/* Buttons in Input Area */\n.btn-circle {\n    width: 40px;\n    height: 40px;\n    padding: 0;\n    border-radius: 50%;\n    display: flex;\n    align-items: center;\n    justify-content: center;\n}\n\n/* Dropdown Menu */\n.dropdown-menu {\n    background-color: var(--input-bg);\n    border-color: var(--border-color);\n}\n.dropdown-item {\n    color: var(--text-color);\n}\n.dropdown-item:hover {\n    background-color: #444;\n    color: white;\n}\n\n/* Session List Items */\n#sessions-list .list-group-item {\n    cursor: pointer;\n    transition: background-color 0.2s;\n    border-color: #333;\n    padding: 0.75rem 1.25rem;\n}\n\n#sessions-list .list-group-item:hover {\n    background-color: #333 !important;\n}\n\n#sessions-list .list-group-item.active-session {\n    background-color: #2b2d42 !important;\n    border-left: 4px solid #3c6e71;\n}\n\n#sessions-list .session-title {\n    font-weight: 500;\n    font-size: 0.9rem;\n    display: block;\n}\n\n#sessions-list .session-time {\n    font-size: 0.75rem;\n    color: #888;\n}\n/* Mobile Safe Area Fixes */\nhtml, body { \n    height: 100%; \n    margin: 0; \n    padding: 0; \n    overflow: hidden; \n    overscroll-behavior: none; \n    background-color: var(--chat-bg);\n}\n.container-fluid { \n    height: 100vh; \n    height: 100dvh; \n    display: flex; \n    flex-direction: column; \n    overflow: hidden; \n}\n\nheader {\n    flex-shrink: 0;\n    z-index: 100;\n}\n\n#chat-container { \n    flex: 1;\n    overflow-y: auto;\n    background-color: var(--chat-bg);\n    padding-bottom: 1rem;\n    -webkit-overflow-scrolling: touch;\n}\n\nfooter {\n    flex-shrink: 0;\n    width: 100%;\n    background-color: #000;\n    border-top: 1px solid var(--border-color);\n    z-index: 100;\n    padding: 0.5rem 0.75rem !important;\n}\n\n@media (max-width: 768px) {\n    #chat-container {\n        padding-bottom: 6rem !important; /* Space for the fixed footer */\n    }\n    footer {\n        position: fixed;\n        bottom: 0;\n        left: 0;\n        width: 100%;\n        padding: 0.25rem 0.5rem !important;\n        padding-bottom: calc(0.25rem + env(safe-area-inset-bottom)) !important;\n    }\n    footer .text-center {\n        display: none;\n    }\n    textarea#message-input {\n        padding: 0.4rem 0.8rem;\n        min-height: 36px;\n        font-size: 0.9rem;\n        border-radius: 1rem !important;\n    }\n}\n\n@media (max-width: 768px) {\n\n    #chat-container {\n\n        padding-bottom: 6rem !important; /* Reduced since footer is smaller */\n\n    }\n\n    footer {\n\n        position: fixed;\n\n        bottom: 0;\n\n        left: 0;\n\n        width: 100%;\n\n        padding: 0.25rem 0.5rem !important;\n\n        padding-bottom: calc(0.25rem + env(safe-area-inset-bottom)) !important;\n\n    }\n\n    footer .text-center {\n\n        display: none; /* Hide model label on mobile to save space */\n\n    }\n\n    textarea#message-input {\n\n        padding: 0.4rem 0.8rem;\n\n        min-height: 36px;\n\n        font-size: 0.9rem;\n\n        border-radius: 1rem !important;\n\n    }\n\n    #send-btn, #stop-btn {\n\n        width: 36px !important;\n\n        height: 36px !important;\n\n        padding: 0 !important;\n\n        display: flex;\n\n        align-items: center;\n\n        justify-content: center;\n\n    }\n\n}\n\n/* Action Buttons in Messages */\n.message { \n    position: relative; \n    padding-right: 40px !important; \n    display: flex;\n    flex-direction: column;\n}\n.message-actions {\n    position: sticky;\n    top: 0;\n    align-self: flex-end;\n    margin-top: -5px;\n    margin-right: -30px;\n    display: flex;\n    gap: 4px;\n    z-index: 10;\n}\n.copy-btn, .clone-btn {\n    background: rgba(0,0,0,0.2); \n    border: 1px solid rgba(255,255,255,0.1);\n    color: rgba(255, 255, 255, 0.5); \n    cursor: pointer;\n    padding: 4px; \n    border-radius: 4px;\n    transition: all 0.2s; \n    font-size: 1rem;\n    display: flex; \n    align-items: center; \n    justify-content: center; \n}\n.copy-btn:hover, .clone-btn:hover { \n    color: #fff; \n    background: rgba(255, 255, 255, 0.2); \n}\n.clone-btn {\n    font-size: 0.9rem;\n}\n\n/* Tree View Styling */\n.tree-view {\n    display: flex;\n    flex-direction: column;\n    gap: 1rem;\n    padding: 1rem;\n}\n\n.tree-node-wrapper {\n    position: relative;\n}\n\n.tree-node {\n    position: relative;\n    z-index: 2;\n    box-shadow: 0 4px 6px rgba(0,0,0,0.3);\n}\n\n.tree-node:hover {\n    transform: translateY(-2px);\n}\n\n.tree-children {\n    position: relative;\n}\n\n.tree-children::before {\n    content: \"\";\n    position: absolute;\n    left: -1rem;\n    top: 0;\n    bottom: 1.5rem;\n    width: 2px;\n    background: #444;\n}\n\n.cursor-pointer {\n    cursor: pointer;\n}\n\n.tree-node-active {\n    border-left: 3px solid var(--bs-primary);\n}\n\n/* Fork Navigation in Messages */\n.fork-nav-controls {\n    border-color: rgba(255,255,255,0.2) !important;\n}\n\n.fork-nav-controls button:hover {\n    color: #fff !important;\n}\n\n@media (max-width: 768px) {\n    .message {\n        max-width: 90%;\n    }\n    .tree-node {\n        max-width: 100% !important;\n    }\n    .message-actions {\n        margin-right: -20px;\n    }\n}\n\n/* Image Thumbnails */\n.message-thumbnail {\n    max-width: 150px;\n    max-height: 150px;\n    border-radius: 8px;\n    cursor: pointer;\n    display: block;\n    transition: transform 0.2s;\n}\n.message-thumbnail:hover {\n    transform: scale(1.02);\n}\n\n/* Sidebar Sections */\n.sidebar-section-header {\n    letter-spacing: 0.05rem;\n    z-index: 10;\n    position: sticky;\n    top: 0;\n}\n\n/* Pinning UI */\n.pin-btn {\n    color: rgba(255, 255, 255, 0.3);\n    transition: all 0.2s;\n    padding: 0.25rem 0.5rem !important;\n}\n.pin-btn:hover {\n    color: rgba(255, 255, 255, 0.7);\n}\n.pin-btn.pinned {\n    color: #ffc107 !important; /* Gold */\n}\n.rename-session-btn {\n    color: rgba(255, 255, 255, 0.3);\n    transition: all 0.2s;\n    padding: 0.25rem 0.5rem !important;\n}\n.rename-session-btn:hover {\n    color: rgba(255, 255, 255, 0.7);\n}\n.delete-session-btn {\n    color: rgba(220, 53, 69, 0.5);\n    transition: all 0.2s;\n    padding: 0.25rem 0.5rem !important;\n}\n.delete-session-btn:hover {\n    color: rgba(220, 53, 69, 1);\n}\n#session-search:focus {\n    border-color: #3c6e71;\n    background-color: #252525 !important;\n}\n.input-group-text {\n    border-bottom: 2px solid #dc3545 !important;\n}\n\n/* Tags */\n.tag-badge {\n    cursor: pointer;\n    font-size: 0.7rem;\n    padding: 0.2rem 0.5rem;\n    border-radius: 10px;\n    background-color: #333;\n    color: #ccc;\n    border: 1px solid #444;\n    white-space: nowrap;\n    transition: all 0.2s;\n}\n\n.tag-badge:hover {\n    background-color: #444;\n    color: #fff;\n}\n\n.tag-badge.selected {\n    background-color: #0d6efd;\n    color: #fff;\n    border-color: #0a58ca;\n}\n\n.tag-badge.add-tag-btn {\n    border-style: dashed;\n    background: transparent;\n}\n\n.session-tags-list {\n    font-size: 0.65rem;\n    margin-top: 2px;\n}\n\n.session-tag-item {\n    color: #888;\n    background: #222;\n    padding: 0 4px;\n    border-radius: 4px;\n    margin-right: 4px;\n}\n\n/* Attachment Queue Styling */\n.attachment-item {\n    transition: all 0.2s;\n    animation: fadeIn 0.3s ease-in-out;\n}\n\n.attachment-item:hover {\n    background-color: rgba(255,255,255,0.1) !important;\n    border-color: rgba(255,255,255,0.2) !important;\n}\n\n.border-dashed {\n    border-style: dashed !important;\n}\n\n@keyframes fadeIn {\n    from { opacity: 0; transform: translateY(5px); }\n    to { opacity: 1; transform: translateY(0); }\n}\n\n\n/* Question Cards */\n.question-card {\n    background-color: #000;\n    border: 1px solid var(--message-user-bg);\n    border-left: 4px solid var(--message-user-bg);\n    border-radius: 0.5rem;\n    padding: 1rem;\n    margin-bottom: 1.2rem;\n    max-width: 85%;\n    align-self: flex-start;\n    margin-right: auto;\n    box-shadow: 0 4px 15px rgba(0,0,0,0.6);\n    animation: slideIn 0.3s ease-out;\n    font-family: 'Consolas', 'Monaco', 'Lucida Console', monospace;\n}\n\n@keyframes slideIn {\n    from { opacity: 0; transform: translateX(-20px); }\n    to { opacity: 1; transform: translateX(0); }\n}\n\n.question-card.removing {\n    animation: fadeOut 0.2s ease-in forwards;\n}\n\n@keyframes fadeOut {\n    from { opacity: 1; transform: scale(1); }\n    to { opacity: 0; transform: scale(0.95); }\n}\n\n.question-text {\n    font-weight: 600;\n    margin-bottom: 1rem;\n    color: var(--message-user-bg);\n    text-transform: uppercase;\n    font-size: 0.85rem;\n    letter-spacing: 1px;\n}\n\n.question-text::before {\n    content: \"> \";\n}\n\n.options-container {\n    display: flex;\n    flex-wrap: wrap;\n    gap: 0.5rem;\n}\n\n.option-btn {\n    background-color: #1a1a1a;\n    color: #0f0; /* Terminal Green */\n    border: 1px solid #333;\n    border-radius: 0.25rem;\n    padding: 0.4rem 0.8rem;\n    cursor: pointer;\n    transition: all 0.2s;\n    font-size: 0.85rem;\n    font-family: inherit;\n}\n\n.option-btn:hover {\n    background-color: #222;\n    border-color: #0f0;\n    box-shadow: 0 0 10px rgba(0, 255, 0, 0.2);\n}\n\n.option-btn.active {\n    background-color: #0f0;\n    color: #000;\n    border-color: #fff;\n    font-weight: bold;\n}\n\n.question-card .submit-btn {\n    margin-top: 1rem;\n    width: 100%;\n    border-radius: 0.25rem;\n    text-transform: uppercase;\n    font-weight: bold;\n    letter-spacing: 1px;\n}\n\n.question-card input[type=\"text\"] {\n    background-color: #111;\n    border: 1px solid #333;\n    color: #0f0;\n    font-family: inherit;\n    border-radius: 0.25rem;\n}\n\n.question-card input[type=\"text\"]:focus {\n    border-color: #0f0;\n    box-shadow: 0 0 5px rgba(0, 255, 0, 0.3);\n}\n\n@media (max-width: 768px) {\n    .question-card {\n        max-width: 95%;\n    }\n}\n\n/* Drive Mode Pulse Animation */\n.pulse-animation {\n    animation: pulse-info 1.5s infinite;\n}\n\n@keyframes pulse-info {\n    0% {\n        box-shadow: 0 0 0 0 rgba(13, 202, 240, 0.7);\n    }\n    70% {\n        box-shadow: 0 0 0 10px rgba(13, 202, 240, 0);\n    }\n    100% {\n        box-shadow: 0 0 0 0 rgba(13, 202, 240, 0);\n    }\n}\n",
        "encoding": "text"
    },
    "sw.js": {
        "content": "const CACHE_NAME = 'gemini-agent-v6'; // Bump version for fresh install\n\nself.addEventListener('install', (event) => {\n  console.log('Service Worker v6 installing...');\n  event.waitUntil(\n    caches.open(CACHE_NAME).then((cache) => {\n      // Pre-cache only essential, non-dynamic assets\n      // (Root path '/' removed to avoid caching redirects)\n      return cache.addAll([\n        '/static/style.css',\n        '/static/script.js',\n        '/static/icon.svg',\n        '/static/icon-192.png',\n        '/static/icon-512.png',\n        '/static/maskable-icon-512.png',\n        '/manifest.json'\n      ]);\n    }).catch((error) => {\n      console.error('Service Worker install failed:', error);\n    })\n  );\n});\n\nself.addEventListener('activate', (event) => {\n  console.log('Service Worker v6 activating...');\n  event.waitUntil(\n    caches.keys().then((cacheNames) => {\n      return Promise.all(\n        cacheNames.filter((cacheName) => {\n          return cacheName !== CACHE_NAME;\n        }).map((cacheName) => {\n          console.log(`[SW] Deleting old cache: ${cacheName}`);\n          return caches.delete(cacheName);\n        })\n      );\n    })\n  );\n  event.waitUntil(self.clients.claim()); // Take control of un-controlled clients\n});\n\nself.addEventListener('fetch', (event) => {\n  console.log('[SW] Fetching:', event.request.url);\n\n  // Network-first strategy for all requests\n  event.respondWith(\n    fetch(event.request)\n      .then((networkResponse) => {\n        // If the network response is good, cache it and return it\n        if (networkResponse.ok && networkResponse.type === 'basic' && event.request.method === 'GET') {\n          const clonedResponse = networkResponse.clone();\n          caches.open(CACHE_NAME).then((cache) => {\n            // Only cache requests for paths that typically don't change often and are not main HTML docs\n            const urlWithoutQuery = event.request.url.split('?')[0].replace(self.location.origin, '');\n            if (urlWithoutQuery.startsWith('/static/') || urlWithoutQuery === '/manifest.json') {\n                 console.log(`[SW] Caching network response for: ${event.request.url}`);\n                cache.put(event.request, clonedResponse);\n            }\n          });\n        }\n        return networkResponse;\n      })\n      .catch((error) => {\n        console.warn(`[SW] Network request failed for: ${event.request.url}. Trying cache.`, error);\n        // Fallback to cache if network fails\n        return caches.match(event.request).then((cachedResponse) => {\n          if (cachedResponse) {\n            console.log(`[SW] Serving from cache: ${event.request.url}`);\n            return cachedResponse;\n          }\n          // If neither network nor cache has a response, return a generic offline page or error\n          console.error(`[SW] No cache match for offline: ${event.request.url}`);\n          // For navigation requests, can show an offline page\n          if (event.request.mode === 'navigate') {\n            return new Response('<h1>Offline</h1><p>You are offline and this page is not available.</p>', { headers: { 'Content-Type': 'text/html' } });\n          }\n          // For other requests, return a network error\n          return new Response(null, { status: 503, statusText: 'Service Unavailable (Offline)' });\n        });\n      })\n  );\n});\n",
        "encoding": "text"
    }
}


# --- MODELS ---
import re
from typing import List, Optional, Dict, Union
from pydantic import BaseModel

class AgentLink(BaseModel):
    path: str
    description: Optional[str] = None

class AgentModel(BaseModel):
    id: Optional[str] = None
    name: str
    description: str
    category: str
    folder_name: str
    prompt: str
    type: str = "FunctionAgent"
    children: List[AgentLink] = []
    uses: List[AgentLink] = []
    projects: List[AgentLink] = []
    skills: List[str] = []
    parent: Optional[str] = None
    used_by: List[str] = []

    def to_markdown(self) -> str:
        """Serializes the agent to AGENT.md format with YAML frontmatter."""
        lines = ["---"]
        if self.id:
            lines.append(f"id: {self.id}")
        lines.append(f"name: {self.name}")
        lines.append(f"description: {self.description}")
        lines.append(f"type: {self.type}")
        
        if self.skills:
            lines.append("skills:")
            for skill in self.skills:
                lines.append(f"  - {skill}")
        
        def add_link_list(key, items: List[AgentLink]):
            if items:
                lines.append(f"{key}:")
                for item in items:
                    line = f"  - [[{item.path}]]"
                    if item.description:
                        line += f" # {item.description}"
                    lines.append(line)
        
        add_link_list("children", self.children)
        add_link_list("uses", self.uses)
        add_link_list("projects", self.projects)
        
        if self.parent:
            lines.append(f"parent: [[{self.parent}]]")
            
        if self.used_by:
            lines.append("used_by:")
            for ub in self.used_by:
                lines.append(f"  - [[{ub}]]")
        
        lines.append("---")
        lines.append(self.prompt)
        
        return "\n".join(lines)

    @classmethod
    def from_markdown(cls, content: str, category: str, folder_name: str) -> "AgentModel":
        """Parses an AGENT.md content into an AgentModel."""
        # Split by frontmatter delimiters
        parts = content.split("---")
        
        if len(parts) < 3:
            # Fallback if no frontmatter
            return cls(
                name=folder_name,
                description="",
                category=category,
                folder_name=folder_name,
                prompt=content.strip()
            )
        
        frontmatter_raw = parts[1].strip()
        prompt = "---".join(parts[2:]).strip()
        
        # Robust parsing for multi-line YAML-ish fields
        metadata = {}
        current_key = None
        for line in frontmatter_raw.splitlines():
            stripped = line.strip()
            if not stripped: continue
            
            # Key: Value or Key: (start of list)
            if ":" in line and not stripped.startswith("-"):
                if ":" in stripped:
                    key, value = stripped.split(":", 1)
                    current_key = key.strip()
                    metadata[current_key] = value.strip()
                else:
                    current_key = stripped.replace(":", "").strip()
                    metadata[current_key] = ""
            # Continued list item or indented block
            elif current_key:
                metadata[current_key] += "\n" + line # Keep indentation for lists
        
        def parse_links(value_str: str) -> List[AgentLink]:
            links = []
            for line in value_str.splitlines():
                # Extract [[path]]
                path_match = re.search(r"\[\[(.*?)\]\]", line)
                if path_match:
                    path = path_match.group(1)
                    # Extract description after #
                    comment_match = re.search(r"#\s*(.*)", line)
                    description = comment_match.group(1).strip() if comment_match else None
                    links.append(AgentLink(path=path, description=description))
            return links

        def extract_simple_paths(value_str: str) -> List[str]:
            return [l.path for l in parse_links(value_str)]

        def parse_simple_list(value_str: str) -> List[str]:
            items = []
            for line in value_str.splitlines():
                stripped = line.strip()
                if stripped.startswith("- "):
                    items.append(stripped[2:].strip())
            return items

        return cls(
            id=metadata.get("id"),
            name=metadata.get("name", folder_name),
            description=metadata.get("description", ""),
            category=category,
            folder_name=folder_name,
            prompt=prompt,
            type=metadata.get("type", "FunctionAgent"),
            children=parse_links(metadata.get("children", "")),
            uses=parse_links(metadata.get("uses", "")),
            projects=parse_links(metadata.get("projects", "")),
            skills=parse_simple_list(metadata.get("skills", "")),
            parent=extract_simple_paths(metadata.get("parent", ""))[0] if extract_simple_paths(metadata.get("parent", "")) else None,
            used_by=extract_simple_paths(metadata.get("used_by", ""))
        )


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

    def update_role(self, username: str, new_role: str) -> bool:
        if username not in self.users: return False
        if new_role not in ["user", "admin"]: return False
        self.users[username]["role"] = new_role
        self._save_users()
        return True

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
import sys
import re
import asyncio
import shutil
import uuid
import subprocess
import threading
from datetime import datetime, timezone
from typing import Optional, List, Dict, AsyncGenerator, Any

FALLBACK_MODELS = {
    "gemini-3-pro": "gemini-3-pro-preview",
    "gemini-3-flash": "gemini-3-flash-preview",
    "gemini-3": "gemini-3-flash-preview",
    "gemini-3-pro-preview": "gemini-3-flash-preview",
    "gemini-2.5-pro": "gemini-2.5-flash",
    "gemini-1.5-pro": "gemini-1.5-flash"
}

CAPACITY_KEYWORDS = ["429", "capacity", "quota", "exhausted", "rate limit", "not found", "404"]

def global_log(msg, level="INFO", user_data=None):
    # If user_data has a 'verbose_logging' setting, we might force INFO level or something.
    # For now, stick to 
    if LOG_LEVEL == "NONE":
        return
    if LOG_LEVEL == "INFO" and level == "DEBUG":
        return
        
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(f"[{ts}] [{level}] {msg}")
    except: pass

class ThreadedStreamReader:
    """Helper to read a pipe in a thread and provide an async interface."""
    def __init__(self, pipe, loop):
        self.pipe = pipe
        self.loop = loop
        self.queue = asyncio.Queue()
        self.thread = threading.Thread(target=self._read_pipe, daemon=True)
        self.thread.start()

    def _read_pipe(self):
        try:
            for line in iter(self.pipe.readline, b''):
                self.loop.call_soon_threadsafe(self.queue.put_nowait, line)
        finally:
            self.loop.call_soon_threadsafe(self.queue.put_nowait, None)

    async def readline(self):
        line = await self.queue.get()
        return line if line is not None else b''

class ThreadedProcess:
    """Minimal wrapper for subprocess.Popen to match asyncio.subprocess.Process."""
    def __init__(self, popen_proc, loop):
        self.proc = popen_proc
        self.loop = loop
        self.stdout = ThreadedStreamReader(popen_proc.stdout, loop) if popen_proc.stdout else None
        self.stderr = ThreadedStreamReader(popen_proc.stderr, loop) if popen_proc.stderr else None
        self.stdin = popen_proc.stdin # synchronous writing usually works ok if not blocked
        self.returncode = None

    async def wait(self):
        while self.proc.poll() is None:
            await asyncio.sleep(0.1)
        self.returncode = self.proc.returncode
        return self.returncode

    async def communicate(self, input=None):
        if input:
            self.proc.stdin.write(input)
            self.proc.stdin.flush()
        
        stdout_content = b''
        stderr_content = b''
        
        if self.stdout:
            while True:
                line = await self.stdout.readline()
                if not line: break
                stdout_content += line
        
        if self.stderr:
            while True:
                line = await self.stderr.readline()
                if not line: break
                stderr_content += line
                
        await self.wait()
        return stdout_content, stderr_content

    def terminate(self):
        self.proc.terminate()

class GeminiAgent:
    def __init__(self, model: str = "gemini-2.5-flash", working_dir: Optional[str] = None):
        self.model_name = model
        self.working_dir = working_dir or os.getcwd()
        self.session_file = os.path.join(self.working_dir, "user_sessions.json")
        self.gemini_cmd = shutil.which(GEMINI_CMD) or GEMINI_CMD
        self.user_data = self._load_user_data()
        self.yolo_mode = False
        self.active_tasks: Dict[str, asyncio.Task] = {}
        
        # Ensure prompts directory exists
        prompts_dir = os.path.join(self.working_dir, "prompts")
        if not os.path.exists(prompts_dir):
            os.makedirs(prompts_dir, exist_ok=True)

    def _load_user_data(self) -> Dict:
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, "r") as f:
                    data = json.load(f)
                    if not data: return {}
                    if isinstance(next(iter(data.values())), str):
                        return {uid: {"active_session": suid, "sessions": [suid], "session_tools": {}} for uid, suid in data.items()}
                    for uid in data:
                        if "sessions" not in data[uid]: data[uid]["sessions"] = []
                        if "active_session" not in data[uid]: data[uid]["active_session"] = None
                        if "session_tools" not in data[uid]: data[uid]["session_tools"] = {}
                        if "session_tags" not in data[uid]: data[uid]["session_tags"] = {}
                        if "pending_tools" not in data[uid]: data[uid]["pending_tools"] = []
                        if "pinned_sessions" not in data[uid]: data[uid]["pinned_sessions"] = []
                        if "session_metadata" not in data[uid]: data[uid]["session_metadata"] = {}
                        if "settings" not in data[uid]: data[uid]["settings"] = {"show_mic": True, "interactive_mode": True, "copy_formatted": False}
                        else:
                            # Ensure defaults for existing settings objects
                            if "copy_formatted" not in data[uid]["settings"]:
                                data[uid]["settings"]["copy_formatted"] = False
                    return data
            except: return {}
        return {}

    def _save_user_data(self):
        with open(self.session_file, "w") as f: json.dump(self.user_data, f, indent=2)

    def get_user_settings(self, user_id: str) -> Dict:
        if user_id not in self.user_data: return {"show_mic": True, "interactive_mode": True, "copy_formatted": False}
        return self.user_data[user_id].get("settings", {"show_mic": True, "interactive_mode": True, "copy_formatted": False})

    def update_user_settings(self, user_id: str, settings: Dict):
        if user_id not in self.user_data:
            self.user_data[user_id] = {"active_session": None, "sessions": [], "session_tools": {}, "pending_tools": [], "pinned_sessions": [], "session_metadata": {}, "settings": {"show_mic": True, "interactive_mode": True, "copy_formatted": False}}
        
        if "settings" not in self.user_data[user_id]:
            self.user_data[user_id]["settings"] = {"show_mic": True, "interactive_mode": True, "copy_formatted": False}
            
        self.user_data[user_id]["settings"].update(settings)
        self._save_user_data()

    async def _create_subprocess(self, args, **kwargs):
        try:
            # Try the standard asyncio approach first
            return await asyncio.create_subprocess_exec(*args, **kwargs)
        except NotImplementedError:
            if sys.platform == 'win32':
                # Robust fallback for Windows (works on ALL loops)
                global_log("asyncio subprocess not implemented, using ThreadedProcess fallback", level="INFO")
                from subprocess import Popen, PIPE
                loop = asyncio.get_running_loop()
                
                # Adapt kwargs for Popen
                popen_kwargs = {
                    "stdout": kwargs.get("stdout", PIPE),
                    "stderr": kwargs.get("stderr", PIPE),
                    "stdin": kwargs.get("stdin", PIPE),
                    "cwd": kwargs.get("cwd"),
                    "env": kwargs.get("env"),
                    "bufsize": 0 # Unbuffered for streaming
                }
                
                # If it's a list, we might need list2cmdline for shell consistency, 
                # but Popen handles lists well on Windows if NOT using shell=True.
                proc = Popen(args, **popen_kwargs)
                return ThreadedProcess(proc, loop)
            else:
                raise

    def toggle_pin(self, user_id: str, session_uuid: str) -> bool:
        if user_id not in self.user_data:
            self.user_data[user_id] = {"active_session": None, "sessions": [], "session_tools": {}, "pending_tools": [], "pinned_sessions": [], "session_metadata": {}}
        
        user_info = self.user_data[user_id]
        if "pinned_sessions" not in user_info: user_info["pinned_sessions"] = []
        
        if session_uuid in user_info["pinned_sessions"]:
            user_info["pinned_sessions"].remove(session_uuid)
            res = False
        else:
            user_info["pinned_sessions"].append(session_uuid)
            res = True
        
        self._save_user_data()
        return res

    def get_session_tools(self, user_id: str, session_uuid: str) -> List[str]:
        user_info = self.user_data.get(user_id)
        if not user_info: return []
        if session_uuid == "pending": return user_info.get("pending_tools", [])
        return user_info.get("session_tools", {}).get(session_uuid, [])

    def set_session_tools(self, user_id: str, session_uuid: str, tools: List[str]):
        if user_id not in self.user_data:
            self.user_data[user_id] = {"active_session": None, "sessions": [], "session_tools": {}, "pending_tools": [], "session_metadata": {}}
        if session_uuid == "pending":
            self.user_data[user_id]["pending_tools"] = tools
        else:
            if "session_tools" not in self.user_data[user_id]: self.user_data[user_id]["session_tools"] = {}
            self.user_data[user_id]["session_tools"][session_uuid] = tools
        self._save_user_data()

    def list_patterns(self) -> List[str]:
        return sorted([k for k in PATTERNS.keys() if k != "__explanations__"])

    async def apply_pattern(self, user_id: str, pattern_name: str, input_text: str, model: Optional[str] = None, file_paths: Optional[List[str]] = None) -> str:
        # Check if it's a custom prompt file
        prompts_dir = os.path.join(self.working_dir, "prompts")
        if os.path.exists(prompts_dir):
            # Try exact match first
            custom_path = os.path.join(prompts_dir, pattern_name)
            if os.path.exists(custom_path):
                try:
                    with open(custom_path, "r", encoding="utf-8") as f:
                        system = f.read()
                    return await self.generate_response(user_id, f"{system}\n\nUSER INPUT:\n{input_text}", model=model, file_paths=file_paths)
                except Exception as e:
                    return f"Error reading custom prompt '{pattern_name}': {str(e)}"

        # Fallback to system patterns
        system = PATTERNS.get(pattern_name)
        if not system: 
            # Try removing colon if present (common issue)
            clean_name = pattern_name.rstrip(":")
            system = PATTERNS.get(clean_name)
            
        if not system: return f"Error: Pattern '{pattern_name}' not found."
        return await self.generate_response(user_id, f"{system}\n\nUSER INPUT:\n{input_text}", model=model, file_paths=file_paths)

    def _filter_errors(self, err: str) -> str:
        err = re.sub(r".*?\[DEP0151\] DeprecationWarning:.*?(\n|$)", "", err)
        err = re.sub(r".*?Default \"index\" lookups for the main are deprecated for ES modules..*?(\n|$)", "", err)
        return "\n".join([s for s in err.splitlines() if s.strip()]).strip()

    def _get_text_content(self, content: Any) -> str:
        """Extracts plain text from potentially multimodal or structured content."""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, dict) and "text" in part:
                    text_parts.append(part["text"])
                elif isinstance(part, str):
                    text_parts.append(part)
            return "".join(text_parts)
        return str(content)

    def filter_title_text(self, text: str) -> str:
        """
        Filters out system instructions and file paths from the text to generate a clean title.
        """
        if not text:
            return "New Conversation"

        # 1. Remove [SYSTEM INSTRUCTION: ... ] blocks (including multi-line)
        text = re.sub(r"\[SYSTEM INSTRUCTION:.*?\]", "", text, flags=re.DOTALL)

        # 2. Remove file path references starting with @
        # Matches @ followed by non-whitespace characters
        text = re.sub(r"@\S+", "", text)

        # 3. Remove common file path patterns (absolute or relative)
        # Windows paths: C:\Users\..., D:\... (Stopped matching spaces to preserve sentence structure)
        text = re.sub(r"[a-zA-Z]:\\[\w\-.\\\\]+", "", text)
        # Unix paths: /var/log/..., /tmp/...
        text = re.sub(r"(?<!\w)/[\w\-./]+", "", text)

        # 4. Cleanup whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # 5. Fallback and truncation
        if not text or len(text) < 3:
            return "New Conversation"
            
        if len(text) > 50:
            return text[:47] + "..."
            
        return text

    async def stop_chat(self, user_id: str):
        task = self.active_tasks.pop(user_id, None)
        if task:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            return True
        return False

    async def _get_latest_session_uuid(self) -> Optional[str]:
        try:
            global_log("Executing --list-sessions...")
            proc = await self._create_subprocess([self.gemini_cmd, "--list-sessions"], stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=self.working_dir)
            stdout, stderr = await proc.communicate()
            content = (stdout.decode() + stderr.decode())
            matches = re.findall(r"\x20\[([a-fA-F0-9-]{36})\]", content)
            res = matches[-1] if matches else None
            global_log(f"Latest session ID found: {res}")
            return res
        except Exception as e:
            global_log(f"Error in _get_latest_session_uuid: {str(e)}")
            return None

    async def generate_response_stream(self, user_id: str, prompt: str, model: Optional[str] = None, file_paths: Optional[List[str]] = None, resume_session: Optional[str] = "AUTO", plan_mode: bool = False) -> AsyncGenerator[Dict, None]:
        def log_debug(msg): global_log(f"[{user_id}] {msg}", level="DEBUG")

        if user_id not in self.user_data:
            self.user_data[user_id] = {"active_session": None, "sessions": [], "session_tools": {}, "pending_tools": [], "session_metadata": {}}
        else:
            self.user_data[user_id].setdefault("sessions", [])
            self.user_data[user_id].setdefault("active_session", None)
            self.user_data[user_id].setdefault("session_tools", {})
            self.user_data[user_id].setdefault("pending_tools", [])
            self.user_data[user_id].setdefault("session_metadata", {})

        if resume_session == "AUTO":
            session_uuid = self.user_data[user_id].get("active_session")
        else:
            session_uuid = resume_session

        current_model = model or self.model_name

        if plan_mode:
            yield {"type": "plan_status", "status": "active", "message": "Entering Plan Mode..."}
        
        # System Prompt Injection for Interactive Mode
        settings = self.get_user_settings(user_id)
        if settings.get("interactive_mode", True):
            default_interactive = (
                "You can ask interactive multiple-choice or open-ended questions to the user in their preferred language (e.g., Greek).\n"
                "To trigger a question card, include a JSON block in your response using this format:\n"
                "{\"type\": \"question\", \"question\": \"Your question text here\", \"options\": [\"Option 1\", \"Option 2\"], \"allow_multiple\": false}\n"
                "- The 'question' and 'options' values should match the language of the conversation.\n"
                "- If 'allow_multiple' is true, users can select several options.\n"
                "- If 'options' is empty [], it is an open-ended question.\n"
                "The user's response will be sent back to you as a normal message."
            )
            global_setting = get_global_setting("interactive_mode_instructions")
            interactive_instruction = global_setting if global_setting is not None else default_interactive
            prompt = f"\n\n[SYSTEM INSTRUCTION: INTERACTIVE QUESTIONING ENABLED]\n{interactive_instruction}\n\n{prompt}"
        else:
            # Subtle instruction to avoid JSON questioning without being overly rigid about identity.
            prompt = f"\n\n[SYSTEM INSTRUCTION: Provide standard text responses only. Do not use JSON formatting for questions.]\n\n{prompt}"

        attempt = 0
        max_attempts = 2
        
        while attempt < max_attempts:
            attempt += 1
            enabled_tools = self.get_session_tools(user_id, session_uuid or "pending")
            log_debug(f"Enabled tools for this run: {enabled_tools}")
            
            args = [self.gemini_cmd, "--output-format", "stream-json"]
            args.extend(["--allowed-tools", ",".join(enabled_tools) if enabled_tools else "none"])
            
            if plan_mode:
                args.extend(["--approval-mode", "plan"])
            else:
                args.extend(["--approval-mode", "default"])
                
            if self.yolo_mode: args.append("--yolo")
            if session_uuid: args.extend(["--resume", session_uuid])
            if current_model: args.extend(["--model", current_model])
            args.extend(["--include-directories", self.working_dir])
            if file_paths:
                for fp in file_paths:
                    args.append(f"@{fp}")
            
            log_debug(f"Attempt {attempt}: Running command {' '.join(args)}")
            
            should_fallback = False
            proc = None
            stderr_buffer = []
            try:
                proc = await self._create_subprocess(
                    args, 
                    stdin=asyncio.subprocess.PIPE, 
                    stdout=asyncio.subprocess.PIPE, 
                    stderr=asyncio.subprocess.PIPE, 
                    cwd=self.working_dir
                )
                
                if prompt:
                    log_debug("Writing prompt to stdin...")
                    async def write_to_stdin(proc, data):
                        if hasattr(proc.stdin, 'drain'): # asyncio.StreamWriter
                            proc.stdin.write(data)
                            await proc.stdin.drain()
                            proc.stdin.close()
                        else: # Synchronous pipe from Popen
                            def sync_write():
                                proc.stdin.write(data)
                                proc.stdin.flush()
                                proc.stdin.close()
                            await asyncio.to_thread(sync_write)
                    
                    await write_to_stdin(proc, prompt.encode('utf-8'))
                
                async def capture_stderr(pipe):
                    while True:
                        line = await pipe.readline()
                        if not line: break
                        line_str = line.decode(errors='replace').strip()
                        log_debug(f"STDERR: {line_str}")
                        stderr_buffer.append(line_str)
                
                stderr_task = asyncio.create_task(capture_stderr(proc.stderr))

                log_debug("Starting to read stdout")
                current_message_content = ""
                json_buffer = ""
                in_json_block = False

                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        log_debug("Stdout closed (EOF)")
                        break
                    line_str = line.decode(errors='replace').strip()
                    if not line_str: continue
                    
                    log_debug(f"Received line ({len(line_str)} chars)")
                    try:
                        data = json.loads(line_str)
                        
                        # Handle interactive questioning protocol
                        if data.get("type") == "message" and data.get("role") == "assistant":
                            content = data.get("content", "")
                            
                            # Add to global buffer for full detection
                            current_message_content += content
                            
                            # Logic to hide JSON and potential markdown backticks from the stream
                            cleaned_content = ""
                            for char in content:
                                if (char == '{' or char == '`') and not in_json_block:
                                    # Potential start of JSON or markdown block
                                    in_json_block = True
                                    json_buffer = char
                                elif in_json_block:
                                    json_buffer += char
                                    # We check for the end of a potential JSON block or markdown block
                                    # If it ends with } or ` we might be at the end.
                                    if char == '}' or char == '`':
                                        # Let's see if we have a complete question JSON (potentially wrapped)
                                        # We use a greedy check in the buffer
                                        if '"type": "question"' in json_buffer or '"type":"question"' in json_buffer:
                                            # We need to decide if this block is COMPLETE.
                                            # If it's wrapped in backticks, we wait for the closing backticks.
                                            # For now, if we see a valid JSON question, we consider it "absorbed"
                                            # but we only clear the buffer if it's truly complete.
                                            
                                            # Simple heuristic: if it's a valid JSON, it's absorbed.
                                            try:
                                                # Try to extract JSON from the buffer (might have backticks)
                                                inner_json_match = re.search(r"\{\s*\"type\"\s*:\s*\"question\".*?\}", json_buffer, re.DOTALL)
                                                if inner_json_match:
                                                    # Check if it's balanced (minimal check)
                                                    json_text = inner_json_match.group(0)
                                                    json.loads(json_text)
                                                    
                                                    # If it was wrapped in backticks, and we just saw a backtick, 
                                                    # or it wasn't wrapped and we just saw }, then it's done.
                                                    is_wrapped = json_buffer.startswith('```')
                                                    if (is_wrapped and json_buffer.endswith('```')) or (not is_wrapped and json_buffer.endswith('}')):
                                                        in_json_block = False
                                                        json_buffer = ""
                                            except:
                                                pass # Not complete yet
                                        else:
                                            # Not a question yet, or ever. 
                                            # If the buffer is getting too large or we are sure it's not a question, release it.
                                            # For now, if it ends with ` and doesn't look like our JSON, release it.
                                            if char == '`':
                                                if len(json_buffer) > 10 and not ('"type"' in json_buffer):
                                                    cleaned_content += json_buffer
                                                    in_json_block = False
                                                    json_buffer = ""
                                            elif char == '}' and not ('"type"' in json_buffer):
                                                cleaned_content += json_buffer
                                                in_json_block = False
                                                json_buffer = ""
                                else:
                                    cleaned_content += char
                            
                            data["content"] = cleaned_content

                            # Global buffer handles full detection and yielding
                            # We update the regex to optionally swallow surrounding backticks and newlines
                            question_pattern = r"(?:```(?:json)?\s*)?\{\s*\"type\"\s*:\s*\"question\".*?\}(?:\s*```)?"
                            question_match = re.search(question_pattern, current_message_content, re.DOTALL)
                            if question_match:
                                try:
                                    full_match_text = question_match.group(0)
                                    # Extract JUST the JSON part for parsing
                                    json_only_match = re.search(r"\{\s*\"type\"\s*:\s*\"question\".*?\}", full_match_text, re.DOTALL)
                                    if json_only_match:
                                        question_data = json.loads(json_only_match.group(0))
                                        yield question_data
                                        current_message_content = current_message_content.replace(full_match_text, "")
                                except: pass
                            
                            # If we have nothing to show yet (still buffering JSON/markdown), don't yield this chunk's message
                            if not data["content"] and in_json_block:
                                continue

                        # Truncate large tool outputs
                        if data.get("type") == "tool_result" and "output" in data:
                            output = data["output"]
                            threshold = 20 * 1024 # 20KB
                            if len(output) > threshold:
                                truncated = output[:threshold]
                                # Save full output to a file
                                try:
                                    fname = f"output_{uuid.uuid4().hex}.txt"
                                    fpath = os.path.join(UPLOAD_DIR, fname)
                                    with open(fpath, "w", encoding="utf-8") as f:
                                        f.write(output)
                                    data["full_output_path"] = f"/uploads/{fname}"
                                    data["output"] = f"{truncated}\n\n[Output truncated. Full output available below.]"
                                    log_debug(f"Truncated tool output and saved to {fpath}")
                                except Exception as e:
                                    log_debug(f"Error saving full output: {str(e)}")
                                    data["output"] = f"{truncated}\n\n[Output truncated. Error saving full version.]"
                                
                                log_debug(f"Truncated tool output from {len(output)} to {len(data['output'])} bytes")

                        # Capture session ID
                        if data.get("type") == "init" and data.get("session_id"):
                            new_id = data["session_id"]
                            if not session_uuid:
                                log_debug(f"Captured session ID: {new_id}")
                                self.user_data[user_id]["active_session"] = new_id
                                if new_id not in self.user_data[user_id]["sessions"]:
                                    self.user_data[user_id]["sessions"].append(new_id)
                                
                                # Auto-name the session based on the first prompt
                                filtered_title = self.filter_title_text(prompt)
                                await self.update_session_title(user_id, new_id, filtered_title)
                                
                                # Promote pending tools to this new session
                                pending = self.user_data[user_id].get("pending_tools", [])
                                if pending:
                                    if "session_tools" not in self.user_data[user_id]:
                                        self.user_data[user_id]["session_tools"] = {}
                                    self.user_data[user_id]["session_tools"][new_id] = pending
                                    self.user_data[user_id]["pending_tools"] = []
                                    log_debug(f"Promoted pending tools to session {new_id}")

                                # Handle pending fork
                                pending_fork = self.user_data[user_id].get("pending_fork")
                                if pending_fork:
                                    if "session_forks" not in self.user_data[user_id]:
                                        self.user_data[user_id]["session_forks"] = {}
                                    self.user_data[user_id]["session_forks"][new_id] = {
                                        "parent": pending_fork["parent"],
                                        "fork_point": pending_fork["fork_point"]
                                    }
                                    if pending_fork.get("title"):
                                        if "custom_titles" not in self.user_data[user_id]:
                                            self.user_data[user_id]["custom_titles"] = {}
                                        self.user_data[user_id]["custom_titles"][new_id] = pending_fork["title"]
                                    if pending_fork.get("tags"):
                                        if "session_tags" not in self.user_data[user_id]:
                                            self.user_data[user_id]["session_tags"] = {}
                                        self.user_data[user_id]["session_tags"][new_id] = pending_fork["tags"]
                                    
                                    if pending_fork.get("tools"):
                                        if "session_tools" not in self.user_data[user_id]:
                                            self.user_data[user_id]["session_tools"] = {}
                                        self.user_data[user_id]["session_tools"][new_id] = pending_fork["tools"]
                                    
                                    del self.user_data[user_id]["pending_fork"]
                                    log_debug(f"Applied pending fork info to session {new_id}")

                                self._save_user_data()
                                session_uuid = new_id
                        
                        # Check for capacity error in JSON chunks
                        content_to_check = str(data).lower()
                        if any(k in content_to_check for k in CAPACITY_KEYWORDS) and attempt < max_attempts:
                            fallback = FALLBACK_MODELS.get(current_model)
                            if fallback:
                                log_debug(f"Capacity error detected in stdout, falling back to {fallback}")
                                yield {"type": "model_switch", "old_model": current_model, "new_model": fallback}
                                yield {"type": "message", "role": "assistant", "content": f"\n\n[Model {current_model} is currently busy or quota exhausted. Switching to {fallback} for a faster response...]\n\n"}
                                current_model = fallback
                                should_fallback = True
                                break
                        
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
                await stderr_task
                log_debug(f"Process exited with code {proc.returncode}")
                
                if plan_mode:
                    yield {"type": "plan_status", "status": "completed", "message": "Plan complete. Review proposed changes below."}
                
                # Check for capacity error in stderr if process failed
                if proc.returncode != 0 and not should_fallback:
                    err_text = "\n".join(stderr_buffer).lower()
                    if any(k in err_text for k in CAPACITY_KEYWORDS) and attempt < max_attempts:
                        fallback = FALLBACK_MODELS.get(current_model)
                        if fallback:
                            log_debug(f"Capacity error detected in stderr, falling back to {fallback}")
                            yield {"type": "model_switch", "old_model": current_model, "new_model": fallback}
                            yield {"type": "message", "role": "assistant", "content": f"\n\n[Model {current_model} is currently busy or quota exhausted. Switching to {fallback}...]\n\n"}
                            current_model = fallback
                            continue 

                    # If not a capacity error, yield generic exit code error
                    yield {"type": "error", "content": f"Exit code {proc.returncode}"}
                
                break 

            except Exception as e:
                log_debug(f"Exception in stream: {repr(e)}")
                yield {"type": "error", "content": f"Exception: {repr(e)}"}
                break
            finally:
                if proc and proc.returncode is None:
                    try:
                        proc.terminate()
                        await proc.wait()
                    except: pass

    async def generate_response(self, user_id: str, prompt: str, model: Optional[str] = None, file_paths: Optional[List[str]] = None, resume_session: Optional[str] = "AUTO") -> str:
        full_response = ""
        async for chunk in self.generate_response_stream(user_id, prompt, model, file_paths, resume_session=resume_session):
            if chunk.get("type") == "message":
                full_response += chunk.get("content", "")
            elif chunk.get("type") == "error":
                full_response += f"\n[Error: {chunk.get('content')}]"
            elif chunk.get("type") == "raw":
                 full_response += chunk.get("content", "") + "\n"
        return full_response.strip()

    async def update_session_title(self, user_id: str, uuid: str, new_title: str) -> bool:
        if user_id in self.user_data and uuid in self.user_data[user_id]["sessions"]:
            if "custom_titles" not in self.user_data[user_id]:
                self.user_data[user_id]["custom_titles"] = {}
            self.user_data[user_id]["custom_titles"][uuid] = new_title
            self._save_user_data()
            return True
        return False

    async def update_session_tags(self, user_id: str, uuid: str, tags: List[str]) -> bool:
        if user_id in self.user_data and uuid in self.user_data[user_id]["sessions"]:
            if "session_tags" not in self.user_data[user_id]:
                self.user_data[user_id]["session_tags"] = {}
            self.user_data[user_id]["session_tags"][uuid] = tags
            self._save_user_data()
            return True
        return False

    def get_unique_tags(self, user_id: str) -> List[str]:
        if user_id not in self.user_data: return []
        user_info = self.user_data[user_id]
        all_tags = set()
        for tags in user_info.get("session_tags", {}).values():
            for t in tags:
                all_tags.add(t)
        return sorted(list(all_tags))

    def is_user_session(self, user_id: str, session_uuid: str) -> bool:
        """Check if a session belongs to a user without filtering for sidebar."""
        if user_id not in self.user_data: return False
        return session_uuid in self.user_data[user_id].get("sessions", [])

    async def get_user_sessions(self, user_id: str, limit: Optional[int] = None, offset: int = 0, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        if user_id not in self.user_data:
            self.user_data[user_id] = {"active_session": None, "sessions": [], "session_tools": {}, "pending_tools": [], "pinned_sessions": [], "session_metadata": {}}
            self._save_user_data()
        
        user_info = self.user_data[user_id]
        uuids = user_info.get("sessions", [])
        custom_titles = user_info.get("custom_titles", {})
        session_tags = user_info.get("session_tags", {})
        session_metadata = user_info.get("session_metadata", {})
        session_forks = user_info.get("session_forks", {})
        
        if not uuids: return {"pinned": [], "history": [], "total_unpinned": 0}

        # Check if we have metadata for all sessions
        missing_metadata = [u for u in uuids if u not in session_metadata]
        
        all_sessions = []
        
        if not missing_metadata:
            # All metadata cached, build from cache
            pinned_uuids = user_info.get("pinned_sessions", [])
            for u in uuids:
                meta = session_metadata.get(u, {"original_title": "Unknown", "time": "Unknown"})
                
                # Check tags filter
                current_tags = session_tags.get(u, [])
                if tags:
                    if not all(tag in current_tags for tag in tags):
                        continue
                        
                title = custom_titles.get(u, meta.get("original_title", "Unknown"))
                
                all_sessions.append({
                    "uuid": u,
                    "title": title,
                    "time": meta.get("time", "Unknown"),
                    "active": (u == user_info.get("active_session")),
                    "pinned": (u in pinned_uuids),
                    "tags": current_tags
                })
            
            all_sessions = all_sessions[::-1]
            
        else:
            # Need to fetch from CLI
            try:
                global_log("Executing --list-sessions...")
                proc = await self._create_subprocess([self.gemini_cmd, "--list-sessions"], stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=self.working_dir)
                stdout, stderr = await proc.communicate()
                raw_content = stdout.decode() + stderr.decode()
                content = self._filter_errors(raw_content)
                
                pattern = r"^\s*\d+\.\s+(?P<title>.*?)\s+\((?P<time>.*?)\)\s+\[(?P<uuid>[a-fA-F0-9-]{36})\]"
                matches = list(re.finditer(pattern, content, re.MULTILINE))
                
                pinned_uuids = user_info.get("pinned_sessions", [])
                found_uuids = set()
                
                cli_sessions = []
                for m in matches:
                    info = m.groupdict()
                    u = info["uuid"]
                    found_uuids.add(u)
                    
                    # ONLY update metadata cache if the session belongs to this user
                    if u in uuids:
                        session_metadata[u] = {
                            "original_title": info["title"],
                            "time": info["time"]
                        }
                        
                        current_tags = session_tags.get(u, [])
                        if tags:
                            if not all(tag in current_tags for tag in tags):
                                continue
                                
                        title = custom_titles.get(u, info["title"])
                        
                        cli_sessions.append({
                            "uuid": u,
                            "title": title,
                            "time": info["time"],
                            "active": (u == user_info.get("active_session")),
                            "pinned": (u in pinned_uuids),
                            "tags": current_tags
                        })
                
                # Update user_data with new metadata
                self.user_data[user_id]["session_metadata"] = session_metadata
                
                # Sync sessions list
                valid_uuids = [u for u in uuids if u in found_uuids]
                if len(valid_uuids) != len(uuids):
                    self.user_data[user_id]["sessions"] = valid_uuids
                    for u in uuids:
                        if u not in valid_uuids:
                            session_metadata.pop(u, None)
                            custom_titles.pop(u, None)
                            session_tags.pop(u, None)
                            if u in pinned_uuids: pinned_uuids.remove(u)
                    
                    self.user_data[user_id]["session_metadata"] = session_metadata
                    self.user_data[user_id]["custom_titles"] = custom_titles
                    self.user_data[user_id]["session_tags"] = session_tags
                    self.user_data[user_id]["pinned_sessions"] = pinned_uuids
                
                self._save_user_data()
                all_sessions = cli_sessions
                all_sessions = all_sessions[::-1]
                
            except Exception as e:
                global_log(f"Error in get_user_sessions (fetching): {str(e)}")
                return {"pinned": [], "history": [], "total_unpinned": 0}
        
        # --- Grouping Logic: Display them as one (the latest fork) ---
        
        def get_root(u):
            """Find the root session UUID for a given session."""
            visited = set()
            curr = u
            while curr in session_forks and session_forks[curr].get("parent") and curr not in visited:
                visited.add(curr)
                curr = session_forks[curr]["parent"]
            return curr

        # Map root -> latest session in that group found in all_sessions
        # all_sessions is already ordered by time (newest first) because of [::-1]
        grouped_sessions = []
        seen_roots = set()
        
        for sess in all_sessions:
            root_uuid = get_root(sess["uuid"])
            if root_uuid not in seen_roots:
                grouped_sessions.append(sess)
                seen_roots.add(root_uuid)
            else:
                # If any fork in the group is active, the latest one shows it
                if sess["active"]:
                    for gs in grouped_sessions:
                        if get_root(gs["uuid"]) == root_uuid:
                            gs["has_active_fork"] = True
                            break

        # Common Pagination Logic
        pinned = [s for s in grouped_sessions if s["pinned"]]
        unpinned = [s for s in grouped_sessions if not s["pinned"]]
        
        total_unpinned = len(unpinned)
        
        if limit is not None:
            paged_unpinned = unpinned[offset : offset + limit]
        else:
            paged_unpinned = unpinned[offset:]
            
        return {
            "pinned": pinned if offset == 0 else [],
            "history": paged_unpinned,
            "total_unpinned": total_unpinned
        }

    async def search_sessions(self, user_id: str, query: str) -> List[Dict]:
        sessions_data = await self.get_user_sessions(user_id)
        if not query:
            return sessions_data.get("pinned", []) + sessions_data.get("history", [])
        
        all_sessions = sessions_data.get("pinned", []) + sessions_data.get("history", [])
        if not all_sessions: return []
        
        query = query.lower()
        results = []
        
        home = os.path.expanduser("~")
        gemini_tmp_base = os.path.join(home, ".gemini", "tmp")
        
        for sess in all_sessions:
            match = False
            # Check title
            if query in sess.get("title", "").lower():
                match = True
            
            if not match:
                # Check messages and attachments in the JSON file
                uuid_start = sess["uuid"].split('-')[0]
                import glob
                search_path = os.path.join(gemini_tmp_base, "*", "chats", f"*{uuid_start}*.json")
                files = glob.glob(search_path)
                if files:
                    try:
                        with open(files[0], 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            for msg in data.get("messages", []):
                                content_text = self._get_text_content(msg.get("content", ""))
                                if query in content_text.lower():
                                    match = True; break
                    except: pass
            
            if match:
                results.append(sess)
        
        return results

    async def get_session_messages(self, session_uuid: str, limit: Optional[int] = None, offset: int = 0) -> Dict:
        try:
            uuid_start = session_uuid.split('-')[0]
            home = os.path.expanduser("~")
            gemini_tmp_base = os.path.join(home, ".gemini", "tmp")
            if not os.path.exists(gemini_tmp_base): return {"messages": [], "total": 0}
            import glob
            search_path = os.path.join(gemini_tmp_base, "*", "chats", f"*{uuid_start}*.json")
            files = glob.glob(search_path)
            if not files: return {"messages": [], "total": 0}
            files.sort(key=os.path.getmtime, reverse=True)
            with open(files[0], 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_messages = data.get("messages", [])
                total = len(all_messages)
                if limit is not None:
                    start = max(0, total - offset - limit); end = max(0, total - offset)
                    messages_to_process = all_messages[start:end]
                else: 
                    start = 0
                    messages_to_process = all_messages
                messages = []
                for idx, msg in enumerate(messages_to_process):
                    content = msg.get("content", "")
                    content_text = self._get_text_content(content)
                    if not content_text or content_text.strip() == "": continue
                    messages.append({
                        "role": "user" if msg.get("type") == "user" else "bot", 
                        "content": content_text,
                        "raw_index": start + idx
                    })
                return {"messages": messages, "total": total}
        except Exception as e:
            print(f"Error loading session messages: {str(e)}")
            return {"messages": [], "total": 0}

    async def switch_session(self, user_id: str, uuid: str) -> bool:
        if user_id in self.user_data and uuid in self.user_data[user_id]["sessions"]:
            self.user_data[user_id]["active_session"] = uuid
            self._save_user_data()
            return True
        return False

    async def clone_session(self, user_id: str, original_uuid: str, message_index: int) -> Optional[str]:
        """
        Clone a session up to a certain message index.
        Returns the new session UUID if successful.
        """
        if user_id not in self.user_data or original_uuid not in self.user_data[user_id]["sessions"]:
            return None

        try:
            if message_index == -1:
                # We want to start a new session but linked to this tree
                user_info = self.user_data[user_id]
                user_info["active_session"] = None # Force new session in CLI
                
                # Store pending info to apply to the NEXT session created
                user_info["pending_fork"] = {
                    "parent": original_uuid,
                    "fork_point": -1,
                    "title": user_info.get("custom_titles", {}).get(original_uuid),
                    "tags": list(user_info.get("session_tags", {}).get(original_uuid, [])),
                    "tools": list(user_info.get("session_tools", {}).get(original_uuid, []))
                }
                
                self._save_user_data()
                return "pending" # Frontend will handle this

            uuid_start = original_uuid.split('-')[0]
            home = os.path.expanduser("~")
            gemini_tmp_base = os.path.join(home, ".gemini", "tmp")
            import glob
            search_path = os.path.join(gemini_tmp_base, "*", "chats", f"*{uuid_start}*.json")
            files = glob.glob(search_path)
            if not files: return None
            files.sort(key=os.path.getmtime, reverse=True)
            
            with open(files[0], 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Truncate messages. message_index is 0-based.
            # If message_index is 5, we keep 0, 1, 2, 3, 4, 5 (total 6 messages)
            data["messages"] = data["messages"][:message_index + 1]
            
            # Generate new UUID
            new_uuid = str(uuid.uuid4())
            data["sessionId"] = new_uuid
            data["startTime"] = datetime.now(timezone.utc).isoformat()
            data["lastUpdated"] = data["startTime"]
            
            # Save to new file in the same directory as original
            original_dir = os.path.dirname(files[0])
            new_filename = f"session-{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M')}-{new_uuid[:8]}.json"
            new_path = os.path.join(original_dir, new_filename)
            
            with open(new_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            # Update user_data
            user_info = self.user_data[user_id]
            user_info["sessions"].append(new_uuid)
            user_info["active_session"] = new_uuid
            
            # Inherit tags and title if they exist
            if "custom_titles" in user_info and original_uuid in user_info["custom_titles"]:
                user_info["custom_titles"][new_uuid] = user_info["custom_titles"][original_uuid]
            
            if "session_tags" in user_info and original_uuid in user_info["session_tags"]:
                user_info["session_tags"][new_uuid] = list(user_info["session_tags"][original_uuid])
            
            # Inherit tools
            if "session_tools" in user_info and original_uuid in user_info["session_tools"]:
                user_info["session_tools"][new_uuid] = list(user_info["session_tools"][original_uuid])
            
            # Track fork relationship
            if "session_forks" not in user_info:
                user_info["session_forks"] = {}
            user_info["session_forks"][new_uuid] = {
                "parent": original_uuid,
                "fork_point": message_index
            }
            
            # Also inherit metadata (original title etc)
            if "session_metadata" in user_info and original_uuid in user_info["session_metadata"]:
                user_info["session_metadata"][new_uuid] = dict(user_info["session_metadata"][original_uuid])
            
            self._save_user_data()
            return new_uuid
            
        except Exception as e:
            global_log(f"Error cloning session {original_uuid}: {str(e)}", level="ERROR")
            return None

    def get_session_forks(self, user_id: str, session_uuid: str) -> Dict[int, List[str]]:
        """
        Get all forks related to this session, organized by fork point.
        Returns a dict: { message_index: [uuid1, uuid2, ...] }
        """
        if user_id not in self.user_data: return {}
        user_info = self.user_data[user_id]
        forks_info = user_info.get("session_forks", {})
        
        fork_map = {}

        def add_to_map(index, uid):
            if index not in fork_map: fork_map[index] = []
            if uid not in fork_map[index]: fork_map[index].append(uid)

        # Current session's parent and fork point (if any)
        my_info = forks_info.get(session_uuid)
        parent_uuid = my_info["parent"] if my_info else None
        my_fork_point = my_info["fork_point"] if my_info else None

        # 1. Any children of the current session
        for u, info in forks_info.items():
            if info["parent"] == session_uuid:
                add_to_map(info["fork_point"], u)
        
        # 2. If we have a parent, we are a fork at 'my_fork_point'
        # The parent is a "branch" at that point, and so are our siblings
        if parent_uuid:
            add_to_map(my_fork_point, parent_uuid)
            for u, info in forks_info.items():
                if u != session_uuid and info["parent"] == parent_uuid and info["fork_point"] == my_fork_point:
                    add_to_map(my_fork_point, u)
            
        return fork_map

    def get_fork_graph(self, user_id: str) -> Dict[str, Dict]:
        """Get the full fork graph for all sessions of a user."""
        if user_id not in self.user_data: return {}
        user_info = self.user_data[user_id]
        forks_info = user_info.get("session_forks", {})
        custom_titles = user_info.get("custom_titles", {})
        session_metadata = user_info.get("session_metadata", {})
        sessions = user_info.get("sessions", [])

        graph = {}
        for uuid in sessions:
            info = forks_info.get(uuid, {})
            meta = session_metadata.get(uuid, {})
            title = custom_titles.get(uuid, meta.get("original_title", "Untitled Chat"))
            
            graph[uuid] = {
                "parent": info.get("parent"),
                "fork_point": info.get("fork_point"),
                "title": title
            }
        return graph

    async def sync_session_updates(self, user_id: str, session_uuid: str, title: Optional[str] = None, tags: Optional[List[str]] = None):
        """Sync title/tags across all related forks."""
        if user_id not in self.user_data: return
        user_info = self.user_data[user_id]
        forks_info = user_info.get("session_forks", {})
        
        # Find the root of the tree or just collect all related
        related_uuids = {session_uuid}
        
        # Simple iterative search to find all connected nodes in the fork tree
        changed = True
        while changed:
            changed = False
            for u, info in forks_info.items():
                if u in related_uuids and info["parent"] not in related_uuids:
                    related_uuids.add(info["parent"])
                    changed = True
                if info["parent"] in related_uuids and u not in related_uuids:
                    related_uuids.add(u)
                    changed = True
        
        # Apply updates
        for u in related_uuids:
            if title is not None:
                if "custom_titles" not in user_info: user_info["custom_titles"] = {}
                user_info["custom_titles"][u] = title
            if tags is not None:
                if "session_tags" not in user_info: user_info["session_tags"] = {}
                user_info["session_tags"][u] = tags
                
        self._save_user_data()

    async def new_session(self, user_id: str):
        self.user_data.setdefault(user_id, {})["active_session"] = None
        self.user_data[user_id].pop("pending_fork", None)
        self._save_user_data()

    async def delete_specific_session(self, user_id: str, uuid: str) -> bool:
        if user_id not in self.user_data or uuid not in self.user_data[user_id]["sessions"]:
            return False
            
        user_info = self.user_data[user_id]
        forks_info = user_info.get("session_forks", {})
        
        # Find all related sessions in the tree
        related_uuids = {uuid}
        changed = True
        while changed:
            changed = False
            for u, info in forks_info.items():
                parent = info.get("parent")
                if u in related_uuids and parent and parent not in related_uuids:
                    related_uuids.add(parent)
                    changed = True
                if parent in related_uuids and u not in related_uuids:
                    related_uuids.add(u)
                    changed = True

        success = True
        for target_uuid in list(related_uuids):
            try:
                # 1. Check if any OTHER user still has this session
                is_tracked_by_others = False
                for other_user_id, other_user_info in self.user_data.items():
                    if other_user_id == user_id: continue
                    if target_uuid in other_user_info.get("sessions", []):
                        is_tracked_by_others = True
                        break

                # 2. Only delete from CLI if no other users are tracking it
                if not is_tracked_by_others:
                    await (await self._create_subprocess([self.gemini_cmd, "--delete-session", target_uuid], cwd=self.working_dir)).communicate()
                
                # 3. Cleanup local tracking
                if target_uuid in user_info["sessions"]:
                    user_info["sessions"].remove(target_uuid)
                
                if user_info.get("active_session") == target_uuid:
                    user_info["active_session"] = None
                
                if "session_metadata" in user_info and target_uuid in user_info["session_metadata"]:
                    del user_info["session_metadata"][target_uuid]
                
                if "custom_titles" in user_info and target_uuid in user_info["custom_titles"]:
                    del user_info["custom_titles"][target_uuid]
                
                if "session_tags" in user_info and target_uuid in user_info["session_tags"]:
                    del user_info["session_tags"][target_uuid]
                
                if "session_forks" in user_info and target_uuid in user_info["session_forks"]:
                    del user_info["session_forks"][target_uuid]
                    
            except Exception as e:
                global_log(f"Error deleting session {target_uuid}: {str(e)}", level="ERROR")
                success = False
        
        self._save_user_data()
        return success

    async def clear_all_session_tags(self) -> int:
        """Clear session_tags for all users."""
        count = 0
        for user_id in self.user_data:
            if "session_tags" in self.user_data[user_id]:
                count += len(self.user_data[user_id]["session_tags"])
                self.user_data[user_id]["session_tags"] = {}
        self._save_user_data()
        return count

    async def share_session(self, user_id: str, session_uuid: str, target_username: str, user_manager: Any) -> bool:
        """
        Share a session with another user.
        Fails silently if target_username does not exist.
        """
        # 1. Verify user_id has access to session_uuid
        if user_id not in self.user_data or session_uuid not in self.user_data[user_id].get("sessions", []):
            return False

        # 2. Verify target_username exists via UserManager
        if target_username not in user_manager.users:
            return False

        # 3. Add session_uuid to target_username's session list in user_data
        if target_username not in self.user_data:
            self.user_data[target_username] = {
                "active_session": None, 
                "sessions": [], 
                "session_tools": {}, 
                "pending_tools": [], 
                "pinned_sessions": [], 
                "session_metadata": {},
                "settings": {"show_mic": True, "interactive_mode": True, "copy_formatted": False}
            }
        
        target_info = self.user_data[target_username]
        if "sessions" not in target_info: target_info["sessions"] = []
        if session_uuid not in target_info["sessions"]:
            target_info["sessions"].append(session_uuid)

        # 4. Copy custom_titles, session_tags, session_metadata, and session_tools to the target user
        source_info = self.user_data[user_id]
        
        if "custom_titles" in source_info and session_uuid in source_info["custom_titles"]:
            target_info.setdefault("custom_titles", {})[session_uuid] = source_info["custom_titles"][session_uuid]
            
        if "session_tags" in source_info and session_uuid in source_info["session_tags"]:
            target_info.setdefault("session_tags", {})[session_uuid] = list(source_info["session_tags"][session_uuid])
            
        if "session_metadata" in source_info and session_uuid in source_info["session_metadata"]:
            target_info.setdefault("session_metadata", {})[session_uuid] = dict(source_info["session_metadata"][session_uuid])
            
        if "session_tools" in source_info and session_uuid in source_info["session_tools"]:
            target_info.setdefault("session_tools", {})[session_uuid] = list(source_info["session_tools"][session_uuid])

        # 5. Save user_sessions.json
        self._save_user_data()
        return True

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


import os
import pypandoc
import logging
import pandas as pd

logger = logging.getLogger(__name__)

class PandocMissingError(RuntimeError):
    """Raised when pandoc is not found on the system."""
    pass

class ConversionServiceError(RuntimeError):
    """Raised when conversion fails."""
    pass

class FileConversionService:
    def __init__(self):
        self._pandoc_available = False
        try:
            pypandoc.get_pandoc_version()
            self._pandoc_available = True
        except OSError:
            logger.warning("Pandoc not found. DOCX conversion will fail. Please install pandoc.")

    def convert_to_markdown(self, file_path: str) -> str:
        """
        Converts a .docx or .xlsx file to markdown.
        Returns the path to the converted .md file.
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in [".docx", ".xlsx"]:
            raise ValueError(f"Unsupported file extension: {file_ext}")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        output_path = os.path.splitext(file_path)[0] + ".md"
        
        try:
            if file_ext == ".docx":
                if not self._pandoc_available:
                    raise PandocMissingError("Pandoc is not available for .docx conversion.")
                
                # For docx, we convert to gfm (GitHub Flavored Markdown)
                # We explicitly do NOT use --extract-media to ensure images are not kept.
                pypandoc.convert_file(
                    file_path, 
                    'gfm', 
                    outputfile=output_path,
                    extra_args=['--wrap=none']
                )
            elif file_ext == ".xlsx":
                # For xlsx, use pandas to read all sheets and convert to markdown tables
                # This does not depend on pandoc
                all_sheets = pd.read_excel(file_path, sheet_name=None)
                md_content = []
                for sheet_name, df in all_sheets.items():
                    md_content.append(f"## Sheet: {sheet_name}\n")
                    try:
                        md_content.append(df.to_markdown(index=False))
                    except ImportError:
                        md_content.append(df.to_string(index=False))
                    md_content.append("\n\n")
                
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(md_content))
            
            return output_path
        except (PandocMissingError, FileNotFoundError, ValueError):
            # Re-raise expected errors
            raise
        except Exception as e:
            logger.error(f"Error converting file {file_path} to markdown: {e}")
            raise ConversionServiceError(f"Conversion failed: {e}")


import os
import shutil
import asyncio
import logging
import uuid
import sys
import subprocess
from datetime import datetime

logger = logging.getLogger(__name__)

def global_log(msg, level="INFO"):
    if LOG_LEVEL == "NONE":
        return
    if LOG_LEVEL == "INFO" and level == "DEBUG":
        return
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(f"[{ts}] [{level}] [PDFService] {msg}")
    except: pass

class PDFService:
    def __init__(self):
        self.gs_path = self._find_ghostscript()
        if self.gs_path:
            global_log(f"Ghostscript found at: {self.gs_path}", level="INFO")
        else:
            global_log("Ghostscript not found. PDF compression will be skipped.", level="WARNING")

    def _find_ghostscript(self):
        # Check for common Ghostscript executable names
        for name in ["gswin64c", "gswin32c", "gs"]:
            path = shutil.which(name)
            if path:
                return path
        return None

    def is_gs_available(self):
        return self.gs_path is not None

    async def compress_pdf(self, input_path: str, output_path: str) -> str:
        """
        Compresses a PDF file using Ghostscript.
        Returns the path to the compressed file if successful and smaller,
        otherwise returns the original input_path.
        
        Uses synchronous subprocess.run in a thread for maximum reliability on Windows.
        """
        if not self.is_gs_available():
            return input_path

        if not os.path.exists(input_path):
            global_log(f"Input file not found: {input_path}", level="ERROR")
            return input_path

        # Create safe temporary paths to avoid encoding issues with Ghostscript on Windows
        base_dir = os.path.dirname(input_path)
        safe_id = uuid.uuid4().hex
        safe_in_path = os.path.join(base_dir, f"gs_in_{safe_id}.pdf")
        safe_out_path = os.path.join(base_dir, f"gs_out_{safe_id}.pdf")
        
        try:
            # Copy input to safe path
            shutil.copy2(input_path, safe_in_path)
            
            # Ghostscript command for ebook quality (150 dpi)
            cmd = [
                self.gs_path,
                "-sDEVICE=pdfwrite",
                "-dCompatibilityLevel=1.4",
                "-dPDFSETTINGS=/ebook",
                "-dNOPAUSE",
                "-dQUIET",
                "-dBATCH",
                f"-sOutputFile={safe_out_path}",
                safe_in_path
            ]

            global_log(f"Starting compression (sync thread): {input_path}", level="INFO")
            
            # Using asyncio.to_thread to run the synchronous subprocess call
            # This bypasses all Proactor/Selector event loop issues on Windows.
            def run_sync():
                return subprocess.run(cmd, capture_output=True, text=False)

            result = await asyncio.to_thread(run_sync)

            if result.returncode != 0:
                stderr_text = result.stderr.decode(errors='replace')
                global_log(f"Ghostscript failed with return code {result.returncode}: {stderr_text}", level="ERROR")
                return input_path

            if not os.path.exists(safe_out_path):
                global_log(f"Ghostscript finished but output file missing: {safe_out_path}", level="ERROR")
                return input_path

            # Compare sizes
            original_size = os.path.getsize(input_path)
            compressed_size = os.path.getsize(safe_out_path)
            
            reduction = original_size - compressed_size
            if reduction > 0:
                percent = (reduction / original_size) * 100
                global_log(f"Compression successful: {original_size} -> {compressed_size} ({percent:.1f}% reduction)", level="INFO")
                
                # Move safe output to final destination
                shutil.move(safe_out_path, output_path)
                return output_path
            else:
                global_log(f"Compression did not reduce size ({original_size} -> {compressed_size}). Keeping original.", level="INFO")
                return input_path

        except Exception as e:
            global_log(f"Error during PDF compression: {repr(e)}", level="ERROR")
            return input_path
        finally:
            # Clean up temp files
            if os.path.exists(safe_in_path):
                try: os.remove(safe_in_path)
                except: pass
            if os.path.exists(safe_out_path):
                try: os.remove(safe_out_path)
                except: pass


import os
import shutil
import glob
import re
from typing import List, Optional

class AgentManager:
    def __init__(self):
        self.base_dir = AGENT_BASE_DIR
        self.project_root = os.getcwd()
        self._ensure_base_dir()

    def _ensure_base_dir(self):
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir, exist_ok=True)

    def _get_agent_path(self, category: str, folder_name: str) -> str:
        return os.path.join(self.base_dir, category, folder_name, "AGENT.md")

    def _get_root_agent_path(self) -> str:
        return os.path.join(self.project_root, "AGENT.md")

    def list_agents(self) -> List[AgentModel]:
        """Lists all agents by recursively scanning the base directory."""
        agents = []
        pattern = os.path.join(self.base_dir, "**", "AGENT.md")
        files = glob.glob(pattern, recursive=True)
        
        for file_path in files:
            try:
                rel_path = os.path.relpath(file_path, self.base_dir)
                parts = rel_path.split(os.sep)
                
                if len(parts) >= 3:
                    category = parts[0]
                    folder_name = parts[1]
                    
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        
                    agent = AgentModel.from_markdown(content, category, folder_name)
                    agents.append(agent)
            except Exception as e:
                print(f"Error loading agent from {file_path}: {e}")
                continue
                
        return agents

    def get_agent(self, category: str, folder_name: str) -> Optional[AgentModel]:
        """Reads a specific agent."""
        path = self._get_agent_path(category, folder_name)
        if not os.path.exists(path):
            return None
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return AgentModel.from_markdown(content, category, folder_name)
        except Exception as e:
            print(f"Error reading agent {category}/{folder_name}: {e}")
            return None

    def save_agent(self, agent: AgentModel) -> bool:
        """Saves or updates an agent."""
        if ".." in agent.category or ".." in agent.folder_name:
            return False
            
        dir_path = os.path.join(self.base_dir, agent.category, agent.folder_name)
        os.makedirs(dir_path, exist_ok=True)
        
        file_path = os.path.join(dir_path, "AGENT.md")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(agent.to_markdown())
            return True
        except Exception as e:
            print(f"Error saving agent {agent.name}: {e}")
            return False

    def delete_agent(self, category: str, folder_name: str) -> bool:
        """Deletes an agent folder."""
        if ".." in category or ".." in folder_name:
            return False
            
        dir_path = os.path.join(self.base_dir, category, folder_name)
        if os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
                cat_path = os.path.join(self.base_dir, category)
                if os.path.exists(cat_path) and not os.listdir(cat_path):
                    os.rmdir(cat_path)
                return True
            except Exception as e:
                print(f"Error deleting agent {category}/{folder_name}: {e}")
                return False
        return False

    def get_root_orchestrator(self) -> Optional[AgentModel]:
        """Reads the root AGENT.md file."""
        path = self._get_root_agent_path()
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return AgentModel.from_markdown(content, "root", "root")
        except Exception as e:
            print(f"Error reading root orchestrator: {e}")
            return None

    def save_root_orchestrator(self, agent: AgentModel) -> bool:
        """Saves the root AGENT.md file."""
        path = self._get_root_agent_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(agent.to_markdown())
            return True
        except Exception as e:
            print(f"Error saving root orchestrator: {e}")
            return False

    def initialize_root_orchestrator(self):
        """Creates a default root AGENT.md if it doesn't exist."""
        path = self._get_root_agent_path()
        if not os.path.exists(path):
            root_agent = AgentModel(
                name="Root Orchestrator",
                description="The central AI agent that manages sub-agents.",
                category="root",
                folder_name="root",
                type="Orchestrator",
                prompt="You are the Root Orchestrator. You manage several sub-agents to fulfill user requests."
            )
            self.save_root_orchestrator(root_agent)

    def set_agent_enabled(self, category: str, folder_name: str, enabled: bool) -> bool:
        """Links or unlinks a sub-agent to the root orchestrator."""
        root = self.get_root_orchestrator()
        if not root:
            self.initialize_root_orchestrator()
            root = self.get_root_orchestrator()
            
        agent = self.get_agent(category, folder_name)
        if not agent:
            return False
            
        agent_abs_path = self._get_agent_path(category, folder_name)
        agent_rel_path = os.path.relpath(agent_abs_path, self.project_root).replace(os.sep, '/')
        
        root_rel_path = "AGENT.md"
        
        # Helper to find link by path
        def find_link_index(links: List[AgentLink], path: str):
            for i, link in enumerate(links):
                if link.path == path: return i
            return -1

        if enabled:
            # Link TO root
            if find_link_index(root.children, agent_rel_path) == -1:
                root.children.append(AgentLink(path=agent_rel_path, description=agent.description))
            # Link FROM agent
            agent.parent = root_rel_path
            if root_rel_path not in agent.used_by:
                agent.used_by.append(root_rel_path)
        else:
            # Unlink FROM root
            idx = find_link_index(root.children, agent_rel_path)
            if idx != -1:
                root.children.pop(idx)
            # Unlink FROM agent
            agent.parent = None
            if root_rel_path in agent.used_by:
                agent.used_by.remove(root_rel_path)
                
        success_root = self.save_root_orchestrator(root)
        success_agent = self.save_agent(agent)
        
        return success_root and success_agent

    def validate_orchestration(self) -> List[str]:
        """Validates that all enabled agents are referenced in the root prompt."""
        root = self.get_root_orchestrator()
        if not root:
            return []
            
        warnings = []
        for child_link in root.children:
            child_path = child_link.path
            full_path = os.path.join(self.project_root, child_path)
            if not os.path.exists(full_path):
                warnings.append(f"Referenced agent at {child_path} does not exist.")
                continue
                
            try:
                rel_to_base = os.path.relpath(full_path, self.base_dir)
                parts = rel_to_base.split(os.sep)
                if len(parts) >= 2:
                    category = parts[0]
                    folder_name = parts[1]
                    child_agent = self.get_agent(category, folder_name)
                    if child_agent:
                        if child_agent.name not in root.prompt and child_agent.folder_name not in root.prompt and child_path not in root.prompt:
                            warnings.append(f"Agent '{child_agent.name}' is enabled but not referenced in the Orchestrator's prompt.")
            except Exception:
                continue
                
        return warnings

    def initialize_defaults(self):
        """Initializes default agents if they don't exist."""
        fabric_path = self._get_agent_path("functions", "fabric")
        if not os.path.exists(fabric_path):
            fabric_agent = AgentModel(
                name="Fabric Agent",
                description="Bridge to Fabric patterns and prompts.",
                category="functions",
                folder_name="fabric",
                prompt="You are a Fabric orchestrator. You can use any of the available patterns to process input."
            )
            self.save_agent(fabric_agent)
        
        self.initialize_root_orchestrator()


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
import asyncio
import re
import uuid
from datetime import datetime



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
    sessions_data = await agent.get_user_sessions(user)
    all_sessions_list = sessions_data.get("pinned", []) + sessions_data.get("history", [])
    active_session = next((s for s in all_sessions_list if s.get('active')), None)
    initial_messages = []
    has_more = False
    total_messages = 0
    if active_session:
        msg_data = await agent.get_session_messages(active_session['uuid'], limit=20)
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
        user_settings=user_settings
    )

@chat_router.get("/settings")
async def get_settings(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    return agent.get_user_settings(user)

@chat_router.post("/settings")
async def update_settings(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    data = await request.json()
    agent.update_user_settings(user, data)
    return {"success": True}

@chat_router.get("/sessions")
async def get_sess(request: Request, limit: Optional[int] = None, offset: int = 0, tags: Optional[str] = None, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    tag_list = tags.split(",") if tags else None
    return await agent.get_user_sessions(user, limit=limit, offset=offset, tags=tag_list)

@chat_router.get("/sessions/search")
async def search_sess(request: Request, q: str = "", user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    return await agent.search_sessions(user, q)

@chat_router.get("/sessions/{session_uuid}/messages")
async def get_sess_messages(session_uuid: str, request: Request, limit: Optional[int] = None, offset: int = 0, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    # Security: check if this session belongs to the user
    if not agent.is_user_session(user, session_uuid):
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

@chat_router.post("/sessions/{session_uuid}/share")
async def share_sess(session_uuid: str, request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    user_manager = request.app.state.user_manager
    if not user: raise HTTPException(401)
    
    # 1. Verify session ownership (or participation)
    if not agent.is_user_session(user, session_uuid):
        raise HTTPException(403, "Access denied")
    
    data = await request.json()
    target_username = data.get("username")
    if not target_username:
        raise HTTPException(400, "Username is required")
        
    # 2. Call agent.share_session
    success = await agent.share_session(user, session_uuid, target_username, user_manager)
    return {"success": success}

@chat_router.post("/sessions/{session_uuid}/pin")
async def pin_sess(session_uuid: str, request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    # Security: check if this session belongs to the user
    if not agent.is_user_session(user, session_uuid):
        raise HTTPException(403, "Access denied")
    return {"pinned": agent.toggle_pin(user, session_uuid)}

@chat_router.post("/sessions/{session_uuid}/clone")
async def clone_sess(session_uuid: str, request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    data = await request.json()
    message_index = data.get("message_index")
    if message_index is None:
        raise HTTPException(400, "message_index is required")
    
    new_uuid = await agent.clone_session(user, session_uuid, message_index)
    if not new_uuid:
        raise HTTPException(500, "Failed to clone session")
    return {"success": True, "new_uuid": new_uuid}

@chat_router.get("/sessions/{session_uuid}/forks")
async def get_forks(session_uuid: str, request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    return {"forks": agent.get_session_forks(user, session_uuid)}

@chat_router.get("/sessions/fork-graph")
async def get_fork_graph(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    return {"graph": agent.get_fork_graph(user)}

@chat_router.post("/sessions/{session_uuid}/title")
async def rename_sess(session_uuid: str, request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    data = await request.json()
    new_title = data.get("title")
    if not new_title:
        raise HTTPException(400, "Title is required")
    
    # Update and sync forks
    await agent.sync_session_updates(user, session_uuid, title=new_title)
    return {"success": True}

@chat_router.get("/sessions/tags")
async def get_all_tags(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    return {"tags": agent.get_unique_tags(user)}

@chat_router.post("/sessions/{session_uuid}/tags")
async def set_sess_tags(session_uuid: str, request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    data = await request.json()
    tags = data.get("tags", [])
    if not isinstance(tags, list):
        raise HTTPException(400, "Tags must be a list of strings")
    
    # Update and sync forks
    await agent.sync_session_updates(user, session_uuid, tags=tags)
    return {"success": True}

@chat_router.get("/sessions/{session_uuid}/tools")
async def get_sess_tools(session_uuid: str, request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    if session_uuid != "pending":
        if not agent.is_user_session(user, session_uuid):
            raise HTTPException(403, "Access denied")
    return {"tools": agent.get_session_tools(user, session_uuid)}

@chat_router.post("/sessions/{session_uuid}/tools")
async def set_sess_tools(session_uuid: str, request: Request, data: dict, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    if session_uuid != "pending":
        if not agent.is_user_session(user, session_uuid):
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
    
    # Custom Prompts
    prompts_dir = "prompts"
    if os.path.exists(prompts_dir):
        for filename in os.listdir(prompts_dir):
            if filename.endswith(".md") or filename.endswith(".txt"):
                res.append({
                    "name": filename,
                    "description": "User generated prompt",
                    "type": "user"
                })

    for line in expl.splitlines():
        m = re.match(r"^\d+\.\s+\*\*(?P<name>.*?)\*\*: (?P<description>.*)", line.strip())
        if m: 
            item = m.groupdict()
            item["type"] = "system"
            res.append(item)
        elif "suggest_pattern" in line:
            m = re.search(r"\*\*(?P<name>suggest_pattern)\*\*, (?P<description>.*)", line)
            if m: 
                item = m.groupdict()
                item["type"] = "system"
                res.append(item)
    
    if not res: 
        res = [{"name": k, "description": "", "type": "system"} for k in agent.list_patterns()]
        
    return res

@chat_router.post("/chat")
async def chat(request: Request, message: str = Form(...), file: Optional[list[UploadFile]] = File(None), model: Optional[str] = Form(None), plan_mode: Optional[str] = Form(None), user=Depends(get_user)):
    agent = request.app.state.agent
    UPLOAD_DIR = request.app.state.UPLOAD_DIR
    if not user: raise HTTPException(401)
    
    file_paths = []
    if file:
        conversion_service = request.app.state.conversion_service
        pdf_service = request.app.state.pdf_service
        for f_upload in file:
            if f_upload.filename:
                # Sanitize filename to ensure ASCII-only for CLI compatibility
                base_name = os.path.basename(f_upload.filename)
                safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', base_name)
                
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
                        logging.getLogger(__name__).info(f"Converted {old_fpath} to {fpath}")
                    except Exception as e:
                        # Fallback to original file on error
                        import logging
                        
                        log = logging.getLogger(__name__)
                        if isinstance(e, PandocMissingError):
                            log.warning(f"Pandoc missing, using original file: {e}")
                        else:
                            log.error(f"Conversion failed, falling back to original: {e}")
                elif fpath.lower().endswith(".pdf"):
                    try:
                        # Compress PDF
                        compressed_path = os.path.join(UPLOAD_DIR, f"compressed_{os.path.basename(fpath)}")
                        # We use a distinct name for output to avoid issues during processing
                        fpath = await pdf_service.compress_pdf(fpath, compressed_path)
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).error(f"PDF compression failed: {e}")
                
                file_paths.append(os.path.relpath(fpath))
    
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
    is_plan = (plan_mode == "true")
    if msg.startswith("/"):
        parts = msg.split(maxsplit=2)
        cmd = parts[0].lower()
        if cmd in ["/reset", "/clear"]: return {"response": await agent.reset_chat(user)}
        if cmd == "/pro":
            m_override = "gemini-3-pro-preview"
            if len(parts) > 1: return {"response": await agent.generate_response(user, parts[1] + (f" {parts[2]}" if len(parts) > 2 else ""), model=m_override, file_paths=file_paths)}
            return {"response": "Model set to Pro."}
        if cmd == "/plan":
            is_plan = True
            if len(parts) > 1:
                message = parts[1] + (f" {parts[2]}" if len(parts) > 2 else "")
            else:
                return {"response": "Plan mode requires a prompt. Usage: /plan <your prompt>"}
        if cmd == "/p" or cmd == "/pattern":
            if len(parts) >= 2: return {"response": await agent.apply_pattern(user, parts[1], parts[2] if len(parts) > 2 else "", model=m_override, file_paths=file_paths)}
        if cmd == "/yolo":
            agent.yolo_mode = not agent.yolo_mode
            return {"response": f"YOLO Mode {'ENABLED' if agent.yolo_mode else 'DISABLED'}."}
        if cmd == "/help": return {"response": "Commands: /reset, /pro, /plan, /p [pattern], /yolo, /help"}
    
    async def event_generator():
        def log_sse(msg, level="DEBUG"):
            if LOG_LEVEL == "NONE":
                return
            if LOG_LEVEL == "INFO" and level == "DEBUG":
                return
            try:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                print(f"[{ts}] [{level}][SSE][{user}] {msg}")
            except: pass

        log_sse("Starting event_generator")
        try:
            stream = agent.generate_response_stream(user, message, model=m_override, file_paths=file_paths, plan_mode=is_plan)
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

@chat_router.post("/stop")
async def stop_chat(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    success = await agent.stop_chat(user)
    return {"success": success}

@chat_router.post("/reset")
async def reset(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user: raise HTTPException(401)
    return {"response": await agent.reset_chat(user)}


admin_router = APIRouter()
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional

import subprocess
import json
import re
import shutil
import os



async def get_user(request: Request):
    return request.session.get("user")

def run_gemini_mcp_command(args):
    cmd = [shutil.which(GEMINI_CMD) or GEMINI_CMD, "mcp"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"

@admin_router.get("/admin/mcp")
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

@admin_router.post("/admin/mcp/add")
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

@admin_router.post("/admin/mcp/remove")
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

@admin_router.post("/admin/mcp/toggle")
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

@admin_router.get("/admin/skills")
async def list_skills(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    skills_dir = SKILLS_BASE_DIR
    skills = []
    if os.path.exists(skills_dir):
        for d in os.listdir(skills_dir):
            d_path = os.path.join(skills_dir, d)
            if os.path.isdir(d_path) and os.path.exists(os.path.join(d_path, "SKILL.md")):
                skills.append(d)
    return sorted(skills)

@admin_router.get("/admin/skills/{name}")
async def get_skill(request: Request, name: str, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    skill_path = os.path.join(SKILLS_BASE_DIR, name, "SKILL.md")
    if not os.path.exists(skill_path):
        raise HTTPException(status_code=404, detail="Skill not found")
    
    with open(skill_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Parse YAML frontmatter
    description = ""
    instructions = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            instructions = parts[2].strip()
            # Simple line-by-line parsing for name/description
            for line in frontmatter.splitlines():
                if line.startswith("description:"):
                    description = line.split(":", 1)[1].strip()
                    # Handle multi-line if needed, but keeping it simple for now
    
    return {"name": name, "description": description, "content": instructions}

@admin_router.post("/admin/skills")
async def save_skill(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    data = await request.json()
    name = data.get("name")
    description = data.get("description", "")
    content = data.get("content") # This is now just the instructions
    
    if not name or not content:
        raise HTTPException(status_code=400, detail="Name and content are required")
    
    # Sanitize name
    name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    
    skill_dir = os.path.join(SKILLS_BASE_DIR, name)
    os.makedirs(skill_dir, exist_ok=True)
    
    # Serialize with YAML frontmatter
    skill_md = f"---\nname: {name}\ndescription: {description}\n---\n\n{content}"
    
    skill_path = os.path.join(skill_dir, "SKILL.md")
    with open(skill_path, "w", encoding="utf-8") as f:
        f.write(skill_md)
    
    return {"success": True}

@admin_router.delete("/admin/skills/{name}")
async def delete_skill(request: Request, name: str, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    skill_dir = os.path.join(SKILLS_BASE_DIR, name)
    if os.path.exists(skill_dir):
        shutil.rmtree(skill_dir)
        return {"success": True}
    return {"success": False, "error": "Skill not found"}

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

@admin_router.post("/admin/system/log-level")
async def set_log_level(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    data = await request.json()
    level = data.get("level", "NONE").upper()
    if level not in ["NONE", "INFO", "DEBUG"]:
        raise HTTPException(status_code=400, detail="Invalid log level")
    
    update_env("LOG_LEVEL", level)
    LOG_LEVEL = level
    return {"success": True}

@admin_router.post("/admin/sessions/cleartags")
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

@admin_router.get("/admin/settings")
async def get_settings(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    return get_all_global_settings()

@admin_router.post("/admin/settings")
async def update_settings(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    data = await request.json()
    for key, value in data.items():
        update_global_setting(key, value)
    return {"success": True}

@admin_router.get("/admin", response_class=HTMLResponse)
async def admin_db(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin": return RedirectResponse("/")
    return request.app.state.render("admin.html", request=request, users=user_manager.get_all_users(), log_level=LOG_LEVEL)

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

@admin_router.post("/admin/user/toggle-role")
async def adm_tog_role(request: Request, username: str = Form(...), role: str = Form(...), user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) == "admin":
        if username == "admin" and role == "user":
            return {"success": False, "error": "Cannot demote primary admin."}
        if user_manager.update_role(username, role):
            return {"success": True}
    return {"success": False}

@admin_router.post("/admin/user/update-password")
async def adm_upd(request: Request, username: str = Form(...), new_password: str = Form(...), user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) == "admin": user_manager.update_password(username, new_password)
    return RedirectResponse("/admin", status_code=303)

# Agent Management Routes

@admin_router.get("/admin/agents")
async def list_agents(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    agent_manager = request.app.state.agent_manager
    agents = agent_manager.list_agents()
    return agents

@admin_router.get("/admin/agents/{category}/{name}")
async def get_agent_details(request: Request, category: str, name: str, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    agent_manager = request.app.state.agent_manager
    agent = agent_manager.get_agent(category, name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@admin_router.post("/admin/agents")
async def save_agent(request: Request, agent_data: AgentModel, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    agent_manager = request.app.state.agent_manager
    success = agent_manager.save_agent(agent_data)
    return {"success": success}

@admin_router.get("/admin/agents/root")
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

@admin_router.post("/admin/agents/root")
async def save_root_agent(request: Request, agent_data: AgentModel, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    agent_manager = request.app.state.agent_manager
    success = agent_manager.save_root_orchestrator(agent_data)
    return {"success": success}

@admin_router.delete("/admin/agents/{category}/{name}")
async def delete_agent(request: Request, category: str, name: str, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    agent_manager = request.app.state.agent_manager
    success = agent_manager.delete_agent(category, name)
    return {"success": success}

@admin_router.post("/admin/agents/{category}/{name}/toggle-enabled")
async def toggle_agent_enabled(request: Request, category: str, name: str, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    data = await request.json()
    enabled = data.get("enabled", False)
    
    agent_manager = request.app.state.agent_manager
    success = agent_manager.set_agent_enabled(category, name, enabled)
    return {"success": success}

@admin_router.get("/admin/agents/validate")
async def validate_orchestration(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    agent_manager = request.app.state.agent_manager
    warnings = agent_manager.validate_orchestration()
    return {"warnings": warnings}


# --- MAIN ---
import os
import sys
import asyncio
import mimetypes
from fastapi import FastAPI, Request

# Set Windows Event Loop Policy for subprocess support
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Register WebP MIME type if not present
mimetypes.add_type('image/webp', '.webp')

from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from jinja2 import Environment, FileSystemLoader

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Verify/Force ProactorEventLoop on Windows at runtime
    if sys.platform == 'win32':
        loop = asyncio.get_running_loop()
        from asyncio import ProactorEventLoop
        if not isinstance(loop, ProactorEventLoop):
            # We can't easily swap the loop if it's already running, 
            # but we can log it for debugging.
            print(f"WARNING: Running on {type(loop).__name__}, but ProactorEventLoop is required for subprocesses.")
        else:
            print("INFO: ProactorEventLoop is active.")
    yield

app = FastAPI(lifespan=lifespan)

# Session Middleware
# We enable https_only if the origin starts with https
https_only = ORIGIN.startswith("https") if ORIGIN else False
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

# Dynamic Auth Middleware to handle LAN/External access
class DynamicAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not ORIGIN or "localhost" in ORIGIN:
            proto = request.headers.get("x-forwarded-proto", request.url.scheme)
            host = request.headers.get("x-forwarded-host", request.url.netloc)
            current_origin = f"{proto}://{host}"
            current_rp_id = host.split(":")[0]
            request.app.state.auth_service.origin = current_origin
            request.app.state.auth_service.rp_id = current_rp_id
        return await call_next(request)

app.add_middleware(DynamicAuthMiddleware)


# UPLOAD_DIR
UPLOAD_DIR = UPLOAD_DIR
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Templates
templates_dir = None


def render(name, **ctx):
    return HTMLResponse(Template(TEMPLATES[name]).render(**ctx))

# Services
user_manager = UserManager()
auth_service = AuthService(RP_ID or "localhost", RP_NAME, ORIGIN or "http://localhost:8000")
agent = GeminiAgent()
conversion_service = FileConversionService()
pdf_service = PDFService()
agent_manager = AgentManager()
agent_manager.initialize_defaults()

# App State
app.state.user_manager = user_manager
app.state.auth_service = auth_service
app.state.agent = agent
app.state.conversion_service = conversion_service
app.state.pdf_service = pdf_service
app.state.agent_manager = agent_manager
app.state.render = render
app.state.UPLOAD_DIR = UPLOAD_DIR

# Static Files
static_dir = os.path.join(os.path.dirname(__file__), "static")


# Uploads
@app.get("/uploads/{filename:path}")
async def serve_upload(filename: str):
    import pathlib
    safe_filename = pathlib.Path(filename).name
    fpath = os.path.join(UPLOAD_DIR, safe_filename)
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