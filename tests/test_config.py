from app.core import config


def test_config_values():
    assert config.SESSION_SECRET is not None
    assert config.RP_NAME == "OpenCode Agent"
    assert config.OPENCODE_CMD == "opencode"
