import os
import importlib
from app.core import config

def test_config_env_loading(monkeypatch):
    # Set environment variables
    monkeypatch.setenv("RP_ID", "test.local")
    monkeypatch.setenv("ORIGIN", "https://test.local")
    monkeypatch.setenv("SESSION_SECRET", "test_secret_123")
    
    # Reload config module to pick up changes
    importlib.reload(config)
    
    assert config.RP_ID == "test.local"
    assert config.ORIGIN == "https://test.local"
    assert config.SESSION_SECRET == "test_secret_123"
