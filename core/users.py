"""
User management for Codex20
Manages user registration and authentication
"""
import os
import json
from pathlib import Path
import hashlib

# User data file
DATA_DIR = Path(__file__).parent.parent / "data"
USERS_FILE = DATA_DIR / "users.json"

def load_users():
    """Load users from JSON file"""
    if USERS_FILE.exists():
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    """Save users to JSON file"""
    DATA_DIR.mkdir(exist_ok=True)
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def hash_password(password):
    """Hash password with SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password):
    """Register a new user"""
    users = load_users()
    
    # Check if user exists
    if username in users:
        return False, "Utente già esistente"
    
    # Create user
    users[username] = {
        "password_hash": hash_password(password),
        "user_id": len(users) + 1,
        "created_at": "2026-07-11T00:00:00"
    }
    
    save_users(users)
    return True, f"Utente '{username}' creato con ID {users[username]['user_id']}"

def verify_user(username, password):
    """Verify user credentials"""
    users = load_users()
    
    if username not in users:
        return False, None
    
    expected_hash = users[username]["password_hash"]
    actual_hash = hash_password(password)
    
    if expected_hash == actual_hash:
        return True, users[username]
    
    return False, None

# Admin user (hardcoded)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")

def is_admin(username):
    """Check if user is admin"""
    return username == ADMIN_USERNAME
