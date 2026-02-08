import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core import config

client = TestClient(app)

def test_path_traversal_vulnerability():
    """
    Test that path traversal sequences are NOT allowed.
    Accessing a file outside UPLOAD_DIR should return 404 (sanitized name not found)
    or at least NOT return the sensitive file.
    Currently, this test is EXPECTED TO FAIL (it will likely return 200 and the settings file).
    """
    # Ensure settings file exists for the test
    if not os.path.exists(config.SETTINGS_FILE):
        os.makedirs(os.path.dirname(config.SETTINGS_FILE), exist_ok=True)
        with open(config.SETTINGS_FILE, "w") as f:
            f.write('{"test": "secret"}')

    # Path traversal attempt
    # From UPLOAD_DIR (tmp/user_attachments), we go up twice to root, then into data/settings.json
    traversal_path = "../../data/settings.json"
    
    response = client.get(f"/uploads/{traversal_path}")
    print(f"DEBUG: status={response.status_code}, text={response.text}")
    
    # After fix, this should be 404 because "settings.json" doesn't exist in UPLOAD_DIR
    # BEFORE fix, this will likely be 200
    assert response.status_code == 404

def test_encoded_path_traversal_vulnerability():
    """
    Test that URL-encoded path traversal sequences are NOT allowed.
    """
    # Encoded "../../data/settings.json"
    # . is %2e, / is %2f
    encoded_path = "%2e%2e%2f%2e%2e%2fdata/settings.json"
    
    response = client.get(f"/uploads/{encoded_path}")
    
    assert response.status_code == 404

def test_one_level_traversal():
    """
    Test that one-level traversal (../) is NOT allowed.
    """
    # secret file in tmp/ (parent of UPLOAD_DIR)
    
    response = client.get("/uploads/../secret.txt")
    print(f"DEBUG one_level: status={response.status_code}, text={response.text}")
    assert response.status_code == 404

def test_valid_file_retrieval():
    """
    Ensure valid file retrieval still works.
    """
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    test_file = os.path.join(config.UPLOAD_DIR, "valid_test.txt")
    with open(test_file, "w") as f:
        f.write("valid content")
    
    try:
        response = client.get("/uploads/valid_test.txt")
        assert response.status_code == 200
        assert response.text == "valid content"
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)
