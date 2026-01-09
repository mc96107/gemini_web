import os

def test_setup_py_sh_no_venv():
    with open("setup_py.sh", "r") as f:
        content = f.read()
    
    assert "venv_release" not in content, "setup_py.sh should not reference venv_release"
    assert "VENV_PYTHON" not in content, "setup_py.sh should not use VENV_PYTHON"
    assert "python" in content, "setup_py.sh should use global python"

def test_setup_py_sh_installs_deps():
    with open("setup_py.sh", "r") as f:
        content = f.read()
    
    # Check if it at least tries to install dependencies
    assert "pip install" in content, "setup_py.sh should install dependencies"
    
    deps = [
        "python-dotenv", "fastapi", "uvicorn", "python-multipart",
        "jinja2", "bcrypt", "itsdangerous", "eth-account", "webauthn", "httpx"
    ]
    for dep in deps:
        assert dep in content, f"setup_py.sh should install {dep}"
