import os
import json
import pytest
from app.core.config import get_global_setting, update_global_setting

def test_settings_file_creation(tmp_path):
    # Mock data directory if necessary, but we'll use the real path for now or mock it
    # For this test, we just want to ensure that if the file doesn't exist, we get defaults
    pass

def test_get_set_global_settings():
    # This test should fail because get_global_setting and update_global_setting don't exist yet
    test_key = "test_setting"
    test_value = "hello_world"
    
    update_global_setting(test_key, test_value)
    assert get_global_setting(test_key) == test_value
