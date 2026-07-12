"""
Codex20 Persistent Session Storage
Storage SQLite per persistenza delle conversazioni e campagna.

v5.0 Security improvements:
- Aggiunto campo `last_access` per tracking attività
- Cleanup automatico sessioni >7 giorni inattive
- Metodo cleanup_all_expired per cleanup globale
- clear_all_sessions per cancellazione completa per utente
"""

import sqlite3
import json
import time
import os
import logging
import contextlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

# Connection pooling (max 5 connessioni simultanee)
_MAX_POOL_SIZE = 5
_POOL_CONNECTIONS: list[sqlite3.Connection] = []


def _get_connection():
    """Recupera connessione dal pool (o crea nuova)."""
    global _POOL_CONNECTIONS
    if len(_POOL_CONNECTIONS) < _MAX_POOL_SIZE:
        db_path = os.environ.get("DB_PATH", "data/sessions.db")
        conn = sqlite3.connect(
            db_path,
            timeout=10,
            isolation_level=None,
        )
        _POOL_CONNECTIONS.append(conn)
        return conn
    oldest = _POOL_CONNECTIONS.pop(0)
    oldest.close()
    db_path = os.environ.get("DB_PATH", "data/sessions.db")
    conn = sqlite3.connect(
        db_path,
        timeout=10,
        isolation_level=None,
    )
    _POOL_CONNECTIONS.append(conn)
    return conn


def _return_connection(conn: sqlite3.Connection):
    """Restituisce connessione al pool."""
    global _POOL_CONNECTIONS
    conn.close()
    if _POOL_CONNECTIONS:
        oldest = _POOL_CONNECTIONS.pop(0)
        oldest.close()


@contextlib.contextmanager
def get_db_connection():
    """Context manager per connessioni DB (usa pool)."""
    conn = _get_connection()
    try:
        yield conn
    finally:
        _return_connection(conn)


class PersistentSessionManager:
    """
    Gestisce sessioni utente con storage persistente SQLite.
    Supporta TTL (7 giorni default) per pulizia automatica.

    v5.0: last_access tracking, cleanup globale, clear_all_sessions.
    """

    def __init__(self, db_path: str = "data/sessions.db",
                 max_messages: int = 20, ttl_hours: int = 168):  # 7 giorni = 168 ore
        self.db_path = db_path
        self.max_messages = max_messages
        self.ttl_hours = ttl_hours
        self._cache: dict[str, list] = {}

        env_path = os.environ.get("DB_PATH")
        os.environ["DB_PATH"] = db_path
        self._init_database()
        logger.info(f"Session DB inizializzato: {db_path} (max={max_messages}, ttl={ttl_hours}h)")

    def _init_database(self, db_path: str = None):
        """Inizializza database SQLite con tabelle e indici.
        Migra schema esistente per aggiungere `last_access`."""
        path = db_path or self.db_path
        env_path = os.environ.get("DB_PATH")
        os.environ["DB_PATH"] = path
        try:
            global _POOL_CONNECTIONS
            _POOL_CONNECTIONS.clear()
            with get_db_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        timestamp TEXT NOT NULL,
                        last_access TEXT NOT NULL,
                        user_message TEXT NOT NULL,
                        bot_response TEXT NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_user_timestamp
                    ON sessions(user_id, timestamp)
                """)
                conn.commit()

                # Migra colonne se mancano
                columns = {desc[1] for desc in conn.execute("PRAGMA table_info(sessions)").fetchall()}
                if "last_access" not in columns:
                    conn.execute("ALTER TABLE sessions ADD COLUMN last_access TEXT DEFAULT CURRENT_TIMESTAMP")
                    conn.commit()
                    logger.info("Colonna `last_access` aggiunta via migrazione")
        finally:
            if env_path is not None:
                os.environ["DB_PATH"] = env_path
            elif "DB_PATH" in os.environ:
                del os.environ["DB_PATH"]

    def add_message(self, user_id: int, user_message: str, bot_response: str):
        """Salva messaggio con aggiornamento last_access."""
        timestamp = datetime.now().isoformat()

        with get_db_connection() as conn:
            try:
                conn.execute("""
                    INSERT INTO sessions (user_id, timestamp, last_access, user_message, bot_response)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, timestamp, timestamp, user_message, bot_response))

                conn.commit()

                # Aggiorna last_access per utente
                conn.execute("""
                    UPDATE sessions SET last_access = ? WHERE user_id = ?
                """, (timestamp, user_id))
                conn.commit()

            except Exception as e:
                conn.rollback()
                logger.warning(f"Session save error: {e}")

    def get_conversation_context(self, user_id: int, max_context: int = 5) -> str:
        """Recupera contesto conversazione per utente."""
        cutoff_time = (datetime.now() - timedelta(hours=self.ttl_hours)).isoformat()

        with get_db_connection() as conn:
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
        for msg in reversed(messages):
            user_text = (msg['user_message'][:200] + "..."
                         if len(msg['user_message']) > 200 else msg['user_message'])
            bot_text = (msg['bot_response'][:300] + "..."
                        if len(msg['bot_response']) > 300 else msg['bot_response'])
            context += f"User: {user_text}\n"
            context += f"Codex20: {bot_text}\n\n"

        return context

    def clear_session(self, user_id: int):
        """Cancella tutte le conversazioni di un utente."""
        with get_db_connection() as conn:
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            conn.commit()

    def clear_all_sessions(self, user_id: int):
        """Cancella TUTTE le sessioni di un utente (anche scadute)."""
        with get_db_connection() as conn:
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            conn.commit()

    def get_expired_sessions(self, user_id: int) -> List[dict]:
        """Lista sessioni scadute per utente."""
        cutoff_time = (datetime.now() - timedelta(hours=self.ttl_hours)).isoformat()

        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT id, user_id, timestamp, last_access, user_message
                FROM sessions
                WHERE user_id = ? AND last_access < ?
            """, (user_id, cutoff_time))
            rows = cursor.fetchall()

        expired = []
        for row in rows:
            expired.append({
                "id": row["id"],
                "user_id": row["user_id"],
                "timestamp": row["timestamp"],
                "last_access": row["last_access"],
                "user_message": row["user_message"][:100]
            })
        return expired

    def cleanup_expired(self) -> int:
        """Rimuove sessioni scadute per un utente specifico."""
        cutoff_time = (datetime.now() - timedelta(hours=self.ttl_hours)).isoformat()

        with get_db_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM sessions
                WHERE last_access < ?
            """, (cutoff_time,))
            conn.commit()
            return cursor.rowcount

    def cleanup_all_expired(self) -> int:
        """Rimuove sessioni scadute per TUTTI gli utenti. Usato dal cleanup background."""
        cutoff_time = (datetime.now() - timedelta(hours=self.ttl_hours)).isoformat()

        with get_db_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM sessions
                WHERE last_access < ?
            """, (cutoff_time,))
            deleted = cursor.rowcount
            conn.commit()
            return deleted

    def get_session_stats(self, user_id: int) -> dict:
        """Restituisce statistiche sessione utente."""
        cutoff_time = (datetime.now() - timedelta(hours=self.ttl_hours)).isoformat()

        with get_db_connection() as conn:
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as message_count,
                    MAX(timestamp) as last_activity,
                    MAX(last_access) as last_access,
                    MIN(timestamp) as first_message
                FROM sessions
                WHERE user_id = ? AND timestamp > ?
            """, (user_id, cutoff_time))

            result = cursor.fetchone()

        message_count = result[0] if result and result[0] else 0
        last_activity = result[1] if result and result[1] else None
        last_access = result[2] if result and result[2] else None
        first_message = result[3] if result and result[3] else None

        return {
            'message_count': message_count,
            'last_activity': last_activity,
            'last_access': last_access,
            'first_message': first_message,
            'session_active': message_count > 0
        }

    def get_user_chats(self, user_id: int, limit: int = 50) -> list:
        """Lista delle ultime chat/conversazioni per utente."""
        cutoff_time = (datetime.now() - timedelta(hours=self.ttl_hours)).isoformat()
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT user_message, timestamp, last_access
                FROM sessions
                WHERE user_id = ? AND last_access > ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, cutoff_time, limit))
            rows = cursor.fetchall()
        chats = []
        for row in rows:
            chats.append({
                "title": row["user_message"][:80] + ("..." if len(row["user_message"]) > 80 else ""),
                "timestamp": row["timestamp"],
                "last_access": row["last_access"],
            })
        return chats

    def create_chat(self, user_id: int, chat_id: str):
        """Crea una nuova chat (placeholder, per compatibilità web)."""
        logger.info(f"Chat '{chat_id}' creata per user {user_id}")

    def get_chat_history(self, user_id: int, limit: int = 100) -> list:
        """Storico messaggi utente per chat."""
        cutoff_time = (datetime.now() - timedelta(hours=self.ttl_hours)).isoformat()
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT user_message, bot_response, timestamp
                FROM sessions
                WHERE user_id = ? AND timestamp > ?
                ORDER BY timestamp ASC
                LIMIT ?
            """, (user_id, cutoff_time, limit))
            rows = cursor.fetchall()
        history = []
        for row in rows:
            history.append({"role": "user", "content": row["user_message"], "timestamp": row["timestamp"]})
            history.append({"role": "assistant", "content": row["bot_response"], "timestamp": row["timestamp"]})
        return history
