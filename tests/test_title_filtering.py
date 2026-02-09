import pytest
from app.services.llm_service import GeminiAgent

def test_filter_title_text_system_instruction():
    """Test filtering of [SYSTEM INSTRUCTION: ... ]"""
    agent = GeminiAgent()
    
    # Case 1: System instruction at the start
    text = "[SYSTEM INSTRUCTION: You are a helpful assistant.] Hello there"
    expected = "Hello there"
    assert agent.filter_title_text(text) == expected
    
    # Case 2: System instruction with newlines
    text = """[SYSTEM INSTRUCTION:
Line 1
Line 2
] Start code"""
    expected = "Start code"
    assert agent.filter_title_text(text) == expected

def test_filter_title_text_file_paths():
    """Test filtering of @path references"""
    agent = GeminiAgent()
    
    # Case 1: Simple @ path
    text = "Analyze this file @/tmp/user_attachments/file.txt please"
    expected = "Analyze this file please"
    assert agent.filter_title_text(text) == expected
    
    # Case 2: @ path with spaces (if supported) or just standard @token
    text = "Look at @data.json"
    expected = "Look at"
    assert agent.filter_title_text(text) == expected

def test_filter_title_text_absolute_paths():
    """Test filtering of absolute and relative file paths"""
    agent = GeminiAgent()
    
    # Case 1: Windows path
    text = r"Debug C:\Users\name\project\file.py for me"
    expected = "Debug for me"
    assert agent.filter_title_text(text) == expected
    
    # Case 2: Unix path
    text = "Check /var/log/syslog now"
    expected = "Check now"
    assert agent.filter_title_text(text) == expected

def test_filter_title_text_fallback():
    """Test fallback to 'New Conversation' for empty results"""
    agent = GeminiAgent()
    
    # Case 1: Only system instruction
    text = "[SYSTEM INSTRUCTION: Secret prompt]"
    expected = "New Conversation"
    assert agent.filter_title_text(text) == expected
    
    # Case 2: Only file path
    text = "@/path/to/file"
    expected = "New Conversation"
    assert agent.filter_title_text(text) == expected
    
    # Case 3: Empty string
    text = ""
    expected = "New Conversation"
    assert agent.filter_title_text(text) == expected

def test_filter_title_text_truncation():
    """Test that the title is truncated to a reasonable length"""
    agent = GeminiAgent()
    
    long_text = "This is a very long message that should be truncated because it is too long for a chat title in the sidebar"
    result = agent.filter_title_text(long_text)
    assert len(result) <= 50
    assert result.endswith("...") or len(result) == len(long_text)