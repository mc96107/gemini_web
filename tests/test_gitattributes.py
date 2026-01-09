import os

def test_gitattributes_exists():
    assert os.path.exists(".gitattributes")

def test_gitattributes_content():
    with open(".gitattributes", "r") as f:
        content = f.read()
    assert "* text=auto eol=lf" in content
