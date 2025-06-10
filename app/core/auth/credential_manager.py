# app/core/auth/credential_manager.py
"""Secure credential storage (simplified for demo)"""

import json
from typing import Optional, Dict
from cryptography.fernet import Fernet
from pathlib import Path


class CredentialManager:
    """Manages encrypted credential storage"""

    def __init__(self, storage_path: str = "data/credentials.enc"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(exist_ok=True)

        # In production, this key should be stored securely (env var, key vault, etc.)
        # For demo, we'll generate or load a key
        self._key = self._get_or_create_key()
        self._cipher = Fernet(self._key)

        # In-memory cache for demo
        self._credentials: Dict[str, Dict[str, str]] = {}
        self._load_credentials()

    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key"""
        key_file = Path("data/.key")

        if key_file.exists():
            return key_file.read_bytes()
        else:
            key = Fernet.generate_key()
            key_file.parent.mkdir(exist_ok=True)
            key_file.write_bytes(key)
            return key

    def save_credentials(self, user_id: str, email: str, password: str) -> bool:
        """Save encrypted credentials"""
        try:
            # Store in memory
            self._credentials[user_id] = {"email": email, "password": password}

            # Encrypt and save to file
            data = json.dumps(self._credentials)
            encrypted = self._cipher.encrypt(data.encode())
            self.storage_path.write_bytes(encrypted)

            return True
        except Exception as e:
            print(f"Error saving credentials: {e}")
            return False

    def get_credentials(self, user_id: str) -> Optional[Dict[str, str]]:
        """Get decrypted credentials"""
        return self._credentials.get(user_id)

    def delete_credentials(self, user_id: str) -> bool:
        """Delete user credentials"""
        if user_id in self._credentials:
            del self._credentials[user_id]

            # Re-save encrypted file
            data = json.dumps(self._credentials)
            encrypted = self._cipher.encrypt(data.encode())
            self.storage_path.write_bytes(encrypted)

            return True
        return False

    def _load_credentials(self):
        """Load credentials from encrypted storage"""
        if self.storage_path.exists():
            try:
                encrypted = self.storage_path.read_bytes()
                decrypted = self._cipher.decrypt(encrypted)
                self._credentials = json.loads(decrypted.decode())
            except Exception as e:
                print(f"Error loading credentials: {e}")
                self._credentials = {}

    def has_credentials(self, user_id: str) -> bool:
        """Check if user has stored credentials"""
        return user_id in self._credentials


# Demo credentials for testing
class DemoCredentialManager(CredentialManager):
    """Demo credential manager with test accounts"""

    def __init__(self):
        super().__init__()
        # Pre-populate with demo account
        self._credentials["demo"] = {
            "email": "weather.protract723@passinbox.com",
            "password": "74mXnpt^8x9Z1bm&FjXc",
        }


# Global instance
credential_manager = DemoCredentialManager()
