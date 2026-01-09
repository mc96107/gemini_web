import os

def test_static_files_exist():
    assert os.path.exists("app/static/style.css"), "style.css should exist in app/static"
    assert os.path.exists("app/static/script.js"), "script.js should exist in app/static"
