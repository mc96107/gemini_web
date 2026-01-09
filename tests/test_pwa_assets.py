import os
import json

def test_pwa_assets_exist():
    assert os.path.exists("app/static/icon.svg")
    assert os.path.exists("app/static/favicon.ico")
    assert os.path.exists("app/static/manifest.json")

def test_manifest_is_valid_json():
    with open("app/static/manifest.json", "r") as f:
        data = json.load(f)
    assert data["name"] == "Gemini Termux Agent"
    assert data["display"] == "standalone"
