import os

def test_pwa_files_exist():
    assert os.path.exists("app/static/sw.js")
    assert os.path.exists("app/static/manifest.json")

def test_template_integration():
    with open("app/templates/index.html", "r") as f:
        content = f.read()
    assert 'link rel="manifest"' in content
    assert 'navigator.serviceWorker.register' in content
    assert 'meta name="theme-color"' in content
