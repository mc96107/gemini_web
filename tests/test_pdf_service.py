import pytest
import os
import shutil
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.pdf_service import PDFService

@pytest.fixture
def pdf_service():
    return PDFService()

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
    
    # We need to simulate that the output file is created by GS
    output_file = tmp_path / "test_compressed.pdf"
    
    with patch("shutil.which", return_value="gs"), \
         patch("asyncio.create_subprocess_exec") as mock_exec, \
         patch("os.path.getsize") as mock_size:
        
        pdf_service = PDFService()
        
        # Mock subprocess
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"stdout", b"stderr")
        mock_process.returncode = 0
        mock_exec.return_value = mock_process
        
        # Mock sizes to show reduction
        mock_size.side_effect = lambda path: 100 if "compressed" in str(path) else 200
        
        # Simulate GS creating the file
        output_file.write_bytes(b"compressed content")
        
        result_path = await pdf_service.compress_pdf(str(input_file), str(output_file))
        
        assert result_path == str(output_file)
        assert mock_exec.called
        # Check if ebook preset was used
        args = mock_exec.call_args[0]
        assert "-dPDFSETTINGS=/ebook" in args

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
    # If compressed file is larger, it should return the original
    input_file = tmp_path / "test.pdf"
    input_file.write_bytes(b"original content")
    output_file = tmp_path / "test_compressed.pdf"
    output_file.write_bytes(b"larger content")
    
    with patch("shutil.which", return_value="gs"), \
         patch("asyncio.create_subprocess_exec") as mock_exec, \
         patch("os.path.getsize") as mock_size:
        
        pdf_service = PDFService()
        
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_exec.return_value = mock_process
        
        # Mock sizes: original 100, "compressed" 120
        mock_size.side_effect = lambda path: 120 if "compressed" in str(path) else 100
        
        result_path = await pdf_service.compress_pdf(str(input_file), str(output_file))
        
        assert result_path == str(input_file)
        # Should have cleaned up the larger file
        assert not os.path.exists(str(output_file))

@pytest.mark.asyncio
async def test_compress_pdf_input_not_found(tmp_path):
    pdf_service = PDFService()
    # Mock GS availability to pass initial check
    pdf_service.gs_path = "gs"
    
    result_path = await pdf_service.compress_pdf("non_existent.pdf", "out.pdf")
    assert result_path == "non_existent.pdf"

@pytest.mark.asyncio
async def test_compress_pdf_gs_error(tmp_path):
    input_file = tmp_path / "test.pdf"
    input_file.write_bytes(b"original content")
    output_file = tmp_path / "test_compressed.pdf"
    
    with patch("shutil.which", return_value="gs"), \
         patch("asyncio.create_subprocess_exec") as mock_exec:
        
        pdf_service = PDFService()
        
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"error message")
        mock_process.returncode = 1
        mock_exec.return_value = mock_process
        
        result_path = await pdf_service.compress_pdf(str(input_file), str(output_file))
        assert result_path == str(input_file)