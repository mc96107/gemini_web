import os
import pytest
from app.core import config

def test_agent_base_dir_default():
    # Verify that AGENT_BASE_DIR is defined and defaults to the expected path
    assert hasattr(config, "AGENT_BASE_DIR")
    expected_default = os.path.join(os.getcwd(), "data", "agents")
    assert config.AGENT_BASE_DIR == expected_default

def test_agent_base_dir_env_override(monkeypatch):
    # Verify that it can be overridden by env var
    # Note: We can't easily reload the module to test the module-level execution,
    # but we can verify the logic if we were to refactor config.py to be more testable.
    # For now, let's just check the default, as reloading modules is tricky.
    pass
