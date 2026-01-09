import pytest
from app.routers import auth, chat, admin

def test_routers_import():
    assert auth.router is not None
    assert chat.router is not None
    assert admin.router is not None
