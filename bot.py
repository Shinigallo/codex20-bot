"""
Codex20 v3.1 - OpenRouter Fork
Bot Telegram AI per D&D 5e con OpenRouter + Gemma4

Multi-utente con API key rotation, RAG, PDF generation, adventure creator.
"""

import os
import sys
import json
import logging
from typing import Optional
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/codex20.log", mode="w"),
    ],
)
logger = logging.getLogger(__name__)

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(__file__))

# Import core modules
from core.api_client import OpenRouterClient, DEFAULT_MODEL
from core.session import PersistentSessionManager
from core.rag import search_5etools

# Import handlers
from handlers.adventure import handle_adventure
from handlers.search import handle_search
from handlers.memory import handle_remember, handle_recall, handle_memory, handle_forget
from handlers.admin import handle_help, handle_admin_users, handle_admin_add_user, handle_proxy_status

# Import PDF (optional)
try:
    from pdf.character_sheet import create_pdf
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# Bot token
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_TOKEN non impostato! Exit.")
    sys.exit(1)

# Owner ID
AUTHORIZED_USER_ID = os.getenv("AUTHORIZED_USER_ID", "323785285")

# Initialize components
openrouter_client = OpenRouterClient()
session_manager = PersistentSessionManager()

# Adventure creator (if available)
try:
    from advanced_adventure_creator import AdvancedAdventureCreator
    adventure_creator = AdvancedAdventureCreator()
    logger.info("Adventure Creator Advanced caricato")
except ImportError:
    logger.warning("AdvancedAdventureCreator non trovato, fallback base")
    adventure_creator = None

# Authorize owner (no API key needed)
authorized_user_ids: set = {int(AUTHORIZED_USER_ID)}

# --- Initialize bot and dispatcher BEFORE handlers ---
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# --- Generic chat handler (non-command messages) ---
@dp.message(~Command())
async def cmd_chat(message: Message):
    """Risponde a messaggi normali (non comandi) con AI."""
    user_id = message.from_user.id
    if user_id not in authorized_user_ids:
        await bot.send_message(message.chat.id, "⚠️ Accesso non autorizzato.")
        return
    prompt = message.text.strip()
    if not prompt:
        return
    prompt = prompt[:3000]  # Limite lunghezza
    response = await handle_chat(message, bot, user_id, openrouter_client,
                                 session_manager, search_5etools, prompt, response)
    await bot.send_message(message.chat.id, response)


async def handle_chat(message, bot, user_id, api_client, session_mgr, search_fn, prompt):
    """Invia prompt al modello OpenRouter e risponde."""
    # Build system prompt with 5e knowledge
    system_prompt = (
        "Sei un assistente D&D 5e esperto. Rispondi in modo conciso e utile "
        "alle domande del giocatore. Usa regole ufficiali D&D 5e quando possibile. "
        "Se non sai la risposta, dì che non lo sai."
    )
    # Add RAG context if available
    rag_context = await search_fn(prompt) if search_fn else ""
    full_prompt = f"{system_prompt}\n\nContexto da regole:\n{rag_context}\n\nDomanda: {prompt}"
    # Truncate if too long
    if len(full_prompt) > 4000:
        full_prompt = full_prompt[:4000]
    response = await api_client.chat_completion(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": full_prompt}
        ]
    )
    return response


# --- Bot Commands ---

async def cmd_help(message, user_id, bot):
    """Mostra guida completa."""
    response = await handle_help(message, bot, user_id, authorized_user_ids)
    if not response.startswith("⚠️"):
        await bot.send_message(message.chat.id, response)


async def cmd_adventure(message, user_id, bot, prompt, adventure_type):
    """Crea avventura."""
    response = await handle_adventure(
        message, bot, user_id, openrouter_client,
        session_manager, search_5etools,
        adventure_creator, prompt, adventure_type
    )
    await bot.send_message(message.chat.id, response)


async def cmd_search(message, user_id, bot, query):
    """Ricerca regole."""
    response = await handle_search(
        message, bot, user_id, openrouter_client,
        session_manager, search_5etools, query
    )
    await bot.send_message(message.chat.id, response)


async def cmd_remember(message, user_id, bot, info):
    """Salva info campagna."""
    response = await handle_remember(
        message, bot, user_id, openrouter_client,
        session_manager, info
    )
    await bot.send_message(message.chat.id, response)


async def cmd_recall(message, user_id, bot, query):
    """Ricorda info campagna."""
    response = await handle_recall(
        message, bot, user_id, openrouter_client,
        session_manager, query
    )
    await bot.send_message(message.chat.id, response)


async def cmd_memory(message, user_id, bot):
    """Info sessione."""
    response = await handle_memory(message, bot, user_id, session_manager)
    await bot.send_message(message.chat.id, response)


async def cmd_forget(message, user_id, bot):
    """Cancella memoria."""
    response = await handle_forget(message, bot, user_id, session_manager)
    await bot.send_message(message.chat.id, response)


async def cmd_admin_users(message, user_id, bot):
    """Lista utenti autorizzati."""
    response = await handle_admin_users(message, bot, user_id, authorized_user_ids)
    await bot.send_message(message.chat.id, response)


async def cmd_admin_add(message, user_id, bot, new_id):
    """Aggiungi utente."""
    new_id_raw = message.text.replace("/admin_add_user ", "")
    new_id = new_id_raw.strip()
    if not new_id or not new_id.isdigit() or len(new_id) > 20:
        await bot.send_message(message.chat.id, "⚠️ ID utente deve essere un numero valido (max 20 cifre).")
        return
    response = await handle_admin_add_user(
        message, bot, user_id, authorized_user_ids, new_id
    )
    await bot.send_message(message.chat.id, response)


async def cmd_proxy_status(message, user_id, bot):
    """Status API."""
    response = await handle_proxy_status(message, bot, user_id, openrouter_client)
    await bot.send_message(message.chat.id, response)


# Register commands
@dp.message(Command("help"))
async def cmd_help_handler(message: Message):
    user_id = message.from_user.id
    if user_id in authorized_user_ids:
        await cmd_help(message, user_id, bot)
    else:
        await bot.send_message(message.chat.id, "⚠️ Accesso non autorizzato.")


@dp.message(Command("version"))
async def cmd_version(message: Message):
    await bot.send_message(message.chat.id, "🎲 Codex20 v3.1 - OpenRouter Fork")


@dp.message(Command("search_rules"))
async def cmd_search_handler(message: Message):
    user_id = message.from_user.id
    if user_id not in authorized_user_ids:
        await bot.send_message(message.chat.id, "⚠️ API key richiesta.")
        return
    prompt = message.text.replace("/search_rules ", "")
    if not prompt or not prompt.strip():
        await bot.send_message(message.chat.id, "Usa: /search_rules <query>")
        return
    prompt = prompt.strip()[:500]
    await cmd_search(message, user_id, bot, prompt)


@dp.message(Command("adventure"))
async def cmd_adventure_handler(message: Message):
    user_id = message.from_user.id
    if user_id not in authorized_user_ids:
        await bot.send_message(message.chat.id, "⚠️ API key richiesta.")
        return
    prompt = message.text.replace("/adventure ", "")
    if not prompt or not prompt.strip():
        await bot.send_message(message.chat.id, "Usa: /adventure <prompt>")
        return
    prompt = prompt.strip()[:2000]
    await cmd_adventure(message, user_id, bot, prompt, None)


@dp.message(Command("adventure_quick"))
async def cmd_adventure_quick_handler(message: Message):
    user_id = message.from_user.id
    if user_id not in authorized_user_ids:
        await bot.send_message(message.chat.id, "⚠️ API key richiesta.")
        return
    prompt = message.text.replace("/adventure_quick ", "")
    if not prompt or not prompt.strip():
        await bot.send_message(message.chat.id, "Usa: /adventure_quick <prompt>")
        return
    prompt = prompt.strip()[:2000]
    await cmd_adventure(message, user_id, bot, prompt, "quick")


@dp.message(Command("adventure_md"))
async def cmd_adventure_md_handler(message: Message):
    user_id = message.from_user.id
    if user_id not in authorized_user_ids:
        await bot.send_message(message.chat.id, "⚠️ API key richiesta.")
        return
    prompt = message.text.replace("/adventure_md ", "")
    if not prompt or not prompt.strip():
        await bot.send_message(message.chat.id, "Usa: /adventure_md <prompt>")
        return
    prompt = prompt.strip()[:2000]
    await cmd_adventure(message, user_id, bot, prompt, "md")


@dp.message(Command("remember_campaign"))
async def cmd_remember_handler(message: Message):
    user_id = message.from_user.id
    if user_id not in authorized_user_ids:
        await bot.send_message(message.chat.id, "⚠️ API key richiesta.")
        return
    info = message.text.replace("/remember_campaign ", "")
    if not info:
        await bot.send_message(message.chat.id, "Usa: /remember_campaign <info>")
        return
    await cmd_remember(message, user_id, bot, info)


@dp.message(Command("recall_campaign"))
async def cmd_recall_handler(message: Message):
    user_id = message.from_user.id
    if user_id not in authorized_user_ids:
        await bot.send_message(message.chat.id, "⚠️ API key richiesta.")
        return
    query = message.text.replace("/recall_campaign ", "")
    if not query:
        await bot.send_message(message.chat.id, "Usa: /recall_campaign <query>")
        return
    await cmd_recall(message, user_id, bot, query)


@dp.message(Command("memory"))
async def cmd_memory_handler(message: Message):
    await cmd_memory(message, message.from_user.id, bot)


@dp.message(Command("forget"))
async def cmd_forget_handler(message: Message):
    await cmd_forget(message, message.from_user.id, bot)


@dp.message(Command("admin_users"))
async def cmd_admin_users_handler(message: Message):
    user_id = message.from_user.id
    if user_id not in authorized_user_ids:
        await bot.send_message(message.chat.id, "⚠️ Solo admin.")
        return
    await cmd_admin_users(message, user_id, bot)


@dp.message(Command("admin_add_user"))
async def cmd_admin_add_handler(message: Message):
    user_id = message.from_user.id
    if user_id not in authorized_user_ids:
        await bot.send_message(message.chat.id, "⚠️ Solo admin.")
        return
    new_id = message.text.replace("/admin_add_user ", "")
    if not new_id:
        await bot.send_message(message.chat.id, "Usa: /admin_add_user <id>")
        return
    await cmd_admin_add(message, user_id, bot, new_id)


@dp.message(Command("proxy_status"))
async def cmd_proxy_status_handler(message: Message):
    user_id = message.from_user.id
    if user_id not in authorized_user_ids:
        await bot.send_message(message.chat.id, "⚠️ Solo admin.")
        return
    await cmd_proxy_status(message, user_id, bot)


# --- Cleanup on shutdown ---

async def on_shutdown(signal, process):
    await session_manager.cleanup_expired()
    logger.info("Codex20 shutting down gracefully.")


# --- Main ---

if __name__ == "__main__":
    logger.info("Inizializzazione Codex20 OpenRouter Fork...")
    logger.info(f"Modello: {DEFAULT_MODEL}")
    # Sanitizzazione API key: mai esporre in log
    key_display = (
        openrouter_client.api_key[:5] + "..." + openrouter_client.api_key[-3:]
        if openrouter_client.api_key and len(openrouter_client.api_key) > 8
        else "***"
    )
    logger.info(f"API Key: {key_display}")

    # Test connessione
    try:
        test_result = openrouter_client.test_connection()
        if test_result:
            logger.info("✅ Connessione OpenRouter OK")
        else:
            logger.warning("⚠️ Test connessione fallito, continuerà comunque")
    except Exception as e:
        logger.error(f"❌ Test connessione fallito: {e}")

    # Start polling
    logger.info("Bot avviato. Attesse messaggi...")
    bot.infinity_polling()
    logger.info("Bot arrestato.")
