# Codex20 Session Memory Patch
# Add this after the imports and before the handlers

# ==========================================
# SESSION MEMORY MANAGEMENT
# ==========================================

from collections import defaultdict, deque
from datetime import datetime, timedelta
import time

class SessionManager:
    """Gestione memoria conversazioni per Codex20"""
    
    def __init__(self, max_memory_per_user=20, memory_ttl_hours=24):
        self.sessions = defaultdict(lambda: deque(maxlen=max_memory_per_user))
        self.last_activity = defaultdict(lambda: datetime.now())
        self.memory_ttl = timedelta(hours=memory_ttl_hours)
        self.max_memory = max_memory_per_user
    
    def add_message(self, user_id: int, user_message: str, bot_response: str):
        """Aggiunge coppia domanda-risposta alla sessione utente"""
        
        # Cleanup old sessions
        self._cleanup_old_sessions()
        
        # Aggiorna timestamp attività
        self.last_activity[user_id] = datetime.now()
        
        # Aggiungi alla memoria (automatically removes old messages se > max_memory)
        self.sessions[user_id].append({
            'timestamp': datetime.now(),
            'user': user_message,
            'bot': bot_response
        })
    
    def get_conversation_context(self, user_id: int, max_context_messages=5) -> str:
        """Recupera contesto conversazione recente"""
        
        if user_id not in self.sessions or not self.sessions[user_id]:
            return ""
        
        # Prendi gli ultimi N messaggi
        recent_messages = list(self.sessions[user_id])[-max_context_messages:]
        
        context = "\n\nCONTESTO CONVERSAZIONE PRECEDENTE:\n"
        for msg in recent_messages:
            # Limita lunghezza per evitare token overflow
            user_text = msg['user'][:200] + "..." if len(msg['user']) > 200 else msg['user']
            bot_text = msg['bot'][:300] + "..." if len(msg['bot']) > 300 else msg['bot']
            
            context += f"User: {user_text}\n"
            context += f"Codex20: {bot_text}\n\n"
        
        return context
    
    def clear_session(self, user_id: int):
        """Cancella sessione utente"""
        if user_id in self.sessions:
            del self.sessions[user_id]
        if user_id in self.last_activity:
            del self.last_activity[user_id]
    
    def _cleanup_old_sessions(self):
        """Rimuove sessioni inattive da troppo tempo"""
        current_time = datetime.now()
        expired_users = [
            user_id for user_id, last_active in self.last_activity.items()
            if current_time - last_active > self.memory_ttl
        ]
        
        for user_id in expired_users:
            self.clear_session(user_id)
    
    def get_session_info(self, user_id: int) -> dict:
        """Info debug sessione"""
        return {
            'messages_count': len(self.sessions.get(user_id, [])),
            'last_activity': self.last_activity.get(user_id),
            'session_exists': user_id in self.sessions
        }

# Inizializza Session Manager globale
session_manager = SessionManager(max_memory_per_user=15, memory_ttl_hours=48)

# ==========================================
# UPDATED CHAT HANDLER WITH MEMORY
# ==========================================

@dp.message(F.text)
async def chat_handler_with_memory(message: types.Message):
    """
    Handler principale CON MEMORIA DI SESSIONE
    """
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    user_id = message.from_user.id
    user_message = message.text
    
    # Controllo per adventure intent senza comando esplicito
    adventure_keywords = [
        'avventura', 'adventure', 'dungeon', 'quest', 'missione',
        'grotta', 'torre', 'castello', 'bosco', 'foresta', 'nave',
        'goblin', 'orchi', 'fantasmi', 'non morti', 'drago', 'banditi'
    ]
    
    # Check se il messaggio contiene "help" o parole chiave help
    if any(word in user_message.lower() for word in ['help', 'aiuto', 'comandi', 'cosa puoi fare']):
        await help_handler(message)
        return
    
    # Check per adventure intent
    if any(keyword in user_message.lower() for keyword in adventure_keywords):
        if any(indicator in user_message.lower() for indicator in ['livello', 'level', 'lv', 'pcs', 'giocatori', 'party']):
            try:
                adventure = adventure_creator.create_adventure(user_message)
                response = adventure_creator.format_quick_summary(adventure)
                
                # Salva in sessione
                session_manager.add_message(user_id, user_message, response)
                
                await message.answer(
                    f"🎯 **Rilevata richiesta avventura!**\n\n{response}",
                    parse_mode="Markdown"
                )
                return
            except Exception as e:
                logger.error(f"Errore adventure intent: {e}")
    
    # 1. Recupera contesto conversazione
    conversation_context = session_manager.get_conversation_context(user_id, max_context_messages=3)
    
    # 2. Ricerca Dinamica nei manuali (5etools)
    tomi_context = search_5etools(user_message)
    
    # 3. Composizione del Prompt CON MEMORIA
    prompt = f"""{system_context_base}{conversation_context}{tomi_context}

Utente: {user_message}"""
    
    try:
        response_text = await generate_content_safe(prompt)
        if not response_text: return

        # Character sheet JSON detection (unchanged)
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```|(\{.*?\})", response_text, re.DOTALL)
        
        if json_match:
            try:
                json_str = json_match.group(1) if json_match.group(1) else json_match.group(2)
                char_data = json.loads(json_str)
                
                pdf_path = create_pdf(char_data, user_id)
                
                clean_text = re.sub(r"```(?:json)?.*?```", "", response_text, flags=re.DOTALL).strip()
                if clean_text == response_text.strip():
                     clean_text = response_text.replace(json_str, "").strip()

                # Salva in sessione
                session_manager.add_message(user_id, user_message, clean_text + " [PDF Generated]")

                if clean_text: 
                    try:
                        await message.answer(clean_text, parse_mode="Markdown")
                    except Exception:
                        await message.answer(clean_text)
                
                if pdf_path:
                    try:
                        await message.answer_document(
                            FSInputFile(pdf_path), 
                            caption=f"Ecco la scheda di *{char_data.get('nome')}*! 🎲",
                            parse_mode="Markdown"
                        )
                    except Exception:
                        await message.answer_document(
                            FSInputFile(pdf_path), 
                            caption=f"Ecco la scheda di {char_data.get('nome')}! 🎲"
                        )
                    
                    if os.path.exists(pdf_path): 
                        os.remove(pdf_path)
                else:
                    await message.answer("Dati generati correttamente, ma c'è stato un problema nella creazione fisica del PDF. 🎲")
                return
            
            except Exception as e:
                logger.error(f"Errore parsing JSON o generazione PDF: {e}")

        # Risposta standard CON salvataggio in sessione
        response_text = response_text.strip()
        
        # Salva conversazione
        session_manager.add_message(user_id, user_message, response_text)
        
        if len(response_text) > 4000:
            truncated = f"{response_text[:4000]}..."
            await message.answer(truncated)
        else:
            try:
                await message.answer(f"{response_text}\n\n🎲", parse_mode="Markdown")
            except Exception:
                await message.answer(f"{response_text}\n\n🎲")
            
    except Exception as e:
        logger.error(f"Errore generale: {e}")
        await message.answer("Spiacente, Codex20 ha subito un glitch arcano. Riprova! 🎲")

# ==========================================
# NEW COMMANDS FOR SESSION MANAGEMENT  
# ==========================================

@dp.message(Command("memory"))
async def memory_command(message: types.Message):
    """Mostra info sessione corrente"""
    user_id = message.from_user.id
    info = session_manager.get_session_info(user_id)
    
    await message.answer(
        f"🧠 **Memoria Sessione**\n\n"
        f"• Messaggi salvati: {info['messages_count']}/15\n"
        f"• Ultima attività: {info['last_activity'].strftime('%H:%M %d/%m') if info['last_activity'] else 'Mai'}\n"
        f"• Sessione attiva: {'Sì' if info['session_exists'] else 'No'}\n\n"
        f"_La memoria viene mantenuta per 48 ore dall'ultimo messaggio._"
    )

@dp.message(Command("forget"))
async def forget_command(message: types.Message):
    """Cancella memoria sessione"""
    user_id = message.from_user.id
    session_manager.clear_session(user_id)
    
    await message.answer(
        "🧠 **Memoria cancellata!**\n\n"
        "La conversazione ripartirà da zero dal prossimo messaggio."
    )

# Update help command
def update_help_with_memory():
    return """🎲 **CODEX20 - IL CUSTODE DEI TOMI**
*Versione 2.1 con Session Memory*

📖 **CONSULTAZIONE D&D 5E:**
Chiedi qualsiasi cosa su regole, mostri, incantesimi!
*"Cos'è un Beholder?"* - *"Come funziona Fireball?"*

👤 **GENERAZIONE PERSONAGGI:**
*"Crea un mago elfo livello 3"* → Scheda PDF completa

🗺️ **ADVENTURE CREATOR:**
• `/adventure <prompt>` - Avventura completa bilanciata
• `/adventure_md <prompt>` - Con markdown Homebrewery

🧠 **GESTIONE MEMORIA (NUOVO!):**
• `/memory` - Info sulla memoria della conversazione
• `/forget` - Cancella la memoria e ricomincia

**Esempi Adventures:**
• `/adventure Grotta goblin per 4 PCs livello 3`
• `/adventure Torre mago abbandonata livello 5`

🔧 **UTILITÀ:**
• `/mappa` - Debug mapping campi PDF  
• `/help` - Questo messaggio

*Powered by Gemini 2.0 Flash + 34MB 5etools database*
*Ora con memoria di conversazione per interazioni più fluide!* 🎲"""

# REPLACE the old chat_handler with chat_handler_with_memory
# And update the help_handler to use update_help_with_memory()