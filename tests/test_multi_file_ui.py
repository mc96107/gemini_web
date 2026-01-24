from bs4 import BeautifulSoup
import os

def test_index_html_multi_file_support():
    """Verify index.html has multiple attribute and drag-and-drop area."""
    template_path = "app/templates/index.html"
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()
    
    soup = BeautifulSoup(html, "html.parser")
    
    # Check for multiple attribute on file upload
    file_input = soup.find("input", {"id": "file-upload"})
    assert file_input is not None, "File upload input not found"
    assert file_input.has_attr("multiple"), "File upload input missing 'multiple' attribute"
    
    # Check for drag-and-drop overlay
    # This might be a div with a specific ID we plan to add
    drop_zone = soup.find("div", {"id": "drag-drop-overlay"})
    assert drop_zone is not None, "Drag-and-drop overlay div not found"

def test_index_html_attachment_queue():
    """Verify index.html has a container for multiple attachments."""
    template_path = "app/templates/index.html"
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()
    
    soup = BeautifulSoup(html, "html.parser")
    
    # We should have a container to hold multiple attachment items
    queue_container = soup.find("div", {"id": "attachment-queue"})
    assert queue_container is not None, "Attachment queue container not found"
