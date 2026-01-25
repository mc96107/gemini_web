import pytest
import os
import shutil
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
            
            print(f"DEBUG: Response status: {response.status_code}")
            print(f"DEBUG: Response body: {response.text[:200]}")
            
            # The chat route returns a response for non-AJAX or an error if streaming fails
            # But here we just want to see if compress_pdf was called
            assert mock_pdf_service.compress_pdf.called
            call_args = mock_pdf_service.compress_pdf.call_args
            # input_path should be in the UPLOAD_DIR
            assert "test_upload.pdf" in call_args[0][0]
    finally:
        # Clean up overrides
        app.dependency_overrides = {}
