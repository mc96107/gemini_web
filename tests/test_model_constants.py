from app.services.llm_service import FALLBACK_MODELS

def test_fallback_models_include_gemini_3_stable():
    # Expecting stable versions as per latest updates
    assert "gemini-3-pro" in FALLBACK_MODELS
    assert FALLBACK_MODELS["gemini-3-pro"] == "gemini-3-flash"
    assert "gemini-3" in FALLBACK_MODELS
    assert FALLBACK_MODELS["gemini-3"] == "gemini-3-flash"
