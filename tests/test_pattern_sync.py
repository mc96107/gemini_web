import pytest
from app.services.pattern_sync_service import PatternSyncService

def test_sanitize_content():
    service = PatternSyncService()
    content = "To use this, run fabric --pattern summarize input.txt. Also fabric is great."
    sanitized = service.sanitize_content(content)
    assert "run the current pattern input.txt" in sanitized
    assert "Gemini is great" in sanitized
    assert "fabric" not in sanitized.lower()

def test_extract_description():
    service = PatternSyncService()
    content = "# IDENTITY and PURPOSE\n\nYou are an expert at summarizing content. This pattern helps you. \n\n# STEPS"
    desc = service.extract_description(content)
    assert desc == "You are an expert at summarizing content."

def test_extract_description_fallback():
    service = PatternSyncService()
    content = "No identity section here."
    desc = service.extract_description(content)
    assert desc == "No description available."
