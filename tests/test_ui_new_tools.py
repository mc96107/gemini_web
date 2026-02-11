import os

def test_new_tools_present_in_index():
    with open("app/templates/index.html", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Read-Only / Safe Tools
    assert 'id="tool-cli_help"' in content
    assert 'id="tool-ask_user"' in content
    assert 'id="tool-confirm_output"' in content
    
    # Modification / High-Risk Tools
    assert 'id="tool-activate_skill"' in content
    assert 'id="tool-codebase_investigator"' in content
