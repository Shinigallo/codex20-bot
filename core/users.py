"""
Gestione utenti con bcrypt e ruolo admin automatico per primo utente.
"""

import os
import json
import bcrypt
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

USERS_FILE = Path("data/users.json")


class UserManager:
    """Gestisce registrazione e autenticazione utenti con bcrypt."""

    def __init__(self, users_file: str = "data/users.json"):
        self.users_file = Path(users_file)
        self.users_file.parent.mkdir(exist_ok=True)
        self._load_users()

    def _load_users(self):
        """Carica utenti da file JSON."""
        if self.users_file.exists():
            with open(self.users_file, 'r') as f:
                self.users = json.load(f)
        else:
            self.users = {}

    def _save_users(self):
        """Salva utenti su file JSON."""
        with open(self.users_file, 'w') as f:
            json.dump(self.users, f, indent=2)

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password con bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def register(self, username: str, password: str) -> tuple[bool, str, int]:
        """
        Registra nuovo utente.
        
        Returns:
            tuple: (successo, messaggio, user_id)
        """
        # Verifica duplicati
        if username in self.users:
            return False, f"Username '{username}' già registrato.", -1

        # Determina ruolo: primo utente = admin, altri = user
        role = "admin" if len(self.users) == 0 else "user"

        # Crea utente con bcrypt
        user_id = len(self.users) + 1
        self.users[username] = {
            "username": username,
            "password_hash": self.hash_password(password),
            "user_id": user_id,
            "role": role,
            "created_at": datetime.now().isoformat()
        }
        self._save_users()

        msg = f"Utente registrato con successo! Ruolo: {role}"
        return True, msg, user_id

    def authenticate(self, username: str, password: str) -> tuple[bool, dict]:
        """
        Autentica utente con bcrypt.
        
        Returns:
            tuple: (successo, user_data)
        """
        if username not in self.users:
            return False, {}

        user = self.users[username]
        if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            return True, user
        return False, {}

    def get_user(self, username: str) -> Optional[dict]:
        """Ottieni utente per username."""
        return self.users.get(username)

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        """Ottieni utente per ID."""
        for user in self.users.values():
            if user['user_id'] == user_id:
                return user
        return None

    def is_admin(self, username: str) -> bool:
        """Verifica se utente è admin."""
        user = self.get_user(username)
        return user is not None and user.get('role') == 'admin'
