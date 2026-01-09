import os

def test_readme_exists():
    assert os.path.exists("README.md")

def test_readme_content():
    with open("README.md", "r") as f:
        content = f.read()
    assert "Fabric" in content
    assert "Termux" in content
    assert "Gemini CLI" in content
    assert "Conductor" in content
    assert "recombine.py" in content
