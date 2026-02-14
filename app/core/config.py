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