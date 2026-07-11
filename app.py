"""
Codex20 Web Interface v4.0 - FastAPI Backend
Interfaccia web stile Telegram con auth JWT, upload/download materiale, sidebar chat.
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

import jwt
import aiofiles
import requests
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Request, Body
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Import existing bot components
from core.api_client import OpenRouterClient, DEFAULT_MODEL, MAX_429_RETRY, INITIAL_429_DELAY
from core.session import PersistentSessionManager
from core.rag import search_5etools
from core.users import register_user, verify_user, is_admin

# Import handlers
from handlers.chat import handle_chat
from handlers.admin import handle_help, handle_proxy_status

# Initialize
app = FastAPI(title="Codex20 Web", version="4.0")
api_key = os.getenv("OPENROUTER_API_KEY", "")
if api_key:
    openrouter_client = OpenRouterClient(api_key=api_key)
else:
    logger.error("OPENROUTER_API_KEY non configurata")
    openrouter_client = None
session_manager = PersistentSessionManager()

# Auth configuration
JWT_SECRET = os.getenv("JWT_SECRET", "codex20-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Login credentials (admin hardcoded)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")

# Upload directory
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# System prompt D&D 5e
SYSTEM_PROMPT = (
    "Sei un assistente D&D 5e esperto. Rispondi in modo conciso e utile "
    "alle domande del giocatore. Usa regole ufficiali D&D 5e quando possibile. "
    "Se non sai la risposta, dì che non lo sai."
)

# Retry state per user
retry_state: dict[str, list[float]] = {}  # user_id -> [retry_times]

# Security scheme
security = HTTPBearer(auto_error=False)


# --- Auth helpers ---
def hash_password(password: str) -> str:
    """Simple hash for demo (use bcrypt in production)"""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, stored_hash: str) -> bool:
    return hash_password(password) == stored_hash


def create_token(user_id: int, username: str) -> str:
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token scaduto")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token non valido")


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Depends per ottenere l'utente corrente dal token"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Autenticazione richiesta")
    return verify_token(credentials.credentials)


# --- Login page ---
@app.get("/", response_class=HTMLResponse)
async def serve_root():
    """Serve il frontend HTML (login o app)"""
    with open("static/index.html") as f:
        return f.read()


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """Serve la pagina di login"""
    with open("static/index.html") as f:
        return f.read()


# --- Register page ---
@app.get("/register", response_class=HTMLResponse)
async def register_page():
    """Serve la pagina di registrazione"""
    with open("static/index.html") as f:
        return f.read()


# --- Register API ---
@app.post("/api/register")
async def register(username: str = Form(...), password: str = Form(...)):
    """Registra un nuovo utente"""
    success, message = register_user(username, password)
    if success:
        return {"message": message, "username": username}
    raise HTTPException(status_code=400, detail=message)


# --- Login API ---
@app.post("/api/login")
async def login(username: str = Form(...), password: str = Form(...)):
    """Login con username/password, restituisce JWT token"""
    # Admin hardcoded
    if username == ADMIN_USERNAME:
        expected_hash = ADMIN_PASSWORD_HASH if ADMIN_PASSWORD_HASH else hash_password(ADMIN_USERNAME)
        if verify_password(password, expected_hash):
            token = create_token(1, username)
            return {"token": token, "username": username, "user_id": 1}

    # Check registered users
    success, user_data = verify_user(username, password)
    if success:
        token = create_token(user_data["user_id"], username)
        return {"token": token, "username": username, "user_id": user_data["user_id"]}

    # Se non trova credenziali, accetta admin/admin per demo
    if username == "admin" and password == "admin":
        token = create_token(1, username)
        return {"token": token, "username": username, "user_id": 1}

    raise HTTPException(status_code=401, detail="Credenziali non valide")


# --- Logout (client-side token removal) ---
@app.get("/api/logout")
async def logout():
    """Logout - il client rimuove il token"""
    return {"message": "Logout effettuato"}


# --- Authenticated chat ---
class ChatRequest(BaseModel):
    messages: list[dict]

@app.post("/api/chat")
async def chat_endpoint(user_id: str, body: ChatRequest, token: str = Depends(get_current_user)):
    """
    Endpoint chat con retry automatico 429/5xx/timeout
    - Se riceve 429, fa retry con backoff esponenziale (max 6 tentativi)
    - Timer visivo per l'utente durante il retry
    - Salva sessione nel DB
    """
    user_message = body.messages[-1]["content"] if body.messages else ""
    prompt = f"{SYSTEM_PROMPT}\n\nDomanda: {user_message}"
    if len(prompt) > 4000:
        prompt = prompt[:4000]

    max_retries = MAX_429_RETRY
    initial_delay = INITIAL_429_DELAY
    attempt = 0

    while attempt < max_retries:
        try:
            rag_context = search_5etools(prompt)
            if rag_context:
                prompt += f"\n\nContexto da regole:\n{rag_context}"

            response = openrouter_client.chat_completion(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]
            )
            session_manager.add_message(int(user_id), user_message, response)
            return response

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                attempt += 1
                delay = initial_delay * (2 ** attempt)
                logger.warning(f"429 retry {attempt}/{max_retries} in {delay:.0f}s")
                time.sleep(delay)
                continue
            elif e.response.status_code >= 500:
                attempt += 1
                if attempt < max_retries:
                    time.sleep(5 * attempt)
                    continue
                raise HTTPException(status_code=500, detail="Server error")
            else:
                raise HTTPException(status_code=e.response.status_code, detail=str(e))

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    raise HTTPException(status_code=500, detail="Tutti i tentativi falliti")


# --- File Upload/Download ---
@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Form(default="1"),
    chat_id: str = Form(default="default"),
    token: str = Depends(get_current_user)
):
    """Upload file per materiale campagna"""
    # Validazione
    allowed_extensions = {'.pdf', '.txt', '.md', '.jpg', '.jpeg', '.png', '.gif', '.csv', '.json', '.xml', '.xlsx', '.docx'}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Estensione non consentita: {ext}")

    # Crea directory per utente
    user_dir = UPLOAD_DIR / str(user_id) / chat_id
    user_dir.mkdir(parents=True, exist_ok=True)

    # Salva file
    filepath = user_dir / file.filename
    async with aiofiles.open(filepath, 'wb') as f:
        content = await file.read()
        await f.write(content)

    logger.info(f"File caricato: {file.filename} per user {user_id} chat {chat_id}")
    return {
        "filename": file.filename,
        "size": len(content),
        "path": str(filepath.relative_to(UPLOAD_DIR)),
        "message": f"File '{file.filename}' caricato con successo"
    }


@app.get("/api/files")
async def list_files(
    user_id: str = "1",
    chat_id: str = "default",
    token: str = Depends(get_current_user)
):
    """Lista file caricati per utente/chat"""
    user_dir = UPLOAD_DIR / str(user_id) / chat_id
    if not user_dir.exists():
        return {"files": []}

    files = []
    for f in user_dir.iterdir():
        if f.is_file():
            files.append({
                "filename": f.name,
                "size": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                "extension": f.suffix,
            })
    return {"files": sorted(files, key=lambda x: x["filename"])}


@app.get("/api/files/download/{user_id}/{chat_id}/{filename}")
async def download_file(user_id: str, chat_id: str, filename: str):
    """Download file specifico"""
    filepath = UPLOAD_DIR / user_id / chat_id / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File non trovato")

    return FileResponse(
        filepath,
        filename=filename,
        media_type="application/octet-stream"
    )


@app.delete("/api/files/{user_id}/{chat_id}/{filename}")
async def delete_file(user_id: str, chat_id: str, filename: str, token: str = Depends(get_current_user)):
    """Elimina file"""
    filepath = UPLOAD_DIR / user_id / chat_id / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File non trovato")
    filepath.unlink()
    return {"message": f"File '{filename}' eliminato"}


# --- Chat list API ---
@app.get("/api/chats")
async def list_chats(user_id: str = "1", token: str = Depends(get_current_user)):
    """Lista chat recenti dell'utente"""
    chats = session_manager.get_user_chats(int(user_id))
    return {"chats": chats}


@app.post("/api/chats/{chat_id}")
async def create_chat(chat_id: str, user_id: str = "1", token: str = Depends(get_current_user)):
    """Crea nuova chat"""
    session_manager.create_chat(int(user_id), chat_id)
    return {"message": f"Chat '{chat_id}' creata"}


# --- Status ---
@app.get("/api/status")
async def get_status():
    """Status API"""
    return {
        "model": DEFAULT_MODEL,
        "backup_model": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "api_key_count": len(openrouter_client._api_keys) if openrouter_client else 0,
        "total_requests": 0,
        "cache_size": len(session_manager._cache),
        "timeout": 180,
    }


@app.get("/api/test")
async def test_connection():
    """Test connessione API"""
    try:
        if not openrouter_client:
            return {"connected": False, "error": "OPENROUTER_API_KEY non configurata"}
        response = openrouter_client.test_connection()
        return {"connected": response}
    except Exception as e:
        return {"connected": False, "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("WEB_PORT", 8084))
    host = os.getenv("WEB_HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)
