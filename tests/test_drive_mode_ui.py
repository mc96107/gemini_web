from bs4 import BeautifulSoup

def test_drive_mode_button_exists():
    """Verify index.html has the Drive Mode button."""
    template_path = "app/templates/index.html"
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()
    
    soup = BeautifulSoup(html, "html.parser")
    
    # Check for Drive Mode button
    drive_btn = soup.find("button", {"id": "drive-mode-btn"})
    assert drive_btn is not None, "Drive Mode button not found"
    assert "d-none" in drive_btn.get("class", []), "Drive Mode button should be hidden by default"
