from app.core import config

def test_config_values():
    assert config.SESSION_SECRET is not None
    assert config.RP_ID == "localhost"
    assert config.RP_NAME == "Gemini Agent"
    assert config.ORIGIN is not None
