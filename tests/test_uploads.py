import os
from fastapi.testclient import TestClient
from app.main import app
from app.core import config

client = TestClient(app)

def test_serve_uploads():
    # Ensure UPLOAD_DIR exists
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    
    # Create a dummy file
    test_file = os.path.join(config.UPLOAD_DIR, "test_image.txt")
    with open(test_file, "w") as f:
        f.write("dummy image data")
    
    try:
        response = client.get("/uploads/test_image.txt")
        # This is expected to fail (404) before implementation
        assert response.status_code == 200
        assert response.text == "dummy image data"
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)

def test_webp_mime_type():
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    test_file = os.path.join(config.UPLOAD_DIR, "test.webp")
    with open(test_file, "wb") as f:
        f.write(b"RIFF....WEBPVP8X")
    
    try:
        response = client.get("/uploads/test.webp")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/webp"
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)
