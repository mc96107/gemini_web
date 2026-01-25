import pytest
import os
import shutil
import re
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_pdf_upload_integration(client, tmp_path):
    # Setup mock for PDFService
    mock_pdf_service = MagicMock()
    # compress_pdf is async, so it must return a coroutine or be an AsyncMock
    mock_pdf_service.compress_pdf = AsyncMock(side_effect=lambda in_p, out_p: in_p)
    
    # Create a dummy PDF
    dummy_pdf = tmp_path / "test_upload.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4 dummy content")
    
    # Mock authentication using dependency_overrides
    from app.routers.chat import get_user
    app.dependency_overrides[get_user] = lambda: "testuser"
    
    try:
        # We need to mock the state.pdf_service in the app
        with patch.object(app.state, 'pdf_service', mock_pdf_service):
            with open(dummy_pdf, "rb") as f:
                response = client.post(
                    "/chat",
                    data={"message": "hello"},
                    files={"file": ("test_upload.pdf", f, "application/pdf")}
                )
            
            assert mock_pdf_service.compress_pdf.called
            call_args = mock_pdf_service.compress_pdf.call_args
            # input_path should be in the UPLOAD_DIR
            assert "test_upload.pdf" in call_args[0][0]
    finally:
        # Clean up overrides
        app.dependency_overrides = {}

def test_pdf_upload_greek_filename(client, tmp_path):
    # Setup mock for PDFService
    mock_pdf_service = MagicMock()
    mock_pdf_service.compress_pdf = AsyncMock(side_effect=lambda in_p, out_p: in_p)
    
    # Create a dummy PDF with Greek name
    filename = "CC ΧΙΟΣ.pdf"
    dummy_pdf = tmp_path / filename
    dummy_pdf.write_bytes(b"%PDF-1.4 dummy content")
    
    from app.routers.chat import get_user
    app.dependency_overrides[get_user] = lambda: "testuser"
    
    try:
        with patch.object(app.state, 'pdf_service', mock_pdf_service):
            # We open with the Greek filename
            with open(dummy_pdf, "rb") as f:
                response = client.post(
                    "/chat",
                    data={"message": "hello"},
                    files={"file": (filename, f, "application/pdf")}
                )
            
            assert mock_pdf_service.compress_pdf.called
            call_args = mock_pdf_service.compress_pdf.call_args
            called_path = call_args[0][0]
            
            # CRITICAL: The path passed to compress_pdf should be SAFE (ASCII only)
            # It should NOT contain the Greek characters
            assert "CC ΧΙΟΣ.pdf" not in called_path
            # It should likely be something sanitized like "CC____.pdf" or "CC_XIOS.pdf" or UUID
            # For now, just asserting it's NOT the original unsafe name
            
    finally:
        app.dependency_overrides = {}