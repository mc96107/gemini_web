import os
import shutil
import pytest
from app.main import app
from app.core import config

def test_fabric_agent_initialization():
    # Verify that the fabric agent is created on app startup
    fabric_path = os.path.join(config.AGENT_BASE_DIR, "functions", "fabric", "AGENT.md")
    assert os.path.exists(fabric_path)
    
    with open(fabric_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    assert "Fabric Agent" in content
    assert "Fabric orchestrator" in content
