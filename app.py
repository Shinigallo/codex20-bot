"""
Codex20 Web Interface v5.0 - FastAPI Backend
Interfaccia web stile Telegram con auth JWT, upload/download materiale, sidebar chat.

v5.0 Security improvements:
- bcrypt per password hashing (SHA256 deprecato)
- JWT_SECRET obbligatorio (crash se default)
- Primo utente = admin automatico
- Nessun fallback hardcoded (admin/admin rimosso)
- Download file richiede autenticazione
- user_id estratto dal JWT, non da query param
- Cleanup automatico chat >7 giorni inattive
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

import jwt
import bcrypt
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
from core.users import UserManager

# Initialize
app = FastAPI(title="Codex20 Web", version="5.0")
api_key = os.getenv("OPENROUTER_API_KEY", "")
if api_key:
    openrouter_client = OpenRouterClient(api_key=api_key)
else:
    logger.error("OPENROUTER_API_KEY non configurata")
    openrouter_client = None
session_manager = PersistentSessionManager()
user_manager = UserManager("data/users.json")

# Auth configuration
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET or JWT_SECRET == "codex20-secret-key-change-in-production":
    logger.critical("JWT_SECRET è obbligatorio e non può essere il default! Imposta JWT_SECRET in .env")
    raise RuntimeError("JWT_SECRET è obbligatorio e non può essere il default! Imposta JWT_SECRET in .env")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Upload directory
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# System prompt D&D 5e
SYSTEM_PROMPT = (
    "Sei un assistente D&D 5e esperto. Rispondi in modo conciso e utile "
    "alle domande del giocatore. Usa regole ufficiali D&D 5e quando possibile. "
    "Se non sai la risposta, dì che non lo sai."
)

# Security scheme
security = HTTPBearer(auto_error=False)


# --- Auth helpers ---
def create_token(user_id: int, username: str) -> str:
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": "admin" if user_id == 1 else "user",
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
    """Depends per ottenere l'utente corrente dal token."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Autenticazione richiesta")
    user_data = verify_token(credentials.credentials)
    return user_data


# --- Login page ---
@app.get("/", response_class=HTMLResponse)
async def serve_root():
    """Serve il frontend HTML (login o app)."""
    with open("static/index.html") as f:
        return f.read()


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """Serve la pagina di login."""
    with open("static/index.html") as f:
        return f.read()


# --- Register page ---
@app.get("/register", response_class=HTMLResponse)
async def register_page():
    """Serve la pagina di registrazione."""
    with open("static/index.html") as f:
        return f.read()


# --- Register API ---
@app.post("/api/register")
async def register(username: str = Form(...), password: str = Form(...)):
    """Registra un nuovo utente. Primo = admin, successivi = user."""
    # Se non ci sono utenti, il primo è admin
    is_first_user = len(user_manager.users) == 0

    success, message, user_id = user_manager.register(username, password)
    if success:
        role = "admin" if is_first_user else "user"
        return {"message": message, "username": username, "user_id": user_id, "role": role}
    raise HTTPException(status_code=400, detail=message)


# --- Login API ---
@app.post("/api/login")
async def login(username: str = Form(...), password: str = Form(...)):
    """Login con username/password, restituisce JWT token."""
    success, user_data = user_manager.authenticate(username, password)
    if success:
        token = create_token(user_data["user_id"], username)
        return {
            "token": token,
            "username": username,
            "user_id": user_data["user_id"],
            "role": user_data.get("role", "user")
        }

    raise HTTPException(status_code=401, detail="Credenziali non valide")


# --- Logout (client-side token removal) ---
@app.get("/api/logout")
async def logout():
    """Logout - il client rimuove il token."""
    return {"message": "Logout effettuato"}


# --- Authenticated chat ---
class ChatRequest(BaseModel):
    messages: list[dict]


@app.post("/api/chat")
async def chat_endpoint(body: ChatRequest, user: dict = Depends(get_current_user)):
    """
    Endpoint chat con retry automatico 429/5xx/timeout.
    user_id estratto dal JWT, non da query param.
    """
    user_id = int(user["sub"])
    user_message = body.messages[-1]["content"] if body.messages else ""
    prompt = f"{SYSTEM_PROMPT}\n\nDomanda: {user_message}"
    if len(prompt) > 4000:
        prompt = prompt[:4000]

    max_retries = MAX_429_RETRY
    initial_delay = INITIAL_429_DELAY
    attempt = 0
    # Guard contro fallback ricorsivo infinito
    if attempt >= max_retries:
        raise HTTPException(status_code=500, detail="Troppi tentativi falliti")

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
            session_manager.add_message(user_id, user_message, response)
            return response

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                attempt += 1
                if attempt >= max_retries:
                    break
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
    token: dict = Depends(get_current_user)
):
    """Upload file per materiale campagna."""
    # Validazione
    allowed_extensions = {'.pdf', '.txt', '.md', '.jpg', '.jpeg', '.png', '.gif', '.csv', '.json', '.xml', '.xlsx', '.docx'}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Estensione non consentita: {ext}")

    # Verifica che user_id corrisponda al token
    if str(token["sub"]) != user_id:
        raise HTTPException(status_code=403, detail="Non autorizzato")

    # Crea directory per utente
    user_dir = UPLOAD_DIR / user_id / chat_id
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
    token: dict = Depends(get_current_user)
):
    """Lista file caricati per utente/chat."""
    # Verifica ownership
    if str(token["sub"]) != user_id:
        raise HTTPException(status_code=403, detail="Non autorizzato")

    user_dir = UPLOAD_DIR / user_id / chat_id
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
async def download_file(user_id: str, chat_id: str, filename: str, token: dict = Depends(get_current_user)):
    """Download file specifico (richiede autenticazione)."""
    # Verifica ownership
    if str(token["sub"]) != user_id:
        raise HTTPException(status_code=403, detail="Non autorizzato")

    filepath = UPLOAD_DIR / user_id / chat_id / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File non trovato")

    return FileResponse(
        filepath,
        filename=filename,
        media_type="application/octet-stream"
    )


@app.delete("/api/files/{user_id}/{chat_id}/{filename}")
async def delete_file(user_id: str, chat_id: str, filename: str, token: dict = Depends(get_current_user)):
    """Elimina file."""
    if str(token["sub"]) != user_id:
        raise HTTPException(status_code=403, detail="Non autorizzato")

    filepath = UPLOAD_DIR / user_id / chat_id / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File non trovato")
    filepath.unlink()
    return {"message": f"File '{filename}' eliminato"}


# --- Chat list API ---
@app.get("/api/chats")
async def list_chats(token: dict = Depends(get_current_user)):
    """Lista chat recenti dell'utente (user_id dal JWT)."""
    user_id = int(token["sub"])
    chats = session_manager.get_user_chats(user_id)
    return {"chats": chats}


@app.post("/api/chats/{chat_id}")
async def create_chat(chat_id: str, token: dict = Depends(get_current_user)):
    """Crea nuova chat."""
    user_id = int(token["sub"])
    session_manager.create_chat(user_id, chat_id)
    return {"message": f"Chat '{chat_id}' creata"}


# --- Session cleanup API ---
@app.delete("/api/sessions")
async def delete_sessions(token: dict = Depends(get_current_user)):
    """Cancella tutte le sessioni dell'utente."""
    user_id = int(token["sub"])
    session_manager.clear_all_sessions(user_id)
    return {"message": "Tutte le sessioni cancellate"}


@app.get("/api/sessions/expired")
async def get_expired_sessions(token: dict = Depends(get_current_user)):
    """Lista sessioni scadute (>7 giorni inattive)."""
    user_id = int(token["sub"])
    expired = session_manager.get_expired_sessions(user_id)
    return {"expired_sessions": expired}


# --- Admin: cleanup tutti gli utenti ---
@app.post("/api/admin/cleanup")
async def admin_cleanup(token: dict = Depends(get_current_user)):
    """Admin: cleanup sessioni scadute per tutti gli utenti."""
    if token.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo admin")

    cleaned = session_manager.cleanup_all_expired()
    return {"message": f"Sessioni pulite: {cleaned}"}


# --- Status ---
@app.get("/api/status")
async def get_status():
    """Status API."""
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
    """Test connessione API."""
    try:
        if not openrouter_client:
            return {"connected": False, "error": "OPENROUTER_API_KEY non configurata"}
        response = openrouter_client.test_connection()
        return {"connected": response}
    except Exception as e:
        return {"connected": False, "error": str(e)}


# --- Background cleanup task ---
async def background_cleanup():
    """Esegue cleanup sessioni scadute ogni 6 ore."""
    while True:
        try:
            cleaned = session_manager.cleanup_all_expired()
            if cleaned > 0:
                logger.info(f"Cleanup automatico: {cleaned} sessioni eliminate")
        except Exception as e:
            logger.error(f"Errore cleanup automatico: {e}")
        await asyncio.sleep(6 * 3600)  # Ogni 6 ore


# --- Startup event ---
@app.on_event("startup")
async def startup_event():
    """Avvia task di cleanup background."""
    asyncio.create_task(background_cleanup())
    logger.info("Cleanup background avviato (ogni 6 ore)")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("WEB_PORT", 8084))
    host = os.getenv("WEB_HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)
