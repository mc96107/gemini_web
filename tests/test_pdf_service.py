import pytest
import os
import shutil
import subprocess
from unittest.mock import MagicMock, patch
from app.services.pdf_service import PDFService

@pytest.mark.asyncio
async def test_ghostscript_detection():
    with patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/bin/gs"
        service = PDFService()
        assert service.is_gs_available() is True
        
        mock_which.return_value = None
        service = PDFService()
        assert service.is_gs_available() is False

@pytest.mark.asyncio
async def test_compress_pdf_success(tmp_path):
    # Setup mock files
    input_file = tmp_path / "test.pdf"
    input_file.write_bytes(b"original content")
    
    output_file = tmp_path / "test_compressed.pdf"
    
    # Predictable UUID for temp files
    fake_uuid = MagicMock()
    fake_uuid.hex = "fake_uuid"
    
    with patch("shutil.which", return_value="gs"), \
         patch("subprocess.run") as mock_run, \
         patch("os.path.getsize") as mock_size, \
         patch("uuid.uuid4", return_value=fake_uuid):
        
        pdf_service = PDFService()
        
        # Mock subprocess result
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        # Determine the temp output path that the service will expect
        temp_out = tmp_path / "gs_out_fake_uuid.pdf"
        temp_out.write_bytes(b"compressed content")
        
        # Mock sizes to show reduction
        def get_size(path):
            if str(path) == str(input_file): return 200
            if "gs_out_" in str(path): return 100
            if str(path) == str(output_file): return 100
            return 0
        mock_size.side_effect = get_size
        
        result_path = await pdf_service.compress_pdf(str(input_file), str(output_file))
        
        assert result_path == str(output_file)
        assert mock_run.called
        # Verify result content (should have been moved from temp_out)
        assert output_file.read_bytes() == b"compressed content"

@pytest.mark.asyncio
async def test_compress_pdf_no_gs(tmp_path):
    input_file = tmp_path / "test.pdf"
    input_file.write_bytes(b"original content")
    output_file = tmp_path / "test_compressed.pdf"
    
    with patch("shutil.which", return_value=None):
        pdf_service = PDFService()
        result_path = await pdf_service.compress_pdf(str(input_file), str(output_file))
        # Should return original path as fallback
        assert result_path == str(input_file)

@pytest.mark.asyncio
async def test_compress_pdf_larger_result(tmp_path):
    input_file = tmp_path / "test.pdf"
    input_file.write_bytes(b"original content")
    output_file = tmp_path / "test_compressed.pdf"
    
    fake_uuid = MagicMock()
    fake_uuid.hex = "fake_uuid"
    
    with patch("shutil.which", return_value="gs"), \
         patch("subprocess.run") as mock_run, \
         patch("os.path.getsize") as mock_size, \
         patch("uuid.uuid4", return_value=fake_uuid):
        
        pdf_service = PDFService()
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        temp_out = tmp_path / "gs_out_fake_uuid.pdf"
        temp_out.write_bytes(b"larger content")
        
        # Mock sizes: original 100, "compressed" 120
        def get_size(path):
            if str(path) == str(input_file): return 100
            if "gs_out_" in str(path): return 120
            return 0
        mock_size.side_effect = get_size
        
        result_path = await pdf_service.compress_pdf(str(input_file), str(output_file))
        
        assert result_path == str(input_file)
        # Should have cleaned up the larger file (temp out)
        assert not os.path.exists(str(temp_out))
        # Output file should not exist
        assert not os.path.exists(str(output_file))

@pytest.mark.asyncio
async def test_compress_pdf_gs_error(tmp_path):
    input_file = tmp_path / "test.pdf"
    input_file.write_bytes(b"original content")
    output_file = tmp_path / "test_compressed.pdf"
    
    fake_uuid = MagicMock()
    fake_uuid.hex = "fake_uuid"
    
    with patch("shutil.which", return_value="gs"), \
         patch("subprocess.run") as mock_run, \
         patch("uuid.uuid4", return_value=fake_uuid):
        
        pdf_service = PDFService()
        
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = b"error message"
        mock_run.return_value = mock_result
        
        result_path = await pdf_service.compress_pdf(str(input_file), str(output_file))
        assert result_path == str(input_file)