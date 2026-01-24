import os
import sys
import subprocess
import venv
import shutil

def run_command(args, cwd=None):
    """Run command as a list of arguments."""
    print(f"Executing: {' '.join(args)}")
    subprocess.check_call(args, cwd=cwd)

def setup():
    app_file = "gemini_agent_release.py"
    
    # ALWAYS Regenerate bundle
    print(f"Regenerating {app_file}...")
    try:
        import scripts.recombine
        scripts.recombine.recombine()
    except ImportError:
        # Fallback to shell if import fails
        run_command([sys.executable, "scripts/recombine.py"])

    # 1. Create virtual environment
    venv_dir = "venv_release"
    if os.path.exists(venv_dir):
        print(f"Removing existing virtual environment in {venv_dir}...")
        shutil.rmtree(venv_dir)
        
    print(f"Creating virtual environment in {venv_dir}...")
    try:
        # We start without pip and use ensurepip for better reliability
        venv.create(venv_dir, with_pip=False)
    except Exception as e:
        print(f"Error creating virtual environment: {e}")
        return

    # 2. Determine python path
    if sys.platform == "win32":
        python_path = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        python_path = os.path.join(venv_dir, "bin", "python")

    if not os.path.exists(python_path):
        print(f"Error: Python not found at {python_path}.")
        return

    # 3. Ensure Pip is installed and working
    print("Ensuring pip is installed...")
    try:
        run_command([python_path, "-m", "ensurepip", "--upgrade"])
    except subprocess.CalledProcessError:
        print("Failed to ensure pip. Trying fallback...")
        # Sometimes ensurepip is not available, but usually it is in standard python
        pass

    # 4. Install dependencies
    deps = [
        "python-dotenv", "fastapi", "uvicorn", "python-multipart",
        "jinja2", "bcrypt", "itsdangerous", "eth-account", "webauthn", "httpx",
        "pypandoc", "pandas", "openpyxl", "tabulate"
    ]
    
    print("Installing dependencies...")
    try:
        run_command([python_path, "-m", "pip", "install", "--upgrade", "pip"])
        run_command([python_path, "-m", "pip", "install"] + deps)
    except subprocess.CalledProcessError as e:
        print(f"Error during installation: {e}")
        return

    print("\n" + "="*40)
    print("Setup complete!")
    print(f"Single-file app: {app_file}")
    print(f"Environment:    {venv_dir}")
    print(f"To run manually: {python_path} {app_file}")
    print("="*40)
    
    try:
        start = input("\nDo you want to start the app now? (y/n): ")
        if start.lower() == 'y':
            try:
                run_command([python_path, app_file])
            except KeyboardInterrupt:
                print("\nApp stopped.")
            except Exception as e:
                print(f"Error running app: {e}")
    except (EOFError, KeyboardInterrupt):
        pass

if __name__ == "__main__":
    setup()