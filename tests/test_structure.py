import os
import sys

def test_app_structure():
    assert os.path.exists("app"), "app directory should exist"
    assert os.path.exists("app/__init__.py"), "app package should be initialized"
    assert os.path.exists("app/core"), "app/core directory should exist"
    assert os.path.exists("app/routers"), "app/routers directory should exist"
    assert os.path.exists("app/models"), "app/models directory should exist"
    assert os.path.exists("app/services"), "app/services directory should exist"
    assert os.path.exists("app/templates"), "app/templates directory should exist"
    assert os.path.exists("app/static"), "app/static directory should exist"
