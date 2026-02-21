from app.services.llm_service import FALLBACK_MODELS


def test_fallback_models_include_gemini_3_stable():
    # Expecting stable versions to fallback to preview if not available
    assert "google/gemini-3-pro" in FALLBACK_MODELS
    assert FALLBACK_MODELS["google/gemini-3-pro"] == "google/gemini-3.1-pro-preview"
    assert "google/gemini-3" in FALLBACK_MODELS
    assert (
        FALLBACK_MODELS["google/gemini-3"] == "google/gemini-3.1-pro-preview"
        or FALLBACK_MODELS["google/gemini-3"] == "google/gemini-3-flash-preview"
    )
