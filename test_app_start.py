import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from app.main import app
    print("App initialized successfully.")
except Exception as e:
    print(f"Error initializing app: {e}")
    import traceback
    traceback.print_exc()
