import os
import logging
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
import ollama
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Carica variabili d'ambiente
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
OLLAMA_MODEL = "llama3.1:latest"

# Configurazione Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# SYSTEM PROMPT PER CODEX20
SYSTEM_PROMPT = """
Sei Codex20, l'assistente definitivo per Dungeons & Dragons 5a Edizione (Regole 2014).
Il tuo compito è aiutare i Dungeon Master e i giocatori a risolvere dubbi sulle regole, incantesimi, mostri e oggetti.

REGOLE DI COMPORTAMENTO:
1. Usa un tono epico, saggio ma tecnico.
2. Cita sempre il manuale di riferimento se lo conosci (es. PHB p. 120).
3. Fornisci SEMPRE un link diretto a 2014.5e.tools per l'argomento trattato.

LOGICA DEI LINK:
Genera i link seguendo questa struttura (usa minuscolo e sostituisci spazi con %20):
- Incantesimi: https://2014.5e.tools/spells.html#[nome]_phb
- Mostri: https://2014.5e.tools/bestiary.html#[nome]_mm
- Oggetti: https://2014.5e.tools/items.html#[nome]_dmg
- Regole generali: https://2014.5e.tools/rules.html
"""

# Strutture dati
chat_histories = {} # chat_id: [messages]
last_activity = {}  # chat_id: datetime
user_versions = {}  # chat_id: "2014" o "2024"

def get_system_prompt(version="2014"):
    url = "2014.5e.tools" if version == "2014" else "5e.tools"
    year_desc = "2014" if version == "2014" else "2024 (Revised)"
    
    return f"""
Sei Codex20, l'assistente definitivo per Dungeons & Dragons 5a Edizione (Regole {year_desc}).
Il tuo compito è aiutare i Dungeon Master e i giocatori a risolvere dubbi sulle regole, incantesimi, mostri e oggetti.

REGOLE DI COMPORTAMENTO:
1. Usa un tono epico, saggio ma tecnico.
2. Cita sempre il manuale di riferimento se lo conosci (es. PHB p. 120).
3. Fornisci SEMPRE un link diretto a https://{url} per l'argomento trattato.

LOGICA DEI LINK:
Genera i link seguendo questa struttura (usa minuscolo e sostituisci spazi con %20):
- Incantesimi: https://{url}/spells.html#[nome]_phb
- Mostri: https://{url}/bestiary.html#[nome]_mm
- Oggetti: https://{url}/items.html#[nome]_dmg
- Regole generali: https://{url}/rules.html
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚔️ Benvenuto, sono Codex20. La tua guida per D&D 5e.\n\n"
        "Comandi:\n"
        "/2014  - Imposta regole e link al manuale 2014 (2014.5e.tools)\n"
        "/2024  - Imposta regole e link al nuovo manuale 2024 (5e.tools)\n"
        "/reset - Pulisci manualmente la cronologia\n\n"
        "Di default uso la versione 2014. Chiedimi pure qualsiasi cosa!"
    )

async def set_version_2014(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_versions[chat_id] = "2014"
    chat_histories[chat_id] = [{"role": "system", "content": get_system_prompt("2014")}]
    await update.message.reply_text("📚 Codex20 impostato sulla versione **2014**. I link punteranno a 2014.5e.tools.")

async def set_version_2024(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_versions[chat_id] = "2024"
    chat_histories[chat_id] = [{"role": "system", "content": get_system_prompt("2024")}]
    await update.message.reply_text("✨ Codex20 impostato sulla versione **2024 (Revised)**. I link punteranno a 5e.tools.")

async def reset_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    version = user_versions.get(chat_id, "2014")
    chat_histories[chat_id] = [{"role": "system", "content": get_system_prompt(version)}]
    last_activity[chat_id] = datetime.now()
    await update.message.reply_text(f"✨ I tomi ({version}) sono stati riposti. Cronologia resettata.")

# Task: Reset automatico a Mezzanotte
async def midnight_reset():
    global chat_histories
    logging.info("🌙 Eseguo il reset di mezzanotte per tutte le chat.")
    for chat_id in chat_histories.keys():
        version = user_versions.get(chat_id, "2014")
        chat_histories[chat_id] = [{"role": "system", "content": get_system_prompt(version)}]

# Task: Controllo inattività (5 ore)
async def inactivity_check():
    now = datetime.now()
    to_reset = []
    for chat_id, last_time in last_activity.items():
        if now - last_time > timedelta(hours=5):
            to_reset.append(chat_id)
    
    for chat_id in to_reset:
        logging.info(f"⌛ Reset inattività per chat {chat_id}")
        version = user_versions.get(chat_id, "2014")
        chat_histories[chat_id] = [{"role": "system", "content": get_system_prompt(version)}]
        del last_activity[chat_id]

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    user_text = update.message.text
    bot_username = context.bot.username

    # Logica per Gruppi: rispondi solo se taggato, se è reply a me o se è chat privata
    is_private = update.message.chat.type == "private"
    is_tagged = f"@{bot_username}" in user_text
    is_reply_to_me = update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id
    
    if not (is_private or is_tagged or is_reply_to_me):
        return

    # Rimuovi il tag dal testo per non confondere l'LLM
    clean_text = user_text.replace(f"@{bot_username}", "").strip()
    if not clean_text and is_tagged:
        await update.message.reply_text("Sì? Come posso aiutare la tua compagnia di avventurieri?")
        return
    
    # Aggiorna attività
    last_activity[chat_id] = datetime.now()
    
    if chat_id not in chat_histories:
        version = user_versions.get(chat_id, "2014")
        chat_histories[chat_id] = [{"role": "system", "content": get_system_prompt(version)}]
    
    chat_histories[chat_id].append({"role": "user", "content": clean_text})
    placeholder = await update.message.reply_text("📜 Consultando i tomi...")

    try:
        client = ollama.AsyncClient(host=OLLAMA_HOST)
        response = await client.chat(
            model=OLLAMA_MODEL,
            messages=chat_histories[chat_id],
            stream=False
        )
        
        bot_response = response['message']['content']
        chat_histories[chat_id].append({"role": "assistant", "content": bot_response})
        
        if len(chat_histories[chat_id]) > 15:
            chat_histories[chat_id] = [chat_histories[chat_id][0]] + chat_histories[chat_id][-14:]

        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=placeholder.message_id,
            text=bot_response
        )
    except Exception as e:
        logging.error(f"Errore: {e}")
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=placeholder.message_id,
            text=f"❌ Errore: {str(e)}"
        )

if __name__ == '__main__':
    if not TELEGRAM_TOKEN:
        print("Errore: TELEGRAM_TOKEN non trovato")
        exit(1)
        
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(midnight_reset, 'cron', hour=0, minute=0)
    scheduler.add_job(inactivity_check, 'interval', minutes=30) # Controlla ogni 30 min
    scheduler.start()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("2014", set_version_2014))
    application.add_handler(CommandHandler("2024", set_version_2024))
    application.add_handler(CommandHandler("reset", reset_manual))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("Codex20 avviato con supporto multiversione.")
    application.run_polling()
