import os
import logging
import asyncio
import json
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
import google.generativeai as genai
from google.api_core import exceptions
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Carica variabili d'ambiente
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
# Configurazione Gemini: Carica la chiave API e inizializza il client
GEMINI_API_KEYS = os.getenv("GEMINI_API_KEYS", os.getenv("GEMINI_API_KEY", "")).split(",")
GEMINI_API_KEYS = [k.strip() for k in GEMINI_API_KEYS if k.strip()]
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

class GeminiManager:
    def __init__(self, api_keys, model_name):
        self.api_keys = api_keys
        self.model_name = model_name
        self.current_key_index = 0
        if self.api_keys:
            self._configure_current_key()
        else:
            logging.warning("Nessuna GEMINI_API_KEY trovata!")

    def _configure_current_key(self):
        key = self.api_keys[self.current_key_index]
        genai.configure(api_key=key)
        logging.info(f"Gemini configurato con la chiave indice {self.current_key_index}")

    def rotate_key(self):
        if len(self.api_keys) <= 1:
            return False
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        self._configure_current_key()
        return True

    async def generate_content_async(self, history, system_instruction=None):
        if not self.api_keys:
            raise Exception("Configurazione Gemini mancante: GEMINI_API_KEYS non impostate.")
        
        max_retries = len(self.api_keys)
        for attempt in range(max_retries):
            try:
                model = genai.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=system_instruction
                )
                response = await model.generate_content_async(history)
                return response.text
            except (exceptions.ResourceExhausted, exceptions.Unauthenticated, exceptions.PermissionDenied) as e:
                logging.warning(f"La chiave Gemini {self.current_key_index} ha fallito: {e}. Rotazione in corso...")
                if not self.rotate_key():
                    raise e
            except Exception as e:
                logging.error(f"Errore inaspettato Gemini: {e}")
                raise e
        raise Exception("Tutte le chiavi API di Gemini sono esaurite o non valide.")

gemini_manager = GeminiManager(GEMINI_API_KEYS, GEMINI_MODEL)

# Configurazione Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

from knowledge_base import kb

# Strutture dati
chat_histories = {} # chat_id: [messages]
last_activity = {}  # chat_id: datetime
user_versions = {}  # chat_id: "2014" o "2024"

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error(f"Exception while handling an update: {context.error}")

def get_system_prompt(version="2014"):
    url = "2014.5e.tools" if version == "2014" else "5e.tools"
    year_desc = "2014" if version == "2014" else "2024 (Revised)"
    
    return f"""
Sei Codex20, l'assistente definitivo per Dungeons & Dragons 5a Edizione (Regole {year_desc}).
Il tuo compito è aiutare i Dungeon Master e i giocatori a risolvere dubbi sulle regole, incantesimi, mostri e oggetti.

REGOLE DI COMPORTAMENTO:
1. Usa un tono epico, saggio e tecnico, tipico di un antico custode del sapere.
2. Rispondi SEMPRE in italiano, anche se ti viene chiesto in altre lingue, a meno che non sia strettamente necessario per citare termini tecnici.
3. Cita sempre il manuale di riferimento e la pagina se possibile (es. PHB p. 120).
4. Fornisci SEMPRE un link diretto a https://{url} per ogni incantesimo, mostro o oggetto menzionato.

LOGICA DEI LINK (MOLTO IMPORTANTE):
Genera i link seguendo questa struttura (usa minuscolo, sostituisci spazi con %20):
- Incantesimi: https://{url}/spells.html#[nome]_[fonte] (es. fireball_phb, magic%20missile_phb).
- Mostri: https://{url}/bestiary.html#[nome]_[fonte] (es. ancient%20red%20dragon_mm, goblin_mm).
- Oggetti: https://{url}/items.html#[nome]_[fonte] (es. plate%20armor_phb, bag%20of%20holding_dmg).
- Regole: https://{url}/rules.html

NOTE SULLE FONTI:
- Usa '_phb' per contenuti del Player's Handbook.
- Usa '_mm' per i mostri del Monster Manual.
- Usa '_dmg' per oggetti magici del Dungeon Master's Guide.
- Se non sei sicuro della fonte, prova con '_phb'.

Se l'utente chiede di regole che appartengono all'altra versione di D&D (es. chiede di regole 2024 mentre sei in modalità 2014), rispondi secondo la tua modalità attuale ma avvisalo che può cambiare versione con /2014 o /2024.
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info(f"Command /start in chat {update.effective_chat.id}")
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
    logging.info(f"Command /2014 in chat {chat_id}")
    user_versions[chat_id] = "2014"
    chat_histories[chat_id] = [{"role": "system", "content": get_system_prompt("2014")}]
    last_activity[chat_id] = datetime.now()
    await update.message.reply_text("📚 Codex20 impostato sulla versione **2014**. I link punteranno a 2014.5e.tools.")

async def set_version_2024(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    logging.info(f"Command /2024 in chat {chat_id}")
    user_versions[chat_id] = "2024"
    chat_histories[chat_id] = [{"role": "system", "content": get_system_prompt("2024")}]
    last_activity[chat_id] = datetime.now()
    await update.message.reply_text("✨ Codex20 impostato sulla versione **2024 (Revised)**. I link punteranno a 5e.tools.")

async def reset_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    logging.info(f"Command /reset in chat {chat_id}")
    version = user_versions.get(chat_id, "2014")
    chat_histories[chat_id] = [{"role": "system", "content": get_system_prompt(version)}]
    last_activity[chat_id] = datetime.now()
    await update.message.reply_text(f"✨ I tomi ({version}) sono stati riposti. Cronologia resettata.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    logging.info(f"Command /status in chat {chat_id}")
    version = user_versions.get(chat_id, "2014")
    
    # Info sul modello e chiave
    model_info = f"Gemini ({GEMINI_MODEL})"
    key_info = f"Chiave attiva: {gemini_manager.current_key_index + 1}/{len(gemini_manager.api_keys)}"
        
    messages_count = len(chat_histories.get(chat_id, []))
    await update.message.reply_text(
        f"📊 **Stato Codex20**\n"
        f"Versione attiva: {version}\n"
        f"Modello in uso: {model_info}\n"
        f"{key_info}\n"
        f"Messaggi in memoria: {messages_count}/20"
    )

# Task: Reset automatico a Mezzanotte
async def midnight_reset(context: ContextTypes.DEFAULT_TYPE):
    global chat_histories
    logging.info("🌙 Eseguo il reset di mezzanotte per tutte le chat.")
    for chat_id in chat_histories.keys():
        version = user_versions.get(chat_id, "2014")
        chat_histories[chat_id] = [{"role": "system", "content": get_system_prompt(version)}]

# Task: Controllo inattività (5 ore)
async def inactivity_check(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    to_reset = []
    for chat_id, last_time in last_activity.items():
        if now - last_time > timedelta(hours=5):
            to_reset.append(chat_id)
    
    for chat_id in to_reset:
        logging.info(f"⌛ Reset inattività per chat {chat_id}")
        version = user_versions.get(chat_id, "2014")
        chat_histories[chat_id] = [{"role": "system", "content": get_system_prompt(version)}]
        # Non eliminiamo last_activity qui per evitare loop, ma resettiamo il tempo
        last_activity[chat_id] = now

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    user_text = update.message.text
    bot_username = context.bot.username

    # Logica per Gruppi: rispondi solo se taggato, se è reply a me o se è chat privata
    is_private = update.message.chat.type == "private"
    is_tagged = f"@{bot_username}".lower() in user_text.lower()
    is_reply_to_me = update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id
    
    logging.info(f"Messaggio ricevuto in {update.message.chat.type} ({chat_id}). Private: {is_private}, Tagged: {is_tagged}, ReplyToMe: {is_reply_to_me}")

    if not (is_private or is_tagged or is_reply_to_me):
        return

    # Rimuovi il tag e pulizia testo
    clean_text = re.sub(rf"@{re.escape(bot_username)}[:,]?", "", user_text, flags=re.IGNORECASE).strip()
    
    if not clean_text and is_tagged:
        await update.message.reply_text("Sì? Come posso aiutare la tua compagnia di avventurieri?")
        return
    
    # Aggiorna attività
    last_activity[chat_id] = datetime.now()
    
    if chat_id not in chat_histories:
        version = user_versions.get(chat_id, "2014")
        chat_histories[chat_id] = [{"role": "system", "content": get_system_prompt(version)}]
    
    # --- RICERCA CONOSCENZA LOCALE (RAG) ---
    # Cerca entità (incantesimi, mostri, oggetti) nel testo del messaggio per iniettare dati reali
    entities = kb.find_potential_entities(clean_text)
    logging.info(f"Entità identificate: {entities}")
    knowledge_injection = ""
    for entity_name in entities:
        entity_data = kb.get_entity_data(entity_name)
        if entity_data:
            logging.info(f"Iniezione dati per: {entity_name} ({entity_data['type']})")
            # Converte i dati JSON in stringa per fornirli come contesto al modello AI
            knowledge_injection += f"\n\nDATI DI RIFERIMENTO ({entity_data['type']}):\n{json.dumps(entity_data['data'], indent=2, ensure_ascii=False)}"
        else:
            logging.warning(f"Dati non trovati per entità identificata: {entity_name}")

    # Se abbiamo trovato dati nel database locale, li aggiungiamo come messaggio di sistema 'RAG'
    if knowledge_injection:
        knowledge_msg = {"role": "system", "content": f"Usa questi dati reali per rispondere accuratamente alla domanda dell'utente. Se i dati non corrispondono esattamente a ciò che l'utente chiede, ignorali o usali come contesto.{knowledge_injection}"}
        chat_histories[chat_id].append(knowledge_msg)
    
    # Aggiunge il messaggio pulito dell'utente alla storia
    current_user_message = {"role": "user", "content": clean_text}
    chat_histories[chat_id].append(current_user_message)
    placeholder = await update.message.reply_text("📜 Consultando i tomi...")

    try:
        # Recupera la storia attuale per questa chat
        history = chat_histories[chat_id]
        system_instruction = None
        
        # Estrai le istruzioni di sistema (di solito il primo messaggio della history)
        if history and history[0]['role'] == 'system':
            system_instruction = history[0]['content']
            history_to_process = history[1:]
        else:
            history_to_process = history

        # --- LOGICA ATTIVA: GEMINI con Rotazione Chiavi ---
        gemini_history = []
        pending_system_content = ""
        
        for msg in history_to_process:
            role = msg['role']
            content = msg['content']
            if role == 'system':
                # I messaggi di sistema extra (RAG) vengono iniettati nel messaggio user successivo
                pending_system_content += f"\n\n[CONTESTO AGGIUNTIVO]: {content}"
            elif role == 'user':
                final_content = content + pending_system_content
                gemini_history.append({"role": "user", "parts": [final_content]})
                pending_system_content = ""
            elif role == 'assistant':
                gemini_history.append({"role": "model", "parts": [content]})
        
        # Se c'è ancora contesto pendente, aggiungilo all'ultimo messaggio user
        if pending_system_content and gemini_history:
            for i in range(len(gemini_history) - 1, -1, -1):
                if gemini_history[i]['role'] == 'user':
                    gemini_history[i]['parts'][0] += pending_system_content
                    break

        bot_response = await gemini_manager.generate_content_async(gemini_history, system_instruction)
        
        # Aggiorna la storia interna con la risposta del bot
        chat_histories[chat_id].append({"role": "assistant", "content": bot_response})
        
        if len(chat_histories[chat_id]) > 21:
            # Manteniamo il primo (system prompt) e gli ultimi 20
            chat_histories[chat_id] = [chat_histories[chat_id][0]] + chat_histories[chat_id][-20:]

        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=placeholder.message_id,
            text=bot_response
        )
    except Exception as e:
        logging.error(f"Errore per chat {chat_id}: {e}")
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=placeholder.message_id,
            text=f"❌ Errore durante la consultazione dei tomi: {str(e)}"
        )

if __name__ == '__main__':
    if not TELEGRAM_TOKEN:
        print("Errore: TELEGRAM_TOKEN non trovato")
        exit(1)
        
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    job_queue = application.job_queue
    
    # Schedulazione Reset Mezzanotte
    from datetime import time
    job_queue.run_daily(midnight_reset, time=time(0, 0, 0))
    
    # Schedulazione Controllo Inattività ogni 30 minuti
    job_queue.run_repeating(inactivity_check, interval=1800, first=10)
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("2014", set_version_2014))
    application.add_handler(CommandHandler("2024", set_version_2024))
    application.add_handler(CommandHandler("reset", reset_manual))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    application.add_error_handler(error_handler)
    
    print(f"Codex20 avviato con modello Gemini ({GEMINI_MODEL}) - {len(GEMINI_API_KEYS)} chiavi caricate")
    application.run_polling()
