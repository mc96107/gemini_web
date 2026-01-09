import os
from app.services.user_manager import UserManager

def test_user_manager_no_auto_admin(tmp_path):
    um = UserManager(working_dir=str(tmp_path))
    assert len(um.users) == 0
    assert not os.path.exists(os.path.join(tmp_path, "adm.txt"))

def test_sensitive_files_removed():
    assert not os.path.exists("adm.txt")
    # users.json and user_sessions.json might be created during other tests, 
    # but they should be in .gitignore
