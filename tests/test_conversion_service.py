import pytest
import os
from app.services.conversion_service import FileConversionService

@pytest.fixture
def conversion_service():
    return FileConversionService()

def test_convert_docx_to_md_success(conversion_service):
    # Use the existing docx file for testing
    docx_path = os.path.join("tmp", "user_attachments", "Τεχνική_περιγραφή (2).docx")
    if not os.path.exists(docx_path):
        pytest.skip(f"Test file {docx_path} not found")
    
    md_path = conversion_service.convert_to_markdown(docx_path)
    
    assert md_path.endswith(".md")
    assert os.path.exists(md_path)
    
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert len(content) > 0
        # Check that it doesn't contain image references if possible
        # This depends on how pandoc handles it, but usually it leaves empty refs or nothing
    
    # Cleanup
    if os.path.exists(md_path):
        os.remove(md_path)

def test_convert_xlsx_to_md_success(conversion_service):
    # Use the provided xlsx file for testing
    xlsx_path = os.path.join("tmp", "user_attachments", "ΑΕΔ ΞΑΝΘΗ.xlsx")
    if not os.path.exists(xlsx_path):
        pytest.skip(f"Test file {xlsx_path} not found")
    
    md_path = conversion_service.convert_to_markdown(xlsx_path)
    
    assert md_path.endswith(".md")
    assert os.path.exists(md_path)
    
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert len(content) > 0
        # XLSX conversion often produces markdown tables
    
    # Cleanup
    if os.path.exists(md_path):
        os.remove(md_path)

def test_convert_invalid_extension(conversion_service):
    with pytest.raises(ValueError, match="Unsupported file extension"):
        conversion_service.convert_to_markdown("test.txt")

def test_convert_non_existent_file(conversion_service):
    with pytest.raises(FileNotFoundError):
        conversion_service.convert_to_markdown("non_existent.docx")
