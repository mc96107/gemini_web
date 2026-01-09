import os
import json
import hashlib
import bcrypt
from typing import Optional, Tuple, Dict, List
from webauthn.helpers import bytes_to_base64url

class UserManager:
    def __init__(self, working_dir: Optional[str] = None):
        self.working_dir = working_dir or os.getcwd()
        self.users_file = os.getenv("USERS_FILE", os.path.join(self.working_dir, "users.json"))
        self.users = self._load_users()
        self._ensure_admin()

    def _load_users(self) -> Dict:
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, "r") as f: return json.load(f)
            except: return {}
        return {}

    def _save_users(self):
        with open(self.users_file, "w") as f: json.dump(self.users, f, indent=2)

    def has_users(self) -> bool:
        return len(self.users) > 0

    def clear_all_users(self):
        self.users = {}
        self._save_users()

    def _ensure_admin(self):
        # We no longer auto-create admin with a default password for security and anonymity.
        # The first-run setup should be handled by the application logic.
        pass

    def _pre_hash(self, password: str) -> str:
        if not password: return ""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    def get_password_hash(self, password: str) -> str:
        return bcrypt.hashpw(self._pre_hash(password).encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def verify_password(self, plain: str, hashed: str) -> bool:
        try: return bcrypt.checkpw(self._pre_hash(plain).encode('utf-8'), hashed.encode('utf-8'))
        except: return False

    def register_user(self, username: str, password: str, pattern: Optional[str] = None, wallet: Optional[str] = None, role: str = "user") -> Tuple[bool, str]:
        if username in self.users: return False, "Exists"
        self.users[username] = {
            "password": self.get_password_hash(password),
            "pattern": self.get_password_hash(pattern) if pattern else None,
            "wallet_address": wallet.lower() if wallet else None,
            "role": role,
            "passkeys": []
        }
        self._save_users()
        return True, "Success"

    def get_all_users(self) -> List[Dict]:
        return [{"username": u, "role": d.get("role", "user"), "pattern_disabled": d.get("pattern_disabled", False)} for u, d in self.users.items()]

    def remove_user(self, username: str) -> bool:
        if username in self.users:
            del self.users[username]
            self._save_users()
            return True
        return False

    def update_password(self, username: str, password: str) -> bool:
        if username in self.users:
            self.users[username]["password"] = self.get_password_hash(password)
            self._save_users()
            return True
        return False

    def get_role(self, username: str) -> Optional[str]:
        return self.users.get(username, {}).get("role")

    def add_passkey(self, username: str, cred_id, pub_key, sign_count: int = 0) -> bool:
        if username not in self.users: return False
        if isinstance(cred_id, bytes): cred_id = bytes_to_base64url(cred_id)
        if isinstance(pub_key, bytes): pub_key = bytes_to_base64url(pub_key)
        self.users[username].setdefault("passkeys", []).append({
            "credential_id": cred_id, "public_key": pub_key, "sign_count": sign_count
        })
        self._save_users()
        return True

    def get_passkeys(self, username: str) -> List[Dict]:
        return self.users.get(username, {}).get("passkeys", [])

    def update_passkey_sign_count(self, username: str, cred_id: str, count: int) -> bool:
        if username not in self.users: return False
        for pk in self.users[username].get("passkeys", []):
            if pk["credential_id"] == cred_id:
                pk["sign_count"] = count
                self._save_users()
                return True
        return False

    def set_pattern_disabled(self, username: str, disabled: bool) -> bool:
        if username not in self.users: return False
        self.users[username]["pattern_disabled"] = disabled
        self._save_users()
        return True

    def is_pattern_disabled(self, username: str) -> bool:
        return self.users.get(username, {}).get("pattern_disabled", False)

    def authenticate_with_pattern(self, username: str, pattern: str) -> bool:
        user = self.users.get(username)
        if not user or user.get("pattern_disabled", False): return False
        return user.get("pattern") and self.verify_password(pattern, user["pattern"])

    def set_pattern(self, username: str, pattern: str) -> bool:
        if username not in self.users: return False
        self.users[username]["pattern"] = self.get_password_hash(pattern)
        self._save_users()
        return True

    def set_wallet_address(self, username: str, addr: str) -> bool:
        if username not in self.users: return False
        self.users[username]["wallet_address"] = addr.lower()
        self._save_users()
        return True

    def authenticate_user(self, username: str, password: str) -> bool:
        user = self.users.get(username)
        return user and self.verify_password(password, user["password"])

    def get_user_by_wallet(self, addr: str) -> Optional[str]:
        addr = addr.lower()
        for u, d in self.users.items():
            if d.get("wallet_address") == addr: return u
        return None

    def get_user_by_credential_id(self, cred_id) -> Tuple[Optional[str], Optional[Dict]]:
        if isinstance(cred_id, bytes): cred_id = bytes_to_base64url(cred_id)
        for u, d in self.users.items():
            for pk in d.get("passkeys", []):
                if pk["credential_id"] == cred_id: return u, pk
        return None, None

    def get_user_by_pattern(self, pattern: str) -> Optional[str]:
        for u, d in self.users.items():
            if not d.get("pattern_disabled", False) and d.get("pattern") and self.verify_password(pattern, d["pattern"]): return u
        return None
