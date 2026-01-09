import os
import subprocess
import sys

def test_recombine_script_exists():
    assert os.path.exists("scripts/recombine.py")

def test_recombine_execution():
    # Remove old release file if exists
    if os.path.exists("gemini_agent_release.py"):
        os.remove("gemini_agent_release.py")
    
    # Run script
    result = subprocess.run([sys.executable, "scripts/recombine.py"], capture_output=True, text=True)
    assert result.returncode == 0
    assert os.path.exists("gemini_agent_release.py")
    
    # Check syntax of output
    result_syntax = subprocess.run([sys.executable, "-m", "py_compile", "gemini_agent_release.py"], capture_output=True, text=True)
    assert result_syntax.returncode == 0
