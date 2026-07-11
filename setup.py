#!/usr/bin/env python3
"""
Codex20 Setup Wizard
Script di installazione interattiva per la prima configurazione.
Guida l'utente nella configurazione iniziale del sistema.
"""

import os
import sys
import json
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime

# Colori per output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'

def print_banner():
    print(f"""
{Colors.CYAN}
╔════════════════════════════════════════════════════════╗
║                   🎲 Codex20 Setup Wizard                  ║
║          Installazione interattiva per GitHub              ║
╚════════════════════════════════════════════════════════╝
{Colors.END}
""")

def get_input(prompt, default=""):
    """Get user input with default value"""
    # Check if running non-interactive
    if os.environ.get('NON_INTERACTIVE'):
        env_var = prompt.lower().replace(' ', '_').replace('?', '').replace(':', '')
        return os.environ.get(env_var.upper(), default)
    
    if default:
        return input(f"{Colors.BLUE}{prompt} [{default}]: {Colors.END}").strip() or default
    return input(f"{Colors.BLUE}{prompt}: {Colors.END}").strip()

def get_password():
    """Get password input"""
    return input(f"{Colors.BLUE}Password: {Colors.END}").strip()

def hash_password(password):
    """Hash password with SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def step_admin_user():
    """Configura il primo utente admin"""
    print(f"\n{Colors.YELLOW}📝 CONFIGURAZIONE UTENTE ADMIN{Colors.END}\n")
    print("Crea il primo account amministratore del sistema.")
    
    username = get_input("Username admin", "admin")
    password = get_password()
    
    # Verifica password
    confirm = get_password()
    if password != confirm:
        print(f"{Colors.RED}❌ Password non corrispondenti!{Colors.END}")
        sys.exit(1)
    
    # Crea utente admin
    user_data = {
        "username": username,
        "password_hash": hash_password(password),
        "user_id": 1,
        "role": "admin",
        "created_at": "2026-07-11T00:00:00"
    }
    
    # Salva in users.json
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    users_file = data_dir / "users.json"
    if users_file.exists():
        with open(users_file, 'r') as f:
            users = json.load(f)
    else:
        users = {}
    
    users[username] = user_data
    with open(users_file, 'w') as f:
        json.dump(users, f, indent=2)
    
    print(f"{Colors.GREEN}✅ Utente admin creato: {username}{Colors.END}")
    return username

def step_api_key():
    """Configura la OpenRouter API key"""
    print(f"\n{Colors.YELLOW}🔑 CONFIGURAZIONE API KEY{Colors.END}\n")
    print("Inserisci la tua OpenRouter API key per usare i modelli AI.")
    print("Puoi ottenere una chiave da: https://openrouter.ai/keys")
    
    api_key = get_password()
    if not api_key.startswith("sk-or-v1-"):
        print(f"{Colors.YELLOW}⚠️  La chiave dovrebbe iniziare con 'sk-or-v1-'...{Colors.END}")
    
    return api_key

def step_models():
    """Seleziona i modelli AI da usare"""
    print(f"\n{Colors.YELLOW}🤖 CONFIGURAZIONE MODELLI{Colors.END}\n")
    print("Seleziona i modelli AI da utilizzare:")
    print("1. google/gemma-4-31b-it:free (Default)")
    print("2. qwen/qwen3.5:free")
    print("3. meta-llama/llama-3.3-70b-instruct:free")
    print("4. nvidia/nemotron-3-ultra-550b-a55b:free")
    
    choice = input(f"{Colors.BLUE}Scegli modello [1]: {Colors.END}").strip() or "1"
    
    models = {
        "1": "google/gemma-4-31b-it:free",
        "2": "qwen/qwen3.5:free",
        "3": "meta-llama/llama-3.3-70b-instruct:free",
        "4": "nvidia/nemotron-3-ultra-550b-a55b:free"
    }
    
    if choice in models:
        model = models[choice]
        print(f"{Colors.GREEN}✅ Modello selezionato: {model}{Colors.END}")
        return model
    else:
        print(f"{Colors.YELLOW}⚠️  Scelta non valida, uso default: gemma-4{Colors.END}")
        return "google/gemma-4-31b-it:free"

def step_backup_model():
    """Seleziona il modello di backup"""
    print(f"\n{Colors.YELLOW}🔄 MODELLO DI BACKUP{Colors.END}\n")
    print("Se il modello principale è rate-limited, userà questo modello.")
    
    choice = input(f"{Colors.BLUE}Scegli backup [2 - nemotron]: {Colors.END}").strip() or "2"
    
    backup_models = {
        "1": "google/gemma-4-31b-it:free",
        "2": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "3": "qwen/qwen3.5:free"
    }
    
    if choice in backup_models:
        backup = backup_models[choice]
        print(f"{Colors.GREEN}✅ Backup selezionato: {backup}{Colors.END}")
        return backup
    else:
        return "nvidia/nemotron-3-ultra-550b-a55b:free"

def generate_env_file(admin_user, api_key, model, backup_model):
    """Genera il file .env con le configurazioni"""
    import secrets
    jwt_secret = secrets.token_hex(32)
    
    env_content = f"""# Codex20 OpenRouter - Configuration
# Generato dal Setup Wizard il 2026-07-11

# OpenRouter API Key
OPENROUTER_API_KEY={api_key}

# Modello AI principale
MODEL_NAME={model}

# Modello di backup
BACKUP_MODEL_NAME={backup_model}

# Admin user (username, non hash)
ADMIN_USERNAME={admin_user}

# Password admin (hash SHA256)
ADMIN_PASSWORD_HASH=<HASH_REPLACE>

# URL OpenRouter
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Porte
WEB_PORT=8084
BOT_PORT=8085

# JWT Secret (cambia in produzione!)
JWT_SECRET={jwt_secret}

# Database
DATABASE_URL=sqlite:///data/sessions.db

# Log level
LOG_LEVEL=INFO
"""
    with open(".env", "w") as f:
        f.write(env_content)
    
    print(f"{Colors.GREEN}✅ File .env creato{Colors.END}")
    return env_content

def run_docker_compose():
    """Avvia il servizio con Docker Compose"""
    print(f"\n{Colors.YELLOW}🐳 AVVIO SERVIZIO DOCKER{Colors.END}\n")
    print("Avvio il servizio Codex20 con Docker Compose...")
    
    # Verifica se docker compose è installato
    try:
        subprocess.run(["docker", "compose", "version"], check=True, capture_output=True)
    except FileNotFoundError:
        print(f"{Colors.RED}❌ Docker Compose non installato. Installa Docker prima di continuare.{Colors.END}")
        sys.exit(1)
    
    # Verifica se l'immagine esiste
    try:
        subprocess.run(["docker", "compose", "build"], check=True, capture_output=True)
        print(f"{Colors.GREEN}✅ Immagine Docker builddata{Colors.END}")
    except subprocess.CalledProcessError:
        print(f"{Colors.YELLOW}⚠️  Errore build, provo a usare immagine esistente...{Colors.END}")
    
    # Avvia container
    try:
        subprocess.run([
            "docker", "compose", "up", "-d"
        ], check=True)
        print(f"{Colors.GREEN}✅ Servizio avviato su porta 8085{Colors.END}")
    except subprocess.CalledProcessError:
        print(f"{Colors.YELLOW}⚠️  Errore avvio servizio. Controlla i log con: docker logs codex20-python{Colors.END}")

def main():
    print_banner()
    
    # Step 1: Admin user
    admin_user = step_admin_user()
    
    # Step 2: API Key
    api_key = step_api_key()
    
    # Step 3: Model
    model = step_models()
    
    # Step 4: Backup model
    backup_model = step_backup_model()
    
    # Step 5: Generate .env
    print(f"\n{Colors.YELLOW}📄 GENERAZIONE CONFIGURAZIONE{Colors.END}\n")
    env_content = generate_env_file(admin_user, api_key, model, backup_model)
    
    # Step 6: Start Docker
    start_docker = input(f"\n{Colors.BLUE}Avviare il servizio Docker Compose? [y/N]: {Colors.END}").strip().lower()
    
    if start_docker == "y":
        run_docker_compose()
        print(f"\n{Colors.GREEN}🎉 Setup completato!{Colors.END}")
        print(f"{Colors.GREEN}🌐 Accedi a: http://localhost:8085{Colors.END}")
        print(f"{Colors.GREEN}👤 Login: {admin_user}{Colors.END}")
        print(f"{Colors.GREEN}🔑 Password: <quella inserita>{Colors.END}")
    else:
        print(f"\n{Colors.YELLOW}⚠️  Setup completato ma servizio non avviato.{Colors.END}")
        print(f"{Colors.YELLOW}Avvia manualmente: docker compose up -d{Colors.END}")

if __name__ == "__main__":
    main()
