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
RP_NAME = os.getenv("RP_NAME", "OpenCode Agent")
ORIGIN = os.getenv("ORIGIN")

# Security Configuration
SESSION_SECRET = os.getenv("SESSION_SECRET", secrets.token_hex(32))

# Project paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Application Configuration
UPLOAD_DIR = os.getenv(
    "UPLOAD_DIR", os.path.join(BASE_DIR, "tmp", "user_attachments")
)
AGENT_BASE_DIR = os.getenv(
    "AGENT_BASE_DIR", os.path.join(BASE_DIR, "data", "agents")
)
SKILLS_BASE_DIR = os.path.join(BASE_DIR, ".opencode", "skills")
SETTINGS_FILE = os.path.join(BASE_DIR, "data", "settings.json")
MODEL_NAME = os.getenv("MODEL_NAME", "google/antigravity-gemini-3.1-pro")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
OPENCODE_CMD = os.getenv("OPENCODE_CMD", "opencode")
WORKSPACE_ROOT = os.getenv("WORKSPACE_ROOT", BASE_DIR)

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
    env_path = os.path.join(BASE_DIR, ".env")
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
    "setup.html": "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n    <meta charset=\"UTF-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n    <title>Setup - OpenCode Agent</title>\n    <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css\" rel=\"stylesheet\">\n    <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css\">\n    <link rel=\"icon\" type=\"image/svg+xml\" href=\"/static/icon.svg?v=2\">\n    <link rel=\"stylesheet\" href=\"/static/style.css\">\n    <style>\n        body {\n            height: 100vh;\n            display: flex;\n            align-items: center;\n            justify-content: center;\n            background-color: #121212;\n        }\n        .setup-card {\n            width: 100%;\n            max-width: 450px;\n            padding: 2.5rem;\n            border-radius: 1rem;\n            background-color: #1e1e1e;\n            border: 1px solid #333;\n            box-shadow: 0 10px 30px rgba(0,0,0,0.5);\n        }\n    </style>\n</head>\n<body class=\"text-light\">\n\n<div class=\"setup-card\">\n    <div class=\"text-center mb-4\">\n        <h1 class=\"h3 mb-3\"><svg xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" fill=\"#6c757d\" viewBox=\"0 0 16 16\" class=\"me-2\"><path d=\"M6 12.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 0 1h-3a.5.5 0 0 1-.5-.5M3 8.062C3 6.76 4.235 5.765 5.53 5.886a26.6 26.6 0 0 0 4.94 0C11.765 5.765 13 6.76 13 8.062v1.157a.93.93 0 0 1-.765.935c-.845.147-2.34.346-4.235.346s-3.39-.2-4.235-.346A.93.93 0 0 1 3 9.219zm4.542-.827a.25.25 0 0 0-.217.068l-.92.9a25 25 0 0 1-1.871-.183.25.25 0 0 0-.068.495c.55.076 1.232.149 2.02.193a.25.25 0 0 0 .189-.071l.754-.736.847 1.71a.25.25 0 0 0 .404.062l.932-.97a25 25 0 0 0 1.922-.188.25.25 0 0 0-.068-.495c-.538.074-1.207.145-1.98.189a.25.25 0 0 0-.166.076l-.754.785-.842-1.7a.25.25 0 0 0-.182-.135\"/><path d=\"M8.5 1.866a1 1 0 1 0-1 0V3h-2A4.5 4.5 0 0 0 1 7.5V8a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1v1a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-1a1 1 0 0 0 1-1V9a1 1 0 0 0-1-1v-.5A4.5 4.5 0 0 0 10.5 3h-2zM14 7.5V13a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V7.5A3.5 3.5 0 0 1 5.5 4h5A3.5 3.5 0 0 1 14 7.5\"/></svg> Initial Setup</h1>\n        <p class=\"text-muted\">Create your administrator account to begin.</p>\n    </div>\n\n    <form action=\"/setup\" method=\"post\">\n        <div class=\"mb-3\">\n            <label class=\"form-label\">Username</label>\n            <input type=\"text\" class=\"form-control bg-dark text-light border-secondary\" value=\"admin\" disabled>\n            <div class=\"form-text\">The default administrator username is 'admin'.</div>\n        </div>\n        <div class=\"mb-3\">\n            <label for=\"origin\" class=\"form-label\">Application Origin (URL)</label>\n            <input type=\"url\" class=\"form-control bg-dark text-light border-secondary\" id=\"origin\" name=\"origin\" value=\"http://localhost:8000\" required>\n            <div class=\"form-text\">The full URL where this app is hosted (e.g., https://myapp.example.com).</div>\n        </div>\n        <div class=\"mb-3\">\n            <label for=\"rp_id\" class=\"form-label\">RP ID (Domain)</label>\n            <input type=\"text\" class=\"form-control bg-dark text-light border-secondary\" id=\"rp_id\" name=\"rp_id\" value=\"localhost\" required>\n            <div class=\"form-text\">The domain for WebAuthn/Passkeys (e.g., myapp.example.com). Usually the domain part of the Origin.</div>\n        </div>\n        <div class=\"mb-4\">\n            <label for=\"password\" class=\"form-label\">Admin Password</label>\n            <input type=\"password\" class=\"form-control bg-dark text-light border-secondary\" id=\"password\" name=\"password\" required autofocus>\n            <div class=\"form-text\">Choose a strong password for your local agent.</div>\n        </div>\n        <button type=\"submit\" class=\"btn btn-info w-100 py-2 text-white\">Complete Setup</button>\n    </form>\n</div>\n\n<script src=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js\"></script>\n<script>\n    document.addEventListener('DOMContentLoaded', () => {\n        const originInput = document.getElementById('origin');\n        const rpIdInput = document.getElementById('rp_id');\n        \n        // Auto-fill based on current URL to handle non-LAN access\n        originInput.value = window.location.origin;\n        rpIdInput.value = window.location.hostname;\n    });\n</script>\n</body>\n</html>\n",
    "login.html": "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n    <meta charset=\"UTF-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n    <title>Login - OpenCode Agent</title>\n    <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css\" rel=\"stylesheet\">\n    <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css\">\n    <link rel=\"icon\" type=\"image/svg+xml\" href=\"/static/icon.svg?v=2\">\n    <link rel=\"manifest\" href=\"/manifest.json?v=3\">\n    <link rel=\"stylesheet\" href=\"/static/style.css\">\n    <style>\n        body {\n            height: 100vh;\n            display: flex;\n            align-items: center;\n            justify-content: center;\n            background-color: #121212;\n        }\n        .login-card {\n            width: 100%;\n            max-width: 400px;\n            padding: 2rem;\n            border-radius: 1rem;\n            background-color: #1e1e1e;\n            border: 1px solid #333;\n            box-shadow: 0 10px 30px rgba(0,0,0,0.5);\n        }\n    </style>\n    <script src=\"https://cdnjs.cloudflare.com/ajax/libs/ethers/5.7.2/ethers.umd.min.js\"></script>\n</head>\n<body class=\"text-light\">\n\n<div class=\"login-card\">\n    <div class=\"text-center mb-4\">\n        <h1 class=\"h3 mb-3\"><svg xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" fill=\"#6c757d\" viewBox=\"0 0 16 16\" class=\"me-2\"><path d=\"M6 12.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 0 1h-3a.5.5 0 0 1-.5-.5M3 8.062C3 6.76 4.235 5.765 5.53 5.886a26.6 26.6 0 0 0 4.94 0C11.765 5.765 13 6.76 13 8.062v1.157a.93.93 0 0 1-.765.935c-.845.147-2.34.346-4.235.346s-3.39-.2-4.235-.346A.93.93 0 0 1 3 9.219zm4.542-.827a.25.25 0 0 0-.217.068l-.92.9a25 25 0 0 1-1.871-.183.25.25 0 0 0-.068.495c.55.076 1.232.149 2.02.193a.25.25 0 0 0 .189-.071l.754-.736.847 1.71a.25.25 0 0 0 .404.062l.932-.97a25 25 0 0 0 1.922-.188.25.25 0 0 0-.068-.495c-.538.074-1.207.145-1.98.189a.25.25 0 0 0-.166.076l-.754.785-.842-1.7a.25.25 0 0 0-.182-.135\"/><path d=\"M8.5 1.866a1 1 0 1 0-1 0V3h-2A4.5 4.5 0 0 0 1 7.5V8a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1v1a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-1a1 1 0 0 0 1-1V9a1 1 0 0 0-1-1v-.5A4.5 4.5 0 0 0 10.5 3h-2zM14 7.5V13a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V7.5A3.5 3.5 0 0 1 5.5 4h5A3.5 3.5 0 0 1 14 7.5\"/></svg> OpenCode Agent</h1>\n        <p class=\"text-muted\">Please sign in to continue</p>\n    </div>\n\n    {% if error %}\n    <div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\">\n        {{ error }}\n        <button type=\"button\" class=\"btn-close\" data-bs-dismiss=\"alert\" aria-label=\"Close\"></button>\n    </div>\n    {% endif %}\n\n    <ul class=\"nav nav-pills nav-fill mb-4\" id=\"loginTabs\" role=\"tablist\">\n        <li class=\"nav-item\" role=\"presentation\">\n            <button class=\"nav-link active\" id=\"passkey-tab\" data-bs-toggle=\"pill\" data-bs-target=\"#passkey-login\" type=\"button\" role=\"tab\" aria-controls=\"passkey-login\" aria-selected=\"true\">Passkey</button>\n        </li>\n        <li class=\"nav-item\" role=\"presentation\">\n            <button class=\"nav-link\" id=\"password-tab\" data-bs-toggle=\"pill\" data-bs-target=\"#password-login\" type=\"button\" role=\"tab\" aria-controls=\"password-login\" aria-selected=\"false\">Password</button>\n        </li>\n        <li class=\"nav-item\" role=\"presentation\">\n            <button class=\"nav-link\" id=\"wallet-tab\" data-bs-toggle=\"pill\" data-bs-target=\"#wallet-login\" type=\"button\" role=\"tab\" aria-controls=\"wallet-login\" aria-selected=\"false\">Wallet</button>\n        </li>\n        <li class=\"nav-item\" role=\"presentation\">\n            <button class=\"nav-link\" id=\"pattern-tab\" data-bs-toggle=\"pill\" data-bs-target=\"#pattern-login\" type=\"button\" role=\"tab\" aria-controls=\"pattern-login\" aria-selected=\"false\">Pattern</button>\n        </li>\n    </ul>\n\n    <div class=\"tab-content\" id=\"loginTabsContent\">\n        <!-- Passkey Login -->\n        <div class=\"tab-pane fade show active\" id=\"passkey-login\" role=\"tabpanel\" aria-labelledby=\"passkey-tab\">\n            <div class=\"text-center py-4\">\n                <i class=\"bi bi-key display-1 text-info mb-3\"></i>\n                <div class=\"mb-3\">\n                    <label for=\"username-passkey\" class=\"form-label\">Username (Optional)</label>\n                    <input type=\"text\" class=\"form-control bg-dark text-light border-secondary\" id=\"username-passkey\" placeholder=\"Leave empty for auto-login\">\n                </div>\n                <button id=\"btn-passkey-login\" class=\"btn btn-info w-100 py-2 text-white\">\n                    Sign In with Passkey\n                </button>\n                <div id=\"passkey-error\" class=\"text-danger small mt-2\"></div>\n            </div>\n        </div>\n\n        <!-- Password Login -->\n        <div class=\"tab-pane fade\" id=\"password-login\" role=\"tabpanel\" aria-labelledby=\"password-tab\">\n            <form action=\"/login\" method=\"post\">\n                <div class=\"mb-3\">\n                    <label for=\"username\" class=\"form-label\">Username</label>\n                    <input type=\"text\" class=\"form-control bg-dark text-light border-secondary\" id=\"username\" name=\"username\" required autofocus>\n                </div>\n                <div class=\"mb-4\">\n                    <label for=\"password\" class=\"form-label\">Password</label>\n                    <input type=\"password\" class=\"form-control bg-dark text-light border-secondary\" id=\"password\" name=\"password\" required>\n                </div>\n                <button type=\"submit\" class=\"btn btn-primary w-100 py-2\">Sign In</button>\n            </form>\n        </div>\n\n        <!-- Wallet Login -->\n        <div class=\"tab-pane fade\" id=\"wallet-login\" role=\"tabpanel\" aria-labelledby=\"wallet-tab\">\n            <div class=\"text-center py-4\">\n                <i class=\"bi bi-wallet2 display-1 text-primary mb-3\"></i>\n                <p>Connect your MetaMask or Brave wallet to sign in.</p>\n                <button id=\"btn-wallet-login\" class=\"btn btn-outline-primary w-100 py-2\">\n                    <img src=\"data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAzMTguNiAzMTguNiI+PHBhdGggZmlsbD0iI0UyN0MxMSIgZD0iTTEyOC42IDYuOGwtMjIuNSAzNi4zIDM0LjYgMjIuM3oiLz48cGF0aCBmaWxsPSIjRTI3QzExIiBkPSJNMTkwIDYuOGwyMi41IDM2LjMtMzQuNiAyMi4zeiIvPjxwYXRoIGZpbGw9IiNFNDc2MTkiIGQ9Ik05OC4zIDY5LjFsLTI5LjEtNCA1MS42IDM4LjV6Ii8+PHBhdGggZmlsbD0iI0U0NzYxOSIgZD0iTTcyMC4zIDY5LjFsMjkuMS00LTUxLjYgMzguNXoiLz48cGF0aCBmaWxsPSIjRTRDMTMzIiBkPSJNOTguNSAxOTMuOGwtMjkuNyA0LjUgMjUuNiA1NnoiLz48cGF0aCBmaWxsPSIjRTRDMjMyIiBkPSJNOTQuNCAyMjMuN2wzOC4zIDE3LjMtMjQuOC00Ny4zeiIvPjxwYXRoIGZpbGw9IiNFNUMxMzMiIGQ9Ik0yMjQuMiAyMjMuN2wtMzguMyAxNy4zIDI0LjgtNDcuM3oiLz48cGF0aCBmaWxsPSIjRTRDMjMyIiBkPSJNMjIwLjEgMTk4LjhsMjkuNyA0LjUtMjUuNiA1NnoiLz48cGF0aCBmaWxsPSIjRTRDMjMyIiBkPSJNMTU5LjMgMTI0LjNsLTI3LjIgOTEuNCAyNy4yIDE0LjIgMjcuMi0xNC4yLTExLjYtOTEuNHoiLz48cGF0aCBmaWxsPSIjRTRDMjMyIiBkPSJNMTU5LjMgMjMwLjFsLTI3LjIgMTQuMkwxNTkuMyAzMTBsMjcuMi02NS43eiIvPjxwYXRoIGZpbGw9IiNGNjhCMTgiIGQ9Ik02OC44IDY1LjFsMTAwLjUgMTguNkwxNTkuMyA2LjhsLTMwLjcgNTguM3oiLz48cGF0aCBmaWxsPSIjRjY4QjE4IiBkPSJNMjQ5LjggNjUuMWwtMTAwLjUgMTguNkwxNTkuMyA2LjhsMzAuNyA1OC4zeiIvPjxwYXRoIGZpbGw9IiNGNjhCMTgiIGQ9Ik02OS4xIDE5OC4zbDU0LjIgMzIuN0wxNTkuMyAxODdsLTM0LjgtNDYuM3oiLz48cGF0aCBmaWxsPSIjRjY4QjE4IiBkPSJNMjQ5LjUgMTk4LjNsLTU0LjIgMzIuN0wxNTkuMyAxODdsMzQuOC00Ni4zeiIvPjxwYXRoIGZpbGw9IiNGNjhCMTgiIGQ9Ik02OS4xIDE5OC4zbDI1LjYgNTZMMTU5LjMgMzEwbC0yNy4yLTY1Ljd6Ii8+PHBhdGggZmlsbD0iI0Y2OEIxOCIgZD0iTTI0OS41IDE5OC4zbC0yNS42IDU2TDE1OS4zIDMxMGwyNy4yLTY1Ljd6Ii8+PC9zdmc+\" alt=\"MetaMask\" style=\"height: 20px; margin-right: 10px;\">\n                    Sign In with Wallet\n                </button>\n                <div id=\"wallet-error\" class=\"text-danger small mt-2\"></div>\n            </div>\n        </div>\n\n        <!-- Pattern Login -->\n        <div class=\"tab-pane fade\" id=\"pattern-login\" role=\"tabpanel\" aria-labelledby=\"pattern-tab\">\n            <form id=\"pattern-form\" action=\"/login/pattern\" method=\"post\">\n                <div class=\"mb-3\">\n                    <label for=\"username-pattern\" class=\"form-label\">Username (Optional)</label>\n                    <input type=\"text\" class=\"form-control bg-dark text-light border-secondary\" id=\"username-pattern\" name=\"username\" placeholder=\"Leave empty for auto-login\">\n                </div>\n                <div class=\"mb-3 text-center\">\n                    <label class=\"form-label d-block\">Draw Pattern</label>\n                    <div id=\"pattern-container\" class=\"mx-auto\" style=\"width: 250px; height: 250px; position: relative; touch-action: none;\">\n                        <svg id=\"pattern-svg\" width=\"250\" height=\"250\" style=\"background: #252525; border-radius: 10px;\"></svg>\n                    </div>\n                    <input type=\"hidden\" id=\"pattern-input\" name=\"pattern\">\n                </div>\n                <button type=\"submit\" class=\"btn btn-primary w-100 py-2\">Sign In with Pattern</button>\n            </form>\n        </div>\n    </div>\n    \n    <div class=\"text-center mt-4\">\n    </div>\n</div>\n\n<script src=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js\"></script>\n<script>\n    document.addEventListener('DOMContentLoaded', () => {\n        // ... (existing pattern logic)\n        const svg = document.getElementById('pattern-svg');\n        // ...\n        const patternInput = document.getElementById('pattern-input');\n        const container = document.getElementById('pattern-container');\n        const dots = [];\n        const selectedDots = [];\n        let isDrawing = false;\n        let currentLine = null;\n\n        // Create 3x3 grid\n        for (let y = 0; y < 3; y++) {\n            for (let x = 0; x < 3; x++) {\n                const cx = 50 + x * 75;\n                const cy = 50 + y * 75;\n                const index = y * 3 + x + 1;\n                \n                const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');\n                dot.setAttribute('cx', cx);\n                dot.setAttribute('cy', cy);\n                dot.setAttribute('r', 10);\n                dot.setAttribute('fill', '#555');\n                dot.setAttribute('data-index', index);\n                svg.appendChild(dot);\n                dots.push({ cx, cy, index, element: dot });\n            }\n        }\n\n        function getMousePos(e) {\n            const rect = svg.getBoundingClientRect();\n            const clientX = e.touches ? e.touches[0].clientX : e.clientX;\n            const clientY = e.touches ? e.touches[0].clientY : e.clientY;\n            return {\n                x: clientX - rect.left,\n                y: clientY - rect.top\n            };\n        }\n\n        function startDrawing(e) {\n            isDrawing = true;\n            resetPattern();\n            handleMove(e);\n        }\n\n        function handleMove(e) {\n            if (!isDrawing) return;\n            const pos = getMousePos(e);\n            \n            // Check if near a dot\n            dots.forEach(dot => {\n                const dist = Math.hypot(pos.x - dot.cx, pos.y - dot.cy);\n                if (dist < 25 && !selectedDots.includes(dot)) {\n                    selectedDots.push(dot);\n                    dot.element.setAttribute('fill', '#0d6efd');\n                    dot.element.setAttribute('r', 15);\n                    \n                    if (selectedDots.length > 1) {\n                        const prevDot = selectedDots[selectedDots.length - 2];\n                        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');\n                        line.setAttribute('x1', prevDot.cx);\n                        line.setAttribute('y1', prevDot.cy);\n                        line.setAttribute('x2', dot.cx);\n                        line.setAttribute('y2', dot.cy);\n                        line.setAttribute('stroke', '#0d6efd');\n                        line.setAttribute('stroke-width', 4);\n                        svg.insertBefore(line, svg.firstChild);\n                    }\n                }\n            });\n\n            // Update floating line\n            if (selectedDots.length > 0) {\n                if (currentLine) currentLine.remove();\n                const lastDot = selectedDots[selectedDots.length - 1];\n                currentLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');\n                currentLine.setAttribute('x1', lastDot.cx);\n                currentLine.setAttribute('y1', lastDot.cy);\n                currentLine.setAttribute('x2', pos.x);\n                currentLine.setAttribute('y2', pos.y);\n                currentLine.setAttribute('stroke', '#0d6efd');\n                currentLine.setAttribute('stroke-width', 2);\n                currentLine.setAttribute('stroke-dasharray', '5,5');\n                svg.appendChild(currentLine);\n            }\n        }\n\n        function stopDrawing() {\n            if (!isDrawing) return;\n            isDrawing = false;\n            if (currentLine) currentLine.remove();\n            patternInput.value = selectedDots.map(d => d.index).join('');\n        }\n\n        function resetPattern() {\n            selectedDots.length = 0;\n            svg.querySelectorAll('line').forEach(l => l.remove());\n            dots.forEach(dot => {\n                dot.element.setAttribute('fill', '#555');\n                dot.element.setAttribute('r', 10);\n            });\n            patternInput.value = '';\n        }\n\n        svg.addEventListener('mousedown', startDrawing);\n        window.addEventListener('mousemove', handleMove);\n        window.addEventListener('mouseup', stopDrawing);\n\n        svg.addEventListener('touchstart', (e) => { e.preventDefault(); startDrawing(e); });\n        svg.addEventListener('touchmove', (e) => { e.preventDefault(); handleMove(e); });\n        svg.addEventListener('touchend', stopDrawing);\n\n        // --- Wallet Login ---\n        const btnWalletLogin = document.getElementById('btn-wallet-login');\n        const walletError = document.getElementById('wallet-error');\n\n        btnWalletLogin.addEventListener('click', async () => {\n            if (typeof window.ethereum === 'undefined') {\n                walletError.textContent = 'Ethereum wallet not found. Please install MetaMask.';\n                return;\n            }\n\n            try {\n                // Request account access\n                const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });\n                const address = accounts[0];\n\n                // Get challenge from server\n                const challengeRes = await fetch('/login/web3/challenge');\n                const { challenge } = await challengeRes.json();\n\n                // Request signature\n                const provider = new ethers.providers.Web3Provider(window.ethereum);\n                const signer = provider.getSigner();\n                const signature = await signer.signMessage(challenge);\n\n                // Verify signature on server\n                const formData = new FormData();\n                formData.append('address', address);\n                formData.append('signature', signature);\n\n                const verifyRes = await fetch('/login/web3/verify', {\n                    method: 'POST',\n                    body: formData\n                });\n\n                const result = await verifyRes.json();\n                if (result.success) {\n                    window.location.href = '/';\n                } else {\n                    walletError.textContent = result.error || 'Login failed';\n                }\n            } catch (err) {\n                console.error(err);\n                walletError.textContent = err.message || 'An error occurred during wallet login';\n            }\n        });\n\n        // --- Passkey Login ---\n        const btnPasskeyLogin = document.getElementById('btn-passkey-login');\n        const passkeyError = document.getElementById('passkey-error');\n        const usernamePasskey = document.getElementById('username-passkey');\n\n        btnPasskeyLogin.addEventListener('click', async () => {\n            const username = usernamePasskey.value;\n            \n            try {\n                // Get authentication options from server\n                const formData = new FormData();\n                if (username) {\n                    formData.append('username', username);\n                }\n                \n                const optionsRes = await fetch('/login/passkey/options', {\n                    method: 'POST',\n                    body: formData\n                });\n\n                if (!optionsRes.ok) {\n                    const errData = await optionsRes.json();\n                    throw new Error(errData.error || 'User not found or no passkeys registered');\n                }\n\n                const options = await optionsRes.json();\n\n                // Convert base64url to Uint8Array for the browser\n                options.challenge = base64urlToUint8Array(options.challenge);\n                if (options.allowCredentials) {\n                    options.allowCredentials.forEach(cred => {\n                        cred.id = base64urlToUint8Array(cred.id);\n                    });\n                }\n\n                // Call the browser's credential API\n                const credential = await navigator.credentials.get({\n                    publicKey: options\n                });\n\n                // Prepare data for verification\n                const authData = {\n                    id: credential.id,\n                    rawId: bufferToBase64Url(credential.rawId),\n                    type: credential.type,\n                    response: {\n                        authenticatorData: bufferToBase64Url(credential.response.authenticatorData),\n                        clientDataJSON: bufferToBase64Url(credential.response.clientDataJSON),\n                        signature: bufferToBase64Url(credential.response.signature),\n                        userHandle: credential.response.userHandle ? bufferToBase64Url(credential.response.userHandle) : null\n                    }\n                };\n\n                // Verify authentication on server\n                const verifyRes = await fetch('/login/passkey/verify', {\n                    method: 'POST',\n                    headers: {\n                        'Content-Type': 'application/json'\n                    },\n                    body: JSON.stringify(authData)\n                });\n\n                const result = await verifyRes.json();\n                if (result.success) {\n                    window.location.href = '/';\n                } else {\n                    passkeyError.textContent = result.error || 'Passkey authentication failed';\n                }\n            } catch (err) {\n                console.error(err);\n                passkeyError.textContent = err.message || 'An error occurred during passkey login';\n            }\n        });\n\n        // Helper functions for WebAuthn\n        function base64urlToUint8Array(base64url) {\n            const padding = '='.repeat((4 - base64url.length % 4) % 4);\n            const base64 = (base64url + padding).replace(/\\-/g, '+').replace(/_/g, '/');\n            const rawData = window.atob(base64);\n            const outputArray = new Uint8Array(rawData.length);\n            for (let i = 0; i < rawData.length; ++i) {\n                outputArray[i] = rawData.charCodeAt(i);\n            }\n            return outputArray;\n        }\n\n        function bufferToBase64Url(buffer) {\n            const bytes = new Uint8Array(buffer);\n            let binary = '';\n            for (let i = 0; i < bytes.byteLength; i++) {\n                binary += String.fromCharCode(bytes[i]);\n            }\n            const base64 = window.btoa(binary);\n            return base64.replace(/\\+/g, '-').replace(/\\//g, '_').replace(/=/g, '');\n        }\n    });\n</script>\n<script>\n    /*\n    if ('serviceWorker' in navigator) {\n        window.addEventListener('load', () => {\n            navigator.serviceWorker.register('/sw.js')\n                .then(reg => console.log('SW Registered', reg))\n                .catch(err => console.log('SW Reg Error', err));\n        });\n    }\n    */\n</script>\n</body>\n</html>\n",
    "admin.html": "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n    <meta charset=\"UTF-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n    <title>Admin Dashboard - OpenCode Agent</title>\n    <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css\" rel=\"stylesheet\">\n    <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css\">\n    <link rel=\"icon\" type=\"image/svg+xml\" href=\"/static/icon.svg?v=2\">\n    <style>\n        body { background-color: #121212; color: #e0e0e0; }\n        .card { background-color: #1e1e1e; border: 1px solid #333; }\n        .table { color: #e0e0e0; }\n        .table-hover tbody tr:hover { background-color: #2c2c2c; }\n        h2, h5, .card-title { color: #fff !important; }\n        .text-muted { color: #aaa !important; }\n        .form-label { color: #ccc !important; }\n    </style>\n</head>\n<body>\n    <nav class=\"navbar navbar-expand-lg navbar-dark bg-dark border-bottom border-secondary\">\n        <div class=\"container\">\n            <a class=\"navbar-brand\" href=\"/\"><svg xmlns=\"http://www.w3.org/2000/svg\" width=\"20\" height=\"20\" fill=\"#6c757d\" viewBox=\"0 0 16 16\" class=\"me-2\"><path d=\"M6 12.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 0 1h-3a.5.5 0 0 1-.5-.5M3 8.062C3 6.76 4.235 5.765 5.53 5.886a26.6 26.6 0 0 0 4.94 0C11.765 5.765 13 6.76 13 8.062v1.157a.93.93 0 0 1-.765.935c-.845.147-2.34.346-4.235.346s-3.39-.2-4.235-.346A.93.93 0 0 1 3 9.219zm4.542-.827a.25.25 0 0 0-.217.068l-.92.9a25 25 0 0 1-1.871-.183.25.25 0 0 0-.068.495c.55.076 1.232.149 2.02.193a.25.25 0 0 0 .189-.071l.754-.736.847 1.71a.25.25 0 0 0 .404.062l.932-.97a25 25 0 0 0 1.922-.188.25.25 0 0 0-.068-.495c-.538.074-1.207.145-1.98.189a.25.25 0 0 0-.166.076l-.754.785-.842-1.7a.25.25 0 0 0-.182-.135\"/><path d=\"M8.5 1.866a1 1 0 1 0-1 0V3h-2A4.5 4.5 0 0 0 1 7.5V8a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1v1a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-1a1 1 0 0 0 1-1V9a1 1 0 0 0-1-1v-.5A4.5 4.5 0 0 0 10.5 3h-2zM14 7.5V13a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V7.5A3.5 3.5 0 0 1 5.5 4h5A3.5 3.5 0 0 1 14 7.5\"/></svg>OpenCode Agent Admin</a>\n            <div class=\"navbar-nav ms-auto\">\n                <a class=\"nav-link\" href=\"/\">Back to Chat</a>\n                <a class=\"nav-link\" href=\"/logout\">Logout</a>\n            </div>\n        </div>\n    </nav>\n\n    <div class=\"container mt-4\">\n        <h2 class=\"mb-4\">User Management</h2>\n\n        <div class=\"row\">\n            <div class=\"col-md-8\">\n                <div class=\"card shadow-sm\">\n                    <div class=\"card-body\">\n                        <h5 class=\"card-title\">Users</h5>\n                        <div class=\"table-responsive\">\n                            <table class=\"table table-dark table-hover\">\n                                <thead>\n                                    <tr>\n                                        <th>Username</th>\n                                        <th>Role</th>\n                                        <th>Pattern Login</th>\n                                        <th>Actions</th>\n                                    </tr>\n                                </thead>\n                                <tbody>\n                                    {% for user in users %}\n                                    <tr>\n                                        <td>{{ user.username }}</td>\n                                        <td>\n                                            <div class=\"dropdown\">\n                                                <button class=\"btn btn-sm {{ 'btn-primary' if user.role == 'admin' else 'btn-secondary' }} dropdown-toggle py-0\" type=\"button\" data-bs-toggle=\"dropdown\" aria-expanded=\"false\" style=\"font-size: 0.75rem;\">\n                                                    {{ user.role }}\n                                                </button>\n                                                <ul class=\"dropdown-menu dropdown-menu-dark shadow\">\n                                                    <li><a class=\"dropdown-item small\" href=\"#\" onclick=\"changeRole('{{ user.username }}', 'user')\">User</a></li>\n                                                    <li><a class=\"dropdown-item small\" href=\"#\" onclick=\"changeRole('{{ user.username }}', 'admin')\">Admin</a></li>\n                                                </ul>\n                                            </div>\n                                        </td>\n                                        <td>\n                                            <div class=\"form-check form-switch\">\n                                                <input class=\"form-check-input\" type=\"checkbox\" role=\"switch\" \n                                                    id=\"patternSwitch_{{ user.username }}\" \n                                                    {% if not user.pattern_disabled %}checked{% endif %}\n                                                    onchange=\"togglePattern('{{ user.username }}', this.checked)\">\n                                                <label class=\"form-check-label\" for=\"patternSwitch_{{ user.username }}\">\n                                                    {{ 'Enabled' if not user.pattern_disabled else 'Disabled' }}\n                                                </label>\n                                            </div>\n                                        </td>\n                                        <td>\n                                            {% if user.username != 'admin' %}\n                                            <button class=\"btn btn-sm btn-outline-danger\" onclick=\"deleteUser('{{ user.username }}')\">Delete</button>\n                                            {% endif %}\n                                            <button class=\"btn btn-sm btn-outline-info\" onclick=\"showChangePassword('{{ user.username }}')\">Change Password</button>\n                                        </td>\n                                    </tr>\n                                    {% endfor %}\n                                </tbody>\n                            </table>\n                        </div>\n                    </div>\n                </div>\n            </div>\n\n            <div class=\"col-md-4\">\n                <div class=\"card shadow-sm mb-4\">\n                    <div class=\"card-body\">\n                        <h5 class=\"card-title\">System Actions</h5>\n                        <button class=\"btn btn-info w-100 mb-2\" onclick=\"syncPatterns()\">\n                            <i class=\"bi bi-arrow-repeat me-1\"></i> Sync Fabric Patterns\n                        </button>\n                        <button class=\"btn btn-outline-danger w-100 mb-2\" onclick=\"clearAllTags()\">\n                            <i class=\"bi bi-trash me-1\"></i> Clear All Chat Tags\n                        </button>\n                        <button class=\"btn btn-warning w-100 mb-2\" onclick=\"restartSetup()\">\n                            <i class=\"bi bi-exclamation-triangle me-1\"></i> Restart Setup\n                        </button>\n                        <div class=\"mt-3\">\n                            <label class=\"form-label small text-muted\">Logging Level</label>\n                            <select id=\"log-level-select\" class=\"form-select form-select-sm bg-dark text-light border-secondary\" onchange=\"updateLogLevel(this.value)\">\n                                <option value=\"NONE\">NONE (Silent)</option>\n                                <option value=\"INFO\">INFO (Normal)</option>\n                                <option value=\"DEBUG\">DEBUG (Verbose)</option>\n                            </select>\n                        </div>\n                        <div id=\"sync-status\" class=\"small mt-2\"></div>\n                    </div>\n                </div>\n\n                <div class=\"card shadow-sm mb-4\">\n                    <div class=\"card-body\">\n                        <h5 class=\"card-title\">Global Settings</h5>\n                        <div class=\"mb-3\">\n                            <div class=\"d-flex justify-content-between align-items-center mb-1\">\n                                <label class=\"form-label small text-muted mb-0\">Interactive Mode Instructions</label>\n                                <button class=\"btn btn-link btn-sm text-warning p-0\" style=\"text-decoration: none; font-size: 0.7rem;\" onclick=\"resetInteractiveModeInstructions()\">\n                                    <i class=\"bi bi-arrow-counterclockwise\"></i> Reset\n                                </button>\n                            </div>\n                            <textarea id=\"interactive-mode-instructions\" class=\"form-control form-control-sm bg-dark text-light border-secondary\" rows=\"4\"></textarea>\n                        </div>\n                        <button class=\"btn btn-primary btn-sm w-100\" onclick=\"saveGlobalSettings()\">\n                            Save All Settings\n                        </button>\n                        <div id=\"settings-status\" class=\"small mt-2\"></div>\n                    </div>\n                </div>\n\n                <div class=\"card shadow-sm mb-4\">\n                    <div class=\"card-body\">\n                        <h5 class=\"card-title\">Add User</h5>\n                        <form action=\"/admin/user/add\" method=\"post\">\n                            <div class=\"mb-3\">\n                                <label class=\"form-label\">Username</label>\n                                <input type=\"text\" name=\"username\" class=\"form-control bg-dark text-light border-secondary\" required>\n                            </div>\n                            <div class=\"mb-3\">\n                                <label class=\"form-label\">Password</label>\n                                <input type=\"password\" name=\"password\" class=\"form-control bg-dark text-light border-secondary\" required>\n                            </div>\n                            <div class=\"mb-3\">\n                                <label class=\"form-label\">Role</label>\n                                <select name=\"role\" class=\"form-select bg-dark text-light border-secondary\">\n                                    <option value=\"user\">User</option>\n                                    <option value=\"admin\">Admin</option>\n                                </select>\n                            </div>\n                            <button type=\"submit\" class=\"btn btn-success w-100\">Add User</button>\n                        </form>\n                    </div>\n                </div>\n            </div>\n        </div>\n\n        <hr class=\"border-secondary my-5\">\n\n        <h2 class=\"mb-4\">Agent Management</h2>\n        \n        <div id=\"orchestration-warnings\" class=\"mb-3\"></div>\n\n        <div class=\"row\">\n            <div class=\"col-md-12\">\n                <div class=\"card shadow-sm\">\n                    <div class=\"card-body\">\n                        <div class=\"d-flex justify-content-between align-items-center mb-3\">\n                            <h5 class=\"card-title mb-0\">Agents</h5>\n                            <div class=\"d-flex gap-2\">\n                                <select id=\"categoryFilter\" class=\"form-select form-select-sm bg-dark text-light border-secondary\" style=\"width: auto;\" onchange=\"renderAgents()\">\n                                    <option value=\"all\">All Categories</option>\n                                </select>\n                                <button class=\"btn btn-sm btn-outline-info\" onclick=\"editRootAgent()\">\n                                    <i class=\"bi bi-gear-fill me-1\"></i> Root Orchestrator\n                                </button>\n                                <button class=\"btn btn-sm btn-primary\" onclick=\"showAgentEditor()\">\n                                    <i class=\"bi bi-plus-lg me-1\"></i> New Agent\n                                </button>\n                            </div>\n                        </div>\n                        <div class=\"table-responsive\">\n                            <table class=\"table table-dark table-hover\">\n                                <thead>\n                                    <tr>\n                                        <th>Category</th>\n                                        <th>Enabled</th>\n                                        <th>Name</th>\n                                        <th>Folder</th>\n                                        <th>Description</th>\n                                        <th>Actions</th>\n                                    </tr>\n                                </thead>\n                                <tbody id=\"agentsTableBody\">\n                                    <!-- Loaded via JS -->\n                                </tbody>\n                            </table>\n                        </div>\n                    </div>\n                </div>\n            </div>\n        </div>\n\n        </div>\n    </div>\n\n    <!-- Agent Editor Modal -->\n    <div class=\"modal fade\" id=\"agentModal\" tabindex=\"-1\" aria-hidden=\"true\">\n        <div class=\"modal-dialog modal-lg\">\n            <div class=\"modal-content bg-dark text-light border-secondary\">\n                <div class=\"modal-header border-secondary\">\n                    <h5 class=\"modal-title\" id=\"agentModalTitle\">New Agent</h5>\n                    <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>\n                </div>\n                <div class=\"modal-body\">\n                    <form id=\"agentForm\">\n                        <div class=\"row mb-3\">\n                            <div class=\"col-md-6\">\n                                <label class=\"form-label\">Category</label>\n                                <input type=\"text\" id=\"agentCategory\" class=\"form-control bg-dark text-light border-secondary\" placeholder=\"e.g., functions, projects\" required>\n                            </div>\n                            <div class=\"col-md-6\">\n                                <label class=\"form-label\">Folder Name</label>\n                                <input type=\"text\" id=\"agentFolder\" class=\"form-control bg-dark text-light border-secondary\" placeholder=\"e.g., team_manager\" required>\n                            </div>\n                        </div>\n                        <div class=\"mb-3\">\n                            <label class=\"form-label\">Name</label>\n                            <input type=\"text\" id=\"agentName\" class=\"form-control bg-dark text-light border-secondary\" placeholder=\"Display Name\" required>\n                        </div>\n                        <div class=\"mb-3\">\n                            <label class=\"form-label\">Description</label>\n                            <input type=\"text\" id=\"agentDescription\" class=\"form-control bg-dark text-light border-secondary\" placeholder=\"Brief description\">\n                        </div>\n                        <div class=\"mb-3\">\n                            <label class=\"form-label\">System Prompt (Markdown)</label>\n                            <textarea id=\"agentPrompt\" class=\"form-control bg-dark text-light border-secondary\" rows=\"10\" placeholder=\"Agent instructions...\" required></textarea>\n                        </div>\n                        <div class=\"mb-3\">\n                            <label class=\"form-label\">Associated Skills</label>\n                            <div id=\"skillsContainer\" class=\"d-flex flex-wrap gap-2\">\n                                <!-- Loaded via JS -->\n                            </div>\n                        </div>\n                    </form>\n                </div>\n                <div class=\"modal-footer border-secondary\">\n                    <button type=\"button\" class=\"btn btn-secondary\" data-bs-dismiss=\"modal\">Cancel</button>\n                    <button type=\"button\" class=\"btn btn-primary\" onclick=\"saveAgent()\">Save Agent</button>\n                </div>\n            </div>\n        </div>\n    </div>\n\n    <!-- Change Password Modal -->\n    <div class=\"modal fade\" id=\"passwordModal\" tabindex=\"-1\" aria-hidden=\"true\">\n        <div class=\"modal-dialog\">\n            <div class=\"modal-content bg-dark text-light border-secondary\">\n                <div class=\"modal-header border-secondary\">\n                    <h5 class=\"modal-title\">Change Password for <span id=\"targetUsername\"></span></h5>\n                    <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>\n                </div>\n                <form action=\"/admin/user/update-password\" method=\"post\">\n                    <div class=\"modal-body\">\n                        <input type=\"hidden\" name=\"username\" id=\"modalUsername\">\n                        <div class=\"mb-3\">\n                            <label class=\"form-label\">New Password</label>\n                            <input type=\"password\" name=\"new_password\" class=\"form-control bg-dark text-light border-secondary\" required>\n                        </div>\n                    </div>\n                    <div class=\"modal-footer border-secondary\">\n                        <button type=\"button\" class=\"btn btn-secondary\" data-bs-dismiss=\"modal\">Cancel</button>\n                        <button type=\"submit\" class=\"btn btn-primary\">Update Password</button>\n                    </div>\n                </form>\n            </div>\n        </div>\n    </div>\n\n    <div class=\"row mt-4\">\n        <div class=\"col-md-6\">\n            <div class=\"card shadow-sm\">\n                <div class=\"card-body\">\n                    <div class=\"d-flex justify-content-between align-items-center mb-3\">\n                        <h5 class=\"card-title mb-0\">Available Skills</h5>\n                        <button class=\"btn btn-primary btn-sm\" onclick=\"showNewSkill()\">\n                            <i class=\"bi bi-plus-lg me-1\"></i> Add Skill\n                        </button>\n                    </div>\n                    <p class=\"text-muted small\">Managed in <code>.opencode/skills/</code></p>\n                    <div id=\"dashboardSkillsList\" class=\"list-group list-group-flush bg-dark\">\n                        <!-- Loaded via JS -->\n                    </div>\n                </div>\n            </div>\n        </div>\n        <div class=\"col-md-6\">\n            <div class=\"card shadow-sm\">\n                <div class=\"card-body\">\n                    <div class=\"d-flex justify-content-between align-items-center mb-3\">\n                        <h5 class=\"card-title mb-0\">MCP Servers</h5>\n                        <button class=\"btn btn-primary btn-sm\" onclick=\"showNewMCP()\">\n                            <i class=\"bi bi-plus-lg me-1\"></i> Add MCP Server\n                        </button>\n                    </div>\n                    <div class=\"table-responsive\">\n                        <table class=\"table table-dark table-hover\">\n                            <thead>\n                                <tr>\n                                    <th>Status</th>\n                                    <th>Name</th>\n                                    <th>Command</th>\n                                    <th>Actions</th>\n                                </tr>\n                            </thead>\n                            <tbody id=\"mcpTableBody\">\n                                <!-- Loaded via JS -->\n                            </tbody>\n                        </table>\n                    </div>\n                </div>\n            </div>\n        </div>\n    </div>\n\n    <hr class=\"border-secondary my-5\">\n\n    <h2 class=\"mb-4\">Account Usage</h2>\n    <div class=\"row\">\n        <div class=\"col-md-12\">\n            <div class=\"card shadow-sm\">\n                <div class=\"card-body\">\n                    <div class=\"table-responsive\">\n                        <table class=\"table table-dark table-hover\">\n                            <thead>\n                                <tr>\n                                    <th>Account</th>\n                                    <th>Enabled</th>\n                                    <th>Model</th>\n                                    <th>Remaining</th>\n                                    <th>Reset Time</th>\n                                </tr>\n                            </thead>\n                            <tbody id=\"accountsTableBody\">\n                                <!-- Loaded via JS -->\n                            </tbody>\n                        </table>\n                    </div>\n                </div>\n            </div>\n        </div>\n    </div>\n\n    <!-- MCP Modal -->\n    <div class=\"modal fade\" id=\"mcpModal\" tabindex=\"-1\" aria-hidden=\"true\">\n        <div class=\"modal-dialog\">\n            <div class=\"modal-content bg-dark text-light border-secondary\">\n                <div class=\"modal-header border-secondary\">\n                    <h5 class=\"modal-title\" id=\"mcpModalTitle\">Add MCP Server</h5>\n                    <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>\n                </div>\n                <div class=\"modal-body\">\n                    <form id=\"mcpForm\">\n                        <div class=\"mb-3\">\n                            <label class=\"form-label\">Name</label>\n                            <input type=\"text\" id=\"mcpName\" class=\"form-control bg-dark text-light border-secondary\" placeholder=\"e.g., sqlite-server\" required>\n                        </div>\n                        <div class=\"mb-3\">\n                            <label class=\"form-label\">Command</label>\n                            <input type=\"text\" id=\"mcpCommand\" class=\"form-control bg-dark text-light border-secondary\" placeholder=\"e.g., npx\" required>\n                        </div>\n                        <div class=\"mb-3\">\n                            <label class=\"form-label\">Arguments (Space separated)</label>\n                            <input type=\"text\" id=\"mcpArgs\" class=\"form-control bg-dark text-light border-secondary\" placeholder=\"e.g., -y @modelcontextprotocol/server-sqlite --db /path/to/db\">\n                        </div>\n                    </form>\n                </div>\n                <div class=\"modal-footer border-secondary\">\n                    <button type=\"button\" class=\"btn btn-secondary\" data-bs-dismiss=\"modal\">Cancel</button>\n                    <button type=\"button\" class=\"btn btn-primary\" onclick=\"saveMCP()\">Add Server</button>\n                </div>\n            </div>\n        </div>\n    </div>\n\n    <!-- Skill Modal -->\n    <div class=\"modal fade\" id=\"skillModal\" tabindex=\"-1\" aria-hidden=\"true\">\n        <div class=\"modal-dialog modal-lg\">\n            <div class=\"modal-content bg-dark text-light border-secondary\">\n                <div class=\"modal-header border-secondary\">\n                    <h5 class=\"modal-title\" id=\"skillModalTitle\">New Skill</h5>\n                    <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>\n                </div>\n                <div class=\"modal-body\">\n                    <form id=\"skillForm\">\n                        <div class=\"mb-3\">\n                            <label class=\"form-label\">Skill Name (Filename)</label>\n                            <input type=\"text\" id=\"skillName\" class=\"form-control bg-dark text-light border-secondary\" placeholder=\"e.g., code-reviewer\" required>\n                        </div>\n                        <div class=\"mb-3\">\n                            <label class=\"form-label\">Description</label>\n                            <input type=\"text\" id=\"skillDescription\" class=\"form-control bg-dark text-light border-secondary\" placeholder=\"Short summary of what this skill does\">\n                        </div>\n                        <div class=\"mb-3\">\n                            <label class=\"form-label\">Instructions (Markdown)</label>\n                            <textarea id=\"skillContent\" class=\"form-control bg-dark text-light border-secondary\" rows=\"15\" placeholder=\"## Instructions\\n...\" required></textarea>\n                        </div>\n                    </form>\n                </div>\n                <div class=\"modal-footer border-secondary\">\n                    <button type=\"button\" class=\"btn btn-secondary\" data-bs-dismiss=\"modal\">Cancel</button>\n                    <button type=\"button\" class=\"btn btn-primary\" onclick=\"saveSkill()\">Save Skill</button>\n                </div>\n            </div>\n        </div>\n    </div>\n\n    <script src=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js\"></script>\n    <script>\n        const passwordModal = new bootstrap.Modal(document.getElementById('passwordModal'));\n        const agentModal = new bootstrap.Modal(document.getElementById('agentModal'));\n        const mcpModal = new bootstrap.Modal(document.getElementById('mcpModal'));\n        const skillModal = new bootstrap.Modal(document.getElementById('skillModal'));\n        let allAgents = [];\n        let allSkills = [];\n\n        document.addEventListener('DOMContentLoaded', () => {\n            const logLevel = \"{{ log_level }}\";\n            const select = document.getElementById('log-level-select');\n            if (select) select.value = logLevel;\n            fetchAgents();\n            fetchMCP();\n            fetchSkills();\n            fetchGlobalSettings();\n            fetchAccounts();\n        });\n\n        async function fetchAccounts() {\n            try {\n                const res = await fetch('/admin/accounts');\n                const data = await res.json();\n                const tbody = document.getElementById('accountsTableBody');\n                \n                if (data.error) {\n                    tbody.innerHTML = `<tr><td colspan=\"5\" class=\"text-danger\">${data.error}</td></tr>`;\n                    return;\n                }\n\n                tbody.innerHTML = '';\n                data.accounts.forEach(acc => {\n                    const models = acc.models || {};\n                    const modelKeys = Object.keys(models);\n                    \n                    if (modelKeys.length === 0) {\n                        const tr = document.createElement('tr');\n                        tr.innerHTML = `\n                            <td>${acc.email}</td>\n                            <td><span class=\"badge ${acc.enabled ? 'bg-success' : 'bg-secondary'}\">${acc.enabled ? 'Yes' : 'No'}</span></td>\n                            <td colspan=\"3\" class=\"text-muted\">No quota data</td>\n                        `;\n                        tbody.appendChild(tr);\n                        return;\n                    }\n\n                    modelKeys.forEach((model, idx) => {\n                        const m = models[model];\n                        const pct = Math.round(m.remainingFraction * 100);\n                        const tr = document.createElement('tr');\n                        tr.innerHTML = `\n                            ${idx === 0 ? `<td rowspan=\"${modelKeys.length}\">${acc.email}</td>` : ''}\n                            ${idx === 0 ? `<td rowspan=\"${modelKeys.length}\"><span class=\"badge ${acc.enabled ? 'bg-success' : 'bg-secondary'}\">${acc.enabled ? 'Yes' : 'No'}</span></td>` : ''}\n                            <td><strong>${model}</strong></td>\n                            <td>\n                                <div class=\"progress\" style=\"height: 20px; min-width: 100px;\">\n                                    <div class=\"progress-bar ${pct > 50 ? 'bg-success' : pct > 20 ? 'bg-warning' : 'bg-danger'}\" \n                                         role=\"progressbar\" style=\"width: ${pct}%;\">${pct}%</div>\n                                </div>\n                            </td>\n                            <td class=\"small text-muted\">${m.resetTime ? new Date(m.resetTime).toLocaleString() : 'N/A'}</td>\n                        `;\n                        tbody.appendChild(tr);\n                    });\n                });\n            } catch (err) {\n                console.error('Error fetching accounts:', err);\n            }\n        }\n\n        async function fetchSkills() {\n            try {\n                const res = await fetch('/admin/skills');\n                allSkills = await res.json();\n                \n                const list = document.getElementById('dashboardSkillsList');\n                if (list) {\n                    list.innerHTML = '';\n                    allSkills.forEach(skill => {\n                        const item = document.createElement('div');\n                        item.className = 'list-group-item bg-dark text-light border-secondary d-flex justify-content-between align-items-center py-1';\n                        item.innerHTML = `\n                            <span><i class=\"bi bi-magic me-2 text-info\"></i>${skill}</span>\n                            <div>\n                                <button class=\"btn btn-sm btn-link text-info p-0 me-2\" onclick=\"editSkill('${skill}')\"><i class=\"bi bi-pencil\"></i></button>\n                                <button class=\"btn btn-sm btn-link text-danger p-0\" onclick=\"deleteSkill('${skill}')\"><i class=\"bi bi-trash\"></i></button>\n                            </div>\n                        `;\n                        list.appendChild(item);\n                    });\n                    if (allSkills.length === 0) {\n                        list.innerHTML = '<div class=\"text-muted small p-2\">No skills found.</div>';\n                    }\n                }\n            } catch (err) { console.error('Error fetching skills:', err); }\n        }\n\n            function showNewSkill() {\n                document.getElementById('skillModalTitle').textContent = 'New Skill';\n                document.getElementById('skillName').value = '';\n                document.getElementById('skillName').disabled = false;\n                document.getElementById('skillDescription').value = '';\n                document.getElementById('skillContent').value = '# Skill Title\\n\\n## Instructions\\n...';\n                skillModal.show();\n            }\n        async function editSkill(name) {\n            try {\n                const res = await fetch(`/admin/skills/${name}`);\n                const skill = await res.json();\n                document.getElementById('skillModalTitle').textContent = 'Edit Skill';\n                document.getElementById('skillName').value = skill.name;\n                document.getElementById('skillName').disabled = true;\n                document.getElementById('skillDescription').value = skill.description || '';\n                document.getElementById('skillContent').value = skill.content;\n                skillModal.show();\n            } catch (err) { alert('Error loading skill'); }\n        }\n\n        async function saveSkill() {\n            const name = document.getElementById('skillName').value.trim();\n            const description = document.getElementById('skillDescription').value.trim();\n            const content = document.getElementById('skillContent').value.trim();\n            if (!name || !content) return;\n\n            try {\n                const res = await fetch('/admin/skills', {\n                    method: 'POST',\n                    headers: {'Content-Type': 'application/json'},\n                    body: JSON.stringify({name, description, content})\n                });\n                const data = await res.json();\n                if (data.success) {\n                    skillModal.hide();\n                    fetchSkills();\n                } else { alert('Error saving skill'); }\n            } catch (err) { alert('Request failed'); }\n        }\n\n        async function deleteSkill(name) {\n            if (!confirm(`Are you sure you want to delete skill \"${name}\"?`)) return;\n            try {\n                const res = await fetch(`/admin/skills/${name}`, { method: 'DELETE' });\n                const data = await res.json();\n                if (data.success) {\n                    fetchSkills();\n                } else { alert('Error deleting skill'); }\n            } catch (err) { alert('Request failed'); }\n        }\n\n        function renderSkillsCheckboxes(selectedSkills = []) {\n            const container = document.getElementById('skillsContainer');\n            container.innerHTML = '';\n            \n            if (allSkills.length === 0) {\n                container.innerHTML = '<span class=\"text-muted small\">No skills found in .opencode/skills/</span>';\n                return;\n            }\n\n            allSkills.forEach(skill => {\n                const div = document.createElement('div');\n                div.className = 'form-check form-check-inline';\n                const checked = selectedSkills.includes(skill) ? 'checked' : '';\n                div.innerHTML = `\n                    <input class=\"form-check-input skill-checkbox\" type=\"checkbox\" value=\"${skill}\" id=\"skill_${skill}\" ${checked}>\n                    <label class=\"form-check-label small\" for=\"skill_${skill}\">${skill}</label>\n                `;\n                container.appendChild(div);\n            });\n        }\n\n        async function fetchMCP() {\n            try {\n                const res = await fetch('/admin/mcp');\n                const servers = await res.json();\n                const tbody = document.getElementById('mcpTableBody');\n                tbody.innerHTML = '';\n                \n                servers.forEach(s => {\n                    const tr = document.createElement('tr');\n                    tr.innerHTML = `\n                        <td>\n                            <div class=\"form-check form-switch\">\n                                <input class=\"form-check-input\" type=\"checkbox\" role=\"switch\" ${s.enabled ? 'checked' : ''} \n                                    onchange=\"toggleMCP('${s.name}', this.checked)\">\n                                <span class=\"badge ${s.status === 'Connected' ? 'bg-success' : 'bg-secondary'} ms-1\" style=\"font-size: 0.6rem;\">${s.status}</span>\n                            </div>\n                        </td>\n                        <td><strong>${s.name}</strong></td>\n                        <td><code>${s.command}</code></td>\n                        <td>\n                            <button class=\"btn btn-sm btn-outline-danger\" onclick=\"removeMCP('${s.name}')\"><i class=\"bi bi-trash\"></i></button>\n                        </td>\n                    `;\n                    tbody.appendChild(tr);\n                });\n            } catch (err) {\n                console.error('Error fetching MCP servers:', err);\n            }\n        }\n\n        function showNewMCP() {\n            document.getElementById('mcpForm').reset();\n            mcpModal.show();\n        }\n\n        async function saveMCP() {\n            const name = document.getElementById('mcpName').value;\n            const command = document.getElementById('mcpCommand').value;\n            const args = document.getElementById('mcpArgs').value;\n            \n            if (!name || !command) return;\n            \n            try {\n                const res = await fetch('/admin/mcp/add', {\n                    method: 'POST',\n                    headers: {'Content-Type': 'application/json'},\n                    body: JSON.stringify({name, command, args})\n                });\n                const data = await res.json();\n                if (data.success) {\n                    mcpModal.hide();\n                    fetchMCP();\n                } else {\n                    alert('Error adding MCP: ' + data.output);\n                }\n            } catch (err) {\n                alert('Request failed');\n            }\n        }\n\n        async function removeMCP(name) {\n            if (!confirm(`Are you sure you want to remove MCP server \"${name}\"?`)) return;\n            try {\n                const res = await fetch('/admin/mcp/remove', {\n                    method: 'POST',\n                    headers: {'Content-Type': 'application/json'},\n                    body: JSON.stringify({name})\n                });\n                const data = await res.json();\n                if (data.success) {\n                    fetchMCP();\n                } else {\n                    alert('Error removing MCP: ' + data.output);\n                }\n            } catch (err) {\n                alert('Request failed');\n            }\n        }\n\n        async function toggleMCP(name, enabled) {\n            try {\n                const res = await fetch('/admin/mcp/toggle', {\n                    method: 'POST',\n                    headers: {'Content-Type': 'application/json'},\n                    body: JSON.stringify({name, enabled})\n                });\n                const data = await res.json();\n                if (!data.success) {\n                    alert('Error toggling MCP: ' + data.output);\n                    fetchMCP(); // Revert UI\n                }\n            } catch (err) {\n                alert('Request failed');\n                fetchMCP();\n            }\n        }\n\n        async function fetchAgents() {\n            try {\n                const res = await fetch('/admin/agents');\n                allAgents = await res.json();\n                updateCategoryFilter();\n                renderAgents();\n                validateOrchestration();\n            } catch (e) { console.error('Error fetching agents:', e); }\n        }\n\n        async function fetchGlobalSettings() {\n            try {\n                const res = await fetch('/admin/settings');\n                const data = await res.json();\n                if (data.interactive_mode_instructions) {\n                    document.getElementById('interactive-mode-instructions').value = data.interactive_mode_instructions;\n                }\n            } catch (e) { console.error('Error fetching settings:', e); }\n        }\n\n        async function saveGlobalSettings() {\n            const status = document.getElementById('settings-status');\n            const interactiveInstructions = document.getElementById('interactive-mode-instructions').value;\n            \n            status.textContent = 'Saving...';\n            status.className = 'small mt-2 text-info';\n\n            try {\n                const res = await fetch('/admin/settings', {\n                    method: 'POST',\n                    headers: { 'Content-Type': 'application/json' },\n                    body: JSON.stringify({ \n                        interactive_mode_instructions: interactiveInstructions\n                    })\n                });\n                const data = await res.json();\n                if (data.success) {\n                    status.textContent = 'Settings saved successfully!';\n                    status.className = 'small mt-2 text-success';\n                    setTimeout(() => { status.textContent = ''; }, 3000);\n                } else {\n                    status.textContent = 'Error saving settings';\n                    status.className = 'small mt-2 text-danger';\n                }\n            } catch (e) {\n                status.textContent = 'Error: ' + e.message;\n                status.className = 'small mt-2 text-danger';\n            }\n        }\n\n        function resetInteractiveModeInstructions() {\n            const defaultInstructions = `You can ask interactive multiple-choice or open-ended questions to the user in their preferred language (e.g., Greek).\nTo trigger a question card, include a JSON block in your response using this format:\n{\"type\": \"question\", \"question\": \"Your question text here\", \"options\": [\"Option 1\", \"Option 2\"], \"allow_multiple\": false}\n- The 'question' and 'options' values should match the language of the conversation.\n- If 'allow_multiple' is true, users can select several options.\n- If 'options' is empty [], it is an open-ended question.\nThe user's response will be sent back to you as a normal message.`;\n            \n            document.getElementById('interactive-mode-instructions').value = defaultInstructions;\n        }\n\n        function updateCategoryFilter() {\n            const filter = document.getElementById('categoryFilter');\n            const categories = [...new Set(allAgents.map(a => a.category))].sort();\n            \n            // Keep \"All Categories\"\n            filter.innerHTML = '<option value=\"all\">All Categories</option>';\n            categories.forEach(cat => {\n                const opt = document.createElement('option');\n                opt.value = cat;\n                opt.textContent = cat;\n                filter.appendChild(opt);\n            });\n        }\n\n        function renderAgents() {\n            const filter = document.getElementById('categoryFilter').value;\n            const tbody = document.getElementById('agentsTableBody');\n            tbody.innerHTML = '';\n\n            const filtered = filter === 'all' ? allAgents : allAgents.filter(a => a.category === filter);\n\n            filtered.forEach(agent => {\n                const tr = document.createElement('tr');\n                const isEnabled = agent.parent !== null && agent.parent !== undefined;\n                const isRoot = agent.category === 'root';\n                \n                tr.innerHTML = `\n                    <td><span class=\"badge bg-secondary\">${agent.category}</span></td>\n                    <td>\n                        <div class=\"form-check form-switch\">\n                            <input class=\"form-check-input\" type=\"checkbox\" role=\"switch\" \n                                id=\"agentEnabled_${agent.category}_${agent.folder_name}\" \n                                ${isEnabled ? 'checked' : ''}\n                                ${isRoot ? 'disabled' : ''}\n                                onchange=\"toggleAgentEnabled('${agent.category}', '${agent.folder_name}', this.checked)\">\n                        </div>\n                    </td>\n                    <td><strong>${agent.name}</strong></td>\n                    <td><code>${agent.folder_name}</code></td>\n                    <td class=\"small text-muted\">${agent.description || ''}</td>\n                    <td>\n                        <button class=\"btn btn-sm btn-outline-info me-1\" onclick=\"editAgent('${agent.category}', '${agent.folder_name}')\">Edit</button>\n                        <button class=\"btn btn-sm btn-outline-danger\" onclick=\"deleteAgent('${agent.category}', '${agent.folder_name}')\">Delete</button>\n                    </td>\n                `;\n                tbody.appendChild(tr);\n            });\n        }\n\n        async function toggleAgentEnabled(category, name, enabled) {\n            try {\n                const res = await fetch(`/admin/agents/${category}/${name}/toggle-enabled`, {\n                    method: 'POST',\n                    headers: { 'Content-Type': 'application/json' },\n                    body: JSON.stringify({ enabled })\n                });\n                const result = await res.json();\n                if (result.success) {\n                    validateOrchestration();\n                } else {\n                    alert('Error toggling agent status');\n                    document.getElementById(`agentEnabled_${category}_${name}`).checked = !enabled;\n                }\n            } catch (e) {\n                console.error(e);\n                alert('Error');\n                document.getElementById(`agentEnabled_${category}_${name}`).checked = !enabled;\n            }\n        }\n\n        async function validateOrchestration() {\n            try {\n                const res = await fetch('/admin/agents/validate');\n                const data = await res.json();\n                const container = document.getElementById('orchestration-warnings');\n                container.innerHTML = '';\n                \n                if (data.warnings && data.warnings.length > 0) {\n                    const alert = document.createElement('div');\n                    alert.className = 'alert alert-warning border-warning bg-dark-subtle py-2 mb-0';\n                    alert.innerHTML = `\n                        <div class=\"d-flex align-items-center\">\n                            <i class=\"bi bi-exclamation-triangle-fill me-2 text-warning\"></i>\n                            <div>\n                                <h6 class=\"alert-heading mb-1 small fw-bold\">Orchestration Warnings</h6>\n                                <ul class=\"mb-0 small ps-3\">\n                                    ${data.warnings.map(w => `<li>${w}</li>`).join('')}\n                                </ul>\n                            </div>\n                        </div>\n                    `;\n                    container.appendChild(alert);\n                }\n            } catch (e) { console.error('Validation error:', e); }\n        }\n\n        function showAgentEditor(agent = null) {\n            const isEdit = !!agent;\n            document.getElementById('agentModalTitle').textContent = isEdit ? 'Edit Agent' : 'New Agent';\n            document.getElementById('agentCategory').value = agent ? agent.category : '';\n            document.getElementById('agentFolder').value = agent ? agent.folder_name : '';\n            document.getElementById('agentName').value = agent ? agent.name : '';\n            document.getElementById('agentDescription').value = agent ? agent.description : '';\n            document.getElementById('agentPrompt').value = agent ? agent.prompt : '';\n            \n            // Disable folder/category edit if editing\n            document.getElementById('agentCategory').disabled = isEdit;\n            document.getElementById('agentFolder').disabled = isEdit;\n            \n            renderSkillsCheckboxes(agent ? (agent.skills || []) : []);\n            \n            agentModal.show();\n        }\n\n        async function editAgent(category, name) {\n            try {\n                const res = await fetch(`/admin/agents/${category}/${name}`);\n                const agent = await res.json();\n                showAgentEditor(agent);\n            } catch (e) { console.error(e); alert('Error fetching agent details'); }\n        }\n\n        async function editRootAgent() {\n            try {\n                const res = await fetch('/admin/agents/root');\n                const agent = await res.json();\n                showAgentEditor(agent);\n            } catch (e) { console.error(e); alert('Error fetching root agent'); }\n        }\n\n        async function saveAgent() {\n            const skillChecks = document.querySelectorAll('.skill-checkbox:checked');\n            const skills = Array.from(skillChecks).map(c => c.value);\n\n            const agentData = {\n                category: document.getElementById('agentCategory').value.trim(),\n                folder_name: document.getElementById('agentFolder').value.trim(),\n                name: document.getElementById('agentName').value.trim(),\n                description: document.getElementById('agentDescription').value.trim(),\n                prompt: document.getElementById('agentPrompt').value.trim(),\n                skills: skills\n            };\n\n            if (!agentData.category || !agentData.folder_name || !agentData.name || !agentData.prompt) {\n                alert('Please fill in all required fields');\n                return;\n            }\n\n            const url = agentData.category === 'root' ? '/admin/agents/root' : '/admin/agents';\n\n            try {\n                const res = await fetch(url, {\n                    method: 'POST',\n                    headers: { 'Content-Type': 'application/json' },\n                    body: JSON.stringify(agentData)\n                });\n                const result = await res.json();\n                if (result.success) {\n                    agentModal.hide();\n                    fetchAgents();\n                } else {\n                    alert('Error saving agent');\n                }\n            } catch (e) { console.error(e); alert('Error saving agent'); }\n        }\n\n        async function deleteAgent(category, name) {\n            if (!confirm(`Are you sure you want to delete agent \"${name}\" in category \"${category}\"?`)) return;\n\n            try {\n                const res = await fetch(`/admin/agents/${category}/${name}`, { method: 'DELETE' });\n                const result = await res.json();\n                if (result.success) {\n                    fetchAgents();\n                } else {\n                    alert('Error deleting agent');\n                }\n            } catch (e) { console.error(e); alert('Error deleting agent'); }\n        }\n\n        function showChangePassword(username) {\n            document.getElementById('targetUsername').innerText = username;\n            document.getElementById('modalUsername').value = username;\n            passwordModal.show();\n        }\n\n        \n        async function togglePattern(username, enabled) {\n            try {\n                const formData = new FormData();\n                formData.append('username', username);\n                formData.append('disabled', !enabled);\n                const res = await fetch('/admin/user/toggle-pattern', { method: 'POST', body: formData });\n                const data = await res.json();\n                if (data.success) {\n                    const label = document.querySelector(`label[for=\"patternSwitch_${username}\"]`);\n                    if (label) label.textContent = enabled ? 'Enabled' : 'Disabled';\n                } else {\n                    alert('Failed to update');\n                    document.getElementById(`patternSwitch_${username}`).checked = !enabled;\n                }\n            } catch (e) { console.error(e); alert('Error'); }\n        }\n\n        async function changeRole(username, newRole) {\n            if (username === 'admin' && newRole === 'user') {\n                alert('Cannot demote primary admin.');\n                return;\n            }\n            if (!confirm(`Change role of user \"${username}\" to \"${newRole}\"?`)) return;\n\n            try {\n                const formData = new FormData();\n                formData.append('username', username);\n                formData.append('role', newRole);\n                const res = await fetch('/admin/user/toggle-role', { method: 'POST', body: formData });\n                const data = await res.json();\n                if (data.success) {\n                    location.reload();\n                } else {\n                    alert('Failed to update role');\n                }\n            } catch (e) { console.error(e); alert('Error'); }\n        }\n\n        async function deleteUser(username) {\n            if (confirm(`Are you sure you want to delete user ${username}?`)) {\n                const formData = new FormData();\n                formData.append('username', username);\n                const res = await fetch('/admin/user/remove', {\n                    method: 'POST',\n                    body: formData\n                });\n                if (res.ok) {\n                    location.reload();\n                } else {\n                    alert('Error deleting user');\n                }\n            }\n        }\n\n        async function syncPatterns() {\n            const status = document.getElementById('sync-status');\n            status.textContent = 'Syncing... Please wait.';\n            status.className = 'small mt-2 text-info';\n            \n            try {\n                const res = await fetch('/admin/patterns/sync', { method: 'POST' });\n                const data = await res.json();\n                if (data.success) {\n                    status.textContent = `Successfully synced ${data.count} patterns!`;\n                    status.className = 'small mt-2 text-success';\n                } else {\n                    status.textContent = 'Error: ' + (data.error || 'Unknown error');\n                    status.className = 'small mt-2 text-danger';\n                }\n            } catch (e) {\n                status.textContent = 'Error: ' + e.message;\n                status.className = 'small mt-2 text-danger';\n            }\n        }\n\n        async function clearAllTags() {\n            if (!confirm('Are you sure you want to CLEAR ALL chat tags? This cannot be undone.')) return;\n\n            const status = document.getElementById('sync-status');\n            status.textContent = 'Clearing tags...';\n            status.className = 'small mt-2 text-info';\n            \n            try {\n                const res = await fetch('/admin/sessions/cleartags', { method: 'POST' });\n                if (!res.ok) throw new Error(`Server error ${res.status}`);\n                const data = await res.json();\n                if (data.success) {\n                    status.textContent = `Successfully cleared tags from ${data.count} sessions!`;\n                    status.className = 'small mt-2 text-success';\n                } else {\n                    status.textContent = 'Error: ' + (data.error || 'Unknown error');\n                    status.className = 'small mt-2 text-danger';\n                }\n            } catch (e) {\n                status.textContent = 'Error: ' + e.message;\n                status.className = 'small mt-2 text-danger';\n            }\n        }\n\n        async function updateLogLevel(level) {\n            const status = document.getElementById('sync-status');\n            try {\n                const res = await fetch('/admin/system/log-level', {\n                    method: 'POST',\n                    headers: { 'Content-Type': 'application/json' },\n                    body: JSON.stringify({ level })\n                });\n                if (res.ok) {\n                    status.textContent = `Logging level updated to ${level}`;\n                    status.className = 'small mt-2 text-success';\n                    setTimeout(() => { status.textContent = ''; }, 3000);\n                }\n            } catch (e) { console.error(e); }\n        }\n\n        async function restartSetup() {\n            if (confirm('Are you sure you want to RESTART SETUP? This will DELETE ALL USERS and you will need to re-configure the admin account.')) {\n                try {\n                    const res = await fetch('/admin/system/restart-setup', { method: 'POST' });\n                    const data = await res.json();\n                    if (data.success) {\n                        window.location.href = '/setup';\n                    } else {\n                        alert('Failed to restart setup');\n                    }\n                } catch (e) {\n                    console.error(e);\n                    alert('Error');\n                }\n            }\n        }\n    </script>\n</body>\n</html>\n",
    "index.html": "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n    <meta charset=\"UTF-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n    <title>OpenCode Termux Agent</title>\n    <link rel=\"manifest\" href=\"/manifest.json?v=2\">\n    <link rel=\"icon\" type=\"image/svg+xml\" href=\"/static/icon.svg?v=2\">\n    <meta name=\"theme-color\" content=\"#6c757d\">\n    <meta name=\"mobile-web-app-capable\" content=\"yes\">\n    <meta name=\"apple-mobile-web-app-status-bar-style\" content=\"black-translucent\">\n    <link rel=\"apple-touch-icon\" href=\"/static/icon.svg?v=2\">\n    <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css\" rel=\"stylesheet\">\n    <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css\">\n    <link rel=\"stylesheet\" href=\"https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/styles/github-dark.min.css\">\n    <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css\">\n    <link rel=\"stylesheet\" href=\"/static/style.css?v={{ range(1, 999999) | random }}\">\n    <script src=\"https://cdnjs.cloudflare.com/ajax/libs/ethers/5.7.2/ethers.umd.min.js\"></script>\n    <script defer src=\"https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js\"></script>\n    <script defer src=\"https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js\"></script>\n</head>\n<body class=\"bg-dark text-light\">\n\n<div class=\"container-fluid d-flex flex-column vh-100 p-0\">\n    <!-- Header -->\n    <!-- Header -->\n    <header class=\"p-2 border-bottom border-secondary bg-black d-flex justify-content-between align-items-center\">\n        <div class=\"d-flex align-items-center\">\n            <button class=\"btn btn-outline-secondary btn-sm me-2\" type=\"button\" data-bs-toggle=\"offcanvas\" data-bs-target=\"#historySidebar\" aria-controls=\"historySidebar\">\n                <i class=\"bi bi-layout-sidebar-inset\"></i>\n            </button>\n            <div class=\"d-flex align-items-center gap-2\">\n                <svg xmlns=\"http://www.w3.org/2000/svg\" width=\"20\" height=\"20\" fill=\"#6c757d\" viewBox=\"0 0 16 16\" class=\"me-1\"><path d=\"M6 12.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 0 1h-3a.5.5 0 0 1-.5-.5M3 8.062C3 6.76 4.235 5.765 5.53 5.886a26.6 26.6 0 0 0 4.94 0C11.765 5.765 13 6.76 13 8.062v1.157a.93.93 0 0 1-.765.935c-.845.147-2.34.346-4.235.346s-3.39-.2-4.235-.346A.93.93 0 0 1 3 9.219zm4.542-.827a.25.25 0 0 0-.217.068l-.92.9a25 25 0 0 1-1.871-.183.25.25 0 0 0-.068.495c.55.076 1.232.149 2.02.193a.25.25 0 0 0 .189-.071l.754-.736.847 1.71a.25.25 0 0 0 .404.062l.932-.97a25 25 0 0 0 1.922-.188.25.25 0 0 0-.068-.495c-.538.074-1.207.145-1.98.189a.25.25 0 0 0-.166.076l-.754.785-.842-1.7a.25.25 0 0 0-.182-.135\"/><path d=\"M8.5 1.866a1 1 0 1 0-1 0V3h-2A4.5 4.5 0 0 0 1 7.5V8a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1v1a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-1a1 1 0 0 0 1-1V9a1 1 0 0 0-1-1v-.5A4.5 4.5 0 0 0 10.5 3h-2zM14 7.5V13a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V7.5A3.5 3.5 0 0 1 5.5 4h5A3.5 3.5 0 0 1 14 7.5\"/></svg>\n                <span class=\"small fw-bold d-md-none text-truncate\" style=\"max-width: 100px;\">{{ user }}</span>\n            </div>\n            <div id=\"chat-tags-header\" class=\"d-none d-md-flex align-items-center gap-2 ms-3 overflow-auto\" style=\"max-width: 40vw;\">\n                <!-- Desktop tags -->\n            </div>\n        </div>\n\n        <div class=\"d-flex align-items-center gap-2\">\n            <span class=\"badge bg-secondary d-none d-md-inline-block\"><i class=\"bi bi-person\"></i> {{ user }}</span>\n            \n            <!-- Mobile Actions Button -->\n            <div class=\"d-md-none\">\n                <button class=\"btn btn-outline-light btn-sm\" type=\"button\" data-bs-toggle=\"offcanvas\" data-bs-target=\"#actionsSidebar\" aria-controls=\"actionsSidebar\" id=\"mobile-actions-toggle\">\n                    <i class=\"bi bi-three-dots-vertical\"></i>\n                </button>\n            </div>\n\n            <!-- Desktop Actions -->\n            <div class=\"d-none d-md-flex gap-2\">\n                {% if is_admin %}\n                <a href=\"/admin\" class=\"btn btn-outline-info btn-sm\" title=\"Admin\"><i class=\"bi bi-gear\"></i> <span class=\"d-none d-lg-inline\">Admin</span></a>\n                {% endif %}\n                <button id=\"tree-view-btn\" class=\"btn btn-outline-info btn-sm\" data-bs-toggle=\"modal\" data-bs-target=\"#treeViewModal\" title=\"View Conversation Tree\"><svg width=\"16\" height=\"16\" fill=\"currentColor\" viewBox=\"0 0 16 16\" class=\"bi\"><path d=\"M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 2.25 0 1 1 1.5 0v.878a2.25 2.25 0 0 1-2.25 2.25h-1.5v2.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25v-.878a2.25 2.25 0 1 1 1.5 0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z\"></path></svg> <span class=\"d-none d-lg-inline\">Tree</span></button>\n                <button id=\"security-btn\" class=\"btn btn-outline-light btn-sm\" data-bs-toggle=\"modal\" data-bs-target=\"#securityModal\" title=\"Security\"><i class=\"bi bi-shield-lock\"></i> <span class=\"d-none d-lg-inline\">Security</span></button>\n                <button id=\"share-btn\" class=\"btn btn-outline-primary btn-sm\" data-bs-toggle=\"modal\" data-bs-target=\"#shareModal\" title=\"Share Chat\"><i class=\"bi bi-share\"></i> <span class=\"d-none d-lg-inline\">Share</span></button>\n                <button id=\"export-btn\" class=\"btn btn-outline-success btn-sm\" title=\"Export Chat\"><i class=\"bi bi-download\"></i> <span class=\"d-none d-lg-inline\">Export</span></button>\n                <button id=\"reset-btn\" class=\"btn btn-outline-warning btn-sm\" title=\"Reset Chat\"><i class=\"bi bi-trash\"></i> <span class=\"d-none d-lg-inline\">Reset</span></button>\n                <button id=\"patterns-btn\" class=\"btn btn-outline-info btn-sm\" data-bs-toggle=\"modal\" data-bs-target=\"#patternsModal\" title=\"Patterns\"><i class=\"bi bi-collection\"></i> <span class=\"d-none d-lg-inline\">Patterns</span></button>\n                <a href=\"/logout\" class=\"btn btn-outline-danger btn-sm\" title=\"Logout\"><i class=\"bi bi-box-arrow-right\"></i> <span class=\"d-none d-lg-inline\">Logout</span></a>\n            </div>\n        </div>\n    </header>\n\n    <!-- History Sidebar (Offcanvas) -->\n    <div class=\"offcanvas offcanvas-start bg-dark text-light border-end border-secondary\" tabindex=\"-1\" id=\"historySidebar\" aria-labelledby=\"historySidebarLabel\">\n      <div class=\"offcanvas-header border-bottom border-secondary\">\n        <h5 class=\"offcanvas-title\" id=\"historySidebarLabel\"><i class=\"bi bi-clock-history\"></i> Chat History</h5>\n        <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"offcanvas\" aria-label=\"Close\"></button>\n      </div>\n      <div class=\"offcanvas-body p-0 d-flex flex-column\">\n        <div class=\"p-3 border-bottom border-secondary\">\n            <button id=\"new-chat-btn\" class=\"btn btn-primary w-100 mb-2\"><i class=\"bi bi-plus-lg\"></i> New Chat</button>\n            <div class=\"mt-2\">\n                <div class=\"input-group input-group-sm\">\n                    <span class=\"input-group-text bg-dark border-secondary text-secondary\"><i class=\"bi bi-search\"></i></span>\n                    <input type=\"text\" id=\"session-search\" class=\"form-control bg-dark text-light border-secondary shadow-none\" placeholder=\"Search history...\">\n                </div>\n            </div>\n            <div id=\"tag-filter-container\" class=\"mt-2 d-flex flex-wrap gap-1\">\n                <!-- Tags will be loaded here -->\n            </div>\n        </div>\n        <div class=\"flex-grow-1 overflow-auto\">\n            <div id=\"sessions-list\" class=\"list-group list-group-flush\">\n                <!-- Pinned Section -->\n                <div id=\"pinned-sessions-header\" class=\"sidebar-section-header d-none px-3 py-2 small text-uppercase fw-bold text-muted bg-black bg-opacity-25 border-bottom border-secondary border-opacity-25\">\n                    <i class=\"bi bi-pin-angle-fill me-1\"></i> Pinned\n                </div>\n                <div id=\"pinned-sessions-list\"></div>\n\n                <!-- Recent Section -->\n                <div id=\"history-sessions-header\" class=\"sidebar-section-header d-none px-3 py-2 small text-uppercase fw-bold text-muted bg-black bg-opacity-25 border-bottom border-secondary border-opacity-25\">\n                    <i class=\"bi bi-clock-history me-1\"></i> Recent\n                </div>\n                <div id=\"history-sessions-list\">\n                    <!-- Sessions will be loaded here -->\n                    <div id=\"sidebar-initial-loader\" class=\"text-center p-3\">\n                        <div class=\"spinner-border text-info spinner-border-sm\" role=\"status\"></div>\n                    </div>\n                </div>\n            </div>\n            <div id=\"sidebar-load-more-container\" class=\"p-3 text-center d-none\">\n                <button id=\"sidebar-load-more-btn\" class=\"btn btn-outline-secondary btn-sm w-100\">Load More</button>\n            </div>\n        </div>\n      </div>\n    </div>\n\n    <!-- Actions Sidebar (Right Offcanvas) -->\n    <div class=\"offcanvas offcanvas-end bg-dark text-light border-start border-secondary\" tabindex=\"-1\" id=\"actionsSidebar\" aria-labelledby=\"actionsSidebarLabel\">\n      <div class=\"offcanvas-header border-bottom border-secondary\">\n        <h5 class=\"offcanvas-title\" id=\"actionsSidebarLabel\"><i class=\"bi bi-gear\"></i> Actions</h5>\n        <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"offcanvas\" aria-label=\"Close\"></button>\n      </div>\n      <div class=\"offcanvas-body p-0\">\n        <div class=\"list-group list-group-flush\">\n            <div class=\"p-3 border-bottom border-secondary bg-black d-flex align-items-center gap-2\">\n                <i class=\"bi bi-person-circle h4 m-0 text-primary\"></i>\n                <span class=\"text-truncate\">{{ user }}</span>\n                {% if is_admin %}<span class=\"badge bg-info ms-auto\">Admin</span>{% endif %}\n            </div>\n            \n            <!-- Workspace Section -->\n            <div class=\"p-3 border-bottom border-secondary\">\n                <h6 class=\"small text-muted text-uppercase fw-bold mb-2\">Workspace</h6>\n                <div class=\"input-group input-group-sm mb-2\">\n                    <span class=\"input-group-text bg-dark border-secondary text-secondary\"><i class=\"bi bi-folder2-open\"></i></span>\n                    <input type=\"text\" id=\"session-workspace-input-sidebar\" class=\"form-control bg-dark text-light border-secondary\" list=\"workspace-suggestions\" placeholder=\"/path/to/workspace\">\n                </div>\n                <button id=\"btn-update-workspace-sidebar\" class=\"btn btn-outline-info btn-sm w-100\">Update Workspace</button>\n                <div id=\"git-status-container-sidebar\" class=\"mt-2 d-none\">\n                    <div class=\"d-flex justify-content-between align-items-center bg-black bg-opacity-50 p-2 rounded border border-secondary border-opacity-25\">\n                        <span class=\"small text-muted\"><i class=\"bi bi-git\"></i> <span id=\"git-branch-sidebar\">main</span> <i class=\"bi bi-arrow-clockwise cursor-pointer ms-1\" onclick=\"updateGitStatus()\" title=\"Refresh Git Status\"></i></span>\n                        <span id=\"git-changes-badge-sidebar\" class=\"badge bg-warning text-dark d-none\">M</span>\n                    </div>\n                </div>\n                <div id=\"workspace-status-sidebar\" class=\"mt-2 small text-center\"></div>\n            </div>\n\n            {% if is_admin %}\n            <a href=\"/admin\" class=\"list-group-item list-group-item-action bg-dark text-light border-secondary\"><i class=\"bi bi-gear me-2\"></i> Admin Maintenance</a>\n            {% endif %}\n            <button id=\"tree-view-btn-mobile\" class=\"list-group-item list-group-item-action bg-dark text-info border-secondary\" data-bs-toggle=\"modal\" data-bs-target=\"#treeViewModal\" data-bs-dismiss=\"offcanvas\"><svg width=\"16\" height=\"16\" fill=\"currentColor\" viewBox=\"0 0 16 16\" class=\"bi me-2\"><path d=\"M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 2.25 0 1 1 1.5 0v.878a2.25 2.25 0 0 1-2.25 2.25h-1.5v2.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25v-.878a2.25 2.25 0 1 1 1.5 0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z\"></path></svg> Conversation Tree</button>\n            <button class=\"list-group-item list-group-item-action bg-dark text-primary border-secondary\" data-bs-toggle=\"modal\" data-bs-target=\"#shareModal\" data-bs-dismiss=\"offcanvas\"><i class=\"bi bi-share me-2\"></i> Share Chat</button>\n            <button class=\"list-group-item list-group-item-action bg-dark text-light border-secondary\" data-bs-toggle=\"modal\" data-bs-target=\"#securityModal\" data-bs-dismiss=\"offcanvas\"><i class=\"bi bi-shield-lock me-2\"></i> Security Settings</button>\n            <button class=\"list-group-item list-group-item-action bg-dark text-light border-secondary\" data-bs-toggle=\"modal\" data-bs-target=\"#patternsModal\" data-bs-dismiss=\"offcanvas\"><i class=\"bi bi-collection me-2\"></i> Available Patterns</button>\n            <button id=\"export-btn-mobile\" class=\"list-group-item list-group-item-action bg-dark text-light border-secondary\" data-bs-dismiss=\"offcanvas\"><i class=\"bi bi-download me-2\"></i> Export Conversation</button>\n            <button id=\"reset-btn-mobile\" class=\"list-group-item list-group-item-action bg-dark text-warning border-secondary\" data-bs-dismiss=\"offcanvas\"><i class=\"bi bi-trash me-2\"></i> Reset History</button>\n            <a href=\"/logout\" class=\"list-group-item list-group-item-action bg-dark text-danger border-secondary\"><i class=\"bi bi-box-arrow-right me-2\"></i> Logout</a>\n        </div>\n      </div>\n    </div>\n\n    <!-- Chat Area -->\n    <div id=\"chat-container\" class=\"flex-grow-1 overflow-auto p-3 position-relative\">\n        <div id=\"drag-drop-overlay\" class=\"d-none position-absolute top-0 start-0 w-100 h-100 d-flex flex-column align-items-center justify-content-center bg-dark bg-opacity-75\" style=\"z-index: 1000; pointer-events: none;\">\n            <div class=\"border border-primary border-3 border-dashed rounded-3 p-5 d-flex flex-column align-items-center\">\n                <i class=\"bi bi-cloud-arrow-up text-primary\" style=\"font-size: 4rem;\"></i>\n                <h4 class=\"text-primary mt-3\">Drop files to attach</h4>\n            </div>\n        </div>\n        <div id=\"scroll-sentinel\" style=\"height: 10px; width: 100%;\"></div>\n        <div id=\"load-more-container\" class=\"text-center {{ 'd-none' if not has_more else '' }} mb-3\">\n            <button id=\"load-more-btn\" class=\"btn btn-outline-secondary btn-sm\">Load Older Messages</button>\n        </div>\n        <div id=\"chat-welcome\" class=\"text-center text-muted mt-3\">\n            <p>Start a conversation with Gemini.</p>\n            <p class=\"small\">Try <code>/help</code> to see available commands.</p>\n        </div>\n    </div>\n\n    <!-- Input Area -->\n    <footer class=\"py-3 px-3 border-top border-secondary bg-black\">\n        <form id=\"chat-form\" class=\"d-flex flex-column gap-1\">\n            \n            <div id=\"attachment-queue\" class=\"d-flex flex-wrap gap-2\">\n                <!-- Attachment items will be injected here -->\n            </div>\n\n            <div class=\"d-flex align-items-end gap-2\">\n                <!-- Left Actions: Model & Attach -->\n                <div class=\"d-flex gap-1 pb-1\">\n                    <div class=\"btn-group dropup\">\n                        <button class=\"btn btn-secondary btn-sm rounded-circle\" type=\"button\" data-bs-toggle=\"dropdown\" aria-expanded=\"false\" title=\"Select Model\">\n                            <i class=\"bi bi-cpu\"></i>\n                        </button>\n                        <ul class=\"dropdown-menu shadow-lg border-secondary\" id=\"model-dropdown-menu\" style=\"width: 320px; max-height: 500px;\">\n                            <li><h6 class=\"dropdown-header\">Model Selection</h6></li>\n                            <li class=\"px-2 pb-2 border-bottom border-secondary border-opacity-25\">\n                                <div class=\"input-group input-group-sm\">\n                                    <span class=\"input-group-text bg-dark border-secondary text-secondary\"><i class=\"bi bi-search\"></i></span>\n                                    <input type=\"text\" id=\"model-search\" class=\"form-control bg-dark text-light border-secondary shadow-none\" placeholder=\"Search models...\">\n                                </div>\n                            </li>\n                            <div id=\"model-list-container\" style=\"max-height: 400px; overflow-y: auto;\">\n                                <!-- Model items will be dynamically injected here -->\n                            </div>\n                        </ul>\n                    </div>\n                    <input type=\"hidden\" name=\"model\" id=\"model-input\" value=\"{{ active_session.model if active_session and active_session.model else user_settings.default_model }}\">\n                    \n                    <div class=\"btn-group dropup\">\n                        <button class=\"btn btn-outline-info btn-sm rounded-circle\" type=\"button\" data-bs-toggle=\"dropdown\" aria-expanded=\"false\" title=\"Select Agent\">\n                            <i class=\"bi bi-person-badge\"></i>\n                        </button>\n                        <ul class=\"dropdown-menu\" id=\"agent-dropdown-menu\">\n                            <li><h6 class=\"dropdown-header\">Agent Selection</h6></li>\n                            <li><a class=\"dropdown-item active\" href=\"#\" data-agent=\"default\">Default Agent</a></li>\n                            <li><a class=\"dropdown-item\" href=\"#\" data-agent=\"github\">GitHub Agent</a></li>\n                            <li><a class=\"dropdown-item\" href=\"#\" data-agent=\"expert\">Expert Agent</a></li>\n                        </ul>\n                    </div>\n                    <input type=\"hidden\" name=\"agent\" id=\"agent-input\" value=\"default\">\n                    \n                    <label class=\"btn btn-outline-secondary btn-sm rounded-circle\" for=\"file-upload\" title=\"Attach Files\">\n                        <i class=\"bi bi-paperclip\"></i>\n                    </label>\n                    <input type=\"file\" id=\"file-upload\" name=\"file\" class=\"d-none\" multiple>\n                    \n                    <div class=\"d-flex gap-2\">\n                        <button class=\"btn btn-outline-info btn-sm rounded-circle d-none\" type=\"button\" id=\"drive-mode-btn\" title=\"Drive Mode (Voice Loop)\">\n                            <i class=\"bi bi-mic-fill\"></i>\n                        </button>\n                    </div>\n\n                    <button class=\"btn btn-outline-warning btn-sm rounded-circle\" type=\"button\" id=\"plan-mode-btn\" title=\"Toggle Plan Mode (Experimental)\">\n                        <i class=\"bi bi-journal-text\"></i>\n                    </button>\n                </div>\n\n                <!-- Text Input -->\n                <div class=\"flex-grow-1\">\n                    <textarea class=\"form-control bg-dark text-light border-secondary shadow-none\" id=\"message-input\" name=\"message\" rows=\"2\" placeholder=\"Message OpenCode...\" required style=\"border-radius: 20px;\"></textarea>\n                </div>\n                \n                <!-- Send Button -->\n                <button class=\"btn btn-primary rounded-circle p-2\" type=\"submit\" id=\"send-btn\" style=\"width: 45px; height: 45px;\">\n                    <i class=\"bi bi-send-fill\"></i>\n                </button>\n                \n                <!-- Stop Button (Hidden by default) -->\n                <button class=\"btn btn-danger rounded-circle p-2 d-none\" type=\"button\" id=\"stop-btn\" style=\"width: 45px; height: 45px;\" title=\"Stop Response\">\n                    <i class=\"bi bi-stop-fill\"></i>\n                </button>\n            </div>\n            \n            <div class=\"text-center\">\n                {% set current_model = active_session.model if active_session and active_session.model else user_settings.default_model %}\n                {% set display_model = \"Antigravity Pro\" if \"pro\" in current_model.lower() else (\"Antigravity Flash\" if \"flash\" in current_model.lower() else (\"Antigravity Sonnet\" if \"sonnet\" in current_model.lower() else (\"Antigravity Opus\" if \"opus\" in current_model.lower() else current_model))) %}\n                <small class=\"text-muted\" style=\"font-size: 0.7rem;\">Currently using: <span id=\"model-label\">{{ display_model }}</span></small>\n            </div>\n        </form>\n    </footer>\n</div>\n\n<!-- Toast Container -->\n<div class=\"toast-container position-fixed bottom-0 end-0 p-3\">\n    <div id=\"liveToast\" class=\"toast align-items-center text-white bg-primary border-0\" role=\"alert\" aria-live=\"assertive\" aria-atomic=\"true\">\n        <div class=\"d-flex\">\n            <div class=\"toast-body\" id=\"toast-body\">\n                Notification message\n            </div>\n            <button type=\"button\" class=\"btn-close btn-close-white me-2 m-auto\" data-bs-dismiss=\"toast\" aria-label=\"Close\"></button>\n        </div>\n    </div>\n</div>\n\n<!-- Patterns Modal -->\n<div class=\"modal fade\" id=\"patternsModal\" tabindex=\"-1\" aria-labelledby=\"patternsModalLabel\">\n  <div class=\"modal-dialog modal-lg modal-dialog-scrollable\">\n    <div class=\"modal-content bg-dark text-light border-secondary\">\n      <div class=\"modal-header border-secondary\">\n        <h5 class=\"modal-title\" id=\"patternsModalLabel\"><i class=\"bi bi-collection\"></i> Available Patterns</h5>\n        <button type=\"button\" class=\"btn btn-primary btn-sm ms-auto me-2\" id=\"btn-new-prompt\">\n            <i class=\"bi bi-plus-lg\"></i> New Prompt\n        </button>\n        <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>\n      </div>\n      <div class=\"modal-body\">\n        <div class=\"mb-3\">\n            <input type=\"text\" id=\"pattern-search\" class=\"form-control bg-dark text-light border-secondary\" placeholder=\"Search patterns...\">\n        </div>\n        <div class=\"list-group\" id=\"patterns-list\">\n            <!-- Patterns will be loaded here -->\n            <div class=\"text-center p-3\">\n                <div class=\"spinner-border text-info\" role=\"status\"></div>\n            </div>\n        </div>\n      </div>\n    </div>\n  </div>\n</div>\n\n<!-- Security Modal -->\n<div class=\"modal fade\" id=\"securityModal\" tabindex=\"-1\" aria-labelledby=\"securityModalLabel\">\n  <div class=\"modal-dialog\">\n    <div class=\"modal-content bg-dark text-light border-secondary\">\n      <div class=\"modal-header border-secondary\">\n        <h5 class=\"modal-title\" id=\"securityModalLabel\"><i class=\"bi bi-shield-lock\"></i> Security Settings</h5>\n        <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>\n      </div>\n      <div class=\"modal-body\">\n        <div class=\"mb-4\">\n            <h6><i class=\"bi bi-key\"></i> Passkeys</h6>\n            <p class=\"small text-muted\">Register a Passkey for faster, more secure login without a password.</p>\n            <button id=\"btn-register-passkey\" class=\"btn btn-outline-info w-100\"><i class=\"bi bi-plus-lg\"></i> Register New Passkey</button>\n            <div id=\"passkey-reg-status\" class=\"mt-2 small\"></div>\n        </div>\n        <hr class=\"border-secondary\">\n        <div class=\"mb-4\">\n            <h6><i class=\"bi bi-grid-3x3\"></i> Login Pattern</h6>\n            <p class=\"small text-muted\">Change your pattern-based login.</p>\n            <div class=\"text-center mb-3\">\n                <div id=\"pattern-container-security\" class=\"mx-auto\" style=\"width: 200px; height: 200px; position: relative; touch-action: none;\">\n                    <svg id=\"pattern-svg-security\" width=\"200\" height=\"200\" style=\"background: #252525; border-radius: 10px;\"></svg>\n                </div>\n                <input type=\"hidden\" id=\"pattern-input-security\">\n            </div>\n            <button id=\"btn-update-pattern\" class=\"btn btn-outline-warning w-100\">Update Pattern</button>\n            <div id=\"pattern-update-status\" class=\"mt-2 small\"></div>\n        </div>\n        <hr class=\"border-secondary\">\n        <div class=\"mb-3\">\n            <h6><i class=\"bi bi-wallet2\"></i> Crypto Wallet</h6>\n            <p class=\"small text-muted\">Link your Ethereum wallet (MetaMask/Brave) to sign in using your wallet.</p>\n            <div class=\"input-group mb-2\">\n                <input type=\"text\" id=\"wallet-address-input\" class=\"form-control bg-dark text-light border-secondary\" placeholder=\"0x...\" readonly>\n                <button id=\"btn-link-wallet\" class=\"btn btn-outline-primary\">Link Wallet</button>\n            </div>\n            <div id=\"wallet-link-status\" class=\"mt-2 small\"></div>\n        </div>\n        <hr class=\"border-secondary\">\n        <div class=\"mb-3\">\n            <h6><i class=\"bi bi-sliders\"></i> Preferences</h6>\n            <div class=\"form-check form-switch mb-2\">\n                <input class=\"form-check-input\" type=\"checkbox\" role=\"switch\" id=\"setting-show-mic\">\n                <label class=\"form-check-label\" for=\"setting-show-mic\">Show Drive Mode (Mic)</label>\n            </div>\n            <div class=\"d-none\">\n                <input class=\"form-check-input\" type=\"checkbox\" role=\"switch\" id=\"setting-show-plan\">\n                <label class=\"form-check-label\" for=\"setting-show-plan\">Show Plan Mode</label>\n            </div>\n            <div class=\"form-check form-switch mb-2\">\n                <input class=\"form-check-input\" type=\"checkbox\" role=\"switch\" id=\"setting-interactive-mode\">\n                <label class=\"form-check-label\" for=\"setting-interactive-mode\">Interactive Mode (AI Questions)</label>\n            </div>\n            <div class=\"form-check form-switch mb-2\">\n                <input class=\"form-check-input\" type=\"checkbox\" role=\"switch\" id=\"setting-lite-mode\">\n                <label class=\"form-check-label\" for=\"setting-lite-mode\">Lite Mode (Performance)</label>\n            </div>\n            <div class=\"form-check form-switch\">\n                <input class=\"form-check-input\" type=\"checkbox\" role=\"switch\" id=\"setting-copy-formatted\">\n                <label class=\"form-check-label\" for=\"setting-copy-formatted\">Copy Formatted Text</label>\n            </div>\n            <div class=\"mb-3\">\n                <label for=\"session-workspace-input-settings\" class=\"form-label small text-muted\">Current Session Workspace</label>\n                <div class=\"input-group input-group-sm mb-2\">\n                    <span class=\"input-group-text bg-dark border-secondary text-secondary\"><i class=\"bi bi-folder2-open\"></i></span>\n                    <input type=\"text\" id=\"session-workspace-input-settings\" class=\"form-control bg-dark text-light border-secondary\" list=\"workspace-suggestions\" placeholder=\"/path/to/workspace\">\n                </div>\n                <button id=\"btn-update-workspace-settings\" class=\"btn btn-outline-info btn-sm w-100\">Update Current Session Workspace</button>\n                <div id=\"git-status-container-settings\" class=\"mt-2 d-none\">\n                    <div class=\"d-flex justify-content-between align-items-center bg-black bg-opacity-50 p-2 rounded border border-secondary border-opacity-25\">\n                        <span class=\"small text-muted\"><i class=\"bi bi-git\"></i> <span id=\"git-branch-settings\">main</span> <i class=\"bi bi-arrow-clockwise cursor-pointer ms-1\" onclick=\"updateGitStatus()\" title=\"Refresh Git Status\"></i></span>\n                        <span id=\"git-changes-badge-settings\" class=\"badge bg-warning text-dark d-none\">M</span>\n                    </div>\n                </div>\n                <div id=\"workspace-status-settings\" class=\"mt-2 small text-center\"></div>\n            </div>\n            <div class=\"mb-3\">\n                <label for=\"setting-default-workspace\" class=\"form-label small text-muted\">Default Workspace</label>\n                <div class=\"input-group input-group-sm\">\n                    <span class=\"input-group-text bg-dark border-secondary text-secondary\"><i class=\"bi bi-folder\"></i></span>\n                    <input type=\"text\" id=\"setting-default-workspace\" class=\"form-control bg-dark text-light border-secondary\" list=\"workspace-suggestions\" placeholder=\"/path/to/workspace\">\n                </div>\n            </div>\n            <div class=\"mb-3 mt-3\">\n                <label for=\"setting-default-model\" class=\"form-label small text-muted\">Default Model</label>\n                <select class=\"form-select form-select-sm bg-dark text-light border-secondary\" id=\"setting-default-model\">\n                    <option value=\"google/antigravity-gemini-3.1-pro\">Antigravity Pro (3.1)</option>\n                    <option value=\"google/antigravity-gemini-3-flash\">Antigravity Flash (3.0)</option>\n                    <option value=\"google/antigravity-claude-sonnet-4-6\">Antigravity Sonnet (4.6)</option>\n                    <option value=\"google/antigravity-claude-opus-4-6-thinking\">Antigravity Opus (Thinking)</option>\n                    <option value=\"google/gemini-2.5-pro\">Gemini 2.5 Pro</option>\n                    <option value=\"google/gemini-2.5-flash\">Gemini 2.5 Flash</option>\n                </select>\n            </div>\n        </div>\n      </div>\n    </div>\n  </div>\n</div>\n\n<!-- Rename Session Modal -->\n<div class=\"modal fade\" id=\"renameSessionModal\" tabindex=\"-1\" aria-labelledby=\"renameSessionModalLabel\">\n  <div class=\"modal-dialog\">\n    <div class=\"modal-content bg-dark text-light border-secondary\">\n      <div class=\"modal-header border-secondary\">\n        <h5 class=\"modal-title\" id=\"renameSessionModalLabel\"><i class=\"bi bi-pencil-square\"></i> Rename Chat</h5>\n        <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>\n      </div>\n      <div class=\"modal-body\">\n        <div class=\"mb-3\">\n            <label for=\"rename-input\" class=\"form-label\">Chat Title</label>\n            <input type=\"text\" class=\"form-control bg-dark text-light border-secondary\" id=\"rename-input\">\n        </div>\n      </div>\n      <div class=\"modal-footer border-secondary justify-content-end\">\n        <div>\n            <button type=\"button\" class=\"btn btn-secondary me-2\" data-bs-dismiss=\"modal\">Cancel</button>\n            <button type=\"button\" class=\"btn btn-primary\" id=\"btn-save-rename\">Save</button>\n        </div>\n      </div>\n    </div>\n  </div>\n</div>\n\n<!-- Edit Prompt Modal -->\n<div class=\"modal fade\" id=\"editPromptModal\" tabindex=\"-1\" aria-labelledby=\"editPromptModalLabel\">\n  <div class=\"modal-dialog modal-lg\">\n    <div class=\"modal-content bg-dark text-light border-secondary\">\n      <div class=\"modal-header border-secondary\">\n        <h5 class=\"modal-title\" id=\"editPromptModalTitle\"><i class=\"bi bi-pencil\"></i> Edit Custom Prompt</h5>\n        <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>\n      </div>\n      <div class=\"modal-body\">\n        <div class=\"mb-3\">\n            <label for=\"edit-prompt-filename\" class=\"form-label small text-muted\">Title / Filename</label>\n            <input type=\"text\" class=\"form-control bg-dark text-light border-secondary\" id=\"edit-prompt-filename\">\n        </div>\n        <div class=\"mb-3\">\n            <label for=\"edit-prompt-content\" class=\"form-label small text-muted\">Content</label>\n            <textarea class=\"form-control bg-dark text-light border-secondary\" id=\"edit-prompt-content\" rows=\"15\" style=\"font-family: monospace;\"></textarea>\n        </div>\n      </div>\n      <div class=\"modal-footer border-secondary\">\n        <button type=\"button\" class=\"btn btn-secondary btn-sm\" data-bs-dismiss=\"modal\">Cancel</button>\n        <button type=\"button\" id=\"btn-save-prompt-edit\" class=\"btn btn-primary btn-sm\">Save Changes</button>\n      </div>\n    </div>\n  </div>\n</div>\n\n\n\n<!-- Tagging Modal -->\n<div class=\"modal fade\" id=\"taggingModal\" tabindex=\"-1\" aria-labelledby=\"taggingModalLabel\">\n  <div class=\"modal-dialog\">\n    <div class=\"modal-content bg-dark text-light border-secondary\">\n      <div class=\"modal-header border-secondary\">\n        <h5 class=\"modal-title\" id=\"taggingModalLabel\"><i class=\"bi bi-tags\"></i> Edit Chat Tags</h5>\n        <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>\n      </div>\n      <div class=\"modal-body\">\n        <div class=\"mb-3\">\n            <label class=\"form-label small text-muted\">Current Tags</label>\n            <div id=\"modal-current-tags\" class=\"d-flex flex-wrap gap-1 mb-2\"></div>\n            <div class=\"input-group input-group-sm\">\n                <input type=\"text\" id=\"tag-input\" class=\"form-control bg-dark text-light border-secondary\" placeholder=\"New tag...\">\n                <button class=\"btn btn-outline-secondary\" type=\"button\" id=\"btn-add-tag\">Add</button>\n            </div>\n            <small class=\"text-muted\" style=\"font-size: 0.6rem;\">Press Enter or use comma to add multiple tags.</small>\n        </div>\n        <div class=\"mb-3\">\n            <label class=\"form-label small text-muted\">Pick from existing tags</label>\n            <div id=\"modal-existing-tags\" class=\"d-flex flex-wrap gap-1\">\n                <!-- Existing tags will be loaded here -->\n            </div>\n        </div>\n      </div>\n      <div class=\"modal-footer border-secondary\">\n        <button type=\"button\" class=\"btn btn-secondary btn-sm\" data-bs-dismiss=\"modal\">Cancel</button>\n        <button type=\"button\" id=\"btn-save-tags\" class=\"btn btn-primary btn-sm\">Save Changes</button>\n      </div>\n    </div>\n  </div>\n</div>\n\n<!-- Tree View Modal -->\n<div class=\"modal fade\" id=\"treeViewModal\" tabindex=\"-1\" aria-labelledby=\"treeViewModalLabel\">\n  <div class=\"modal-dialog modal-xl modal-dialog-scrollable\">\n    <div class=\"modal-content bg-dark text-light border-secondary\">\n      <div class=\"modal-header border-secondary\">\n        <h5 class=\"modal-title\" id=\"treeViewModalLabel\"><svg width=\"20\" height=\"20\" fill=\"currentColor\" viewBox=\"0 0 16 16\" class=\"bi me-2\" style=\"margin-top: -4px;\"><path d=\"M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 2.25 0 1 1 1.5 0v.878a2.25 2.25 0 0 1-2.25 2.25h-1.5v2.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25v-.878a2.25 2.25 0 1 1 1.5 0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z\"></path></svg> Conversation Tree</h5>\n        <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>\n      </div>\n      <div class=\"modal-body\">\n        <div id=\"tree-container\" class=\"p-3 overflow-auto\" style=\"min-height: 400px;\">\n            <!-- Tree will be rendered here -->\n            <div class=\"text-center p-5\">\n                <div class=\"spinner-border text-info\" role=\"status\"></div>\n                <p class=\"mt-2\">Building conversation tree...</p>\n            </div>\n        </div>\n      </div>\n    </div>\n  </div>\n</div>\n\n<!-- Share Modal -->\n<div class=\"modal fade\" id=\"shareModal\" tabindex=\"-1\" aria-labelledby=\"shareModalLabel\">\n  <div class=\"modal-dialog\">\n    <div class=\"modal-content bg-dark text-light border-secondary\">\n      <div class=\"modal-header border-secondary\">\n        <h5 class=\"modal-title\" id=\"shareModalLabel\"><i class=\"bi bi-share\"></i> Share Chat</h5>\n        <button type=\"button\" class=\"btn-close btn-close-white\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>\n      </div>\n      <div class=\"modal-body\">\n        <p class=\"small text-muted\">Enter the username of the person you want to share this chat with. They will be able to read and participate in the conversation.</p>\n        <div class=\"mb-3\">\n            <label for=\"share-username-input\" class=\"form-label\">Username</label>\n            <input type=\"text\" class=\"form-control bg-dark text-light border-secondary\" id=\"share-username-input\" placeholder=\"e.g. bob\">\n        </div>\n        <div id=\"share-status\" class=\"small mt-2\"></div>\n      </div>\n      <div class=\"modal-footer border-secondary\">\n        <button type=\"button\" class=\"btn btn-secondary btn-sm\" data-bs-dismiss=\"modal\">Cancel</button>\n        <button type=\"button\" id=\"btn-confirm-share\" class=\"btn btn-primary btn-sm\">Share</button>\n      </div>\n    </div>\n  </div>\n</div>\n\n<script src=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js\"></script>\n<script src=\"https://cdn.jsdelivr.net/npm/marked/marked.min.js\"></script>\n<script src=\"https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/highlight.min.js\"></script>\n<script>\n    // Security Modal Logic\n    document.addEventListener('DOMContentLoaded', () => {\n        const btnLinkWallet = document.getElementById('btn-link-wallet');\n        const walletStatus = document.getElementById('wallet-link-status');\n        const btnRegisterPasskey = document.getElementById('btn-register-passkey');\n        const passkeyStatus = document.getElementById('passkey-reg-status');\n        \n        // --- Pattern Update Logic ---\n        const svgSec = document.getElementById('pattern-svg-security');\n        const patternInputSec = document.getElementById('pattern-input-security');\n        const btnUpdatePattern = document.getElementById('btn-update-pattern');\n        const patternStatus = document.getElementById('pattern-update-status');\n        const dotsSec = [];\n        const selectedDotsSec = [];\n        let isDrawingSec = false;\n        let currentLineSec = null;\n\n        // Create 3x3 grid for security modal\n        for (let y = 0; y < 3; y++) {\n            for (let x = 0; x < 3; x++) {\n                const cx = 40 + x * 60;\n                const cy = 40 + y * 60;\n                const index = y * 3 + x + 1;\n                \n                const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');\n                dot.setAttribute('cx', cx);\n                dot.setAttribute('cy', cy);\n                dot.setAttribute('r', 8);\n                dot.setAttribute('fill', '#555');\n                dot.setAttribute('data-index', index);\n                svgSec.appendChild(dot);\n                dotsSec.push({ cx, cy, index, element: dot });\n            }\n        }\n\n        function getMousePosSec(e) {\n            const rect = svgSec.getBoundingClientRect();\n            const clientX = e.touches ? e.touches[0].clientX : e.clientX;\n            const clientY = e.touches ? e.touches[0].clientY : e.clientY;\n            return {\n                x: clientX - rect.left,\n                y: clientY - rect.top\n            };\n        }\n\n        function startDrawingSec(e) {\n            isDrawingSec = true;\n            resetPatternSec();\n            handleMoveSec(e);\n        }\n\n        function handleMoveSec(e) {\n            if (!isDrawingSec) return;\n            const pos = getMousePosSec(e);\n            \n            dotsSec.forEach(dot => {\n                const dist = Math.hypot(pos.x - dot.cx, pos.y - dot.cy);\n                if (dist < 20 && !selectedDotsSec.includes(dot)) {\n                    selectedDotsSec.push(dot);\n                    dot.element.setAttribute('fill', '#ffc107');\n                    dot.element.setAttribute('r', 12);\n                    \n                    if (selectedDotsSec.length > 1) {\n                        const prevDot = selectedDotsSec[selectedDotsSec.length - 2];\n                        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');\n                        line.setAttribute('x1', prevDot.cx);\n                        line.setAttribute('y1', prevDot.cy);\n                        line.setAttribute('x2', dot.cx);\n                        line.setAttribute('y2', dot.cy);\n                        line.setAttribute('stroke', '#ffc107');\n                        line.setAttribute('stroke-width', 3);\n                        svgSec.insertBefore(line, svgSec.firstChild);\n                    }\n                }\n            });\n\n            if (selectedDotsSec.length > 0) {\n                if (currentLineSec) currentLineSec.remove();\n                const lastDot = selectedDotsSec[selectedDotsSec.length - 1];\n                currentLineSec = document.createElementNS('http://www.w3.org/2000/svg', 'line');\n                currentLineSec.setAttribute('x1', lastDot.cx);\n                currentLineSec.setAttribute('y1', lastDot.cy);\n                currentLineSec.setAttribute('x2', pos.x);\n                currentLineSec.setAttribute('y2', pos.y);\n                currentLineSec.setAttribute('stroke', '#ffc107');\n                currentLineSec.setAttribute('stroke-width', 2);\n                currentLineSec.setAttribute('stroke-dasharray', '5,5');\n                svgSec.appendChild(currentLineSec);\n            }\n        }\n\n        function stopDrawingSec() {\n            if (!isDrawingSec) return;\n            isDrawingSec = false;\n            if (currentLineSec) currentLineSec.remove();\n            patternInputSec.value = selectedDotsSec.map(d => d.index).join('');\n        }\n\n        function resetPatternSec() {\n            selectedDotsSec.length = 0;\n            svgSec.querySelectorAll('line').forEach(l => l.remove());\n            dotsSec.forEach(dot => {\n                dot.element.setAttribute('fill', '#555');\n                dot.element.setAttribute('r', 8);\n            });\n            patternInputSec.value = '';\n        }\n\n        const showMicSetting = document.getElementById('setting-show-mic');\n        const interactiveModeSetting = document.getElementById('setting-interactive-mode');\n        const copyFormattedSetting = document.getElementById('setting-copy-formatted');\n\n        if (showMicSetting && window.USER_SETTINGS) {\n            showMicSetting.checked = window.USER_SETTINGS.show_mic !== false;\n            \n            showMicSetting.onchange = async () => {\n                const enabled = showMicSetting.checked;\n                try {\n                    await fetch('/settings', {\n                        method: 'POST',\n                        headers: { 'Content-Type': 'application/json' },\n                        body: JSON.stringify({ show_mic: enabled })\n                    });\n                    window.USER_SETTINGS.show_mic = enabled;\n                    // Trigger visibility update if DriveModeManager is available\n                    if (window.updateDriveModeVisibility) window.updateDriveModeVisibility();\n                } catch (err) { console.error(err); }\n            };\n        }\n\n        if (interactiveModeSetting && window.USER_SETTINGS) {\n            interactiveModeSetting.checked = window.USER_SETTINGS.interactive_mode !== false;\n            \n            interactiveModeSetting.onchange = async () => {\n                const enabled = interactiveModeSetting.checked;\n                try {\n                    await fetch('/settings', {\n                        method: 'POST',\n                        headers: { 'Content-Type': 'application/json' },\n                        body: JSON.stringify({ interactive_mode: enabled })\n                    });\n                    window.USER_SETTINGS.interactive_mode = enabled;\n                } catch (err) { console.error(err); }\n            };\n        }\n\n        if (copyFormattedSetting && window.USER_SETTINGS) {\n            copyFormattedSetting.checked = window.USER_SETTINGS.copy_formatted === true;\n            \n            copyFormattedSetting.onchange = async () => {\n                const enabled = copyFormattedSetting.checked;\n                try {\n                    await fetch('/settings', {\n                        method: 'POST',\n                        headers: { 'Content-Type': 'application/json' },\n                        body: JSON.stringify({ copy_formatted: enabled })\n                    });\n                    window.USER_SETTINGS.copy_formatted = enabled;\n                } catch (err) { console.error(err); }\n            };\n        }\n\n        svgSec.addEventListener('mousedown', startDrawingSec);\n        window.addEventListener('mousemove', handleMoveSec);\n        window.addEventListener('mouseup', stopDrawingSec);\n\n        svgSec.addEventListener('touchstart', (e) => { e.preventDefault(); startDrawingSec(e); });\n        svgSec.addEventListener('touchmove', (e) => { e.preventDefault(); handleMoveSec(e); });\n        svgSec.addEventListener('touchend', stopDrawingSec);\n\n        btnUpdatePattern.addEventListener('click', async () => {\n            const pattern = patternInputSec.value;\n            if (!pattern) {\n                patternStatus.textContent = 'Please draw a pattern first.';\n                patternStatus.className = 'mt-2 small text-danger';\n                return;\n            }\n\n            try {\n                const formData = new FormData();\n                formData.append('pattern', pattern);\n                const res = await fetch('/user/update-pattern', {\n                    method: 'POST',\n                    body: formData\n                });\n                const result = await res.json();\n                if (result.success) {\n                    patternStatus.textContent = 'Pattern updated successfully!';\n                    patternStatus.className = 'mt-2 small text-success';\n                } else {\n                    patternStatus.textContent = result.error || 'Update failed';\n                    patternStatus.className = 'mt-2 small text-danger';\n                }\n            } catch (err) {\n                patternStatus.textContent = err.message;\n                patternStatus.className = 'mt-2 small text-danger';\n            }\n        });\n\n        btnLinkWallet.addEventListener('click', async () => {\n            if (typeof window.ethereum === 'undefined') {\n                walletStatus.textContent = 'Ethereum wallet not found.';\n                walletStatus.className = 'mt-2 small text-danger';\n                return;\n            }\n\n            try {\n                const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });\n                const address = accounts[0];\n\n                const challengeRes = await fetch('/login/web3/challenge');\n                const { challenge } = await challengeRes.json();\n\n                const provider = new ethers.providers.Web3Provider(window.ethereum);\n                const signer = provider.getSigner();\n                const signature = await signer.signMessage(challenge);\n\n                const formData = new FormData();\n                formData.append('address', address);\n                formData.append('signature', signature);\n\n                const res = await fetch('/user/link-wallet', {\n                    method: 'POST',\n                    body: formData\n                });\n\n                const result = await res.json();\n                if (result.success) {\n                    walletStatus.textContent = 'Wallet linked successfully!';\n                    walletStatus.className = 'mt-2 small text-success';\n                    document.getElementById('wallet-address-input').value = address;\n                } else {\n                    walletStatus.textContent = result.error || 'Linking failed';\n                    walletStatus.className = 'mt-2 small text-danger';\n                }\n            } catch (err) {\n                walletStatus.textContent = err.message;\n                walletStatus.className = 'mt-2 small text-danger';\n            }\n        });\n\n        btnRegisterPasskey.addEventListener('click', async () => {\n            try {\n                const optionsRes = await fetch('/register/passkey/options');\n                const options = await optionsRes.json();\n\n                options.challenge = base64urlToUint8Array(options.challenge);\n                options.user.id = base64urlToUint8Array(options.user.id);\n                if (options.excludeCredentials) {\n                    options.excludeCredentials.forEach(cred => {\n                        cred.id = base64urlToUint8Array(cred.id);\n                    });\n                }\n\n                const credential = await navigator.credentials.create({\n                    publicKey: options\n                });\n\n                const regData = {\n                    id: credential.id,\n                    rawId: bufferToBase64Url(credential.rawId),\n                    type: credential.type,\n                    response: {\n                        attestationObject: bufferToBase64Url(credential.response.attestationObject),\n                        clientDataJSON: bufferToBase64Url(credential.response.clientDataJSON),\n                    }\n                };\n\n                const verifyRes = await fetch('/register/passkey/verify', {\n                    method: 'POST',\n                    headers: { 'Content-Type': 'application/json' },\n                    body: JSON.stringify(regData)\n                });\n\n                const result = await verifyRes.json();\n                if (result.success) {\n                    passkeyStatus.textContent = 'Passkey registered successfully!';\n                    passkeyStatus.className = 'mt-2 small text-success';\n                } else {\n                    passkeyStatus.textContent = result.error || 'Registration failed';\n                    passkeyStatus.className = 'mt-2 small text-danger';\n                }\n            } catch (err) {\n                passkeyStatus.textContent = err.message;\n                passkeyStatus.className = 'mt-2 small text-danger';\n            }\n        });\n\n        function base64urlToUint8Array(base64url) {\n            const padding = '='.repeat((4 - base64url.length % 4) % 4);\n            const base64 = (base64url + padding).replace(/\\-/g, '+').replace(/_/g, '/');\n            const rawData = window.atob(base64);\n            const outputArray = new Uint8Array(rawData.length);\n            for (let i = 0; i < rawData.length; ++i) {\n                outputArray[i] = rawData.charCodeAt(i);\n            }\n            return outputArray;\n        }\n\n        function bufferToBase64Url(buffer) {\n            const bytes = new Uint8Array(buffer);\n            let binary = '';\n            for (let i = 0; i < bytes.byteLength; i++) {\n                binary += String.fromCharCode(bytes[i]);\n            }\n            const base64 = window.btoa(binary);\n            return base64.replace(/\\+/g, '-').replace(/\\//g, '_').replace(/=/g, '');\n        }\n    });\n</script>\n<script src=\"/static/compression.js?v={{ range(1, 999999) | random }}\"></script>\n<script src=\"/static/drive_mode.js?v={{ range(1, 999999) | random }}\"></script>\n<script src=\"/static/attachment_manager.js?v={{ range(1, 999999) | random }}\"></script>\n<script>\n    window.INITIAL_MESSAGES = {{ initial_messages | tojson }};\n    window.TOTAL_MESSAGES = {{ total_messages }};\n    window.ACTIVE_SESSION_UUID = \"{{ active_session.uuid if active_session else '' }}\";\n    window.USER_SETTINGS = {{ user_settings | tojson }};\n\n    // Mobile Height Fix\n\n</script>\n<script src=\"/static/script.js?v={{ range(1, 999999) | random }}\"></script>\n<script>\n    /*\n    if ('serviceWorker' in navigator) {\n        window.addEventListener('load', () => {\n            navigator.serviceWorker.register('/sw.js')\n                .then(reg => console.log('SW Registered', reg))\n                .catch(err => console.log('SW Reg Error', err));\n        });\n    }\n    */\n</script>\n    <datalist id=\"workspace-suggestions\"></datalist>\n</body>\n</html>\n"
}


STATIC = {
    "manifest.json": {
        "content": "{\n  \"name\": \"OpenCode Termux Agent\",\n  \"short_name\": \"OpenCode Agent\",\n  \"description\": \"Mobile-first web interface for Gemini AI.\",\n  \"version\": \"1.0.5\",\n  \"start_url\": \"/\",\n  \"scope\": \"/\",\n  \"display\": \"standalone\",\n  \"orientation\": \"portrait\",\n  \"background_color\": \"#121212\",\n  \"theme_color\": \"#6c757d\",\n  \"icons\": [\n    {\n      \"src\": \"/static/icon.svg?v=2\",\n      \"sizes\": \"any\",\n      \"type\": \"image/svg+xml\",\n      \"purpose\": \"any maskable\"\n    },\n    {\n      \"src\": \"/static/icon-192.png?v=2\",\n      \"sizes\": \"192x192\",\n      \"type\": \"image/png\",\n      \"purpose\": \"any\"\n    },\n    {\n      \"src\": \"/static/icon-512.png?v=2\",\n      \"sizes\": \"512x512\",\n      \"type\": \"image/png\",\n      \"purpose\": \"any\"\n    },\n    {\n      \"src\": \"/static/maskable-icon-512.png?v=2\",\n      \"sizes\": \"512x512\",\n      \"type\": \"image/png\",\n      \"purpose\": \"maskable\"\n    }\n  ]\n}\n",
        "encoding": "text"
    },
    "icon-512.png": {
        "content": "iVBORw0KGgoAAAANSUhEUgAAAgAAAAIACAMAAADDpiTIAAAABGdBTUEAALGPC/xhBQAAACBjSFJNAAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAC91BMVEUAAABsdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX0AAACKDVklAAAA+3RSTlMAAQsMJEt/wQhsBFdF+jHaKSEZE/4O6Y8RcVgC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",
        "encoding": "base64"
    },
    "attachment_manager.js": {
        "content": "class AttachmentManager {\n    constructor(options = {}) {\n        this.attachments = []; // Array of objects: { file, id, compressedFile, previewUrl, size }\n        this.maxTotalSize = options.maxTotalSize || 20 * 1024 * 1024; // Default 20MB\n        this.onQueueChange = options.onQueueChange || (() => {});\n        this.onSizeLimitExceeded = options.onSizeLimitExceeded || (() => {});\n    }\n\n    /**\n     * Adds files to the queue.\n     * @param {FileList|File[]} files \n     */\n    async addFiles(files) {\n        for (const file of Array.from(files)) {\n            const id = Math.random().toString(36).substring(2, 9);\n            let processedFile = file;\n            let previewUrl = null;\n\n            if (file.type.startsWith('image/')) {\n                try {\n                    // Assume compressImage is available globally or we'll inject it\n                    if (typeof compressImage === 'function') {\n                        processedFile = await compressImage(file);\n                    }\n                    previewUrl = URL.createObjectURL(processedFile);\n                } catch (e) {\n                    console.error(\"Compression failed for\", file.name, e);\n                }\n            }\n\n            const attachmentSize = processedFile.size;\n            if (this.getTotalSize() + attachmentSize > this.maxTotalSize) {\n                this.onSizeLimitExceeded(file.name);\n                continue;\n            }\n\n            this.attachments.push({\n                id,\n                originalFile: file,\n                file: processedFile,\n                previewUrl,\n                name: processedFile.name,\n                size: attachmentSize,\n                type: file.type\n            });\n        }\n        this.onQueueChange(this.attachments);\n    }\n\n    removeAttachment(id) {\n        const index = this.attachments.findIndex(a => a.id === id);\n        if (index !== -1) {\n            const attachment = this.attachments[index];\n            if (attachment.previewUrl) {\n                URL.revokeObjectURL(attachment.previewUrl);\n            }\n            this.attachments.splice(index, 1);\n            this.onQueueChange(this.attachments);\n        }\n    }\n\n    clear() {\n        this.attachments.forEach(a => {\n            if (a.previewUrl) URL.revokeObjectURL(a.previewUrl);\n        });\n        this.attachments = [];\n        this.onQueueChange(this.attachments);\n    }\n\n    getTotalSize() {\n        return this.attachments.reduce((sum, a) => sum + a.size, 0);\n    }\n\n    getFiles() {\n        return this.attachments.map(a => a.file);\n    }\n}\n\nif (typeof module !== 'undefined' && module.exports) {\n    module.exports = AttachmentManager;\n}\n",
        "encoding": "text"
    },
    "script.js": {
        "content": "document.addEventListener('DOMContentLoaded', () => {\n    // --- Global State ---\n    let currentActiveUUID = window.ACTIVE_SESSION_UUID || null;\n    let currentOffset = 0;\n    let sidebarOffset = 0;\n    const PAGE_LIMIT = 20;\n    const SIDEBAR_PAGE_LIMIT = 15;\n    let isLoadingHistory = false;\n    let isLoadingSidebar = false;\n    let planModeActive = false;\n    let activeTags = new Set();\n    let allUniqueTags = [];\n    let currentForkMap = {}; // index -> [uuids]\n    let allPatterns = [];\n    let sessionGeneration = 0; // Bug 9: generation counter to prevent init race\n\n    let allModels = [];\n    \n    // --- DOM Elements ---\n    const chatForm = document.getElementById('chat-form');\n    const messageInput = document.getElementById('message-input');\n    const chatContainer = document.getElementById('chat-container');\n    const sendBtn = document.getElementById('send-btn');\n    const stopBtn = document.getElementById('stop-btn');\n    const chatWelcome = document.getElementById('chat-welcome');\n    \n    const modelInput = document.getElementById('model-input');\n    const modelLabel = document.getElementById('model-label');\n    const modelDropdownMenu = document.getElementById('model-dropdown-menu');\n    \n    const agentInput = document.getElementById('agent-input');\n    const agentDropdownMenu = document.getElementById('agent-dropdown-menu');\n    \n    const workspaceInputs = [\n        document.getElementById('session-workspace-input-sidebar'),\n        document.getElementById('session-workspace-input-settings')\n    ].filter(el => el !== null);\n    \n    const updateWorkspaceBtns = [\n        document.getElementById('btn-update-workspace-sidebar'),\n        document.getElementById('btn-update-workspace-settings')\n    ].filter(el => el !== null);\n\n    const workspaceStatuses = [\n        document.getElementById('workspace-status-sidebar'),\n        document.getElementById('workspace-status-settings')\n    ].filter(el => el !== null);\n\n    const workspaceSuggestions = document.getElementById('workspace-suggestions');\n    const defaultWorkspaceSetting = document.getElementById('setting-default-workspace');\n    const defaultModelSetting = document.getElementById('setting-default-model');\n\n    const historySidebar = document.getElementById('historySidebar');\n    const sessionSearch = document.getElementById('session-search');\n    const newChatBtn = document.getElementById('new-chat-btn');\n    \n    const patternsModalEl = document.getElementById('patternsModal');\n    const patternsList = document.getElementById('patterns-list');\n    \n    const planModeBtn = document.getElementById('plan-mode-btn');\n    const driveModeBtn = document.getElementById('drive-mode-btn');\n\n    const treeViewModalEl = document.getElementById('treeViewModal');\n    const treeContainer = document.getElementById('tree-container');\n\n    const exportBtn = document.getElementById('export-btn');\n    const exportBtnMobile = document.getElementById('export-btn-mobile');\n    const resetBtn = document.getElementById('reset-btn');\n    const resetBtnMobile = document.getElementById('reset-btn-mobile');\n\n    const renameModalEl = document.getElementById('renameSessionModal');\n    const renameInput = document.getElementById('rename-input');\n    const btnSaveRename = document.getElementById('btn-save-rename');\n    let currentRenameUUID = null;\n\n    const taggingModalEl = document.getElementById('taggingModal');\n    const modalCurrentTags = document.getElementById('modal-current-tags');\n    const modalExistingTags = document.getElementById('modal-existing-tags');\n    const tagInput = document.getElementById('tag-input');\n    const btnAddTag = document.getElementById('btn-add-tag');\n    const btnSaveTags = document.getElementById('btn-save-tags');\n\n    const editPromptModalEl = document.getElementById('editPromptModal');\n    const btnSavePrompt = document.getElementById('btn-save-prompt');\n\n    const sidebarLoadMoreBtn = document.getElementById('sidebar-load-more-btn');\n    // Bug 7: Wire sidebar \"Load More\" button\n    if (sidebarLoadMoreBtn) {\n        sidebarLoadMoreBtn.onclick = () => {\n            sidebarOffset += SIDEBAR_PAGE_LIMIT;\n            loadSessions(true);\n        };\n    }\n\n    // Bug 8: Wire session search input with debounce\n    if (sessionSearch) {\n        let searchTimer;\n        sessionSearch.oninput = () => {\n            clearTimeout(searchTimer);\n            searchTimer = setTimeout(() => loadSessions(), 300);\n        };\n    }\n\n    // --- Managers ---\n    const driveMode = (typeof DriveModeManager !== 'undefined') ? new DriveModeManager() : { isSupported: () => false };\n    const attachments = (typeof AttachmentManager !== 'undefined') ? new AttachmentManager({\n        maxTotalSize: 20 * 1024 * 1024,\n        onQueueChange: (items) => renderAttachmentQueue(items),\n        onSizeLimitExceeded: (name) => showToast(`Size limit exceeded: ${name}`)\n    }) : { getFiles: () => [], clear: () => {} };\n\n    // --- UI Helpers ---\n    function renderAttachmentQueue(items) {\n        const queue = document.getElementById('attachment-queue');\n        if (!queue) return;\n        queue.innerHTML = items.map(item => `\n            <div class=\"attachment-item position-relative bg-dark border border-secondary rounded p-2 d-flex align-items-center gap-2 mb-2\" style=\"max-width: 200px;\">\n                ${item.previewUrl ? `<img src=\"${item.previewUrl}\" style=\"width: 30px; height: 30px; object-fit: cover; border-radius: 4px;\">` : `<i class=\"bi bi-file-earmark\"></i>`}\n                <span class=\"small text-truncate flex-grow-1\">${item.name}</span>\n                <button type=\"button\" class=\"btn-close btn-close-white small p-1\" style=\"font-size: 0.5rem;\" onclick=\"attachments.removeAttachment('${item.id}')\"></button>\n            </div>\n        `).join('');\n    }\n    window.attachments = attachments; // Make global for onclick handlers\n\n    // --- File Upload Handlers ---\n    const fileInput = document.getElementById('file-upload');\n    if (fileInput) {\n        fileInput.addEventListener('change', async (e) => {\n            if (e.target.files && e.target.files.length > 0) {\n                await attachments.addFiles(e.target.files);\n                fileInput.value = ''; // Reset to allow selecting same file again\n            }\n        });\n    }\n\n    // Drag and drop support\n    if (chatContainer) {\n        chatContainer.addEventListener('dragover', (e) => {\n            e.preventDefault();\n            chatContainer.classList.add('drag-over');\n        });\n        chatContainer.addEventListener('dragleave', () => {\n            chatContainer.classList.remove('drag-over');\n        });\n        chatContainer.addEventListener('drop', async (e) => {\n            e.preventDefault();\n            chatContainer.classList.remove('drag-over');\n            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {\n                await attachments.addFiles(e.dataTransfer.files);\n            }\n        });\n    }\n\n    function showToast(message) {\n        const toastEl = document.getElementById('liveToast');\n        const toastBody = document.getElementById('toast-body');\n        if (toastEl && toastBody) {\n            toastBody.textContent = message;\n            const toast = new bootstrap.Toast(toastEl);\n            toast.show();\n        }\n    }\n\n    function toggleStopButton(show) {\n        if (!sendBtn || !stopBtn) return;\n        if (show) {\n            sendBtn.classList.add('d-none');\n            stopBtn.classList.remove('d-none');\n        } else {\n            sendBtn.classList.remove('d-none');\n            stopBtn.classList.add('d-none');\n        }\n    }\n\n    function updateActiveModelUI(model) {\n        if (!modelInput) return;\n        modelInput.value = model;\n        const modelLinks = document.querySelectorAll('[data-model]');\n        let found = false;\n        modelLinks.forEach(link => {\n            if (link.dataset.model === model) {\n                link.classList.add('active');\n                let modelName = link.innerText;\n                modelName = modelName.replace('Stable (v0.28+)', '').replace('Preview', '').trim();\n                if (modelLabel) modelLabel.textContent = modelName;\n                found = true;\n            } else link.classList.remove('active');\n        });\n        if (!found && modelLabel) {\n            modelLabel.textContent = model.split('/').pop().replace(/-/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase());\n        }\n    }\n\n    function updateActiveAgentUI(agentId) {\n        if (!agentInput) return;\n        agentInput.value = agentId;\n        const agentLinks = document.querySelectorAll('[data-agent]');\n        agentLinks.forEach(link => {\n            if (link.dataset.agent === agentId) link.classList.add('active');\n            else link.classList.remove('active');\n        });\n    }\n\n    async function loadDynamicModels() {\n        if (!modelDropdownMenu) return;\n        \n        // Wire the search input that's already in HTML\n        const searchInput = document.getElementById('model-search');\n        if (searchInput) {\n            searchInput.onclick = (e) => e.stopPropagation();\n            searchInput.oninput = (e) => {\n                const query = e.target.value.toLowerCase();\n                const filtered = allModels.filter(m => m.toLowerCase().includes(query));\n                renderModelList(filtered, true);\n            };\n        }\n\n        try {\n            const res = await fetch('/models');\n            const data = await res.json();\n            if (data.models && data.models.length > 0) {\n                allModels = data.models;\n                renderModelList(allModels);\n            }\n        } catch (err) { console.error('loadDynamicModels error:', err); }\n    }\n\n    function renderModelList(models, isFiltered = false) {\n        const container = document.getElementById('model-list-container');\n        if (!container) return;\n        \n        let html = '';\n        let displayedModels = new Set();\n\n        if (!isFiltered) {\n            // Include some \"featured\" models at top if not searching\n            const featured = [\n                'google/antigravity-gemini-3.1-pro',\n                'google/antigravity-gemini-3-flash',\n                'google/antigravity-claude-sonnet-4-6',\n                'google/antigravity-claude-opus-4-6-thinking'\n            ];\n            featured.forEach(m => {\n                if (models.includes(m)) {\n                    const isActive = m === (modelInput ? modelInput.value : '');\n                    const name = m.split('/').pop().replace(/-/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase());\n                    html += `<li><a class=\"dropdown-item ${isActive ? 'active' : ''}\" href=\"#\" data-model=\"${m}\">${name} <span class=\"badge bg-secondary ms-1\" style=\"font-size: 0.6rem;\">Featured</span></a></li>`;\n                    displayedModels.add(m);\n                }\n            });\n            if (html) html += '<li><hr class=\"dropdown-divider\"></li>';\n        }\n\n        models.forEach(m => {\n            if (displayedModels.has(m)) return;\n            const isActive = m === (modelInput ? modelInput.value : '');\n            const parts = m.split('/');\n            const provider = parts[0];\n            const name = parts.length > 1 ? parts.slice(1).join('/') : parts[0];\n            html += `<li><a class=\"dropdown-item ${isActive ? 'active' : ''}\" href=\"#\" data-model=\"${m}\">${name} <small class=\"text-muted\" style=\"font-size: 0.65rem;\">(${provider})</small></a></li>`;\n        });\n        \n        container.innerHTML = html;\n        attachModelListeners();\n    }\n\n    async function loadDynamicAgents() {\n        if (!agentDropdownMenu) return;\n        try {\n            const res = await fetch('/agents');\n            const data = await res.json();\n            if (data.agents && data.agents.length > 0) {\n                let html = '<li><h6 class=\"dropdown-header\">Agent Selection</h6></li>';\n                data.agents.forEach(a => {\n                    const isActive = a.id === agentInput.value;\n                    html += `<li><a class=\"dropdown-item ${isActive ? 'active' : ''}\" href=\"#\" data-agent=\"${a.id}\">${a.name}</a></li>`;\n                });\n                agentDropdownMenu.innerHTML = html;\n                attachAgentListeners();\n            }\n        } catch (err) { console.error('loadDynamicAgents error:', err); }\n    }\n\n    function attachModelListeners() {\n        document.querySelectorAll('#model-list-container [data-model]').forEach(l => {\n            l.onclick = (e) => {\n                e.preventDefault();\n                const model = l.dataset.model;\n                updateActiveModelUI(model);\n                // Also update others in the list\n                document.querySelectorAll('#model-list-container [data-model]').forEach(link => {\n                    link.classList.toggle('active', link.dataset.model === model);\n                });\n            };\n        });\n    }\n\n    function attachAgentListeners() {\n        document.querySelectorAll('[data-agent]').forEach(l => {\n            l.onclick = (e) => {\n                e.preventDefault();\n                updateActiveAgentUI(l.dataset.agent);\n            };\n        });\n    }\n\n    // --- Workspace Management ---\n    async function loadWorkspaces() {\n        try {\n            const res = await fetch('/workspaces');\n            const data = await res.json();\n            if (data.workspaces && workspaceSuggestions) {\n                workspaceSuggestions.innerHTML = data.workspaces.map(w => `<option value=\"${w}\">`).join('');\n                window.WORKSPACE_ROOT = data.root;\n            }\n        } catch (err) { console.error('loadWorkspaces error:', err); }\n    }\n\n    async function updateGitStatus() {\n        const containers = [\n            document.getElementById('git-status-container-sidebar'),\n            document.getElementById('git-status-container-settings')\n        ].filter(el => el !== null);\n        \n        try {\n            const res = await fetch('/session/git-status');\n            const data = await res.json();\n            \n            if (data.is_repo) {\n                containers.forEach(container => container.classList.remove('d-none'));\n                \n                const branchEls = [\n                    document.getElementById('git-branch-sidebar'),\n                    document.getElementById('git-branch-settings')\n                ].filter(el => el !== null);\n                \n                const badgeEls = [\n                    document.getElementById('git-changes-badge-sidebar'),\n                    document.getElementById('git-changes-badge-settings')\n                ].filter(el => el !== null);\n                \n                branchEls.forEach(el => el.textContent = data.branch);\n                badgeEls.forEach(el => {\n                    if (data.has_changes) {\n                        el.classList.remove('d-none');\n                        el.textContent = data.change_count;\n                    } else {\n                        el.classList.add('d-none');\n                    }\n                });\n            } else {\n                containers.forEach(container => container.classList.add('d-none'));\n            }\n        } catch (err) {\n            console.error('updateGitStatus error:', err);\n            containers.forEach(container => container.classList.add('d-none'));\n        }\n    }\n\n    async function loadSessionWorkspace(uuid) {\n        if (workspaceInputs.length === 0 || !uuid) return;\n        try {\n            const res = await fetch(`/session/workspace/${uuid}`);\n            const data = await res.json();\n            if (data.path) {\n                workspaceInputs.forEach(input => input.value = data.path);\n                updateGitStatus();\n            }\n        } catch (err) { console.error('loadSessionWorkspace error:', err); }\n    }\n\n    updateWorkspaceBtns.forEach((btn, idx) => {\n        btn.onclick = async () => {\n            const uuid = currentActiveUUID || 'pending';\n            const input = workspaceInputs[idx];\n            const status = workspaceStatuses[idx];\n            if (!input) return;\n            \n            const path = input.value.trim();\n            if (!path) { showToast('Enter a workspace path'); return; }\n            if (status) status.textContent = 'Updating...';\n            try {\n                const res = await fetch('/session/workspace', {\n                    method: 'POST',\n                    headers: { 'Content-Type': 'application/json' },\n                    body: JSON.stringify({ uuid, path })\n                });\n                const data = await res.json();\n                if (data.success) {\n                    if (status) {\n                        status.textContent = 'Workspace updated!';\n                        status.className = 'mt-2 small text-center text-success';\n                        setTimeout(() => { status.textContent = ''; }, 2000);\n                    }\n                    // Sync other inputs\n                    workspaceInputs.forEach(inp => inp.value = path);\n                    loadPatterns();\n                    updateGitStatus();\n                } else {\n                    if (status) {\n                        status.textContent = 'Error: Path must be within root';\n                        status.className = 'mt-2 small text-center text-danger';\n                    }\n                }\n            } catch (err) { if (status) status.textContent = 'Network error'; }\n        };\n    });\n\n    // --- Settings ---\n    if (defaultModelSetting && window.USER_SETTINGS) {\n        defaultModelSetting.value = window.USER_SETTINGS.default_model || '';\n        defaultModelSetting.onchange = async () => {\n            const model = defaultModelSetting.value;\n            const res = await fetch('/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ default_model: model }) });\n            if (res.ok) { window.USER_SETTINGS.default_model = model; if (!currentActiveUUID) updateActiveModelUI(model); showToast('Default model updated'); }\n        };\n    }\n\n    if (defaultWorkspaceSetting && window.USER_SETTINGS) {\n        defaultWorkspaceSetting.value = window.USER_SETTINGS.default_workspace || '';\n        defaultWorkspaceSetting.onchange = async () => {\n            const workspace = defaultWorkspaceSetting.value.trim();\n            if (!workspace) return;\n            const res = await fetch('/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ default_workspace: workspace }) });\n            if (res.ok) { window.USER_SETTINGS.default_workspace = workspace; showToast('Default workspace updated'); loadWorkspaces(); }\n        };\n    }\n\n    const liteModeSetting = document.getElementById('setting-lite-mode');\n    if (liteModeSetting && window.USER_SETTINGS) {\n        liteModeSetting.checked = window.USER_SETTINGS.lite_mode === true;\n        if (liteModeSetting.checked) document.body.classList.add('lite-mode');\n        \n        liteModeSetting.onchange = async () => {\n            const enabled = liteModeSetting.checked;\n            const res = await fetch('/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ lite_mode: enabled }) });\n            if (res.ok) { \n                window.USER_SETTINGS.lite_mode = enabled; \n                document.body.classList.toggle('lite-mode', enabled);\n                showToast(`Lite Mode ${enabled ? 'enabled' : 'disabled'}`); \n            }\n        };\n    }\n\n    const showMicSetting = document.getElementById('setting-show-mic');\n    if (showMicSetting && window.USER_SETTINGS) {\n        showMicSetting.checked = window.USER_SETTINGS.show_mic !== false;\n        showMicSetting.onchange = async () => {\n            const enabled = showMicSetting.checked;\n            const res = await fetch('/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ show_mic: enabled }) });\n            if (res.ok) { window.USER_SETTINGS.show_mic = enabled; updateDriveModeVisibility(); }\n        };\n    }\n\n    const showPlanSetting = document.getElementById('setting-show-plan');\n    if (showPlanSetting && window.USER_SETTINGS) {\n        showPlanSetting.checked = window.USER_SETTINGS.show_plan === true;\n        showPlanSetting.onchange = async () => {\n            const enabled = showPlanSetting.checked;\n            const res = await fetch('/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ show_plan: enabled }) });\n            if (res.ok) { window.USER_SETTINGS.show_plan = enabled; updatePlanModeVisibility(); }\n        };\n    }\n\n    function updateDriveModeVisibility() {\n        if (!driveModeBtn) return;\n        const isEnabled = window.USER_SETTINGS && window.USER_SETTINGS.show_mic !== false;\n        if (driveMode.isSupported && driveMode.isSupported() && isEnabled) driveModeBtn.classList.remove('d-none');\n        else driveModeBtn.classList.add('d-none');\n    }\n\n    function updatePlanModeVisibility() {\n        if (!planModeBtn) return;\n        planModeBtn.classList.remove('d-none');\n    }\n\n    // --- Session History ---\n    async function loadSessions(append = false) {\n        if (isLoadingSidebar) return;\n        if (!append) sidebarOffset = 0;\n        isLoadingSidebar = true;\n        let query = sessionSearch ? sessionSearch.value.trim() : \"\";\n        let url = `/sessions?limit=${SIDEBAR_PAGE_LIMIT}&offset=${sidebarOffset}`;\n        if (activeTags.size > 0) url += `&tags=${encodeURIComponent(Array.from(activeTags).join(','))}`;\n        if (query) url = `/sessions/search?q=${encodeURIComponent(query)}`;\n        try {\n            const res = await fetch(url);\n            const data = await res.json();\n            renderSessions(data, append);\n            const sessions = Array.isArray(data) ? data : (data.history || []);\n            const activeSession = sessions.find(s => s.active || s.uuid === currentActiveUUID);\n            if (activeSession && activeSession.model) updateActiveModelUI(activeSession.model);\n            if (sidebarLoadMoreBtn) {\n                 const total = data.total_unpinned || 0;\n                 sidebarLoadMoreBtn.parentElement.classList.toggle('d-none', Array.isArray(data) || (sidebarOffset + sessions.length >= total));\n            }\n        } catch (e) { console.error('loadSessions error:', e); } \n        finally { isLoadingSidebar = false; }\n    }\n\n    function getFriendlyWorkspaceName(path) {\n        if (!path) return 'Default';\n        const root = window.WORKSPACE_ROOT || '';\n        let cp = path.replace(/\\\\/g, '/');\n        let cr = root.replace(/\\\\/g, '/');\n        \n        // Remove trailing slashes for comparison\n        if (cp.endsWith('/')) cp = cp.slice(0, -1);\n        if (cr.endsWith('/')) cr = cr.slice(0, -1);\n\n        if (cp.toLowerCase() === cr.toLowerCase()) return 'Project Root';\n        \n        if (cp.toLowerCase().startsWith(cr.toLowerCase() + '/')) {\n            return cp.substring(cr.length + 1);\n        }\n        \n        return cp.split('/').pop() || cp;\n    }\n\n    function toggleWorkspaceCollapse(header) {\n        const group = header.closest('.workspace-group');\n        if (group) {\n            group.classList.toggle('collapsed');\n            const icon = header.querySelector('.collapse-icon');\n            if (icon) {\n                icon.classList.toggle('bi-chevron-down');\n                icon.classList.toggle('bi-chevron-right');\n            }\n        }\n    }\n    window.toggleWorkspaceCollapse = toggleWorkspaceCollapse;\n\n    function renderSessions(data, append = false) {\n        const pinnedList = document.getElementById('pinned-sessions-list');\n        const historyList = document.getElementById('history-sessions-list');\n        const pinnedHeader = document.getElementById('pinned-sessions-header');\n        let pinned = data.pinned || [];\n        let history = Array.isArray(data) ? data : (data.history || []);\n        \n        const createHTML = (s) => `\n            <div class=\"list-group-item list-group-item-action bg-dark text-light session-item ${(s.active || s.uuid === currentActiveUUID) ? 'active-session' : ''}\" data-uuid=\"${s.uuid}\">\n                <div class=\"d-flex justify-content-between align-items-start\">\n                    <div class=\"flex-grow-1 overflow-hidden\">\n                        <span class=\"session-title text-truncate d-block\">${s.title || 'Untitled Chat'}</span>\n                        <div class=\"session-tags-list\">${(s.tags || []).map(t => `<span class=\"session-tag-item\">${t}</span>`).join('')}</div>\n                        <span class=\"session-time text-muted small\">${s.time || ''}</span>\n                    </div>\n                    <div class=\"d-flex align-items-center gap-1\">\n                        <button class=\"btn btn-sm pin-btn border-0 ${s.pinned ? 'text-warning' : 'text-muted'}\" data-uuid=\"${s.uuid}\"><i class=\"bi ${s.pinned ? 'bi-pin-fill' : 'bi-pin'}\"></i></button>\n                        <button class=\"btn btn-sm tag-btn border-0 text-warning\" data-uuid=\"${s.uuid}\"><i class=\"bi bi-tags\"></i></button>\n                        <button class=\"btn btn-sm rename-session-btn border-0 text-info\" data-uuid=\"${s.uuid}\"><i class=\"bi bi-pencil\"></i></button>\n                        <button class=\"btn btn-sm btn-outline-danger border-0 delete-session-btn\" data-uuid=\"${s.uuid}\"><i class=\"bi bi-trash\"></i></button>\n                    </div>\n                </div>\n            </div>`;\n            \n        if (!append) {\n            if (pinnedList) pinnedList.innerHTML = pinned.map(createHTML).join('');\n            if (pinnedHeader) pinnedHeader.classList.toggle('d-none', pinned.length === 0);\n            \n            if (historyList) {\n                const groups = {};\n                history.forEach(s => {\n                    const ws = s.workspace || 'default';\n                    if (!groups[ws]) groups[ws] = [];\n                    groups[ws].push(s);\n                });\n                \n                let historyHTML = '';\n                Object.keys(groups).forEach(wsPath => {\n                    const friendlyName = getFriendlyWorkspaceName(wsPath);\n                    historyHTML += `\n                        <div class=\"workspace-group\" data-workspace=\"${wsPath}\">\n                            <div class=\"workspace-group-header px-3 py-1 small text-muted bg-black bg-opacity-25 border-bottom border-secondary border-opacity-10 d-flex align-items-center gap-2 mt-1 cursor-pointer\" onclick=\"toggleWorkspaceCollapse(this)\">\n                                <i class=\"bi bi-chevron-down collapse-icon\" style=\"font-size: 0.6rem;\"></i>\n                                <i class=\"bi bi-folder2 text-secondary\"></i> \n                                <span class=\"fw-bold flex-grow-1\">${friendlyName}</span>\n                                <span class=\"badge bg-dark border border-secondary border-opacity-25 text-muted\" style=\"font-size: 0.6rem;\">${groups[wsPath].length}</span>\n                            </div>\n                            <div class=\"workspace-items\">\n                                ${groups[wsPath].map(createHTML).join('')}\n                            </div>\n                        </div>\n                    `;\n                });\n                historyList.innerHTML = historyHTML;\n            }\n        } else if (historyList) {\n            historyList.insertAdjacentHTML('beforeend', history.map(createHTML).join(''));\n        }\n        attachSessionListeners();\n    }\n\n    function attachSessionListeners() {\n        document.querySelectorAll('.session-item').forEach(item => { item.onclick = (e) => { if (!e.target.closest('button')) switchSession(item.dataset.uuid); }; });\n        document.querySelectorAll('.pin-btn').forEach(btn => { btn.onclick = async (e) => { e.stopPropagation(); await fetch(`/sessions/${btn.dataset.uuid}/pin`, { method: 'POST' }); loadSessions(); }; });\n        document.querySelectorAll('.tag-btn').forEach(btn => { btn.onclick = (e) => { e.stopPropagation(); openTaggingModal(btn.dataset.uuid); }; });\n        document.querySelectorAll('.rename-session-btn').forEach(btn => {\n            btn.onclick = (e) => {\n                e.stopPropagation();\n                currentRenameUUID = btn.dataset.uuid;\n                renameInput.value = btn.closest('.session-item').querySelector('.session-title').textContent;\n                new bootstrap.Modal(renameModalEl).show();\n            };\n        });\n        document.querySelectorAll('.delete-session-btn').forEach(btn => {\n            btn.onclick = async (e) => {\n                e.stopPropagation();\n                if (confirm('Delete this chat?')) { await fetch('/sessions/delete', { method: 'POST', body: new URLSearchParams({ session_uuid: btn.dataset.uuid }) }); if (btn.dataset.uuid === currentActiveUUID) window.location.reload(); else loadSessions(); }\n            };\n        });\n    }\n\n    if (btnSaveRename) {\n        btnSaveRename.onclick = async () => {\n            const title = renameInput.value.trim();\n            if (!title || !currentRenameUUID) return;\n            const res = await fetch(`/sessions/${currentRenameUUID}/title`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title }) });\n            if (res.ok) { bootstrap.Modal.getInstance(renameModalEl).hide(); loadSessions(); }\n        };\n    }\n\n    async function handleNewChat() {\n        try {\n            sessionGeneration++;\n            const res = await fetch('/sessions/new', { method: 'POST' });\n            if (res.ok) {\n                currentActiveUUID = null;\n                window.ACTIVE_SESSION_UUID = null;\n                window.INITIAL_MESSAGES = [];\n                chatContainer.innerHTML = '';\n                if (chatWelcome) chatWelcome.classList.remove('d-none');\n                currentOffset = 0;\n                window.TOTAL_MESSAGES = 0;\n                if (window.USER_SETTINGS && window.USER_SETTINGS.default_model) updateActiveModelUI(window.USER_SETTINGS.default_model);\n                if (window.USER_SETTINGS && window.USER_SETTINGS.default_workspace) {\n                    workspaceInputs.forEach(input => input.value = window.USER_SETTINGS.default_workspace);\n                }\n                const sidebar = document.getElementById('historySidebar');\n                if (sidebar) bootstrap.Offcanvas.getInstance(sidebar)?.hide();\n                showToast('New session started');\n                loadSessions();\n                loadPatterns();\n            }\n        } catch (e) { console.error('Error starting new chat:', e); }\n    }\n    if (newChatBtn) newChatBtn.onclick = handleNewChat;\n\n    async function switchSession(uuid) {\n        if (uuid === currentActiveUUID) { \n            const sidebar = document.getElementById('historySidebar');\n            if (sidebar) bootstrap.Offcanvas.getInstance(sidebar)?.hide(); \n            return; \n        }\n        sessionGeneration++;\n        chatContainer.innerHTML = '<div class=\"text-center text-muted mt-5\"><p>Loading conversation...</p></div>';\n        try {\n            const res = await fetch('/sessions/switch', { method: 'POST', body: new URLSearchParams({ session_uuid: uuid }) });\n            const data = await res.json();\n            if (data.success) {\n                currentActiveUUID = uuid;\n                await loadMessages(uuid);\n                const sidebar = document.getElementById('historySidebar');\n                if (sidebar) bootstrap.Offcanvas.getInstance(sidebar)?.hide();\n                loadSessions();\n                loadSessionWorkspace(uuid);\n                loadPatterns();\n            }\n        } catch (e) {\n            console.error('switchSession error:', e);\n            chatContainer.innerHTML = '<div class=\"text-center text-danger mt-5\"><p>Failed to load conversation. Please try again.</p></div>';\n        }\n    }\n\n    async function loadMessages(uuid, limit = PAGE_LIMIT, offset = 0) {\n        if (isLoadingHistory) return;\n        isLoadingHistory = true;\n        if (offset === 0) { \n            currentActiveUUID = uuid; \n            chatContainer.innerHTML = '<div id=\"scroll-sentinel\" style=\"height: 10px; width: 100%;\"></div>'; \n            currentOffset = 0; \n            if (chatWelcome) chatWelcome.classList.add('d-none'); \n            // Re-observe the new sentinel element\n            const newSentinel = document.getElementById('scroll-sentinel');\n            if (newSentinel) observer.observe(newSentinel);\n            await fetchForks(uuid); \n        }\n\n        try {\n            const res = await fetch(`/sessions/${uuid}/messages?limit=${limit}&offset=${offset}`);\n            // Stale session guard: abort if user switched away during fetch\n            if (uuid !== currentActiveUUID) return;\n            const data = await res.json();\n            const messages = data.messages || [];\n            window.TOTAL_MESSAGES = data.total || 0;\n            if (messages.length === 0 && offset === 0) {\n                chatContainer.innerHTML = '<div class=\"text-center text-muted mt-5\"><p>No messages found or failed to load chat.</p></div>';\n            } else {\n                if (chatContainer.querySelector('.text-muted') && chatContainer.querySelector('.text-muted').innerText.includes('No messages found')) {\n                    chatContainer.innerHTML = '<div id=\"scroll-sentinel\" style=\"height: 10px; width: 100%;\"></div>';\n                    if (observer && document.getElementById('scroll-sentinel')) observer.observe(document.getElementById('scroll-sentinel'));\n                }\n            }\n            messages.forEach((msg, idx) => {\n                const index = (msg.raw_index !== undefined) ? msg.raw_index : (window.TOTAL_MESSAGES - offset - messages.length + idx);\n                // Check if message has embedded question data\n                if (msg.question) {\n                    const card = createQuestionCard(msg.question);\n                    if (card) { \n                        if (offset === 0) chatContainer.appendChild(card); \n                        else chatContainer.insertBefore(card, document.getElementById('scroll-sentinel').nextSibling); \n                    }\n                } else {\n                    const div = createMessageDiv(msg.role, msg.content, null, null, index);\n                    if (div) { \n                        if (offset === 0) chatContainer.appendChild(div); \n                        else chatContainer.insertBefore(div, document.getElementById('scroll-sentinel').nextSibling); \n                    }\n                }\n            });\n            if (offset === 0) chatContainer.scrollTop = chatContainer.scrollHeight;\n            currentOffset = offset + messages.length;\n        } catch (e) { console.error('loadMessages error:', e); } \n        finally { isLoadingHistory = false; }\n    }\n\n    async function openTaggingModal(uuid) {\n        const modal = new bootstrap.Modal(taggingModalEl);\n        try {\n            const res = await fetch(`/sessions/${uuid}/tags`);\n            const data = await res.json();\n            let workingTags = data.tags || [];\n            const render = () => {\n                modalCurrentTags.innerHTML = workingTags.map(t => `<span class=\"badge bg-primary me-1\">${t} <i class=\"bi bi-x-circle cursor-pointer\" onclick=\"window.removeTagFromWorking('${t}')\"></i></span>`).join('');\n                modalExistingTags.innerHTML = allUniqueTags.filter(t => !workingTags.includes(t)).map(t => `<span class=\"badge bg-secondary me-1 cursor-pointer\" onclick=\"window.addTagToWorking('${t}')\">${t}</span>`).join('');\n            };\n            window.removeTagFromWorking = (tag) => { workingTags = workingTags.filter(t => t !== tag); render(); };\n            window.addTagToWorking = (tag) => { if (!workingTags.includes(tag)) workingTags.push(tag); render(); };\n            btnAddTag.onclick = () => { const val = tagInput.value.trim(); if (val && !workingTags.includes(val)) { workingTags.push(val); tagInput.value = ''; render(); } };\n            btnSaveTags.onclick = async () => { const res = await fetch(`/sessions/${uuid}/tags`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ tags: workingTags }) }); if (res.ok) { modal.hide(); loadSessions(); fetchUniqueTags(); } };\n            render(); modal.show();\n        } catch (e) { console.error('openTaggingModal error:', e); }\n    }\n\n    async function fetchUniqueTags() {\n        try {\n            const res = await fetch('/sessions/tags');\n            const data = await res.json();\n            allUniqueTags = data.tags || [];\n            const container = document.getElementById('tag-filter-container');\n            if (container) container.innerHTML = allUniqueTags.map(t => `<span class=\"badge ${activeTags.has(t) ? 'bg-primary' : 'bg-dark border border-secondary'} cursor-pointer me-1 mb-1\" onclick=\"window.toggleTagFilter('${t}')\">${t}</span>`).join('');\n        } catch (e) {}\n    }\n\n    window.toggleTagFilter = (tag) => { if (activeTags.has(tag)) activeTags.delete(tag); else activeTags.add(tag); fetchUniqueTags(); loadSessions(); };\n\n    // --- Chat Flow ---\n    if (chatForm) {\n        chatForm.addEventListener('submit', async (e) => {\n            e.preventDefault();\n            console.log('Chat form submitted');\n            const msg = messageInput.value.trim();\n            const files = attachments.getFiles ? attachments.getFiles() : [];\n            if (!msg && files.length === 0) return;\n            \n            const index = window.TOTAL_MESSAGES || 0;\n            appendMessage('user', msg, null, files[0], index);\n            window.TOTAL_MESSAGES = index + 1;\n            \n            messageInput.value = ''; messageInput.style.height = '';\n            const filesToSend = [...files]; if (attachments.clear) attachments.clear();\n            const loadingId = appendLoading(); toggleStopButton(true);\n            \n            try {\n                const fd = new FormData();\n                fd.append('message', msg); \n                fd.append('model', modelInput.value);\n                if (agentInput) fd.append('agent_name', agentInput.value);\n                if (planModeActive) fd.append('plan_mode', 'true');\n                filesToSend.forEach(f => fd.append('file', f));\n                console.log('Sending fetch request to /chat');\n                const res = await fetch('/chat', { method: 'POST', body: fd });\n                console.log('Fetch response received', res.status);\n                if (!res.ok) {\n                    const errData = await res.json().catch(() => ({}));\n                    throw new Error(errData.detail || `Server error: ${res.status}`);\n                }\n                await processStream(res, loadingId);\n            } catch (error) { \n                removeLoading(loadingId); \n                appendMessage('bot', `Error: ${error.message}`); \n            } finally { \n                toggleStopButton(false); \n                loadSessions(); \n            }\n        });\n    }\n\n    async function processStream(response, loadingId) {\n        const reader = response.body.getReader();\n        const decoder = new TextDecoder();\n        let messageDiv = null, fullText = \"\", streamItems = [], buffer = \"\";\n        const streamGeneration = sessionGeneration;\n        try {\n            while (true) {\n                const { done, value } = await reader.read();\n                if (done) break;\n                buffer += decoder.decode(value, { stream: true });\n                const lines = buffer.split('\\n');\n                buffer = lines.pop();\n                for (const line of lines) {\n                    if (!line.startsWith('data: ')) continue;\n                    const dataStr = line.substring(6).trim();\n                    if (dataStr === '[DONE]') continue;\n                    try {\n                        const data = JSON.parse(dataStr);\n                        if (data.type === 'message') fullText += data.content;\n                        else if (data.type === 'init') {\n                            if (streamGeneration === sessionGeneration) {\n                                currentActiveUUID = data.session_id;\n                                window.ACTIVE_SESSION_UUID = data.session_id;\n                            }\n                        }\n                        else if (data.type === 'plan_status') {\n                            if (data.status === 'active') {\n                                const loadingEl = document.getElementById(loadingId);\n                                if (loadingEl) loadingEl.innerHTML = `<div class=\"spinner-border spinner-border-sm\"></div> ${data.message || 'Thinking...'}`;\n                            } else if (data.status === 'completed') {\n                                if (!fullText.trim() && !streamItems.length) removeLoading(loadingId);\n                            }\n                        }\n                        else if (data.type === 'raw') {\n                            fullText += data.content + '\\n';\n                        }\n                        else if (data.type === 'question') { \n                            const card = createQuestionCard(data); \n                            chatContainer.appendChild(card); \n                            chatContainer.scrollTop = chatContainer.scrollHeight; \n                            if (!fullText.trim() && !streamItems.length) removeLoading(loadingId);\n                        }\n                        else if (data.type === 'reasoning_start') {\n                            streamItems.push({ type: 'reasoning', content: data.content, active: true });\n                        }\n                        else if (data.type === 'reasoning') {\n                            const last = streamItems[streamItems.length - 1];\n                            if (last && last.type === 'reasoning' && last.active) {\n                                last.content += data.content;\n                            } else {\n                                streamItems.push({ type: 'reasoning', content: data.content, active: true });\n                            }\n                        }\n                        else if (data.type === 'reasoning_finish') {\n                            const last = streamItems[streamItems.length - 1];\n                            if (last && last.type === 'reasoning') last.active = false;\n                        }\n                        else if (data.type === 'tool_use') {\n                            streamItems.push({ type: 'tool_call', name: data.tool_name, input: data.parameters });\n                        }\n                        else if (data.type === 'tool_result') {\n                            streamItems.push({ type: 'tool_output', output: data.output, full_path: data.full_output_path });\n                        }\n                        else if (data.type === 'step_start') {\n                            const loadingEl = document.getElementById(loadingId);\n                            if (loadingEl) loadingEl.innerHTML = `<div class=\"message-content\"><div class=\"thinking-block\">${data.message || 'Thinking'}<span class=\"thinking-loading\"></span></div></div>`;\n                        }\n                        else if (data.type === 'step_finish') {\n                            if (messageDiv) {\n                                const tokens = data.tokens || {};\n                                const statsHtml = `<div class=\"mt-2 small text-muted border-top border-secondary pt-1\" style=\"font-size: 0.65rem;\">\n                                    <i class=\"bi bi-lightning-charge\"></i> ${tokens.total || 0} tokens \n                                    ${data.cost ? `| <i class=\"bi bi-currency-dollar\"></i> ${data.cost.toFixed(4)}` : ''}\n                                    ${tokens.reasoning ? `| <i class=\"bi bi-brain\"></i> ${tokens.reasoning}` : ''}\n                                </div>`;\n                                const content = messageDiv.querySelector('.message-content');\n                                if (content && !content.querySelector('.message-stats')) {\n                                    const statsDiv = document.createElement('div');\n                                    statsDiv.className = 'message-stats';\n                                    statsDiv.innerHTML = statsHtml;\n                                    content.appendChild(statsDiv);\n                                }\n                            }\n                        }\n                        else if (data.type === 'error') fullText += `\\n\\n[Error: ${data.content}]`;\n                        else if (data.type === 'model_switch') { updateActiveModelUI(data.new_model); showToast(`Switching to ${data.new_model}...`); }\n\n                        if (!messageDiv && (fullText.trim() || streamItems.length || data.type === 'init' || data.type === 'step_start')) { \n                            if (data.type === 'init' || data.type === 'step_start') {\n                                if (data.type === 'init') removeLoading(loadingId);\n                            } else {\n                                messageDiv = createStreamingMessage('bot', window.TOTAL_MESSAGES++); \n                                removeLoading(loadingId); \n                            }\n                        }\n                        if (messageDiv) updateStreamingMessage(messageDiv, fullText, streamItems);\n                    } catch (e) {}\n                }\n            }\n            if (messageDiv) {\n                updateStreamingMessage(messageDiv, fullText, streamItems, true);\n                updateGitStatus(); // Refresh Git status after bot responds\n            } else {\n                removeLoading(loadingId);\n                if (!fullText.trim() && streamItems.length === 0) {\n                    appendMessage('bot', '[System Error] The agent exited without responding. Check backend logs or try again.');\n                }\n            }\n        } catch (e) { console.error('processStream error:', e); }\n    }\n\n    function createMessageDiv(sender, text, info, file, index) {\n        const div = document.createElement('div'); div.className = `message ${sender}`;\n        if (index !== null) div.dataset.index = index;\n        let parsedText = text;\n        if (sender === 'bot') {\n            // First parse markdown, then transform [Thinking] blocks in the HTML\n            parsedText = (typeof marked !== 'undefined') ? marked.parse(text) : text;\n            // Legacy/History: transform [Thinking] blocks into collapsible details\n            parsedText = parsedText.replace(/\\[Thinking\\]([\\s\\S]*?)\\[\\/Thinking\\]/g, (m, c) => `\n                <details class=\"reasoning-details mb-2\">\n                    <summary class=\"small text-muted cursor-pointer d-flex align-items-center gap-2\">\n                        <i class=\"bi bi-brain\"></i> Thinking <i class=\"bi bi-check2 text-success\"></i>\n                    </summary>\n                    <div class=\"thinking-block mt-2\">\n                        ${c.trim()}\n                    </div>\n                </details>`);\n        }\n        const content = document.createElement('div'); content.className = 'message-content';\n        content.innerHTML = parsedText;\n        div.appendChild(content);\n        \n        // Add a placeholder for tool logs in history if they exist in metadata (future)\n        const logsDiv = document.createElement('div');\n        logsDiv.className = 'tool-logs mt-2 d-none';\n        div.appendChild(logsDiv);\n\n        const actions = document.createElement('div'); actions.className = 'message-actions';\n        const copyBtn = document.createElement('button'); copyBtn.className = 'copy-btn'; copyBtn.innerHTML = '<i class=\"bi bi-clipboard\"></i>';\n        copyBtn.onclick = () => {\n            if (navigator.clipboard) {\n                navigator.clipboard.writeText(text).then(() => showToast('Copied!'));\n            } else {\n                const ta = document.createElement('textarea');\n                ta.value = text; document.body.appendChild(ta); ta.select();\n                document.execCommand('copy'); document.body.removeChild(ta);\n                showToast('Copied!');\n            }\n        };\n        actions.appendChild(copyBtn);\n        if (index !== null) {\n            const forkBtn = document.createElement('button'); forkBtn.className = 'clone-btn'; forkBtn.innerHTML = '<i class=\"bi bi-pencil-square\"></i>';\n            forkBtn.onclick = () => { \n                if (sender === 'user') { messageInput.value = text; messageInput.focus(); handleClone(currentActiveUUID, parseInt(index) - 1, false); } \n                else handleClone(currentActiveUUID, parseInt(index)); \n            };\n            actions.appendChild(forkBtn);\n        }\n        div.prepend(actions); return div;\n    }\n\n    function createStreamingMessage(sender, index) {\n        const div = document.createElement('div'); div.className = `message ${sender} streaming`; div.dataset.index = index;\n        div.innerHTML = '<div class=\"message-content\"></div><div class=\"tool-logs mt-2 d-none\"></div>';\n        chatContainer.appendChild(div); chatContainer.scrollTop = chatContainer.scrollHeight; return div;\n    }\n\n    window.sendQuickCommand = (cmd) => {\n        if (!messageInput || !chatForm) return;\n        messageInput.value = cmd;\n        chatForm.dispatchEvent(new Event('submit'));\n    };\n\n    function updateStreamingMessage(div, text, items, isFinal = false) {\n        const content = div.querySelector('.message-content');\n        content.innerHTML = (typeof marked !== 'undefined') ? marked.parse(text) : text;\n        \n        const logsDiv = div.querySelector('.tool-logs');\n        if (items.length) {\n            logsDiv.classList.remove('d-none');\n            logsDiv.innerHTML = items.map(item => {\n                if (item.type === 'reasoning') {\n                    return `\n                        <details class=\"reasoning-details mb-2\" ${item.active ? 'open' : ''}>\n                            <summary class=\"small text-muted cursor-pointer d-flex align-items-center gap-2\">\n                                <i class=\"bi bi-brain\"></i> Thinking\n                                ${item.active ? '<span class=\"thinking-loading\"></span>' : '<i class=\"bi bi-check2 text-success\"></i>'}\n                            </summary>\n                            <div class=\"thinking-block mt-2\">\n                                ${(typeof marked !== 'undefined') ? marked.parse(item.content) : item.content}\n                            </div>\n                        </details>`;\n                } else if (item.type === 'tool_call') {\n                    return `<div class=\"small text-info border-start border-info ps-2 mb-1\"><strong>Tool Call:</strong> ${item.name}</div>`;\n                } else if (item.type === 'tool_output') {\n                    const isRead = item.name === 'read' || item.name === 'read_file';\n                    const output = item.output || '';\n                    \n                    // Specialized Git Branch UI\n                    let gitActionsHtml = '';\n                    if (item.name === 'bash' || item.name === 'git') {\n                        if (output.includes('*') && (output.includes('main') || output.includes('master') || output.includes('branch'))) {\n                            const branches = output.split('\\n').map(b => b.trim().replace('* ', ''));\n                            gitActionsHtml = `<div class=\"mt-2 d-flex flex-wrap gap-1\">\n                                ${branches.filter(b => b && b.length < 50).map(b => `<button class=\"btn btn-outline-info btn-xs py-0 px-2\" style=\"font-size: 0.6rem;\" onclick=\"sendQuickCommand('git checkout ${b}')\"><i class=\"bi bi-git\"></i> ${b}</button>`).join('')}\n                            </div>`;\n                        }\n                    }\n\n                    return `\n                        <div class=\"small text-success border-start border-success ps-2 mb-2 tool-output-container\">\n                            <div class=\"d-flex justify-content-between align-items-center mb-1\">\n                                <strong>Result${item.name ? ' (' + item.name + ')' : ''}:</strong>\n                                <div class=\"d-flex gap-2\">\n                                    <button class=\"btn btn-link p-0 text-success\" title=\"Copy Output\" onclick=\"copyToClipboard(\\`${output.replace(/`/g, '\\\\`').replace(/\\$/g, '\\\\$')}\\`)\"><i class=\"bi bi-clipboard\" style=\"font-size: 0.7rem;\"></i></button>\n                                </div>\n                            </div>\n                            <pre class=\"m-0 mt-1 tool-output-pre\" style=\"font-size: 0.7rem; max-height: 150px; overflow: auto;\">${isRead ? '<code>' : ''}${output.substring(0, 2000)}${isRead ? '</code>' : ''}</pre>\n                            ${gitActionsHtml}\n                            ${item.full_path ? `<a href=\"${item.full_path}\" target=\"_blank\" class=\"small text-success d-inline-block mt-1\">Download Full Output</a>` : ''}\n                        </div>`;\n                }\n                return '';\n            }).join('');\n            \n            if (isFinal) {\n                logsDiv.querySelectorAll('pre code').forEach(b => typeof hljs !== 'undefined' && hljs.highlightElement(b));\n            }\n        }\n\n        if (isFinal) {\n            div.classList.remove('streaming');\n            div.querySelectorAll('pre code').forEach(b => typeof hljs !== 'undefined' && hljs.highlightElement(b));\n            \n            const stats = div.querySelector('.message-stats');\n            if (stats) content.appendChild(stats);\n\n            const actions = div.querySelector('.message-actions') || document.createElement('div');\n            actions.className = 'message-actions'; actions.innerHTML = '';\n            const copyBtn = document.createElement('button'); copyBtn.className = 'copy-btn'; copyBtn.innerHTML = '<i class=\"bi bi-clipboard\"></i>';\n            copyBtn.onclick = () => navigator.clipboard.writeText(text).then(() => showToast('Copied!'));\n            actions.appendChild(copyBtn);\n            const forkBtn = document.createElement('button'); forkBtn.className = 'clone-btn'; forkBtn.innerHTML = '<i class=\"bi bi-pencil-square\"></i>';\n            forkBtn.onclick = () => handleClone(currentActiveUUID, parseInt(div.dataset.index));\n            actions.appendChild(forkBtn);\n            if (!div.querySelector('.message-actions')) div.prepend(actions);\n        }\n        chatContainer.scrollTop = chatContainer.scrollHeight;\n    }\n\n    window.copyToClipboard = (text) => {\n        if (navigator.clipboard) {\n            navigator.clipboard.writeText(text).then(() => showToast('Copied!'));\n        } else {\n            const ta = document.createElement('textarea');\n            ta.value = text; document.body.appendChild(ta); ta.select();\n            document.execCommand('copy'); document.body.removeChild(ta);\n            showToast('Copied!');\n        }\n    };\n\n    function createQuestionCard(data) {\n        const card = document.createElement('div'); card.className = 'question-card';\n        const qText = document.createElement('div'); qText.className = 'question-text'; qText.innerText = data.question; card.appendChild(qText);\n        const optContainer = document.createElement('div'); optContainer.className = 'options-container';\n        const dismiss = () => { card.classList.add('removing'); setTimeout(() => card.remove(), 200); };\n        if (!data.options || data.options.length === 0) {\n            const input = document.createElement('input'); input.type = 'text'; input.className = 'form-control bg-dark text-light mb-2'; input.placeholder = 'Type answer...'; card.appendChild(input);\n            const btn = document.createElement('button'); btn.className = 'btn btn-primary btn-sm w-100'; btn.innerText = 'Submit';\n            btn.onclick = () => { if (input.value.trim()) { messageInput.value = input.value.trim(); if (chatForm) chatForm.dispatchEvent(new Event('submit')); dismiss(); } };\n            card.appendChild(input); card.appendChild(btn);\n        } else {\n            const selected = new Set();\n            data.options.forEach(opt => {\n                const btn = document.createElement('button'); btn.className = 'option-btn'; btn.innerText = opt;\n                btn.onclick = () => {\n                    if (data.allow_multiple) { if (selected.has(opt)) { selected.delete(opt); btn.classList.remove('active'); } else { selected.add(opt); btn.classList.add('active'); } }\n                    else { messageInput.value = opt; if (chatForm) chatForm.dispatchEvent(new Event('submit')); dismiss(); }\n                };\n                optContainer.appendChild(btn);\n            });\n            card.appendChild(optContainer);\n            if (data.allow_multiple) {\n                const btn = document.createElement('button'); btn.className = 'btn btn-primary btn-sm mt-2 w-100'; btn.innerText = 'Submit';\n                btn.onclick = () => { if (selected.size) { messageInput.value = Array.from(selected).join(', '); if (chatForm) chatForm.dispatchEvent(new Event('submit')); dismiss(); } };\n                card.appendChild(btn);\n            }\n        }\n        return card;\n    }\n\n    function appendMessage(sender, text, info, file, index) { const div = createMessageDiv(sender, text, info, file, index); if (div) { chatContainer.appendChild(div); chatContainer.scrollTop = chatContainer.scrollHeight; } }\n    function appendLoading() { \n        const div = document.createElement('div'); \n        div.className = 'message bot loading'; \n        const id = 'loading-' + Date.now(); \n        div.id = id; \n        div.innerHTML = '<div class=\"message-content\"><div class=\"thinking-block\">Thinking<span class=\"thinking-loading\"></span></div></div>'; \n        chatContainer.appendChild(div); \n        chatContainer.scrollTop = chatContainer.scrollHeight; \n        return id; \n    }\n    function removeLoading(id) { const el = document.getElementById(id); if (el) el.remove(); }\n\n    async function handleClone(uuid, messageIndex, showAlert = true) {\n        try {\n            const res = await fetch(`/sessions/${uuid}/clone`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message_index: messageIndex }) });\n            const data = await res.json();\n            if (data.success) { if (showAlert) showToast('Conversation forked!'); if (data.new_uuid === \"pending\") { chatContainer.innerHTML = ''; loadSessions(); } else switchSession(data.new_uuid); }\n        } catch (e) { console.error('handleClone error:', e); }\n    }\n\n    async function handleReset() { if (confirm('Reset chat?')) { const res = await fetch('/reset', { method: 'POST' }); const data = await res.json(); chatContainer.innerHTML = `<div class=\"text-center text-muted mt-5\">${data.response}</div>`; currentActiveUUID = null; loadSessions(); } }\n    if (resetBtn) resetBtn.onclick = handleReset;\n    if (resetBtnMobile) resetBtnMobile.onclick = handleReset;\n\n    async function handleExport() {\n        if (!currentActiveUUID) return;\n        try {\n            const res = await fetch(`/sessions/${currentActiveUUID}/messages`);\n            const data = await res.json();\n            const messages = data.messages || [];\n            let md = \"# Export\\n\\n\"; messages.forEach(m => md += `## ${m.role}\\n${m.content}\\n\\n`);\n            const b = new Blob([md], { type: 'text/markdown' }); const u = URL.createObjectURL(b);\n            const a = document.createElement('a'); a.href = u; a.download = `chat_${currentActiveUUID}.md`; a.click();\n        } catch (e) {}\n    }\n    if (exportBtn) exportBtn.onclick = handleExport;\n    if (exportBtnMobile) exportBtnMobile.onclick = handleExport;\n\n    async function fetchForks(uuid) { try { const res = await fetch(`/sessions/${uuid}/forks`); currentForkMap = await res.json(); } catch (e) { currentForkMap = {}; } }\n\n    async function loadPatterns() { try { const res = await fetch('/patterns'); const data = await res.json(); allPatterns = data; renderPatterns(data); } catch (e) {} }\n    function renderPatterns(patterns) {\n        if (!patternsList) return;\n        patternsList.innerHTML = patterns.map(p => {\n            if (p.type === 'user') return `<div class=\"list-group-item bg-dark border-secondary d-flex justify-content-between align-items-center\"><div class=\"pattern-item cursor-pointer\" data-type=\"user\" data-name=\"${p.name}\"><h6 class=\"mb-0 text-info\">${p.name}</h6></div><button class=\"btn btn-sm btn-outline-warning edit-prompt-btn\" data-name=\"${p.name}\"><i class=\"bi bi-pencil\"></i></button></div>`;\n            return `<button type=\"button\" class=\"list-group-item list-group-item-action bg-dark text-light border-secondary pattern-item\" data-type=\"${p.type}\" data-name=\"${p.name}\"><h6 class=\"mb-0\">${p.name.replace('skill:', '')}</h6></button>`;\n        }).join('');\n        document.querySelectorAll('.pattern-item').forEach(item => { item.onclick = () => {\n            const {name, type} = item.dataset;\n            if (type === 'skill') messageInput.value = `Use skill '${name.replace('skill:', '')}' to ${messageInput.value}`;\n            else if (type === 'system') messageInput.value = `/p ${name} ${messageInput.value}`;\n            else fetch(`/prompts/${name}`).then(r => r.json()).then(d => { if (d.content) { messageInput.value = d.content; messageInput.dispatchEvent(new Event('input')); } });\n            bootstrap.Modal.getInstance(patternsModalEl).hide(); messageInput.focus();\n        }; });\n        document.querySelectorAll('.edit-prompt-btn').forEach(btn => { btn.onclick = async (e) => { e.stopPropagation(); const res = await fetch(`/prompts/${btn.dataset.name}`); const d = await res.json(); if (d.content) { document.getElementById('edit-prompt-filename').value = btn.dataset.name; document.getElementById('edit-prompt-content').value = d.content; editPromptModalEl.dataset.mode = 'edit'; new bootstrap.Modal(editPromptModalEl).show(); } }; });\n    }\n\n    if (btnSavePrompt) {\n        btnSavePrompt.onclick = async () => {\n            const name = document.getElementById('edit-prompt-filename').value.trim(), content = document.getElementById('edit-prompt-content').value, mode = editPromptModalEl.dataset.mode || 'create';\n            const fd = new FormData(); fd.append('content', content); if (mode === 'create') fd.append('filename', name);\n            const res = await fetch(mode === 'create' ? '/prompts' : `/prompts/${name}`, { method: mode === 'create' ? 'POST' : 'PUT', body: fd });\n            if (res.ok) { bootstrap.Modal.getInstance(editPromptModalEl).hide(); loadPatterns(); }\n        };\n    }\n\n    // --- Observer ---\n    const observer = new IntersectionObserver((entries) => { if (entries[0].isIntersecting && !isLoadingHistory && currentOffset > 0 && currentActiveUUID) loadMessages(currentActiveUUID, PAGE_LIMIT, currentOffset); }, { root: chatContainer, threshold: 0.1 });\n    if (!document.getElementById('scroll-sentinel')) { const s = document.createElement('div'); s.id = 'scroll-sentinel'; s.style.height = '10px'; chatContainer.prepend(s); }\n    observer.observe(document.getElementById('scroll-sentinel'));\n\n    // --- Share ---\n    const shareModalEl = document.getElementById('shareModal');\n    const btnConfirmShare = document.getElementById('btn-confirm-share');\n    const shareUsernameInput = document.getElementById('share-username-input');\n    const shareStatus = document.getElementById('share-status');\n    \n    if (btnConfirmShare) { btnConfirmShare.onclick = async () => {\n        const u = shareUsernameInput.value.trim(); if (!u || !currentActiveUUID) return;\n        const res = await fetch(`/sessions/${currentActiveUUID}/share`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: u }) });\n        if (res.ok) { shareStatus.textContent = 'Shared!'; setTimeout(() => bootstrap.Modal.getInstance(shareModalEl).hide(), 1000); }\n    }; }\n\n    // --- Initialization ---\n    loadWorkspaces(); loadSessions(); loadPatterns(); fetchUniqueTags();\n    loadDynamicModels(); loadDynamicAgents();\n    if (currentActiveUUID) { \n        loadSessionWorkspace(currentActiveUUID); \n        if (window.INITIAL_MESSAGES && window.INITIAL_MESSAGES.length > 0) {\n            // Render server-provided initial messages into the DOM\n            if (chatWelcome) chatWelcome.classList.add('d-none');\n            chatContainer.innerHTML = '<div id=\"scroll-sentinel\" style=\"height: 10px; width: 100%;\"></div>';\n            const sentinel = document.getElementById('scroll-sentinel');\n            if (sentinel) observer.observe(sentinel);\n            window.INITIAL_MESSAGES.forEach((msg, idx) => {\n                const index = (msg.raw_index !== undefined) ? msg.raw_index : idx;\n                // Check if message has embedded question data\n                if (msg.question) {\n                    const card = createQuestionCard(msg.question);\n                    chatContainer.appendChild(card);\n                } else {\n                    const div = createMessageDiv(msg.role, msg.content, null, null, index);\n                    if (div) chatContainer.appendChild(div);\n                }\n            });\n            currentOffset = window.INITIAL_MESSAGES.length;\n            chatContainer.scrollTop = chatContainer.scrollHeight;\n            fetchForks(currentActiveUUID);\n        } else {\n            loadMessages(currentActiveUUID); \n        }\n    }\n\n    if (window.USER_SETTINGS) {\n        updateDriveModeVisibility();\n        updatePlanModeVisibility();\n    }\n\n    if (planModeBtn) planModeBtn.onclick = () => { planModeActive = !planModeActive; planModeBtn.classList.toggle('btn-warning', planModeActive); planModeBtn.classList.toggle('btn-outline-warning', !planModeActive); messageInput.placeholder = planModeActive ? \"Plan Mode...\" : \"Message...\"; };\n\n    messageInput.oninput = () => { messageInput.style.height = 'auto'; messageInput.style.height = messageInput.scrollHeight + 'px'; };\n    messageInput.addEventListener('keydown', (e) => {\n        if (e.key === 'Enter' && !e.shiftKey) {\n            e.preventDefault();\n            if (chatForm) chatForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));\n        }\n    });\n    \n    // Swipe\n    let ts = 0; document.addEventListener('touchstart', e => ts = e.touches[0].clientX, { passive: true });\n    document.addEventListener('touchend', e => { const dx = e.changedTouches[0].clientX - ts; if (Math.abs(dx) > 100) { if (dx > 0 && ts < 50) bootstrap.Offcanvas.getOrCreateInstance(historySidebar).show(); else if (dx < 0 && ts > window.innerWidth - 50) bootstrap.Offcanvas.getOrCreateInstance(document.getElementById('actionsSidebar')).show(); } }, { passive: true });\n});\n",
        "encoding": "text"
    },
    "style.css": {
        "content": "/* Lite Mode optimizations */\nbody.lite-mode {\n    --box-shadow-level: none;\n    --transition-speed: 0s;\n}\nbody.lite-mode * {\n    box-shadow: var(--box-shadow-level) !important;\n    text-shadow: none !important;\n    transition: var(--transition-speed) !important;\n}\nbody.lite-mode .pulse-animation {\n    animation: none !important;\n}\nbody.lite-mode .thinking-loading::after {\n    animation-duration: 3s; /* Slower animation for lower CPU usage */\n}\nbody.lite-mode .spinner-border {\n    animation-duration: 2s;\n}\n\n/* Default Variables */\n:root {\n    --bg-color: #121212;\n    --chat-bg: #0b0b0b;\n    --sidebar-bg: #1e1e1e;\n    --message-user-bg: #3c6e71; /* Teal muted */\n    --message-bot-bg: #2b2d42; /* Dark blue/grey */\n    --text-color: #e0e0e0;\n    --input-bg: #2d2d2d;\n    --border-color: #444;\n    --box-shadow-level: 0 1px 2px rgba(0,0,0,0.2);\n    --transition-speed: 0.2s;\n}\n\nbody {\n    background-color: var(--bg-color) !important;\n    color: var(--text-color) !important;\n    font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;\n    touch-action: pan-y;\n}\n\n/* Header Styling */\nheader {\n    background-color: var(--sidebar-bg) !important;\n    box-shadow: 0 2px 10px rgba(0,0,0,0.3);\n    z-index: 1000;\n}\n\n/* Chat Container */\n#chat-container {\n    background-color: var(--chat-bg);\n    padding-bottom: 2rem;\n    touch-action: pan-y;\n}\n\n/* Messages */\n.message {\n    max-width: 85%;\n    margin-bottom: 1.2rem;\n    padding: 1rem 1.2rem;\n    border-radius: 1.2rem;\n    position: relative;\n    word-wrap: break-word;\n    box-shadow: var(--box-shadow-level);\n    font-size: 0.95rem;\n    line-height: 1.5;\n}\n\n.message.user {\n    background-color: var(--message-user-bg);\n    color: #ffffff;\n    align-self: flex-end;\n    margin-left: auto;\n    border-bottom-right-radius: 0.2rem;\n}\n\n.message.bot {\n    background-color: #2d2d2d; /* Dark Grey */\n    color: #ffffff; /* Brighter white */\n    align-self: flex-start;\n    margin-right: auto;\n    border-bottom-left-radius: 0.2rem;\n}\n\n.text-muted {\n    color: #b0b0b0 !important; /* Brighter muted text */\n}\n\n/* Code Blocks */\n.message pre {\n    background-color: #1a1a1a !important;\n    padding: 1rem;\n    border-radius: 0.5rem;\n    overflow-x: auto;\n    margin-top: 0.5rem;\n    border: 1px solid #333;\n}\n\n/* Thinking & Reasoning Blocks */\n.reasoning-details {\n    background-color: rgba(0, 0, 0, 0.15);\n    border: 1px solid rgba(255, 255, 255, 0.05);\n    border-radius: 8px;\n    padding: 2px 8px;\n    transition: all 0.2s;\n}\n.reasoning-details[open] {\n    background-color: rgba(0, 0, 0, 0.25);\n    padding-bottom: 8px;\n}\n.reasoning-details summary {\n    list-style: none;\n    outline: none;\n    user-select: none;\n}\n.reasoning-details summary::-webkit-details-marker {\n    display: none;\n}\n.reasoning-details summary:hover {\n    color: #fff !important;\n}\n\n.thinking-block {\n    font-style: normal;\n    color: #aaa;\n    background-color: transparent;\n    border-left: 2px solid #444;\n    padding: 0.2rem 0.8rem;\n    margin-bottom: 0;\n    font-size: 0.85rem;\n    border-radius: 0;\n}\n.thinking-block::before {\n    display: none;\n}\n\n.thinking-loading {\n    display: inline-block;\n    margin-left: 5px;\n}\n.thinking-loading::after {\n    content: \"...\";\n    animation: thinking-dots 1.5s steps(4, end) infinite;\n}\n@keyframes thinking-dots {\n    0%, 20% { content: \"\"; }\n    40% { content: \".\"; }\n    60% { content: \"..\"; }\n    80%, 100% { content: \"...\"; }\n}\n\n/* Footer / Input Area */\nfooter {\n    background-color: var(--sidebar-bg) !important;\n    box-shadow: 0 -2px 10px rgba(0,0,0,0.2);\n}\n\n/* Custom Scrollbar */\n::-webkit-scrollbar {\n    width: 6px;\n}\n\n::-webkit-scrollbar-track {\n    background: var(--chat-bg);\n}\n\n::-webkit-scrollbar-thumb {\n    background: #555;\n    border-radius: 3px;\n}\n\n::-webkit-scrollbar-thumb:hover {\n    background: #777;\n}\n\n/* Input Field Styling */\ntextarea#message-input {\n    resize: none;\n    max-height: 200px;\n    min-height: 50px; /* Enforce a minimum height */\n    background-color: var(--input-bg);\n    color: white;\n    border: 1px solid var(--border-color);\n    border-radius: 1.5rem !important; /* Pill shape */\n    padding: 0.8rem 1.2rem;\n    font-size: 1rem;\n}\n\ntextarea#message-input:focus {\n    background-color: #333;\n    border-color: #666;\n    box-shadow: none;\n    color: white;\n}\n\n/* Buttons in Input Area */\n.btn-circle {\n    width: 40px;\n    height: 40px;\n    padding: 0;\n    border-radius: 50%;\n    display: flex;\n    align-items: center;\n    justify-content: center;\n}\n\n/* Dropdown Menu */\n.dropdown-menu {\n    background-color: var(--input-bg);\n    border-color: var(--border-color);\n}\n.dropdown-item {\n    color: var(--text-color);\n}\n.dropdown-item:hover {\n    background-color: #444;\n    color: white;\n}\n\n/* Session List Items */\n#sessions-list .list-group-item {\n    cursor: pointer;\n    transition: background-color 0.2s;\n    border-color: #333;\n    padding: 0.75rem 1.25rem;\n}\n\n#sessions-list .list-group-item:hover {\n    background-color: #333 !important;\n}\n\n#sessions-list .list-group-item.active-session {\n    background-color: #2b2d42 !important;\n    border-left: 4px solid #3c6e71;\n}\n\n#sessions-list .session-title {\n    font-weight: 500;\n    font-size: 0.9rem;\n    display: block;\n}\n\n#sessions-list .session-time {\n    font-size: 0.75rem;\n    color: #888;\n}\n/* Mobile Safe Area Fixes */\nhtml, body { \n    height: 100%; \n    margin: 0; \n    padding: 0; \n    overflow: hidden; \n    overscroll-behavior: none; \n    background-color: var(--chat-bg);\n}\n.container-fluid { \n    height: 100vh; \n    height: 100dvh; \n    display: flex; \n    flex-direction: column; \n    overflow: hidden; \n}\n\nheader {\n    flex-shrink: 0;\n    z-index: 100;\n}\n\n#chat-container { \n    flex: 1;\n    overflow-y: auto;\n    background-color: var(--chat-bg);\n    padding-bottom: 1rem;\n    -webkit-overflow-scrolling: touch;\n}\n\nfooter {\n    flex-shrink: 0;\n    width: 100%;\n    background-color: #000;\n    border-top: 1px solid var(--border-color);\n    z-index: 100;\n    padding: 0.5rem 0.75rem !important;\n}\n\n@media (max-width: 768px) {\n    #chat-container {\n        padding-bottom: 6rem !important; /* Space for the fixed footer */\n    }\n    footer {\n        position: fixed;\n        bottom: 0;\n        left: 0;\n        width: 100%;\n        padding: 0.25rem 0.5rem !important;\n        padding-bottom: calc(0.25rem + env(safe-area-inset-bottom)) !important;\n    }\n    footer .text-center {\n        display: none;\n    }\n    textarea#message-input {\n        padding: 0.4rem 0.8rem;\n        min-height: 36px;\n        font-size: 0.9rem;\n        border-radius: 1rem !important;\n    }\n}\n\n@media (max-width: 768px) {\n\n    #chat-container {\n\n        padding-bottom: 6rem !important; /* Reduced since footer is smaller */\n\n    }\n\n    footer {\n\n        position: fixed;\n\n        bottom: 0;\n\n        left: 0;\n\n        width: 100%;\n\n        padding: 0.25rem 0.5rem !important;\n\n        padding-bottom: calc(0.25rem + env(safe-area-inset-bottom)) !important;\n\n    }\n\n    footer .text-center {\n\n        display: none; /* Hide model label on mobile to save space */\n\n    }\n\n    textarea#message-input {\n\n        padding: 0.4rem 0.8rem;\n\n        min-height: 36px;\n\n        font-size: 0.9rem;\n\n        border-radius: 1rem !important;\n\n    }\n\n    #send-btn, #stop-btn {\n\n        width: 36px !important;\n\n        height: 36px !important;\n\n        padding: 0 !important;\n\n        display: flex;\n\n        align-items: center;\n\n        justify-content: center;\n\n    }\n\n}\n\n/* Action Buttons in Messages */\n.message { \n    position: relative; \n    padding-right: 40px !important; \n    display: flex;\n    flex-direction: column;\n}\n.message-actions {\n    position: sticky;\n    top: 0;\n    align-self: flex-end;\n    margin-top: -5px;\n    margin-right: -30px;\n    display: flex;\n    gap: 4px;\n    z-index: 10;\n}\n.copy-btn, .clone-btn {\n    background: rgba(0,0,0,0.2); \n    border: 1px solid rgba(255,255,255,0.1);\n    color: rgba(255, 255, 255, 0.5); \n    cursor: pointer;\n    padding: 4px; \n    border-radius: 4px;\n    transition: all 0.2s; \n    font-size: 1rem;\n    display: flex; \n    align-items: center; \n    justify-content: center; \n}\n.copy-btn:hover, .clone-btn:hover { \n    color: #fff; \n    background: rgba(255, 255, 255, 0.2); \n}\n.clone-btn {\n    font-size: 0.9rem;\n}\n\n/* Tree View Styling */\n.tree-view {\n    display: flex;\n    flex-direction: column;\n    gap: 1rem;\n    padding: 1rem;\n}\n\n.tree-node-wrapper {\n    position: relative;\n}\n\n.tree-node {\n    position: relative;\n    z-index: 2;\n    box-shadow: 0 4px 6px rgba(0,0,0,0.3);\n}\n\n.tree-node:hover {\n    transform: translateY(-2px);\n}\n\n.tree-children {\n    position: relative;\n}\n\n.tree-children::before {\n    content: \"\";\n    position: absolute;\n    left: -1rem;\n    top: 0;\n    bottom: 1.5rem;\n    width: 2px;\n    background: #444;\n}\n\n.cursor-pointer {\n    cursor: pointer;\n}\n\n.tree-node-active {\n    border-left: 3px solid var(--bs-primary);\n}\n\n/* Fork Navigation in Messages */\n.fork-nav-controls {\n    border-color: rgba(255,255,255,0.2) !important;\n}\n\n.fork-nav-controls button:hover {\n    color: #fff !important;\n}\n\n@media (max-width: 768px) {\n    .message {\n        max-width: 90%;\n    }\n    .tree-node {\n        max-width: 100% !important;\n    }\n    .message-actions {\n        margin-right: -20px;\n    }\n}\n\n/* Image Thumbnails */\n.message-thumbnail {\n    max-width: 150px;\n    max-height: 150px;\n    border-radius: 8px;\n    cursor: pointer;\n    display: block;\n    transition: transform 0.2s;\n}\n.message-thumbnail:hover {\n    transform: scale(1.02);\n}\n\n/* Sidebar Sections */\n.sidebar-section-header {\n    letter-spacing: 0.05rem;\n    z-index: 10;\n    position: sticky;\n    top: 0;\n}\n\n.workspace-group-header {\n    background-color: rgba(0, 0, 0, 0.4) !important;\n    color: #6c757d !important;\n    font-size: 0.65rem !important;\n    text-transform: uppercase;\n    letter-spacing: 0.5px;\n    border-top: 1px solid rgba(255, 255, 255, 0.05);\n    border-bottom: 1px solid rgba(255, 255, 255, 0.05);\n}\n\n.workspace-group-header i {\n    font-size: 0.8rem;\n}\n\n.workspace-group.collapsed .workspace-items {\n    display: none;\n}\n\n.workspace-group-header:hover {\n    background-color: rgba(255, 255, 255, 0.05) !important;\n    color: #fff !important;\n}\n\n.workspace-group-header .badge {\n    opacity: 0.6;\n}\n\n/* Pinning UI */\n.pin-btn {\n    color: rgba(255, 255, 255, 0.3);\n    transition: all 0.2s;\n    padding: 0.25rem 0.5rem !important;\n}\n.pin-btn:hover {\n    color: rgba(255, 255, 255, 0.7);\n}\n.pin-btn.pinned {\n    color: #ffc107 !important; /* Gold */\n}\n.rename-session-btn {\n    color: rgba(255, 255, 255, 0.3);\n    transition: all 0.2s;\n    padding: 0.25rem 0.5rem !important;\n}\n.rename-session-btn:hover {\n    color: rgba(255, 255, 255, 0.7);\n}\n.delete-session-btn {\n    color: rgba(220, 53, 69, 0.5);\n    transition: all 0.2s;\n    padding: 0.25rem 0.5rem !important;\n}\n.delete-session-btn:hover {\n    color: rgba(220, 53, 69, 1);\n}\n#session-search:focus {\n    border-color: #3c6e71;\n    background-color: #252525 !important;\n}\n.input-group-text {\n    border-bottom: 2px solid #dc3545 !important;\n}\n\n/* Tags */\n.tag-badge {\n    cursor: pointer;\n    font-size: 0.7rem;\n    padding: 0.2rem 0.5rem;\n    border-radius: 10px;\n    background-color: #333;\n    color: #ccc;\n    border: 1px solid #444;\n    white-space: nowrap;\n    transition: all 0.2s;\n}\n\n.tag-badge:hover {\n    background-color: #444;\n    color: #fff;\n}\n\n.tag-badge.selected {\n    background-color: #0d6efd;\n    color: #fff;\n    border-color: #0a58ca;\n}\n\n.tag-badge.add-tag-btn {\n    border-style: dashed;\n    background: transparent;\n}\n\n.session-tags-list {\n    font-size: 0.65rem;\n    margin-top: 2px;\n}\n\n.session-tag-item {\n    color: #888;\n    background: #222;\n    padding: 0 4px;\n    border-radius: 4px;\n    margin-right: 4px;\n}\n\n/* Attachment Queue Styling */\n.attachment-item {\n    transition: all 0.2s;\n    animation: fadeIn 0.3s ease-in-out;\n}\n\n.attachment-item:hover {\n    background-color: rgba(255,255,255,0.1) !important;\n    border-color: rgba(255,255,255,0.2) !important;\n}\n\n#chat-container.drag-over {\n    background-color: rgba(13, 110, 253, 0.1);\n    border: 2px dashed #0d6efd;\n}\n\n.border-dashed {\n    border-style: dashed !important;\n}\n\n@keyframes fadeIn {\n    from { opacity: 0; transform: translateY(5px); }\n    to { opacity: 1; transform: translateY(0); }\n}\n\n\n/* Question Cards */\n.question-card {\n    background-color: #000;\n    border: 1px solid var(--message-user-bg);\n    border-left: 4px solid var(--message-user-bg);\n    border-radius: 0.5rem;\n    padding: 1rem;\n    margin-bottom: 1.2rem;\n    max-width: 85%;\n    align-self: flex-start;\n    margin-right: auto;\n    box-shadow: 0 4px 15px rgba(0,0,0,0.6);\n    animation: slideIn 0.3s ease-out;\n    font-family: 'Consolas', 'Monaco', 'Lucida Console', monospace;\n}\n\n@keyframes slideIn {\n    from { opacity: 0; transform: translateX(-20px); }\n    to { opacity: 1; transform: translateX(0); }\n}\n\n.question-card.removing {\n    animation: fadeOut 0.2s ease-in forwards;\n}\n\n@keyframes fadeOut {\n    from { opacity: 1; transform: scale(1); }\n    to { opacity: 0; transform: scale(0.95); }\n}\n\n.question-text {\n    font-weight: 600;\n    margin-bottom: 1rem;\n    color: var(--message-user-bg);\n    text-transform: uppercase;\n    font-size: 0.85rem;\n    letter-spacing: 1px;\n}\n\n.question-text::before {\n    content: \"> \";\n}\n\n.options-container {\n    display: flex;\n    flex-wrap: wrap;\n    gap: 0.5rem;\n}\n\n.option-btn {\n    background-color: #1a1a1a;\n    color: #0f0; /* Terminal Green */\n    border: 1px solid #333;\n    border-radius: 0.25rem;\n    padding: 0.4rem 0.8rem;\n    cursor: pointer;\n    transition: all 0.2s;\n    font-size: 0.85rem;\n    font-family: inherit;\n}\n\n.option-btn:hover {\n    background-color: #222;\n    border-color: #0f0;\n    box-shadow: 0 0 10px rgba(0, 255, 0, 0.2);\n}\n\n.option-btn.active {\n    background-color: #0f0;\n    color: #000;\n    border-color: #fff;\n    font-weight: bold;\n}\n\n.question-card .submit-btn {\n    margin-top: 1rem;\n    width: 100%;\n    border-radius: 0.25rem;\n    text-transform: uppercase;\n    font-weight: bold;\n    letter-spacing: 1px;\n}\n\n.question-card input[type=\"text\"] {\n    background-color: #111;\n    border: 1px solid #333;\n    color: #0f0;\n    font-family: inherit;\n    border-radius: 0.25rem;\n}\n\n.question-card input[type=\"text\"]:focus {\n    border-color: #0f0;\n    box-shadow: 0 0 5px rgba(0, 255, 0, 0.3);\n}\n\n@media (max-width: 768px) {\n    .question-card {\n        max-width: 95%;\n    }\n}\n\n#model-list-container {\n    max-height: 400px;\n    overflow-y: auto;\n    overflow-x: hidden;\n}\n\n#model-list-container::-webkit-scrollbar {\n    width: 4px;\n}\n\n#model-list-container::-webkit-scrollbar-thumb {\n    background: #444;\n    border-radius: 2px;\n}\n\n.message-stats {\n    opacity: 0.8;\n    transition: opacity 0.2s;\n}\n.message-stats:hover {\n    opacity: 1;\n}\n\n/* Drive Mode Pulse Animation */\n.pulse-animation {\n    animation: pulse-info 1.5s infinite;\n}\n\n@keyframes pulse-info {\n    0% {\n        box-shadow: 0 0 0 0 rgba(13, 202, 240, 0.7);\n    }\n    70% {\n        box-shadow: 0 0 0 10px rgba(13, 202, 240, 0);\n    }\n    100% {\n        box-shadow: 0 0 0 0 rgba(13, 202, 240, 0);\n    }\n}\n",
        "encoding": "text"
    },
    "sw.js": {
        "content": "const CACHE_NAME = 'opencode-agent-v6'; // Bump version for fresh install\n\nself.addEventListener('install', (event) => {\n  console.log('Service Worker v6 installing...');\n  event.waitUntil(\n    caches.open(CACHE_NAME).then((cache) => {\n      // Pre-cache only essential, non-dynamic assets\n      // (Root path '/' removed to avoid caching redirects)\n      return cache.addAll([\n        '/static/style.css',\n        '/static/script.js',\n        '/static/icon.svg',\n        '/static/icon-192.png',\n        '/static/icon-512.png',\n        '/static/maskable-icon-512.png',\n        '/manifest.json'\n      ]);\n    }).catch((error) => {\n      console.error('Service Worker install failed:', error);\n    })\n  );\n});\n\nself.addEventListener('activate', (event) => {\n  console.log('Service Worker v6 activating...');\n  event.waitUntil(\n    caches.keys().then((cacheNames) => {\n      return Promise.all(\n        cacheNames.filter((cacheName) => {\n          return cacheName !== CACHE_NAME;\n        }).map((cacheName) => {\n          console.log(`[SW] Deleting old cache: ${cacheName}`);\n          return caches.delete(cacheName);\n        })\n      );\n    })\n  );\n  event.waitUntil(self.clients.claim()); // Take control of un-controlled clients\n});\n\nself.addEventListener('fetch', (event) => {\n  console.log('[SW] Fetching:', event.request.url);\n\n  // Network-first strategy for all requests\n  event.respondWith(\n    fetch(event.request)\n      .then((networkResponse) => {\n        // If the network response is good, cache it and return it\n        if (networkResponse.ok && networkResponse.type === 'basic' && event.request.method === 'GET') {\n          const clonedResponse = networkResponse.clone();\n          caches.open(CACHE_NAME).then((cache) => {\n            // Only cache requests for paths that typically don't change often and are not main HTML docs\n            const urlWithoutQuery = event.request.url.split('?')[0].replace(self.location.origin, '');\n            if (urlWithoutQuery.startsWith('/static/') || urlWithoutQuery === '/manifest.json') {\n                 console.log(`[SW] Caching network response for: ${event.request.url}`);\n                cache.put(event.request, clonedResponse);\n            }\n          });\n        }\n        return networkResponse;\n      })\n      .catch((error) => {\n        console.warn(`[SW] Network request failed for: ${event.request.url}. Trying cache.`, error);\n        // Fallback to cache if network fails\n        return caches.match(event.request).then((cachedResponse) => {\n          if (cachedResponse) {\n            console.log(`[SW] Serving from cache: ${event.request.url}`);\n            return cachedResponse;\n          }\n          // If neither network nor cache has a response, return a generic offline page or error\n          console.error(`[SW] No cache match for offline: ${event.request.url}`);\n          // For navigation requests, can show an offline page\n          if (event.request.mode === 'navigate') {\n            return new Response('<h1>Offline</h1><p>You are offline and this page is not available.</p>', { headers: { 'Content-Type': 'text/html' } });\n          }\n          // For other requests, return a network error\n          return new Response(null, { status: 503, statusText: 'Service Unavailable (Offline)' });\n        });\n      })\n  );\n});\n",
        "encoding": "text"
    },
    "maskable-icon-512.png": {
        "content": "iVBORw0KGgoAAAANSUhEUgAAAgAAAAIACAMAAADDpiTIAAAABGdBTUEAALGPC/xhBQAAACBjSFJNAAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAC91BMVEUAAABsdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX0AAACKDVklAAAA+3RSTlMAAQsMJEt/wQhsBFdF+jHaKSEZE/4O6Y8RcVgC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",
        "encoding": "base64"
    },
    "icon-192.png": {
        "content": "iVBORw0KGgoAAAANSUhEUgAAAMAAAADACAMAAABlApw1AAAABGdBTUEAALGPC/xhBQAAACBjSFJNAAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAC7lBMVEUAAABsdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX1sdX0AAABzFpLTAAAA+HRSTlMAAAMPJy8XBgEHRKLG5O3QtmkVI57v+04CILvoUqvhOlP3oAUL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",
        "encoding": "base64"
    },
    "icon.svg": {
        "content": "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"512\" height=\"512\" fill=\"#6c757d\" viewBox=\"0 0 16 16\">\n  <g transform=\"translate(2.4, 2.4) scale(0.7)\">\n    <path d=\"M6 12.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 0 1h-3a.5.5 0 0 1-.5-.5M3 8.062C3 6.76 4.235 5.765 5.53 5.886a26.6 26.6 0 0 0 4.94 0C11.765 5.765 13 6.76 13 8.062v1.157a.93.93 0 0 1-.765.935c-.845.147-2.34.346-4.235.346s-3.39-.2-4.235-.346A.93.93 0 0 1 3 9.219zm4.542-.827a.25.25 0 0 0-.217.068l-.92.9a25 25 0 0 1-1.871-.183.25.25 0 0 0-.068.495c.55.076 1.232.149 2.02.193a.25.25 0 0 0 .189-.071l.754-.736.847 1.71a.25.25 0 0 0 .404.062l.932-.97a25 25 0 0 0 1.922-.188.25.25 0 0 0-.068-.495c-.538.074-1.207.145-1.98.189a.25.25 0 0 0-.166.076l-.754.785-.842-1.7a.25.25 0 0 0-.182-.135\"/>\n    <path d=\"M8.5 1.866a1 1 0 1 0-1 0V3h-2A4.5 4.5 0 0 0 1 7.5V8a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1v1a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-1a1 1 0 0 0 1-1V9a1 1 0 0 0-1-1v-.5A4.5 4.5 0 0 0 10.5 3h-2zM14 7.5V13a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V7.5A3.5 3.5 0 0 1 5.5 4h5A3.5 3.5 0 0 1 14 7.5\"/>\n  </g>\n</svg>",
        "encoding": "text"
    },
    "drive_mode.js": {
        "content": "/**\n * Manages the \"Drive Mode\" voice-only conversation loop.\n * Handles speech recognition (STT) and speech synthesis (TTS).\n */\nclass DriveModeManager {\n    constructor() {\n        this.isActive = false;\n        this.state = 'idle'; // idle, listening, processing, speaking\n        this.wakeLock = null;\n        \n        // Pre-load voices for Chrome/Android\n        if (typeof window !== 'undefined' && window.speechSynthesis) {\n            window.speechSynthesis.getVoices();\n            window.speechSynthesis.onvoiceschanged = () => {\n                window.speechSynthesis.getVoices();\n            };\n        }\n    }\n\n    /**\n     * Checks if the browser supports the necessary Web Speech APIs and Wake Lock API.\n     * @returns {boolean}\n     */\n    isSupported() {\n        const hasSTT = 'webkitSpeechRecognition' in window || 'speechRecognition' in window;\n        const hasTTS = 'speechSynthesis' in window;\n        return hasSTT && hasTTS;\n    }\n\n    /**\n     * Requests a screen wake lock to prevent the device from sleeping.\n     */\n    async requestWakeLock() {\n        if ('wakeLock' in navigator) {\n            try {\n                this.wakeLock = await navigator.wakeLock.request('screen');\n                console.log('Wake Lock acquired');\n            } catch (err) {\n                console.error(`${err.name}, ${err.message}`);\n            }\n        }\n    }\n\n    /**\n     * Releases the acquired wake lock.\n     */\n    async releaseWakeLock() {\n        if (this.wakeLock) {\n            await this.wakeLock.release();\n            this.wakeLock = null;\n            console.log('Wake Lock released');\n        }\n    }\n\n    /**\n     * Starts the Speech-to-Text (STT) recognition.\n     * @param {Function} onResult - Callback called with transcribed text.\n     * @param {Function} onError - Callback called on recognition error.\n     */\n    startListening(onResult, onError) {\n        const SpeechRecognition = window.webkitSpeechRecognition || window.SpeechRecognition;\n        if (!SpeechRecognition) {\n            if (onError) onError('Speech Recognition not supported');\n            return;\n        }\n\n        const recognition = new SpeechRecognition();\n        \n        // Using el-GR generally allows for better recognition of Greek + English\n        // mixed together than using en-US on an English device.\n        recognition.lang = 'el-GR'; \n        recognition.interimResults = false;\n        recognition.maxAlternatives = 1;\n        recognition.continuous = false; // We want automatic end-of-speech detection\n\n        recognition.onstart = () => {\n            this.state = 'listening';\n            console.log('STT: Started listening...');\n        };\n\n        recognition.onresult = (event) => {\n            const transcript = event.results[0][0].transcript;\n            console.log('STT Result:', transcript);\n            this.state = 'idle';\n            if (onResult) onResult(transcript);\n        };\n\n        recognition.onerror = (event) => {\n            console.error('STT Error:', event.error);\n            this.state = 'idle';\n            if (onError) onError(event.error);\n        };\n\n        recognition.onend = () => {\n            console.log('STT: Stopped listening.');\n            if (this.state === 'listening') {\n                this.state = 'idle';\n            }\n        };\n\n        try {\n            recognition.start();\n            this.recognition = recognition;\n        } catch (e) {\n            console.error('STT Start Error:', e);\n            this.state = 'idle';\n            if (onError) onError(e.message);\n        }\n    }\n\n    /**\n     * Stops current recognition.\n     */\n    stopListening() {\n        if (this.recognition) {\n            try {\n                this.recognition.stop();\n            } catch (e) {\n                // Ignore if already stopped\n            }\n            this.recognition = null;\n        }\n    }\n\n    /**\n     * Reads text aloud using Speech Synthesis (TTS).\n     * @param {string} text - The text to speak.\n     * @param {Function} onEnd - Callback called when speaking finishes.\n     */\n    speak(text, onEnd) {\n        if (!window.speechSynthesis) {\n            if (onEnd) onEnd();\n            return;\n        }\n\n        // Cancel any ongoing speech\n        window.speechSynthesis.cancel();\n\n        const utterance = new SpeechSynthesisUtterance(text);\n        \n        // Smarter Voice Selection\n        const voices = window.speechSynthesis.getVoices();\n        if (voices.length > 0) {\n            // Detect if text is mostly Greek or English (simplified)\n            const isGreek = /[\\u0370-\\u03FF]/.test(text);\n            const targetLang = isGreek ? 'el' : 'en';\n            \n            // Find a voice that matches the language\n            const voice = voices.find(v => v.lang.startsWith(targetLang)) || \n                          voices.find(v => v.lang.startsWith(document.documentElement.lang)) ||\n                          voices[0];\n            \n            if (voice) {\n                utterance.voice = voice;\n                utterance.lang = voice.lang;\n            }\n        } else {\n            utterance.lang = document.documentElement.lang || window.navigator.language || 'el-GR';\n        }\n        \n        utterance.onstart = () => {\n            this.state = 'speaking';\n            console.log('TTS: Started speaking...');\n        };\n\n        utterance.onend = () => {\n            this.state = 'idle';\n            console.log('TTS: Finished speaking.');\n            if (onEnd) onEnd();\n        };\n\n        utterance.onerror = (event) => {\n            console.error('TTS Error:', event.error);\n            this.state = 'idle';\n            if (onEnd) onEnd();\n        };\n\n        window.speechSynthesis.speak(utterance);\n    }\n\n    /**\n     * Stops current speaking.\n     */\n    stopSpeaking() {\n        if (window.speechSynthesis) {\n            window.speechSynthesis.cancel();\n        }\n    }\n}\n\nif (typeof module !== 'undefined' && module.exports) {\n    module.exports = DriveModeManager;\n}\n",
        "encoding": "text"
    },
    "favicon.ico": {
        "content": "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",
        "encoding": "base64"
    },
    "compression.js": {
        "content": "/**\n * Compresses an image file client-side.\n * @param {File} file - The original image file.\n * @returns {Promise<File>} - A promise that resolves to the compressed WebP File.\n */\nasync function compressImage(file) {\n    // Only compress images\n    if (!file.type.startsWith('image/')) {\n        return file;\n    }\n\n    return new Promise((resolve, reject) => {\n        const reader = new FileReader();\n        reader.onload = (e) => {\n            const img = new Image();\n            img.onload = () => {\n                const canvas = document.createElement('canvas');\n                let width = img.width;\n                let height = img.height;\n                const maxDim = 1536;\n\n                // Calculate new dimensions\n                if (width > maxDim || height > maxDim) {\n                    if (width > height) {\n                        height = Math.round((height * maxDim) / width);\n                        width = maxDim;\n                    } else {\n                        width = Math.round((width * maxDim) / height);\n                        height = maxDim;\n                    }\n                }\n\n                canvas.width = width;\n                canvas.height = height;\n                const ctx = canvas.getContext('2d');\n                \n                // Use better image scaling if supported\n                ctx.imageSmoothingEnabled = true;\n                ctx.imageSmoothingQuality = 'high';\n                \n                ctx.drawImage(img, 0, 0, width, height);\n\n                // Convert to WebP with 0.8 quality\n                canvas.toBlob((blob) => {\n                    if (blob) {\n                        // Create a new File object with .webp extension\n                        const newFileName = file.name.replace(/\\.[^/.]+$/, \"\") + \".webp\";\n                        const compressedFile = new File([blob], newFileName, {\n                            type: 'image/webp',\n                            lastModified: Date.now()\n                        });\n                        resolve(compressedFile);\n                    } else {\n                        // Fallback to original if compression fails\n                        resolve(file);\n                    }\n                }, 'image/webp', 0.8);\n            };\n            img.onerror = () => reject(new Error('Failed to load image for compression.'));\n            img.src = e.target.result;\n        };\n        reader.onerror = () => reject(new Error('Failed to read file for compression.'));\n        reader.readAsDataURL(file);\n    });\n}",
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
import datetime as dt_pkg
from typing import Optional, List, Dict, AsyncGenerator, Any

WORKSPACE_ROOT = WORKSPACE_ROOT

FALLBACK_MODELS = {
    "google/antigravity-gemini-3.1-pro": "google/antigravity-gemini-3-flash",
    "google/antigravity-gemini-3-flash": "google/gemini-2.5-flash",
    "google/antigravity-claude-sonnet-4-6": "google/antigravity-gemini-3.1-pro",
    "google/antigravity-claude-opus-4-6-thinking": "google/antigravity-gemini-3.1-pro",
    "google/gemini-3-flash-preview": "google/antigravity-gemini-3-flash",
    "google/gemini-2.5-pro": "google/gemini-2.5-flash",
    "google/gemini-1.5-pro": "google/gemini-1.5-flash",
}

CAPACITY_KEYWORDS = [
    "429",
    "capacity",
    "quota",
    "exhausted",
    "rate limit",
    "not found",
    "404",
]


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
    except:
        pass


def log_debug(msg):
    global_log(msg, level="DEBUG")


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
            while True:
                # Read in small chunks to avoid blocking and ensure low latency
                chunk = self.pipe.read(1)  # Byte by byte is safest for unbuffered
                if not chunk:
                    log_debug("Pipe EOF reached")
                    break
                self.loop.call_soon_threadsafe(self.queue.put_nowait, chunk)
        except Exception as e:
            log_debug(f"Error reading pipe: {e}")
        finally:
            self.loop.call_soon_threadsafe(self.queue.put_nowait, None)

    async def readline(self, timeout=None):
        # We now act as a stream reader for bytes
        line = b""
        while True:
            try:
                # Use a short timeout internally to allow checking for cancellation
                chunk = await asyncio.wait_for(self.queue.get(), timeout=0.1)
            except asyncio.TimeoutError:
                if (
                    timeout
                ):  # If user provided a global timeout, check if we exceeded it
                    # This is a bit simplified, but for our purposes 0.1s check is fine
                    continue
                continue  # Keep waiting for data

            if chunk is None:
                # EOF reached, return what we have (even if no newline)
                return line
            line += chunk
            if chunk == b"\n":
                return line


class ThreadedProcess:
    """Minimal wrapper for subprocess.Popen to match asyncio.subprocess.Process."""

    def __init__(self, popen_proc, loop):
        self.proc = popen_proc
        self.loop = loop
        self.stdout = (
            ThreadedStreamReader(popen_proc.stdout, loop) if popen_proc.stdout else None
        )
        self.stderr = (
            ThreadedStreamReader(popen_proc.stderr, loop) if popen_proc.stderr else None
        )
        self.stdin = (
            popen_proc.stdin
        )  # synchronous writing usually works ok if not blocked
        self.returncode = None

    async def wait(self):
        while self.proc.poll() is None:
            await asyncio.sleep(0.01)
        self.returncode = self.proc.returncode
        return self.returncode

    def poll(self):
        return self.proc.poll()

    async def communicate(self, input=None):
        if input:
            self.proc.stdin.write(input)
            self.proc.stdin.flush()

        stdout_content = b""
        stderr_content = b""

        if self.stdout:
            while True:
                line = await self.stdout.readline()
                if not line:
                    break
                stdout_content += line

        if self.stderr:
            while True:
                line = await self.stderr.readline()
                if not line:
                    break
                stderr_content += line

        await self.wait()
        return stdout_content, stderr_content

    def terminate(self):
        self.proc.terminate()


class AsyncProcessWrapper:
    """Wrapper for asyncio.subprocess.Process to provide poll()."""

    def __init__(self, proc):
        self.proc = proc
        self.stdout = proc.stdout
        self.stderr = proc.stderr
        self.stdin = proc.stdin

    @property
    def returncode(self):
        return self.proc.returncode

    def poll(self):
        return self.proc.returncode

    async def wait(self):
        return await self.proc.wait()

    async def communicate(self, input=None):
        return await self.proc.communicate(input)

    def terminate(self):
        self.proc.terminate()


class OpenCodeAgent:
    WORKSPACE_ROOT = WORKSPACE_ROOT

    def __init__(
        self,
        model: str = "google/antigravity-gemini-3.1-pro",
        working_dir: Optional[str] = None,
    ):
        self.model_name = model
        self.working_dir = working_dir or os.getcwd()
        self.session_file = os.path.join(self.working_dir, "user_sessions.json")

        # Cross-platform command resolution
        cmd_base = OPENCODE_CMD
        if sys.platform == "win32" and not cmd_base.lower().endswith(".cmd"):
            self.opencode_cmd = (
                shutil.which(f"{cmd_base}.cmd") or shutil.which(cmd_base) or cmd_base
            )
        else:
            self.opencode_cmd = shutil.which(cmd_base) or cmd_base

        self.user_data = self._load_user_data()
        self.yolo_mode = False
        self.active_tasks: Dict[str, asyncio.Task] = {}

        # Ensure prompts directory exists
        prompts_dir = os.path.join(self.working_dir, "prompts")
        if not os.path.exists(prompts_dir):
            os.makedirs(prompts_dir, exist_ok=True)

        # Ensure workspace root exists
        if not os.path.exists(WORKSPACE_ROOT):
            try:
                os.makedirs(WORKSPACE_ROOT, exist_ok=True)
                global_log(f"Created workspace root: {WORKSPACE_ROOT}")
            except Exception as e:
                global_log(f"Failed to create workspace root: {e}", level="ERROR")

    def _load_user_data(self) -> Dict:
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, "r") as f:
                    data = json.load(f)
                    if not data:
                        return {}
                    if isinstance(next(iter(data.values())), str):
                        return {
                            uid: {
                                "active_session": suid,
                                "sessions": [suid],
                                "session_tools": {},
                            }
                            for uid, suid in data.items()
                        }
                    for uid in data:
                        if "sessions" not in data[uid]:
                            data[uid]["sessions"] = []
                        if "active_session" not in data[uid]:
                            data[uid]["active_session"] = None
                        if "session_tools" not in data[uid]:
                            data[uid]["session_tools"] = {}
                        if "session_tags" not in data[uid]:
                            data[uid]["session_tags"] = {}
                        if "pending_tools" not in data[uid]:
                            data[uid]["pending_tools"] = []
                        if "pinned_sessions" not in data[uid]:
                            data[uid]["pinned_sessions"] = []
                        if "session_metadata" not in data[uid]:
                            data[uid]["session_metadata"] = {}
                        if "settings" not in data[uid]:
                            data[uid]["settings"] = {
                                "show_mic": True,
                                "interactive_mode": True,
                                "copy_formatted": False,
                                "default_model": "google/antigravity-gemini-3.1-pro",
                            }
                        else:
                            # Ensure defaults for existing settings objects
                            if "copy_formatted" not in data[uid]["settings"]:
                                data[uid]["settings"]["copy_formatted"] = False
                            if "default_model" not in data[uid]["settings"]:
                                data[uid]["settings"]["default_model"] = (
                                    "google/antigravity-gemini-3.1-pro"
                                )
                    return data
            except:
                return {}
        return {}

    def _save_user_data(self):
        with open(self.session_file, "w") as f:
            json.dump(self.user_data, f, indent=2)

    async def get_git_status(self, workspace_path: str) -> Dict:
        """Fetch basic Git status for the workspace."""
        if not os.path.exists(os.path.join(workspace_path, ".git")):
            return {"is_repo": False}

        try:
            # Get current branch
            proc = await self._create_subprocess(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace_path.replace("\\", "/"),
            )
            stdout, _ = await proc.communicate()
            branch = stdout.decode().strip()

            # Check for changes
            proc = await self._create_subprocess(
                ["git", "status", "--porcelain"],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace_path.replace("\\", "/"),
            )
            stdout, _ = await proc.communicate()
            changes = stdout.decode().strip()
            has_changes = len(changes) > 0

            return {
                "is_repo": True,
                "branch": branch,
                "has_changes": has_changes,
                "change_count": len(changes.splitlines()) if has_changes else 0,
            }
        except Exception as e:
            global_log(f"Error fetching Git status: {e}", level="DEBUG")
            return {"is_repo": False, "error": str(e)}

    async def get_available_models(self) -> List[str]:
        try:
            proc = await self._create_subprocess(
                [self.opencode_cmd, "models"],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir.replace("\\", "/"),
            )
            stdout, stderr = await proc.communicate()
            content = stdout.decode().strip()
            if not content:
                return []
            # Split by lines and filter empty
            return [line.strip() for line in content.splitlines() if line.strip()]
        except Exception as e:
            global_log(f"Error fetching models: {e}", level="ERROR")
            return []

    async def get_available_agents(self) -> List[Dict]:
        try:
            # Try 'agent list' without JSON format since it's not supported
            proc = await self._create_subprocess(
                [self.opencode_cmd, "agent", "list"],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir.replace("\\", "/"),
            )
            stdout, stderr = await proc.communicate()
            content = stdout.decode().strip()

            agents = [{"id": "default", "name": "Default Agent"}]
            seen = {"default"}

            if content:
                # Parse lines like "general (subagent)"
                for line in content.splitlines():
                    line = line.strip()
                    if (
                        "(" in line
                        and ")" in line
                        and not line.startswith("[")
                        and not line.startswith("{")
                    ):
                        parts = line.split("(")
                        agent_id = parts[0].strip()
                        if agent_id and agent_id not in seen:
                            agents.append(
                                {
                                    "id": agent_id,
                                    "name": agent_id.capitalize() + " Agent",
                                }
                            )
                            seen.add(agent_id)

            return agents
        except Exception as e:
            global_log(f"Error fetching agents: {e}", level="ERROR")
            return [
                {"id": "default", "name": "Default Agent"},
                {"id": "github", "name": "GitHub Agent"},
                {"id": "expert", "name": "Expert Agent"},
            ]

    def get_user_settings(self, user_id: str) -> Dict:
        default_settings = {
            "show_mic": True,
            "interactive_mode": True,
            "copy_formatted": False,
            "default_model": "google/antigravity-gemini-3.1-pro",
            "default_workspace": WORKSPACE_ROOT,
        }
        if user_id not in self.user_data:
            return default_settings

        settings = self.user_data[user_id].get("settings", default_settings)
        # Ensure all keys exist
        for k, v in default_settings.items():
            if k not in settings:
                settings[k] = v
        return settings

    def update_user_settings(self, user_id: str, settings: Dict):
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                "active_session": None,
                "sessions": [],
                "session_tools": {},
                "pending_tools": [],
                "pinned_sessions": [],
                "session_metadata": {},
                "settings": {
                    "show_mic": True,
                    "interactive_mode": True,
                    "copy_formatted": False,
                    "default_model": "google/antigravity-gemini-3.1-pro",
                    "default_workspace": WORKSPACE_ROOT,
                },
            }

        if "settings" not in self.user_data[user_id]:
            self.user_data[user_id]["settings"] = {
                "show_mic": True,
                "interactive_mode": True,
                "copy_formatted": False,
                "default_model": "google/antigravity-gemini-3.1-pro",
                "default_workspace": WORKSPACE_ROOT,
            }

        if "default_workspace" in settings:
            if not settings["default_workspace"].startswith(WORKSPACE_ROOT):
                del settings["default_workspace"]

        self.user_data[user_id]["settings"].update(settings)
        self._save_user_data()

    async def _create_subprocess(self, args, **kwargs):
        if sys.platform == "win32":
            # Always use ThreadedProcess on Windows for maximum reliability across loop types
            from subprocess import Popen, PIPE

            loop = asyncio.get_running_loop()

            # Adapt kwargs for Popen
            popen_kwargs = {
                "stdout": kwargs.get("stdout", PIPE),
                "stderr": kwargs.get("stderr", PIPE),
                "stdin": kwargs.get("stdin", PIPE),
                "cwd": kwargs.get("cwd"),
                "env": kwargs.get("env"),
                "bufsize": 0,  # Unbuffered
            }

            # Explicitly find opencode.cmd if it exists to avoid shell dependency
            if args[0] == self.opencode_cmd and not args[0].lower().endswith(".cmd"):
                cmd_path = shutil.which(f"{args[0]}.cmd") or shutil.which(args[0])
                if cmd_path:
                    args[0] = cmd_path

            proc = Popen(args, **popen_kwargs)
            return ThreadedProcess(proc, loop)

        try:
            p = await asyncio.create_subprocess_exec(*args, **kwargs)
            return AsyncProcessWrapper(p)
        except Exception as e:
            global_log(f"Subprocess creation failed: {e}", level="ERROR")
            raise

    def toggle_pin(self, user_id: str, session_uuid: str) -> bool:
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                "active_session": None,
                "sessions": [],
                "session_tools": {},
                "pending_tools": [],
                "pinned_sessions": [],
                "session_metadata": {},
            }

        user_info = self.user_data[user_id]
        if "pinned_sessions" not in user_info:
            user_info["pinned_sessions"] = []

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
        if not user_info:
            return []
        if session_uuid == "pending":
            return user_info.get("pending_tools", [])
        return user_info.get("session_tools", {}).get(session_uuid, [])

    def set_session_tools(self, user_id: str, session_uuid: str, tools: List[str]):
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                "active_session": None,
                "sessions": [],
                "session_tools": {},
                "pending_tools": [],
                "session_metadata": {},
            }
        if session_uuid == "pending":
            self.user_data[user_id]["pending_tools"] = tools
        else:
            if "session_tools" not in self.user_data[user_id]:
                self.user_data[user_id]["session_tools"] = {}
            self.user_data[user_id]["session_tools"][session_uuid] = tools
        self._save_user_data()

    def list_patterns(self) -> List[str]:
        return sorted([k for k in PATTERNS.keys() if k != "__explanations__"])

    async def apply_pattern(
        self,
        user_id: str,
        pattern_name: str,
        input_text: str,
        model: Optional[str] = None,
        file_paths: Optional[List[str]] = None,
    ) -> str:
        # Check if it's a custom prompt file
        prompts_dir = os.path.join(self.working_dir, "prompts")
        if os.path.exists(prompts_dir):
            # Try exact match first
            custom_path = os.path.join(prompts_dir, pattern_name)
            if os.path.exists(custom_path):
                try:
                    with open(custom_path, "r", encoding="utf-8") as f:
                        system = f.read()
                    return await self.generate_response(
                        user_id,
                        f"{system}\n\nUSER INPUT:\n{input_text}",
                        model=model,
                        file_paths=file_paths,
                    )
                except Exception as e:
                    return f"Error reading custom prompt '{pattern_name}': {str(e)}"

        # Fallback to system patterns
        system = PATTERNS.get(pattern_name)
        if not system:
            # Try removing colon if present (common issue)
            clean_name = pattern_name.rstrip(":")
            system = PATTERNS.get(clean_name)

        if not system:
            return f"Error: Pattern '{pattern_name}' not found."
        return await self.generate_response(
            user_id,
            f"{system}\n\nUSER INPUT:\n{input_text}",
            model=model,
            file_paths=file_paths,
        )

    def _filter_errors(self, err: str) -> str:
        err = re.sub(r".*?\[DEP0151\] DeprecationWarning:.*?(\n|$)", "", err)
        err = re.sub(
            r".*?Default \"index\" lookups for the main are deprecated for ES modules..*?(\n|$)",
            "",
            err,
        )
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
        # Match from [SYSTEM INSTRUCTION: to the double newline that separates it from the actual prompt
        text = re.sub(r"\[SYSTEM INSTRUCTION:.*?\n\n", "", text, flags=re.DOTALL)

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
            global_log("Executing session list --format json...")
            proc = await self._create_subprocess(
                [self.opencode_cmd, "session", "list", "--format", "json"],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir.replace("\\", "/"),
            )
            stdout, stderr = await proc.communicate()
            content = stdout.decode().strip()
            if not content:
                return None

            sessions = json.loads(content)
            if not sessions:
                return None

            sessions.sort(key=lambda x: x.get("created", 0), reverse=True)
            res = sessions[0].get("id")
            global_log(f"Latest session ID found: {res}")
            return res
        except Exception as e:
            global_log(f"Error in _get_latest_session_uuid: {str(e)}")
            return None

    async def generate_response_stream(
        self,
        user_id: str,
        prompt: str,
        model: Optional[str] = None,
        agent_name: Optional[str] = None,
        file_paths: Optional[List[str]] = None,
        resume_session: Optional[str] = "AUTO",
        plan_mode: bool = False,
    ) -> AsyncGenerator[Dict, None]:
        def log_debug(msg):
            global_log(f"[{user_id}] {msg}", level="DEBUG")

        if user_id not in self.user_data:
            self.user_data[user_id] = {
                "active_session": None,
                "sessions": [],
                "session_tools": {},
                "pending_tools": [],
                "session_metadata": {},
            }
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

        settings = self.get_user_settings(user_id)
        current_model = model or settings.get("default_model") or self.model_name

        # Signal start immediately to clear UI loading state
        yield {"type": "step_start", "message": "Initializing OpenCode Agent..."}

        if plan_mode:
            yield {
                "type": "plan_status",
                "status": "active",
                "message": "Entering Plan Mode...",
            }
            # Inject Plan Mode instruction
            plan_instruction = (
                "\n\n[SYSTEM INSTRUCTION: PLAN MODE ACTIVE]\n"
                "Provide a comprehensive, step-by-step plan for the user's request. "
                "Describe exactly what tools you would use and why. "
                "CRITICAL: Do NOT execute any modification tools (like write, edit, shell) yet. "
                "Wait for the user to approve your plan."
            )
            prompt = f"{plan_instruction}\n\n{prompt}"

        # System Prompt Injection for Interactive Mode
        if settings.get("interactive_mode", True):
            enabled_tools = self.get_session_tools(user_id, session_uuid or "pending")
            if enabled_tools:
                log_debug(f"User intended tools: {enabled_tools}")

            default_interactive = (
                "You can ask interactive multiple-choice or open-ended questions to the user in their preferred language (e.g., Greek).\n"
                "To trigger a question card, include a JSON block in your response using this format:\n"
                '{"type": "question", "question": "Your question text here", "options": ["Option 1", "Option 2"], "allow_multiple": false}\n'
                "- The 'question' and 'options' values should match the language of the conversation.\n"
                "- If 'allow_multiple' is true, users can select several options.\n"
                "- If 'options' is empty [], it is an open-ended question.\n"
                "The user's response will be sent back to you as a normal message."
            )
            global_setting = get_global_setting("interactive_mode_instructions")
            interactive_instruction = (
                global_setting if global_setting is not None else default_interactive
            )
            prompt = f"\n\n[SYSTEM INSTRUCTION: INTERACTIVE QUESTIONING ENABLED]\n{interactive_instruction}\n\n{prompt}"
        else:
            # Subtle instruction to avoid JSON questioning without being overly rigid about identity.
            prompt = f"\n\n[SYSTEM INSTRUCTION: Provide standard text responses only. Do not use JSON formatting for questions.]\n\n{prompt}"

        attempt = 0
        max_attempts = 2

        # Prepare environment with tool permissions
        env = os.environ.copy()
        enabled_tools = self.get_session_tools(user_id, session_uuid or "pending")
        if enabled_tools:
            perms = {"*": "deny"}
            for t in enabled_tools:
                perms[t] = "allow"
                # Map common aliases/guards
                if t == "google_search" or t == "google_web_search":
                    perms["websearch"] = "allow"
                if t in ["edit", "write", "replace", "write_file"]:
                    perms["edit"] = "allow"
                if t in ["read", "read_file", "list", "list_directory"]:
                    perms["read"] = "allow"
                    perms["list"] = "allow"

            # Core helper tools that should generally be allowed for app integration
            perms["question"] = "allow"

            opencode_config = {"permission": perms}
            env["OPENCODE_CONFIG_CONTENT"] = json.dumps(opencode_config)
            log_debug(
                f"Applying tool permissions via OPENCODE_CONFIG_CONTENT: {enabled_tools}"
            )

        # Resolve Workspace
        workspace = self.get_session_workspace(user_id, session_uuid or "pending")
        norm_workspace = os.path.normcase(os.path.abspath(workspace))
        norm_root = os.path.normcase(os.path.abspath(WORKSPACE_ROOT))

        log_debug(f"Resolved workspace: {workspace} (norm: {norm_workspace})")

        # Check if workspace is within root in a cross-platform way
        is_within_root = False
        try:
            common = os.path.normcase(os.path.commonpath([norm_root, norm_workspace]))
            is_within_root = common == norm_root
        except:
            pass

        # Sanitize for CLI (use forward slashes)
        cli_workspace = workspace.replace("\\", "/")

        if not os.path.exists(workspace) and is_within_root:
            try:
                os.makedirs(workspace, exist_ok=True)
                global_log(f"Created missing workspace: {workspace}")
            except Exception as e:
                global_log(f"Error creating workspace {workspace}: {e}", level="ERROR")
                workspace = WORKSPACE_ROOT.replace("\\", "/")  # Fallback

        while attempt < max_attempts:
            attempt += 1

            args = [
                self.opencode_cmd,
                "run",
                "--format",
                "json",
                "--thinking",
                "--dir",
                workspace.replace("\\", "/"),
            ]
            if session_uuid:
                args.extend(["-s", session_uuid])
            if current_model:
                args.extend(["-m", current_model])
            if agent_name and agent_name != "default":
                args.extend(["--agent", agent_name])
            if file_paths:
                for fp in file_paths:
                    args.extend(["-f", fp.replace("\\", "/")])

            log_debug(f"Attempt {attempt}: Running command {' '.join(args)}")

            should_fallback = False
            high_demand_detected = False
            proc = None
            stderr_buffer = []
            in_reasoning = False
            try:
                try:
                    proc = await self._create_subprocess(
                        args,
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=workspace,
                        env=env,
                    )
                except Exception as e:
                    global_log(
                        f"CRITICAL: Failed to start subprocess: {e}", level="ERROR"
                    )
                    yield {
                        "type": "error",
                        "content": f"Failed to start backend: {str(e)}",
                    }
                    return

                if prompt:
                    log_debug("Writing prompt to stdin...")

                    async def write_to_stdin(proc, data):
                        if hasattr(proc.stdin, "drain"):  # asyncio.StreamWriter
                            proc.stdin.write(data)
                            await proc.stdin.drain()
                            proc.stdin.close()
                        else:  # Synchronous pipe from Popen

                            def sync_write():
                                proc.stdin.write(data)
                                proc.stdin.flush()
                                proc.stdin.close()

                            await asyncio.to_thread(sync_write)

                    await write_to_stdin(proc, prompt.encode("utf-8"))

                async def capture_stderr(pipe):
                    nonlocal high_demand_detected
                    if not pipe:
                        return
                    while True:
                        try:
                            line = await asyncio.wait_for(pipe.readline(), timeout=0.5)
                        except asyncio.TimeoutError:
                            line = None
                        except Exception:
                            line = None

                        if not line:
                            if proc and proc.poll() is not None:
                                break
                            await asyncio.sleep(0.1)
                            continue
                        line_str = line.decode(errors="replace").strip()
                        log_debug(f"STDERR: {line_str}")
                        stderr_buffer.append(line_str)
                        # OpenCode high demand signal might be different, but let's keep this for now
                        if "High demand" in line_str or "429" in line_str:
                            log_debug("High demand detected in stderr")
                            high_demand_detected = True
                            try:
                                if proc:
                                    proc.terminate()
                            except:
                                pass

                stderr_task = asyncio.create_task(capture_stderr(proc.stderr))

                log_debug("Starting to read stdout")
                current_message_content = ""
                json_buffer = ""
                in_json_block = False
                captured_session_id = False

                if not proc or not proc.stdout:
                    log_debug("No stdout to read")
                    return

                while True:
                    try:
                        line = await asyncio.wait_for(
                            proc.stdout.readline(), timeout=1.0
                        )
                    except asyncio.TimeoutError:
                        if proc.poll() is not None:
                            log_debug("Stdout closed (EOF) and process finished")
                            break
                        continue
                    except Exception as e:
                        log_debug(f"Error reading stdout: {e}")
                        break
                    if not line:
                        if proc.poll() is not None:
                            log_debug("Stdout closed (EOF) and process finished")
                            break
                        continue
                    line_str = line.decode(errors="replace").strip()
                    if not line_str:
                        continue

                    log_debug(f"Received line ({len(line_str)} chars)")

                    if "High demand. Retry?" in line_str:
                        log_debug("High demand detected in stdout")
                        high_demand_detected = True
                        try:
                            proc.terminate()
                        except:
                            pass
                        break

                    try:
                        data = json.loads(line_str)

                        # Capture session ID from OpenCode event
                        if not captured_session_id and data.get("sessionID"):
                            new_id = data["sessionID"]
                            if not session_uuid:
                                log_debug(f"Captured session ID: {new_id}")
                                self.user_data[user_id]["active_session"] = new_id
                                if new_id not in self.user_data[user_id]["sessions"]:
                                    self.user_data[user_id]["sessions"].append(new_id)

                                # Auto-name the session based on the first prompt
                                filtered_title = self.filter_title_text(prompt)
                                await self.update_session_title(
                                    user_id, new_id, filtered_title
                                )

                                if "session_metadata" not in self.user_data[user_id]:
                                    self.user_data[user_id]["session_metadata"] = {}

                                # Store model in metadata for persistence
                                if (
                                    new_id
                                    not in self.user_data[user_id]["session_metadata"]
                                ):
                                    self.user_data[user_id]["session_metadata"][
                                        new_id
                                    ] = {}

                                self.user_data[user_id]["session_metadata"][new_id][
                                    "model"
                                ] = current_model
                                self.user_data[user_id]["session_metadata"][new_id][
                                    "original_title"
                                ] = filtered_title
                                self.user_data[user_id]["session_metadata"][new_id][
                                    "time"
                                ] = dt_pkg.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                                self._save_user_data()
                                yield {"type": "init", "session_id": new_id}
                                session_uuid = new_id
                            captured_session_id = True

                        # Transform OpenCode events to Gemini format
                        transformed_data = None

                        if data.get("type") == "text":
                            if in_reasoning:
                                yield {"type": "reasoning_finish"}
                                in_reasoning = False
                            transformed_data = {
                                "type": "message",
                                "role": "assistant",
                                "content": data.get("part", {}).get("text", ""),
                            }
                        elif data.get("type") == "reasoning":
                            text = data.get("part", {}).get("text", "")
                            if not in_reasoning:
                                transformed_data = {
                                    "type": "reasoning_start",
                                    "content": text,
                                }
                                in_reasoning = True
                            else:
                                transformed_data = {
                                    "type": "reasoning",
                                    "content": text,
                                }
                        elif data.get("type") == "tool_use":
                            if in_reasoning:
                                yield {"type": "reasoning_finish"}
                                in_reasoning = False

                            tool_part = data.get("part", {})
                            state = tool_part.get("state", {})
                            if state.get("status") == "completed":
                                transformed_data = {
                                    "type": "tool_result",
                                    "tool_name": tool_part.get("tool"),
                                    "output": state.get("output", ""),
                                }
                            else:
                                # New event: tool started
                                transformed_data = {
                                    "type": "tool_use",
                                    "tool_name": tool_part.get("tool"),
                                    "parameters": tool_part.get("input", {}),
                                }
                        elif data.get("type") == "step_finish":
                            transformed_data = {
                                "type": "step_finish",
                                "tokens": data.get("part", {}).get("tokens", {}),
                                "cost": data.get("part", {}).get("cost", 0),
                            }

                        if not transformed_data:
                            continue

                        data = transformed_data

                        # Handle interactive questioning protocol
                        if (
                            data.get("type") == "message"
                            and data.get("role") == "assistant"
                        ):
                            content = data.get("content", "")

                            # Add to global buffer for full detection
                            current_message_content += content

                            # Logic to hide JSON and potential markdown backticks from the stream
                            cleaned_content = ""
                            i = 0
                            while i < len(content):
                                char = content[i]
                                if not in_json_block:
                                    # Lookahead for potential JSON start
                                    # Only buffer if we see { or ` and NOT in reasoning
                                    if (
                                        char == "{" or char == "`"
                                    ) and not in_reasoning:
                                        # Peek ahead for "type": "question" or ```json
                                        rem = content[i:]
                                        # Aggressive peek: if we see { followed soon by "type"
                                        if char == "{" and (
                                            '"type"' in rem[:50]
                                            or '"type"' in current_message_content[-50:]
                                        ):
                                            in_json_block = True
                                            json_buffer = char
                                        elif char == "`" and rem.startswith("```"):
                                            in_json_block = True
                                            json_buffer = char
                                        else:
                                            cleaned_content += char
                                    else:
                                        cleaned_content += char
                                else:
                                    json_buffer += char
                                    # Check for end of block
                                    if char == "}" or char == "`":
                                        # Heuristic: if valid question, stay in block until closed
                                        if (
                                            '"type": "question"' in json_buffer
                                            or '"type":"question"' in json_buffer
                                        ):
                                            try:
                                                inner_json_match = re.search(
                                                    r"\{\s*\"type\"\s*:\s*\"question\".*?\}",
                                                    json_buffer,
                                                    re.DOTALL,
                                                )
                                                if inner_json_match:
                                                    json_text = inner_json_match.group(
                                                        0
                                                    )
                                                    json.loads(json_text)
                                                    # Balanced? Check if closed correctly
                                                    is_wrapped = json_buffer.startswith(
                                                        "```"
                                                    )
                                                    if (
                                                        is_wrapped
                                                        and json_buffer.endswith("```")
                                                    ) or (
                                                        not is_wrapped
                                                        and json_buffer.endswith("}")
                                                    ):
                                                        in_json_block = False
                                                        json_buffer = ""
                                            except:
                                                pass  # Not complete yet
                                        else:
                                            # Not a question. Flush it.
                                            # If buffer ends with ` (closing backtick) or looks too big
                                            if (
                                                char == "`"
                                                and json_buffer.endswith("```")
                                            ) or len(json_buffer) > 50:
                                                cleaned_content += json_buffer
                                                in_json_block = False
                                                json_buffer = ""
                                i += 1

                            data["content"] = cleaned_content

                            # Global buffer handles full detection and yielding
                            # We update the regex to optionally swallow surrounding backticks and newlines
                            question_pattern = r"(?:```(?:json)?\s*)?\{\s*\"type\"\s*:\s*\"question\".*?\}(?:\s*```)?"
                            question_match = re.search(
                                question_pattern, current_message_content, re.DOTALL
                            )
                            if question_match:
                                try:
                                    full_match_text = question_match.group(0)
                                    # Extract JUST the JSON part for parsing
                                    json_only_match = re.search(
                                        r"\{\s*\"type\"\s*:\s*\"question\".*?\}",
                                        full_match_text,
                                        re.DOTALL,
                                    )
                                    if json_only_match:
                                        question_data = json.loads(
                                            json_only_match.group(0)
                                        )
                                        yield question_data
                                        current_message_content = (
                                            current_message_content.replace(
                                                full_match_text, ""
                                            )
                                        )
                                except:
                                    pass

                            # If we have nothing to show yet (still buffering JSON/markdown), don't yield this chunk's message
                            if not data["content"] and in_json_block:
                                continue

                        # Truncate large tool outputs
                        if data.get("type") == "tool_result" and "output" in data:
                            output = data["output"]
                            threshold = 20 * 1024  # 20KB
                            if len(output) > threshold:
                                truncated = output[:threshold]
                                # Save full output to a file
                                try:
                                    fname = f"output_{uuid.uuid4().hex}.txt"
                                    fpath = os.path.join(UPLOAD_DIR, fname)
                                    with open(fpath, "w", encoding="utf-8") as f:
                                        f.write(output)
                                    data["full_output_path"] = f"/uploads/{fname}"
                                    data["output"] = (
                                        f"{truncated}\n\n[Output truncated. Full output available below.]"
                                    )
                                    log_debug(
                                        f"Truncated tool output and saved to {fpath}"
                                    )
                                except Exception as e:
                                    log_debug(f"Error saving full output: {str(e)}")
                                    data["output"] = (
                                        f"{truncated}\n\n[Output truncated. Error saving full version.]"
                                    )

                                log_debug(
                                    f"Truncated tool output from {len(output)} to {len(data['output'])} bytes"
                                )

                        # Check for capacity error in JSON chunks
                        content_to_check = str(data).lower()
                        if (
                            any(k in content_to_check for k in CAPACITY_KEYWORDS)
                            and attempt < max_attempts
                        ):
                            fallback = FALLBACK_MODELS.get(current_model)
                            if fallback:
                                log_debug(
                                    f"Capacity error detected in stdout, falling back to {fallback}"
                                )
                                yield {
                                    "type": "model_switch",
                                    "old_model": current_model,
                                    "new_model": fallback,
                                }
                                yield {
                                    "type": "message",
                                    "role": "assistant",
                                    "content": f"\n\n[Model {current_model} is currently busy or quota exhausted. Switching to {fallback} for a faster response...]\n\n",
                                }
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
                    except:
                        pass
                    continue

                await proc.wait()
                await stderr_task

                if in_reasoning:
                    yield {"type": "reasoning_finish"}
                    in_reasoning = False

                log_debug(f"Process exited with code {proc.returncode}")

                if high_demand_detected:
                    yield {
                        "type": "question",
                        "question": "We are currently experiencing high demand. Should I keep trying?",
                        "options": ["Retry", "Stop"],
                        "allow_multiple": False,
                        "is_retry": True,
                    }
                    break

                if plan_mode:
                    yield {
                        "type": "plan_status",
                        "status": "completed",
                        "message": "Plan complete. Review proposed changes below.",
                    }

                # Check for capacity error in stderr if process failed
                if proc.returncode != 0 and not should_fallback:
                    err_text = "\n".join(stderr_buffer).lower()
                    if (
                        any(k in err_text for k in CAPACITY_KEYWORDS)
                        and attempt < max_attempts
                    ):
                        fallback = FALLBACK_MODELS.get(current_model)
                        if fallback:
                            log_debug(
                                f"Capacity error detected in stderr, falling back to {fallback}"
                            )
                            yield {
                                "type": "model_switch",
                                "old_model": current_model,
                                "new_model": fallback,
                            }
                            yield {
                                "type": "message",
                                "role": "assistant",
                                "content": f"\n\n[Model {current_model} is currently busy or quota exhausted. Switching to {fallback}...]\n\n",
                            }
                            current_model = fallback
                            continue

                    # If not a capacity error, yield generic exit code error
                    yield {"type": "error", "content": f"Exit code {proc.returncode}"}

                break
            finally:
                if proc and proc.returncode is None:
                    try:
                        proc.terminate()
                        await proc.wait()
                    except:
                        pass

    async def generate_response(
        self,
        user_id: str,
        prompt: str,
        model: Optional[str] = None,
        agent_name: Optional[str] = None,
        file_paths: Optional[List[str]] = None,
        resume_session: Optional[str] = "AUTO",
    ) -> str:
        full_response = ""
        async for chunk in self.generate_response_stream(
            user_id,
            prompt,
            model,
            agent_name,
            file_paths,
            resume_session=resume_session,
        ):
            if chunk.get("type") == "message":
                full_response += chunk.get("content", "")
            elif chunk.get("type") == "error":
                full_response += f"\n[Error: {chunk.get('content')}]"
            elif chunk.get("type") == "raw":
                full_response += chunk.get("content", "") + "\n"
        return full_response.strip()

    async def update_session_title(
        self, user_id: str, uuid: str, new_title: str
    ) -> bool:
        if user_id in self.user_data and uuid in self.user_data[user_id]["sessions"]:
            if "custom_titles" not in self.user_data[user_id]:
                self.user_data[user_id]["custom_titles"] = {}
            self.user_data[user_id]["custom_titles"][uuid] = new_title
            self._save_user_data()
            return True
        return False

    async def update_session_tags(
        self, user_id: str, uuid: str, tags: List[str]
    ) -> bool:
        if user_id in self.user_data and uuid in self.user_data[user_id]["sessions"]:
            if "session_tags" not in self.user_data[user_id]:
                self.user_data[user_id]["session_tags"] = {}
            self.user_data[user_id]["session_tags"][uuid] = tags
            self._save_user_data()
            return True
        return False

    def get_unique_tags(self, user_id: str) -> List[str]:
        if user_id not in self.user_data:
            return []
        user_info = self.user_data[user_id]
        all_tags = set()
        for tags in user_info.get("session_tags", {}).values():
            for t in tags:
                all_tags.add(t)
        return sorted(list(all_tags))

    def get_session_workspace(self, user_id: str, session_uuid: str) -> str:
        if user_id not in self.user_data:
            return WORKSPACE_ROOT
        user_info = self.user_data[user_id]
        workspaces = user_info.get("session_workspaces", {})
        path = workspaces.get(session_uuid)
        if not path:
            settings = user_info.get("settings", {})
            path = settings.get("default_workspace", WORKSPACE_ROOT)
        return path

    def update_session_workspace(
        self, user_id: str, session_uuid: str, workspace_path: str
    ):
        # Normalize paths for comparison
        # Use abspath to ensure we have the full path
        norm_root = os.path.normcase(os.path.abspath(WORKSPACE_ROOT))
        norm_path = os.path.normcase(os.path.abspath(workspace_path))

        # Security check: must be within root or equal to root
        try:
            common = os.path.normcase(os.path.commonpath([norm_root, norm_path]))
            is_within = common == norm_root
        except ValueError:
            is_within = False

        if not is_within:
            return False

        if user_id not in self.user_data:
            return False

        if "session_workspaces" not in self.user_data[user_id]:
            self.user_data[user_id]["session_workspaces"] = {}
        self.user_data[user_id]["session_workspaces"][session_uuid] = workspace_path
        self._save_user_data()
        return True

    def get_available_workspaces(self) -> List[str]:
        workspaces = []
        if not os.path.exists(WORKSPACE_ROOT):
            return [WORKSPACE_ROOT]

        workspaces.append(WORKSPACE_ROOT)
        try:
            # Walk with limited depth and ignore common massive folders
            ignore_dirs = {
                "node_modules",
                ".git",
                ".venv",
                "venv",
                "__pycache__",
                ".opencode",
                "tmp",
                "data",
            }
            for root, dirs, files in os.walk(WORKSPACE_ROOT):
                # Modify dirs in-place to prune the walk
                dirs[:] = [
                    d for d in dirs if d not in ignore_dirs and not d.startswith(".")
                ]

                # Limit total count to prevent UI lag
                if len(workspaces) > 500:
                    break

                for d in dirs:
                    full_path = os.path.join(root, d)
                    workspaces.append(full_path)

                # Limit depth by checking relative path
                rel_path = os.path.relpath(root, WORKSPACE_ROOT)
                if rel_path != "." and rel_path.count(os.sep) >= 2:
                    dirs[:] = []  # Don't go deeper than 3 levels

        except Exception as e:
            global_log(f"Error walking workspaces: {e}")

        return sorted(list(set(workspaces)))

    def is_user_session(self, user_id: str, session_uuid: str) -> bool:
        """Check if a session belongs to a user without filtering for sidebar."""
        if user_id not in self.user_data:
            return False
        return session_uuid in self.user_data[user_id].get("sessions", [])

    async def get_user_sessions(
        self,
        user_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
        tags: Optional[List[str]] = None,
        force_sync: bool = False,
    ) -> Dict[str, Any]:
        global_log(
            f"get_user_sessions for {user_id}, limit={limit}, offset={offset}, force_sync={force_sync}"
        )
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                "active_session": None,
                "sessions": [],
                "session_tools": {},
                "pending_tools": [],
                "pinned_sessions": [],
                "session_metadata": {},
            }
            self._save_user_data()

        user_info = self.user_data[user_id]
        uuids = user_info.get("sessions", [])
        custom_titles = user_info.get("custom_titles", {})
        session_tags = user_info.get("session_tags", {})
        session_metadata = user_info.get("session_metadata", {})
        session_forks = user_info.get("session_forks", {})

        global_log(f"User has {len(uuids)} session UUIDs")

        # Check if we have metadata for all sessions (including incomplete metadata missing 'time')
        missing_metadata = [
            u
            for u in uuids
            if u not in session_metadata or not session_metadata[u].get("time")
        ]
        global_log(f"Missing metadata for {len(missing_metadata)} sessions")

        all_sessions = []

        # Force sync if list is empty or explicitly requested
        if not uuids or missing_metadata or force_sync:
            # Need to fetch from CLI
            try:
                global_log("Executing session list --format json...")
                proc = await self._create_subprocess(
                    [
                        self.opencode_cmd,
                        "session",
                        "list",
                        "--format",
                        "json",
                    ],
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.working_dir.replace("\\", "/"),
                )
                stdout, stderr = await proc.communicate()
                raw_content = stdout.decode().strip()

                if not raw_content:
                    parsed_sessions = []
                else:
                    # Find start of JSON array
                    json_start = raw_content.find("[")
                    if json_start != -1:
                        try:
                            parsed_sessions = json.loads(raw_content[json_start:])
                        except json.JSONDecodeError as e:
                            global_log(f"Failed to parse session list JSON: {e}")
                            parsed_sessions = []
                    else:
                        parsed_sessions = []

                global_log(f"CLI returned {len(parsed_sessions)} sessions")

                pinned_uuids = user_info.get("pinned_sessions", [])
                found_uuids = set()

                cli_sessions = []
                for sess in parsed_sessions:
                    u = sess.get("id")
                    if not u:
                        continue
                    found_uuids.add(u)

                    ts = sess.get("updated", sess.get("created", 0)) / 1000.0
                    time_str = dt_pkg.datetime.fromtimestamp(ts).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )

                    # Update metadata cache and ensure it's in user's session list
                    # Use .update() to preserve existing fields like 'model'
                    if u not in session_metadata:
                        session_metadata[u] = {}
                    session_metadata[u].update(
                        {
                            "original_title": sess.get("title", "Unknown"),
                            "time": time_str,
                        }
                    )

                    # Only process sessions that are already in the user's list
                    if u not in uuids:
                        continue

                    current_tags = session_tags.get(u, [])
                    if tags:
                        if not all(tag in current_tags for tag in tags):
                            continue

                    title = custom_titles.get(u, sess.get("title", "Unknown"))

                    cli_sessions.append(
                        {
                            "uuid": u,
                            "title": title,
                            "time": time_str,
                            "active": (u == user_info.get("active_session")),
                            "pinned": (u in pinned_uuids),
                            "tags": current_tags,
                            "model": session_metadata[u].get("model"),  # Include model
                            "workspace": self.get_session_workspace(user_id, u),
                        }
                    )

                # Update user_data with new metadata
                self.user_data[user_id]["session_metadata"] = session_metadata
                self.user_data[user_id]["sessions"] = uuids

                self._save_user_data()
                all_sessions = list(cli_sessions)

                # If we have local sessions NOT in cli_sessions (e.g. older ones), we should probably add them from cache
                cached_ids = set(session_metadata.keys())
                cli_ids = {s["uuid"] for s in cli_sessions}

                for u in uuids:
                    if u not in cli_ids:
                        meta = session_metadata.get(
                            u, {"original_title": "Unknown Chat", "time": "Unknown"}
                        )
                        # Check tags filter
                        current_tags = session_tags.get(u, [])
                        if tags:
                            if not all(tag in current_tags for tag in tags):
                                continue

                        all_sessions.append(
                            {
                                "uuid": u,
                                "title": custom_titles.get(
                                    u, meta.get("original_title", "Unknown Chat")
                                ),
                                "time": meta.get("time", "Unknown"),
                                "active": (u == user_info.get("active_session")),
                                "pinned": (u in pinned_uuids),
                                "tags": current_tags,
                                "model": meta.get("model"),
                                "workspace": self.get_session_workspace(user_id, u),
                            }
                        )

                # Sort combined list by time descending (Unknown timestamps go to end)
                all_sessions.sort(
                    key=lambda x: x.get("time") or ""
                    if x.get("time") != "Unknown"
                    else "",
                    reverse=True,
                )
            except Exception as e:
                global_log(
                    f"Error in get_user_sessions (fetching): {str(e)}", level="ERROR"
                )
                return {"pinned": [], "history": [], "total_unpinned": 0}

        else:
            # All metadata cached, build from cache
            pinned_uuids = user_info.get("pinned_sessions", [])
            for u in uuids:
                meta = session_metadata.get(
                    u, {"original_title": "Unknown", "time": "Unknown"}
                )

                # Check tags filter
                current_tags = session_tags.get(u, [])
                if tags:
                    if not all(tag in current_tags for tag in tags):
                        continue

                title = custom_titles.get(u, meta.get("original_title", "Unknown"))

                all_sessions.append(
                    {
                        "uuid": u,
                        "title": title,
                        "time": meta.get("time", "Unknown"),
                        "active": (u == user_info.get("active_session")),
                        "pinned": (u in pinned_uuids),
                        "tags": current_tags,
                        "model": meta.get("model"),
                        "workspace": self.get_session_workspace(user_id, u),
                    }
                )

            # Sort combined list by time descending (Unknown timestamps go to end)
            all_sessions.sort(
                key=lambda x: x.get("time") or "" if x.get("time") != "Unknown" else "",
                reverse=True,
            )

        global_log(f"Processing grouping for {len(all_sessions)} sessions")
        # --- Grouping Logic: Display them as one (the latest fork) ---
        # ... rest of function ...

        def get_root(u):
            """Find the root session UUID for a given session."""
            visited = set()
            curr = u
            while (
                curr in session_forks
                and session_forks[curr].get("parent")
                and curr not in visited
            ):
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
            "total_unpinned": total_unpinned,
        }

    async def search_sessions(self, user_id: str, query: str) -> List[Dict]:
        sessions_data = await self.get_user_sessions(user_id)
        if not query:
            return sessions_data.get("pinned", []) + sessions_data.get("history", [])

        all_sessions = sessions_data.get("pinned", []) + sessions_data.get(
            "history", []
        )
        if not all_sessions:
            return []

        query = query.lower()
        results = []

        for sess in all_sessions:
            match = False
            # Check title
            if query in sess.get("title", "").lower():
                match = True

            if not match:
                # Check messages and attachments by exporting
                try:
                    msgs_data = await self.get_session_messages(sess["uuid"])
                    for msg in msgs_data.get("messages", []):
                        if query in msg.get("content", "").lower():
                            match = True
                            break
                except:
                    pass

            if match:
                results.append(sess)

        return results

    async def get_session_messages(
        self, session_uuid: str, limit: Optional[int] = None, offset: int = 0
    ) -> Dict:
        async def run_export_with_retry(retries: int = 2, delay: float = 0.15) -> tuple:
            stderr_output = ""
            for attempt in range(retries + 1):
                global_log(
                    f"Exporting session {session_uuid} for messages (attempt {attempt + 1})..."
                )
                proc = await self._create_subprocess(
                    [self.opencode_cmd, "export", session_uuid],
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.working_dir.replace("\\", "/"),
                )
                stdout, stderr = await proc.communicate()
                content = stdout.decode().strip()
                stderr_output = stderr.decode().strip() if stderr else ""

                if stderr_output:
                    global_log(f"Export stderr: {stderr_output[:500]}")

                json_match = re.search(r"\{.*\}", content, re.DOTALL)
                if json_match:
                    try:
                        data = json.loads(json_match.group(0))
                        messages = data.get("messages", [])
                        if messages or attempt == retries:
                            return data, stderr_output
                    except json.JSONDecodeError as e:
                        global_log(f"Failed to parse session messages JSON: {e}")

                if attempt < retries:
                    global_log(f"Export returned empty, retrying in {delay}s...")
                    await asyncio.sleep(delay)

            return None, stderr_output

        try:
            data, stderr_output = await run_export_with_retry()

            if not data:
                global_log(
                    f"No JSON found in export output after retries. stderr: {stderr_output[:200] if stderr_output else 'none'}"
                )
                return {"messages": [], "total": 0, "error": "export_failed"}

            all_messages = data.get("messages", [])
            total = len(all_messages)

            if limit is not None:
                start = max(0, total - offset - limit)
                end = max(0, total - offset)
                messages_to_process = all_messages[start:end]
            else:
                start = 0
                messages_to_process = all_messages

            messages = []
            for idx, msg in enumerate(messages_to_process):
                role = msg.get("info", {}).get("role", "user")

                parts = msg.get("parts", [])
                text_parts = []
                for p in parts:
                    if p.get("type") == "text":
                        text_parts.append(p.get("text", ""))
                    elif p.get("type") == "reasoning":
                        text_parts.append(
                            f"[Thinking]\n{p.get('text', '')}\n[/Thinking]"
                        )

                content_text = "\n".join(text_parts).strip()
                if not content_text:
                    continue

                msg_data = {
                    "role": "user" if role == "user" else "bot",
                    "content": content_text,
                    "raw_index": start + idx,
                }

                # Extract question JSON from content if present
                question_match = re.search(
                    r'\{\s*"type"\s*:\s*"question".*?\}', content_text, re.DOTALL
                )
                if question_match:
                    try:
                        question_data = json.loads(question_match.group(0))
                        # Validate it's not a placeholder
                        if (
                            question_data.get("question")
                            and question_data.get("question")
                            != "Your question text here"
                        ):
                            msg_data["question"] = question_data
                            # Remove the question JSON from content to avoid rendering issues
                            content_text = content_text.replace(
                                question_match.group(0), ""
                            )
                            msg_data["content"] = content_text.strip()
                    except:
                        pass

                # Cleanup malformed/corrupted question patterns (e.g., missing type field, corrupted JSON)
                # Match patterns containing options and allow_multiple that look like question data
                if "question" not in msg_data:
                    malformed_pattern = re.search(
                        r'\{\s*"[^}]*"options"\s*:\s*\[[^\]]+\][^}]*"allow_multiple"\s*:\s*(?:true|false)[^}]*\}',
                        msg_data["content"],
                        re.DOTALL,
                    )
                    if malformed_pattern:
                        # Try to parse and extract as question
                        try:
                            potential_q = json.loads(malformed_pattern.group(0))
                            # Only accept if it has valid question text (not placeholder)
                            if (
                                potential_q.get("question")
                                and potential_q.get("question")
                                != "Your question text here"
                            ):
                                msg_data["question"] = potential_q
                                msg_data["content"] = msg_data["content"].replace(
                                    malformed_pattern.group(0), ""
                                )
                        except:
                            # If parsing fails, just remove the pattern
                            msg_data["content"] = msg_data["content"].replace(
                                malformed_pattern.group(0), ""
                            )

                # Also remove standalone "options": [...] patterns that appear corrupted
                standalone_options = re.findall(
                    r'options"\s*:\s*\[[^\]]+\],\s*"allow_multiple"\s*:\s*(?:true|false)',
                    msg_data["content"],
                )
                for opt in standalone_options:
                    clean_opt = (
                        'options": ' + opt.split('options": ')[1]
                        if 'options": ' in opt
                        else opt
                    )
                    msg_data["content"] = msg_data["content"].replace(opt, "")

                msg_data["content"] = msg_data["content"].strip()

                messages.append(msg_data)
            return {"messages": messages, "total": total}
        except Exception as e:
            print(f"Error loading session messages: {str(e)}")
            return {"messages": [], "total": 0, "error": str(e)}

    async def switch_session(self, user_id: str, uuid: str) -> bool:
        if user_id not in self.user_data:
            return False

        user_info = self.user_data[user_id]

        # More permissive switch: if it's in our metadata or we just found it
        if uuid in user_info.get("sessions", []) or uuid in user_info.get(
            "session_metadata", {}
        ):
            user_info["active_session"] = uuid
            if uuid not in user_info.setdefault("sessions", []):
                user_info["sessions"].append(uuid)
            self._save_user_data()
            return True

        # Last resort: check if it exists in CLI
        try:
            proc = await self._create_subprocess(
                [self.opencode_cmd, "session", "list", "--format", "json"],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir.replace("\\", "/"),
            )
            stdout, _ = await proc.communicate()
            sessions = json.loads(stdout.decode())
            if any(s.get("id") == uuid for s in sessions):
                user_info["active_session"] = uuid
                if uuid not in user_info.setdefault("sessions", []):
                    user_info["sessions"].append(uuid)
                self._save_user_data()
                return True
        except:
            pass

        return False

    async def clone_session(
        self, user_id: str, original_uuid: str, message_index: int
    ) -> Optional[str]:
        """
        Clone a session up to a certain message index.
        Returns the new session UUID if successful.
        """
        if (
            user_id not in self.user_data
            or original_uuid not in self.user_data[user_id]["sessions"]
        ):
            return None

        try:
            if message_index == -1:
                # We want to start a new session but linked to this tree
                user_info = self.user_data[user_id]
                user_info["active_session"] = None  # Force new session in CLI

                # Store pending info to apply to the NEXT session created
                user_info["pending_fork"] = {
                    "parent": original_uuid,
                    "fork_point": -1,
                    "title": user_info.get("custom_titles", {}).get(original_uuid),
                    "tags": list(
                        user_info.get("session_tags", {}).get(original_uuid, [])
                    ),
                    "tools": list(
                        user_info.get("session_tools", {}).get(original_uuid, [])
                    ),
                }

                self._save_user_data()
                return "pending"  # Frontend will handle this

            # For specific index, we export, slice, and import
            global_log(f"Cloning session {original_uuid} at index {message_index}...")
            proc = await self._create_subprocess(
                [self.opencode_cmd, "export", original_uuid],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir.replace("\\", "/"),
            )
            stdout, stderr = await proc.communicate()
            content = stdout.decode().strip()

            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if not json_match:
                return None

            try:
                data = json.loads(json_match.group(0))
            except json.JSONDecodeError as e:
                global_log(f"Failed to parse clone session JSON: {e}")
                return None
            if "messages" in data:
                data["messages"] = data["messages"][: message_index + 1]

            # Save to a temporary file for import
            temp_file = os.path.join(
                self.working_dir, f"temp_clone_{uuid.uuid4().hex}.json"
            )
            with open(temp_file, "w") as f:
                json.dump(data, f)

            try:
                proc = await self._create_subprocess(
                    [self.opencode_cmd, "import", temp_file.replace("\\", "/")],
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.working_dir.replace("\\", "/"),
                )
                stdout, stderr = await proc.communicate()
                output = stdout.decode().strip()

                # OpenCode import usually prints the new session ID
                # We need to extract it
                new_uuid_match = re.search(r"ses_[a-zA-Z0-9]+", output)
                if not new_uuid_match:
                    # Fallback: check latest session
                    new_uuid = await self._get_latest_session_uuid()
                else:
                    new_uuid = new_uuid_match.group(0)

                if new_uuid and new_uuid != original_uuid:
                    user_info = self.user_data[user_id]
                    if new_uuid not in user_info["sessions"]:
                        user_info["sessions"].append(new_uuid)

                    if "session_forks" not in user_info:
                        user_info["session_forks"] = {}
                    user_info["session_forks"][new_uuid] = {
                        "parent": original_uuid,
                        "fork_point": message_index,
                    }

                    # Inherit title and tags
                    orig_title = user_info.get("custom_titles", {}).get(original_uuid)
                    if orig_title:
                        if "custom_titles" not in user_info:
                            user_info["custom_titles"] = {}
                        user_info["custom_titles"][new_uuid] = f"{orig_title} (Fork)"

                    orig_tags = user_info.get("session_tags", {}).get(original_uuid)
                    if orig_tags:
                        if "session_tags" not in user_info:
                            user_info["session_tags"] = {}
                        user_info["session_tags"][new_uuid] = list(orig_tags)

                    self._save_user_data()
                    return new_uuid
            finally:
                if os.path.exists(temp_file):
                    os.remove(temp_file)

            return None
        except Exception as e:
            print(f"Error cloning session: {str(e)}")
            return None

    def get_session_forks(
        self, user_id: str, session_uuid: str
    ) -> Dict[int, List[str]]:
        """
        Get all forks related to this session, organized by fork point.
        Returns a dict: { message_index: [uuid1, uuid2, ...] }
        """
        if user_id not in self.user_data:
            return {}
        user_info = self.user_data[user_id]
        forks_info = user_info.get("session_forks", {})

        fork_map = {}

        def add_to_map(index, uid):
            if index not in fork_map:
                fork_map[index] = []
            if uid not in fork_map[index]:
                fork_map[index].append(uid)

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
                if (
                    u != session_uuid
                    and info["parent"] == parent_uuid
                    and info["fork_point"] == my_fork_point
                ):
                    add_to_map(my_fork_point, u)

        return fork_map

    def get_fork_graph(self, user_id: str) -> Dict[str, Dict]:
        """Get the full fork graph for all sessions of a user."""
        if user_id not in self.user_data:
            return {}
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
                "title": title,
            }
        return graph

    async def sync_session_updates(
        self,
        user_id: str,
        session_uuid: str,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ):
        """Sync title/tags across all related forks."""
        if user_id not in self.user_data:
            return
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
                if "custom_titles" not in user_info:
                    user_info["custom_titles"] = {}
                user_info["custom_titles"][u] = title
            if tags is not None:
                if "session_tags" not in user_info:
                    user_info["session_tags"] = {}
                user_info["session_tags"][u] = tags

        self._save_user_data()

    async def new_session(self, user_id: str):
        self.user_data.setdefault(user_id, {})["active_session"] = None
        self.user_data[user_id].pop("pending_fork", None)
        self._save_user_data()

    async def delete_specific_session(self, user_id: str, uuid: str) -> bool:
        if (
            user_id not in self.user_data
            or uuid not in self.user_data[user_id]["sessions"]
        ):
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
                    if other_user_id == user_id:
                        continue
                    if target_uuid in other_user_info.get("sessions", []):
                        is_tracked_by_others = True
                        break

                # 2. Only delete from CLI if no other users are tracking it
                if not is_tracked_by_others:
                    await (
                        await self._create_subprocess(
                            [self.opencode_cmd, "session", "delete", target_uuid],
                            cwd=self.working_dir.replace("\\", "/"),
                        )
                    ).communicate()

                # 3. Cleanup local tracking
                if target_uuid in user_info["sessions"]:
                    user_info["sessions"].remove(target_uuid)

                if user_info.get("active_session") == target_uuid:
                    user_info["active_session"] = None

                if (
                    "session_metadata" in user_info
                    and target_uuid in user_info["session_metadata"]
                ):
                    del user_info["session_metadata"][target_uuid]

                if (
                    "custom_titles" in user_info
                    and target_uuid in user_info["custom_titles"]
                ):
                    del user_info["custom_titles"][target_uuid]

                if (
                    "session_tags" in user_info
                    and target_uuid in user_info["session_tags"]
                ):
                    del user_info["session_tags"][target_uuid]

                if (
                    "session_forks" in user_info
                    and target_uuid in user_info["session_forks"]
                ):
                    del user_info["session_forks"][target_uuid]

            except Exception as e:
                global_log(
                    f"Error deleting session {target_uuid}: {str(e)}", level="ERROR"
                )
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

    async def share_session(
        self, user_id: str, session_uuid: str, target_username: str, user_manager: Any
    ) -> bool:
        """
        Share a session with another user.
        Fails silently if target_username does not exist.
        """
        # 1. Verify user_id has access to session_uuid
        if user_id not in self.user_data or session_uuid not in self.user_data[
            user_id
        ].get("sessions", []):
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
                "settings": {
                    "show_mic": True,
                    "interactive_mode": True,
                    "copy_formatted": False,
                },
            }

        target_info = self.user_data[target_username]
        if "sessions" not in target_info:
            target_info["sessions"] = []
        if session_uuid not in target_info["sessions"]:
            target_info["sessions"].append(session_uuid)

        # 4. Copy custom_titles, session_tags, session_metadata, and session_tools to the target user
        source_info = self.user_data[user_id]

        if (
            "custom_titles" in source_info
            and session_uuid in source_info["custom_titles"]
        ):
            target_info.setdefault("custom_titles", {})[session_uuid] = source_info[
                "custom_titles"
            ][session_uuid]

        if (
            "session_tags" in source_info
            and session_uuid in source_info["session_tags"]
        ):
            target_info.setdefault("session_tags", {})[session_uuid] = list(
                source_info["session_tags"][session_uuid]
            )

        if (
            "session_metadata" in source_info
            and session_uuid in source_info["session_metadata"]
        ):
            target_info.setdefault("session_metadata", {})[session_uuid] = dict(
                source_info["session_metadata"][session_uuid]
            )

        if (
            "session_tools" in source_info
            and session_uuid in source_info["session_tools"]
        ):
            target_info.setdefault("session_tools", {})[session_uuid] = list(
                source_info["session_tools"][session_uuid]
            )

        # 5. Save user_sessions.json
        self._save_user_data()
        return True

    async def reset_chat(self, user_id: str) -> str:
        uuid = self.user_data.get(user_id, {}).get("active_session")
        if uuid:
            if await self.delete_specific_session(user_id, uuid):
                return "Conversation reset."
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
import re
import json
import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
import subprocess
import logging

logger = logging.getLogger(__name__)


@dataclass
class Skill:
    name: str
    description: str
    content: str
    workspace_path: str
    keywords: List[str] = field(default_factory=list)
    execution_type: str = "context"  # "context" or "script"
    script_path: Optional[str] = None
    script_args: List[str] = field(default_factory=list)


class SkillService:
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.skills_cache: Dict[str, Skill] = {}
        self._load_skills()

    def _get_skills_dir(self) -> str:
        return os.path.join(self.workspace_root, ".opencode", "skills")

    def _load_skills(self):
        """Load all skills from the workspace skills directory."""
        skills_dir = self._get_skills_dir()
        if not os.path.exists(skills_dir):
            logger.warning(f"Skills directory not found: {skills_dir}")
            return

        for skill_name in os.listdir(skills_dir):
            skill_path = os.path.join(skills_dir, skill_name)
            if not os.path.isdir(skill_path):
                continue

            skill_md = os.path.join(skill_path, "SKILL.md")
            if not os.path.exists(skill_md):
                continue

            try:
                with open(skill_md, "r", encoding="utf-8") as f:
                    content = f.read()

                skill = self._parse_skill(skill_name, skill_path, content)
                if skill:
                    self.skills_cache[skill_name] = skill
                    logger.info(f"Loaded skill: {skill_name}")
            except Exception as e:
                logger.error(f"Error loading skill {skill_name}: {e}")

    def _parse_skill(self, name: str, skill_path: str, content: str) -> Optional[Skill]:
        """Parse skill from SKILL.md content."""
        description = "Workspace Skill"
        execution_type = "context"
        script_path = None
        
        # Skill-specific keyword overrides for better detection
        skill_keywords = {
            'searxng-researcher': ['search', 'web', 'searxng', 'research', 'privacy', 'aggregated'],
            'search-email-archive': ['email', 'mail', 'archive', 'inbox'],
            'recoll-researcher': ['recoll', 'technical', 'search'],
            'daily-agenda-manager': ['agenda', 'calendar', 'meeting', 'schedule', 'today', 'tomorrow', 'daily'],
            'obsidian-rclone-saver': ['obsidian', 'save', 'export', 'note'],
            'boq-estimator': ['boq', 'bill', 'quantity', 'estimate', 'cost', 'pricing'],
            'crypto-finance-analyzer': ['crypto', 'nexo', 'cryptocurrency', 'portfolio', 'financial'],
            'loyalty-ratio-analyzer': ['loyalty', 'ratio', 'x coefficient', 'rebalancing'],
            'milestone-generator': ['milestone', 'calendar', 'ics', 'regenerate'],
            'team-manager': ['team', 'hr', 'leadership', 'coach', 'slii'],
            'technical-compliance-auditor': ['compliance', 'technical', 'fire', 'electrical', 'energy', 'e/m'],
            'content-distiller': ['content', 'distiller', 'fabric', 'summarize'],
            'high-precision-reviewer': ['review', 'precision', 'verify', 'quality', 'critique'],
        }

        lines = content.split("\n")
        
        # Parse frontmatter if present
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1]
                for line in frontmatter.split("\n"):
                    if line.startswith("description:"):
                        description = line.split(":", 1)[1].strip().strip('"').strip("'")
                    elif line.startswith("execution_type:"):
                        execution_type = line.split(":", 1)[1].strip()
                    elif line.startswith("script_path:"):
                        script_path = line.split(":", 1)[1].strip()
        
        # If no frontmatter description, try first # heading after title
        if description == "Workspace Skill":
            for i, line in enumerate(lines[1:], 1):
                line = line.strip()
                if line.startswith("# ") and "Identity" not in line and "Purpose" not in line:
                    description = line.lstrip("# ").strip()
                    break
        
        # Use predefined keywords if available, else extract from content
        if name in skill_keywords:
            keywords = skill_keywords[name]
        else:
            keywords = self._extract_keywords(description, content)

        return Skill(
            name=name,
            description=description,
            content=content,
            workspace_path=skill_path,
            keywords=keywords,
            execution_type=execution_type,
            script_path=script_path,
        )

    def _extract_keywords(self, description: str, content: str) -> List[str]:
        """Extract keywords from skill description and content."""
        keywords = set()

        # Focus on description and first few sections for better keywords
        text = f"{description} {content}".lower()

        # Extract important words
        words = re.findall(r'\b[a-zA-Zα-ωά-ώ]{4,}\b', text)
        keywords.update(words)

        # Filter out common stopwords
        stopwords = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can',
            'had', 'her', 'was', 'one', 'our', 'out', 'has', 'have', 'been',
            'would', 'could', 'there', 'their', 'what', 'about', 'which',
            'when', 'make', 'like', 'time', 'just', 'know', 'take', 'into',
            'year', 'your', 'some', 'them', 'than', 'then', 'look', 'only',
            'come', 'its', 'over', 'think', 'also', 'back', 'after', 'use',
            'two', 'how', 'first', 'being', 'other', 'these', 'give', 'day',
            'used', 'using', 'from', 'this', 'that', 'with', 'will', 'each',
            'should', 'may', 'want', 'need', 'must', 'skill', 'identity', 
            'purpose', 'tasks', 'steps', 'example', 'parameters', 'reference', 
            'configuration', 'optional', 'required', 'always', 'never',
            'execute', 'return', 'following', 'section', 'details', 'information'
        }
        
        greek_stopwords = {
            'και', 'ή', 'το', 'την', 'τον', 'της', 'των', 'στο', 'στην',
            'στον', 'με', 'για', 'από', 'σε', 'ότι', 'είναι', 'μπορεί',
            'πρέπει', 'όπως', 'ήδη', 'κάθε', 'όλα', 'όλες', 'κάποιο',
            'κάποια', 'αυτό', 'αυτή', 'αυτά', 'εκεί', 'εδώ', 'μέσα',
            'του', 'μου', 'σου', 'μας', 'τους', 'αυτών', 'όποιο'
        }

        filtered = [w for w in keywords if w not in stopwords and w not in greek_stopwords]

        # Prioritize domain-specific keywords
        priority_keywords = {'search', 'web', 'research', 'email', 'calendar', 
                           'agenda', 'schedule', 'project', 'milestone', 'construction',
                           'compliance', 'technical', 'boq', 'estimate', 'crypto',
                           'content', 'distiller', 'loyalty', 'ratio', 'review',
                           'milestone', 'generator', 'team', 'manager', 'obsidian',
                           'rclone', 'saver', 'recoll', 'searxng', 'privacy'}

        prioritized = [w for w in filtered if w in priority_keywords]
        prioritized.extend([w for w in filtered if w not in priority_keywords][:30])

        return prioritized[:50]

    def get_all_skills(self) -> List[Skill]:
        return list(self.skills_cache.values())

    def get_skill(self, name: str) -> Optional[Skill]:
        return self.skills_cache.get(name)

    def detect_skill(self, message: str) -> Optional[Skill]:
        """
        Hybrid skill detection:
        1. Exact match (skill name in message)
        2. Keyword matching with weighted scoring
        3. Return None (no skill detected)
        """
        msg_lower = message.lower()

        # 1. Exact match - skill name in message
        for name, skill in self.skills_cache.items():
            if name.lower() in msg_lower:
                logger.info(f"Exact skill match: {name}")
                return skill

        # 2. Weighted keyword matching
        scores = {}
        for name, skill in self.skills_cache.items():
            score = 0
            skill_keywords = set(skill.keywords + [skill.name.lower()])
            
            msg_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', msg_lower))
            
            for keyword in skill_keywords:
                if keyword.lower() in msg_words:
                    score += 1
                elif keyword in msg_lower:  # Partial match
                    score += 0.5
            
            if score > 0:
                scores[name] = score
        
        if scores:
            best_skill = max(scores, key=scores.get)
            if scores[best_skill] >= 1:  # Minimum threshold
                logger.info(f"Keyword match: {best_skill} (score: {scores[best_skill]})")
                return self.skills_cache[best_skill]

        return None

    async def execute_skill_script(
        self, 
        skill: Skill, 
        message: str, 
        user: str
    ) -> str:
        """Execute skill script and return output."""
        if skill.execution_type != "script":
            return ""

        if not skill.script_path:
            return f"[Error: Script path not defined for skill {skill.name}]"

        script_path = skill.script_path
        if not os.path.isabs(script_path):
            script_path = os.path.join(skill.workspace_path, script_path)

        if not os.path.exists(script_path):
            return f"[Error: Script not found: {script_path}]"

        try:
            cmd = ["python3", script_path, message, user]
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                logger.error(f"Script error: {stderr.decode()}")
                return f"[Error executing script: {stderr.decode()}]"
            
            return stdout.decode()
        except Exception as e:
            logger.error(f"Exception executing script: {e}")
            return f"[Error: {str(e)}]"

    def inject_context(
        self, 
        skill: Skill, 
        message: str, 
        script_output: Optional[str] = None
    ) -> str:
        """Inject skill context into the user message."""
        context_parts = [
            f"\n\n[SKILL ACTIVATED: {skill.name}]",
            f"Description: {skill.description}",
            f"\n{skill.content}",
        ]

        if script_output:
            context_parts.append(f"\n[SKILL OUTPUT]\n{script_output}")

        context_parts.append(f"\n[END SKILL CONTEXT]\n")

        return message + "".join(context_parts)

    def should_use_llm_routing(self, message: str) -> bool:
        """Check if message might need LLM routing (fallback for unclear cases)."""
        if self.detect_skill(message):
            return False

        routing_indicators = [
            'schedule', 'calendar', 'meeting', 'agenda', 'today', 'tomorrow',
            'search', 'research', 'web', 'find', 'look up', 'email', 'mail',
            'project', 'task', 'deadline', 'milestone', 'construction',
            'schedule', 'calendar', 'meeting', 'agenda', 'today', 'tomorrow',
            'πρόγραμμα', 'ημερολόγιο', 'συνάντηση', 'εργασία', 'σήμερα', 'αύριο',
            'email', 'έργο', 'προθεσμία', 'κατασκευή'
        ]
        
        msg_lower = message.lower()
        return any(indicator in msg_lower for indicator in routing_indicators)

    def get_llm_routing_prompt(self, message: str) -> str:
        """Generate LLM routing prompt for unclear cases."""
        skills_info = []
        for name, skill in self.skills_cache.items():
            skills_info.append(f"- {name}: {skill.description}")

        skills_str = "\n".join(skills_info) if skills_info else "No skills available."

        return f"""User message: {message}

Available skills:
{skills_str}

Should any skill be activated? Reply with:
- The skill name if a skill should be used
- "none" if no skill is needed

Reply only with the skill name or "none":"""


_skill_service_instance: Optional[SkillService] = None


def get_skill_service(workspace_root: str) -> SkillService:
    global _skill_service_instance
    if _skill_service_instance is None or _skill_service_instance.workspace_root != workspace_root:
        _skill_service_instance = SkillService(workspace_root)
    return _skill_service_instance


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

    def _get_agent_path(
        self, category: str, folder_name: str, project_root: Optional[str] = None
    ) -> str:
        base = (
            os.path.join(project_root, "data", "agents")
            if project_root
            else self.base_dir
        )
        return os.path.join(base, category, folder_name, "AGENT.md")

    def _get_root_agent_path(self, project_root: Optional[str] = None) -> str:
        return os.path.join(project_root or self.project_root, "AGENT.md")

    def list_agents(self, project_root: Optional[str] = None) -> List[AgentModel]:
        """Lists all agents by recursively scanning the base directory."""
        agents = []
        base = (
            os.path.join(project_root, "data", "agents")
            if project_root
            else self.base_dir
        )
        if not os.path.exists(base):
            return []

        pattern = os.path.join(base, "**", "AGENT.md")
        files = glob.glob(pattern, recursive=True)

        for file_path in files:
            try:
                rel_path = os.path.relpath(file_path, base)
                parts = rel_path.split(os.sep)

                if len(parts) >= 2:  # At least category/folder/AGENT.md
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

    def get_agent(
        self, category: str, folder_name: str, project_root: Optional[str] = None
    ) -> Optional[AgentModel]:
        """Reads a specific agent."""
        path = self._get_agent_path(category, folder_name, project_root)
        if not os.path.exists(path):
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return AgentModel.from_markdown(content, category, folder_name)
        except Exception as e:
            print(f"Error reading agent {category}/{folder_name}: {e}")
            return None

    def save_agent(self, agent: AgentModel, project_root: Optional[str] = None) -> bool:
        """Saves or updates an agent."""
        if ".." in agent.category or ".." in agent.folder_name:
            return False

        base = (
            os.path.join(project_root, "data", "agents")
            if project_root
            else self.base_dir
        )
        dir_path = os.path.join(base, agent.category, agent.folder_name)
        os.makedirs(dir_path, exist_ok=True)

        file_path = os.path.join(dir_path, "AGENT.md")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(agent.to_markdown())
            return True
        except Exception as e:
            print(f"Error saving agent {agent.name}: {e}")
            return False

    def delete_agent(
        self, category: str, folder_name: str, project_root: Optional[str] = None
    ) -> bool:
        """Deletes an agent folder."""
        if ".." in category or ".." in folder_name:
            return False

        base = (
            os.path.join(project_root, "data", "agents")
            if project_root
            else self.base_dir
        )
        dir_path = os.path.join(base, category, folder_name)
        if os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
                cat_path = os.path.join(base, category)
                if os.path.exists(cat_path) and not os.listdir(cat_path):
                    os.rmdir(cat_path)
                return True
            except Exception as e:
                print(f"Error deleting agent {category}/{folder_name}: {e}")
                return False
        return False

    def get_root_orchestrator(
        self, project_root: Optional[str] = None
    ) -> Optional[AgentModel]:
        """Reads the root AGENT.md file."""
        path = self._get_root_agent_path(project_root)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return AgentModel.from_markdown(content, "root", "root")
        except Exception as e:
            print(f"Error reading root orchestrator: {e}")
            return None

    def save_root_orchestrator(
        self, agent: AgentModel, project_root: Optional[str] = None
    ) -> bool:
        """Saves the root AGENT.md file."""
        path = self._get_root_agent_path(project_root)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(agent.to_markdown())
            return True
        except Exception as e:
            print(f"Error saving root orchestrator: {e}")
            return False

    def initialize_root_orchestrator(self, project_root: Optional[str] = None):
        """Creates a default root AGENT.md if it doesn't exist."""
        path = self._get_root_agent_path(project_root)
        if not os.path.exists(path):
            root_agent = AgentModel(
                name="Root Orchestrator",
                description="The central AI agent that manages sub-agents.",
                category="root",
                folder_name="root",
                type="Orchestrator",
                prompt="You are the Root Orchestrator. You manage several sub-agents to fulfill user requests.",
            )
            self.save_root_orchestrator(root_agent, project_root)

    def set_agent_enabled(
        self,
        category: str,
        folder_name: str,
        enabled: bool,
        project_root: Optional[str] = None,
    ) -> bool:
        """Links or unlinks a sub-agent to the root orchestrator."""
        root = self.get_root_orchestrator(project_root)
        if not root:
            self.initialize_root_orchestrator(project_root)
            root = self.get_root_orchestrator(project_root)

        if not root:
            return False

        agent = self.get_agent(category, folder_name, project_root)
        if not agent:
            return False

        agent_abs_path = self._get_agent_path(category, folder_name, project_root)
        effective_root = project_root or self.project_root
        agent_rel_path = os.path.relpath(agent_abs_path, effective_root).replace(
            os.sep, "/"
        )

        root_rel_path = "AGENT.md"

        # Helper to find link by path
        def find_link_index(links: List[AgentLink], path: str):
            for i, link in enumerate(links):
                if link.path == path:
                    return i
            return -1

        if enabled:
            # Link TO root
            if find_link_index(root.children, agent_rel_path) == -1:
                root.children.append(
                    AgentLink(path=agent_rel_path, description=agent.description)
                )
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

        success_root = self.save_root_orchestrator(root, project_root)
        success_agent = self.save_agent(agent, project_root)

        return success_root and success_agent

    def validate_orchestration(self, project_root: Optional[str] = None) -> List[str]:
        """Validates that all enabled agents are referenced in the root prompt."""
        root = self.get_root_orchestrator(project_root)
        if not root:
            return []

        warnings = []
        effective_root = project_root or self.project_root
        base = (
            os.path.join(project_root, "data", "agents")
            if project_root
            else self.base_dir
        )

        for child_link in root.children:
            child_path = child_link.path
            full_path = os.path.join(effective_root, child_path)
            if not os.path.exists(full_path):
                warnings.append(f"Referenced agent at {child_path} does not exist.")
                continue

            try:
                rel_to_base = os.path.relpath(full_path, base)
                parts = rel_to_base.split(os.sep)
                if len(parts) >= 2:
                    category = parts[0]
                    folder_name = parts[1]
                    child_agent = self.get_agent(category, folder_name, project_root)
                    if child_agent:
                        if (
                            child_agent.name not in root.prompt
                            and child_agent.folder_name not in root.prompt
                            and child_path not in root.prompt
                        ):
                            warnings.append(
                                f"Agent '{child_agent.name}' is enabled but not referenced in the Orchestrator's prompt."
                            )
            except Exception:
                continue

        return warnings

    def initialize_defaults(self, project_root: Optional[str] = None):
        """Initializes default agents if they don't exist."""
        fabric_path = self._get_agent_path("functions", "fabric", project_root)
        if not os.path.exists(fabric_path):
            fabric_agent = AgentModel(
                name="Fabric Agent",
                description="Bridge to Fabric patterns and prompts.",
                category="functions",
                folder_name="fabric",
                prompt="You are a Fabric orchestrator. You can use any of the available patterns to process input.",
            )
            self.save_agent(fabric_agent, project_root)

        self.initialize_root_orchestrator(project_root)


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




async def get_user(request: Request):
    return request.session.get("user")


@chat_router.get("/", response_class=HTMLResponse)
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


@chat_router.get("/settings")
async def get_settings(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    return agent.get_user_settings(user)


@chat_router.post("/settings")
async def update_settings(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    data = await request.json()
    agent.update_user_settings(user, data)
    return {"success": True}


@chat_router.get("/sessions")
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


@chat_router.get("/sessions/search")
async def search_sess(request: Request, q: str = "", user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    return await agent.search_sessions(user, q)


@chat_router.get("/sessions/{session_uuid}/messages")
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


@chat_router.post("/sessions/switch")
async def sw_sess(
    request: Request, session_uuid: str = Form(...), user=Depends(get_user)
):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    return {"success": await agent.switch_session(user, session_uuid)}


@chat_router.post("/sessions/new")
async def nw_sess(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    await agent.new_session(user)
    return {"success": True}


@chat_router.post("/sessions/delete")
async def dl_sess(
    request: Request, session_uuid: str = Form(...), user=Depends(get_user)
):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    return {"success": await agent.delete_specific_session(user, session_uuid)}


@chat_router.post("/sessions/{session_uuid}/share")
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


@chat_router.post("/sessions/{session_uuid}/pin")
async def pin_sess(session_uuid: str, request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    # Security: check if this session belongs to the user
    if not agent.is_user_session(user, session_uuid):
        raise HTTPException(403, "Access denied")
    return {"pinned": agent.toggle_pin(user, session_uuid)}


@chat_router.post("/sessions/{session_uuid}/clone")
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


@chat_router.get("/sessions/{session_uuid}/forks")
async def get_forks(session_uuid: str, request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    return {"forks": agent.get_session_forks(user, session_uuid)}


@chat_router.get("/sessions/fork-graph")
async def get_fork_graph(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    return {"graph": agent.get_fork_graph(user)}


@chat_router.post("/sessions/{session_uuid}/title")
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


@chat_router.get("/sessions/tags")
async def get_all_tags(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    return {"tags": agent.get_unique_tags(user)}


@chat_router.post("/sessions/{session_uuid}/tags")
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


@chat_router.get("/sessions/{session_uuid}/tools")
async def get_sess_tools(session_uuid: str, request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    if session_uuid != "pending":
        if not agent.is_user_session(user, session_uuid):
            raise HTTPException(403, "Access denied")
    return {"tools": agent.get_session_tools(user, session_uuid)}


@chat_router.post("/sessions/{session_uuid}/tools")
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


@chat_router.get("/patterns")
async def get_pats(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)

    workspace = await get_effective_workspace(agent, user)

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


@chat_router.get("/prompts/{filename}")
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


@chat_router.delete("/prompts/{filename}")
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


@chat_router.put("/prompts/{filename}")
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


@chat_router.post("/prompts/new")
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


@chat_router.post("/chat")
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
            if LOG_LEVEL == "NONE":
                return
            if LOG_LEVEL == "INFO" and level == "DEBUG":
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


@chat_router.post("/stop")
async def stop_chat(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    success = await agent.stop_chat(user)
    return {"success": success}


@chat_router.post("/reset")
async def reset(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    return {"response": await agent.reset_chat(user)}


@chat_router.get("/workspaces")
async def get_workspaces(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)

    return {"workspaces": agent.get_available_workspaces(), "root": WORKSPACE_ROOT}


@chat_router.post("/session/workspace")
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


@chat_router.get("/session/workspace/{uuid}")
async def get_session_workspace_path(
    uuid: str, request: Request, user=Depends(get_user)
):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    return {"path": agent.get_session_workspace(user, uuid)}


@chat_router.get("/session/git-status")
async def get_git_status(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    
    workspace = await get_effective_workspace(agent, user)
    return await agent.get_git_status(workspace)


@chat_router.get("/models")
async def get_models(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    return {"models": await agent.get_available_models()}


@chat_router.get("/agents")
async def get_agents(request: Request, user=Depends(get_user)):
    agent = request.app.state.agent
    if not user:
        raise HTTPException(401)
    return {"agents": await agent.get_available_agents()}


admin_router = APIRouter()
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional

import subprocess
import json
import re
import shutil
import os
from pathlib import Path

ACCOUNTS_FILE = Path.home() / ".config" / "opencode" / "antigravity-accounts.json"




async def get_user(request: Request):
    return request.session.get("user")


def run_opencode_mcp_command(args):
    cmd = [shutil.which(OPENCODE_CMD) or OPENCODE_CMD, "mcp"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"
    except Exception as e:
        return f"Error: {str(e)}"


@admin_router.get("/admin/mcp")
async def list_mcp(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    output = run_opencode_mcp_command(["list"])
    if not output:
        return []
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

    full_args = ["add", name, command] + (
        args if isinstance(args, list) else args.split()
    )
    output = run_opencode_mcp_command(full_args)
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

    output = run_opencode_mcp_command(["remove", name])
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
    output = run_opencode_mcp_command([cmd, name])
    return {"success": "Error" not in output, "output": output}


@admin_router.get("/admin/accounts")
async def list_accounts(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    if not ACCOUNTS_FILE.exists():
        return {"accounts": [], "error": "No accounts file found"}

    try:
        with open(ACCOUNTS_FILE, "r") as f:
            data = json.load(f)

        accounts = []
        for acc in data.get("accounts", []):
            quota = acc.get("cachedQuota", {})
            accounts.append({
                "email": acc.get("email"),
                "enabled": acc.get("enabled", True),
                "lastUsed": acc.get("lastUsed"),
                "models": {
                    model: {
                        "remainingFraction": info.get("remainingFraction", 0),
                        "resetTime": info.get("resetTime"),
                        "modelCount": info.get("modelCount", 0),
                    }
                    for model, info in quota.items()
                }
            })

        return {"accounts": accounts}
    except Exception as e:
        return {"accounts": [], "error": str(e)}


# Agent Management Routes


@admin_router.get("/admin/agents")
async def list_agents(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    agent_manager = request.app.state.agent_manager
    agent = request.app.state.agent
    workspace = await get_effective_workspace(agent, user)
    agents = agent_manager.list_agents(project_root=workspace)
    return agents


@admin_router.get("/admin/agents/{category}/{name}")
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


@admin_router.post("/admin/agents")
async def save_agent(request: Request, agent_data: AgentModel, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    agent_manager = request.app.state.agent_manager
    agent = request.app.state.agent
    workspace = await get_effective_workspace(agent, user)
    success = agent_manager.save_agent(agent_data, project_root=workspace)
    return {"success": success}


@admin_router.get("/admin/agents/root")
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


@admin_router.post("/admin/agents/root")
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


@admin_router.delete("/admin/agents/{category}/{name}")
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


@admin_router.post("/admin/agents/{category}/{name}/toggle-enabled")
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


@admin_router.get("/admin/agents/validate")
async def validate_orchestration(request: Request, user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    agent_manager = request.app.state.agent_manager
    agent = request.app.state.agent
    workspace = await get_effective_workspace(agent, user)
    warnings = agent_manager.validate_orchestration(project_root=workspace)
    return {"warnings": warnings}


@admin_router.get("/admin/skills")
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


@admin_router.get("/admin/skills/{name}")
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


@admin_router.post("/admin/skills")
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


@admin_router.delete("/admin/skills/{name}")
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


@admin_router.post("/admin/patterns/sync")
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


@admin_router.post("/admin/tags/clear")
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
    if user_manager.get_role(user) != "admin":
        return RedirectResponse("/")
    return request.app.state.render(
        "admin.html",
        request=request,
        user=user,
        users=user_manager.get_all_users(),
        log_level=LOG_LEVEL,
    )


@admin_router.post("/admin/user/add")
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


@admin_router.post("/admin/user/remove")
async def adm_rem(request: Request, username: str = Form(...), user=Depends(get_user)):
    user_manager = request.app.state.user_manager
    if user_manager.get_role(user) == "admin" and username != "admin":
        user_manager.remove_user(username)
    return {"success": True}


@admin_router.post("/admin/user/toggle-pattern")
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


@admin_router.post("/admin/user/toggle-role")
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


@admin_router.post("/admin/user/update-password")
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


# --- MAIN ---
import os
import sys
import asyncio
import mimetypes
from fastapi import FastAPI, Request

# Set Windows Event Loop Policy for subprocess support
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Register WebP MIME type if not present
mimetypes.add_type("image/webp", ".webp")

from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from jinja2 import Environment, FileSystemLoader

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Verify/Force ProactorEventLoop on Windows at runtime
    if sys.platform == "win32":
        loop = asyncio.get_running_loop()
        from asyncio import ProactorEventLoop

        if not isinstance(loop, ProactorEventLoop):
            # We can't easily swap the loop if it's already running,
            # but we can log it for debugging.
            print(
                f"WARNING: Running on {type(loop).__name__}, but ProactorEventLoop is required for subprocesses."
            )
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
    session_cookie="opencode_session",
    same_site="lax",
    https_only=https_only,
)


# Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        if https_only:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

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
auth_service = AuthService(
    RP_ID or "localhost",
    RP_NAME,
    ORIGIN or "http://localhost:8000",
)
agent = OpenCodeAgent()
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

    parser = argparse.ArgumentParser(description="Run the OpenCode Agent")
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to run the service on"
    )
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)