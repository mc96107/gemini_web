import os

def test_templates_exist():
    assert os.path.exists("app/templates/index.html"), "index.html should exist in app/templates"
    assert os.path.exists("app/templates/login.html"), "login.html should exist in app/templates"
    assert os.path.exists("app/templates/admin.html"), "admin.html should exist in app/templates"
