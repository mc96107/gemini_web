import pytest
from app.services.user_manager import UserManager
from app.services.auth_service import AuthService
from app.services.llm_service import OpenCodeAgent
import os


def test_user_manager_init(tmp_path):
    # Use tmp_path for isolated testing
    um = UserManager(working_dir=str(tmp_path))
    assert len(um.users) == 0


def test_auth_service_init():
    auth = AuthService("example.com", "Test App", "https://example.com")
    assert auth.rp_id == "example.com"


def test_llm_service_init(tmp_path):
    agent = OpenCodeAgent(working_dir=str(tmp_path))
    assert agent.model_name in ["google/gemini-2.5-flash", "google/antigravity-gemini-3.1-pro"]
