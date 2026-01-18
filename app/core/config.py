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
LOG_LEVEL = os.getenv("LOG_LEVEL", "NONE").upper()

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