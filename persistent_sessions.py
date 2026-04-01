# Codex20 Persistent Session Storage
# For production deployment with session persistence across bot restarts

import sqlite3
import json
import time
from datetime import datetime, timedelta

class PersistentSessionManager:
    """Session manager con storage SQLite per persistenza"""
    
    def __init__(self, db_path="data/sessions.db", max_messages=20, ttl_hours=72):
        self.db_path = db_path
        self.max_messages = max_messages
        self.ttl_hours = ttl_hours
        self._init_database()
    
    def _init_database(self):
        """Inizializza database SQLite"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    user_message TEXT NOT NULL,
                    bot_response TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Index per performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user_timestamp ON sessions(user_id, timestamp)")
            
    def add_message(self, user_id: int, user_message: str, bot_response: str):
        """Salva messaggio in database"""
        timestamp = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            # Aggiungi nuovo messaggio
            conn.execute("""
                INSERT INTO sessions (user_id, timestamp, user_message, bot_response)
                VALUES (?, ?, ?, ?)
            """, (user_id, timestamp, user_message, bot_response))
            
            # Mantieni solo gli ultimi N messaggi per utente
            conn.execute("""
                DELETE FROM sessions 
                WHERE user_id = ? AND id NOT IN (
                    SELECT id FROM sessions 
                    WHERE user_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                )
            """, (user_id, user_id, self.max_messages))
            
    def get_conversation_context(self, user_id: int, max_context=5) -> str:
        """Recupera contesto da database"""
        cutoff_time = (datetime.now() - timedelta(hours=self.ttl_hours)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT user_message, bot_response, timestamp
                FROM sessions 
                WHERE user_id = ? AND timestamp > ?
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (user_id, cutoff_time, max_context))
            
            messages = cursor.fetchall()
        
        if not messages:
            return ""
            
        context = "\n\nCONTESTO CONVERSAZIONE PRECEDENTE:\n"
        
        # Reverse per ordine cronologico
        for msg in reversed(messages):
            user_text = msg['user_message'][:200] + "..." if len(msg['user_message']) > 200 else msg['user_message']
            bot_text = msg['bot_response'][:300] + "..." if len(msg['bot_response']) > 300 else msg['bot_response']
            
            context += f"User: {user_text}\n"
            context += f"Codex20: {bot_text}\n\n"
        
        return context
    
    def clear_session(self, user_id: int):
        """Cancella tutte le conversazioni dell'utente"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    
    def cleanup_expired(self):
        """Rimuove conversazioni scadute"""
        cutoff_time = (datetime.now() - timedelta(hours=self.ttl_hours)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM sessions WHERE timestamp < ?", (cutoff_time,))
            return cursor.rowcount
    
    def get_session_stats(self, user_id: int) -> dict:
        """Statistiche sessione utente"""
        cutoff_time = (datetime.now() - timedelta(hours=self.ttl_hours)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as message_count,
                    MAX(timestamp) as last_activity,
                    MIN(timestamp) as first_message
                FROM sessions 
                WHERE user_id = ? AND timestamp > ?
            """, (user_id, cutoff_time))
            
            result = cursor.fetchone()
            
        return {
            'message_count': result[0] if result[0] else 0,
            'last_activity': result[1],
            'first_message': result[2],
            'session_active': result[0] > 0 if result[0] else False
        }

# Daily cleanup task
def schedule_cleanup(session_manager):
    """Scheduled cleanup - può essere chiamato da cron"""
    removed = session_manager.cleanup_expired()
    print(f"Session cleanup: removed {removed} expired messages")
    return removed

# Usage in bot
"""
# Replace SessionManager with:
session_manager = PersistentSessionManager(
    db_path="data/sessions.db", 
    max_messages=20, 
    ttl_hours=72
)

# Add cleanup command
@dp.message(Command("admin_cleanup"))  
async def admin_cleanup(message: types.Message):
    if message.from_user.id == ADMIN_USER_ID:  # Set admin ID
        removed = session_manager.cleanup_expired()
        await message.answer(f"🧹 Cleanup completed: {removed} expired sessions removed")
"""