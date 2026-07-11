"""
Codex20 Persistent Session Storage
Storage SQLite per persistenza delle conversazioni e campagna.

Miglioramenti v3.1:
- Connection pooling (max 5 connessioni)
- Context manager per connessioni
- Timeout su operazioni DB
- Error handling migliorato
"""

import sqlite3
import json
import time
import os
import logging
import contextlib
from datetime import datetime, timedelta
from typing import Optional

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
            isolation_level=None,  # Autocommit
        )
        _POOL_CONNECTIONS.append(conn)
        return conn
    # Se pool pieno, chiudi la più vecchia e usa quella
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
    Supporta TTL (time-to-live) per pulizia automatica e limiti dimensione.

    v3.1: connection pooling, timeout, error handling migliorato.
    """

    def __init__(self, db_path: str = "data/sessions.db",
                 max_messages: int = 20, ttl_hours: int = 72):
        """
        Inizializza session manager.

        Args:
            db_path: Percorso file database SQLite
            max_messages: Max messaggi conservati per utente
            ttl_hours: Ore di validità sessione prima di scadenza
        """
        self.db_path = db_path
        self.max_messages = max_messages
        self.ttl_hours = ttl_hours

        # Imposta DB_PATH permanentemente per questo manager
        env_path = os.environ.get("DB_PATH")
        os.environ["DB_PATH"] = db_path
        # Inizializza tabelle
        self._init_database()
        logger = logging.getLogger(__name__)
        logger.info(f"Session DB inizializzato: {db_path} (max={max_messages}, ttl={ttl_hours}h)")

    def _init_database(self, db_path: str = None):
        """Inizializza database SQLite con tabelle e indici.

        Args:
            db_path: Percorso file database. Se None, usa self.db_path.
        """
        # Usa self.db_path o il path passato
        path = db_path or self.db_path
        # Imposta DB_PATH per override temporaneo
        env_path = os.environ.get("DB_PATH")
        os.environ["DB_PATH"] = path
        try:
            # Chiudi connessioni pool precedenti per forzare creazione con nuovo path
            global _POOL_CONNECTIONS
            _POOL_CONNECTIONS.clear()
            with get_db_connection() as conn:
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
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_user_timestamp
                    ON sessions(user_id, timestamp)
                """)
                conn.commit()
        finally:
            # Ripristina DB_PATH originale
            if env_path is not None:
                os.environ["DB_PATH"] = env_path
            elif "DB_PATH" in os.environ:
                del os.environ["DB_PATH"]

    def _ensure_initialized(self):
        """Assicura che DB sia inizializzato."""
        try:
            # Chiudi connessioni pool precedenti per forzare creazione con nuovo path
            global _POOL_CONNECTIONS
            _POOL_CONNECTIONS.clear()
            with get_db_connection() as conn:
                conn.execute("SELECT 1")
        except sqlite3.OperationalError:
            self._init_database()

    def add_message(self, user_id: int, user_message: str, bot_response: str):
        """
        Salva messaggio in database.

        Args:
            user_id: ID utente Telegram
            user_message: Messaggio dell'utente
            bot_response: Risposta del bot
        """
        timestamp = datetime.now().isoformat()

        with get_db_connection() as conn:
            try:
                # Salva nuovo messaggio
                conn.execute("""
                    INSERT INTO sessions (user_id, timestamp, user_message, bot_response)
                    VALUES (?, ?, ?, ?)
                """, (user_id, timestamp, user_message, bot_response))

                # Mantieni solo ultimi N messaggi per utente (cleanup in-memory)
                conn.execute("""
                    DELETE FROM sessions
                    WHERE user_id = ? AND id NOT IN (
                        SELECT id FROM sessions
                        WHERE user_id = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                    )
                """, (user_id, user_id, self.max_messages))

                conn.commit()
            except Exception as e:
                conn.rollback()
                logger = logging.getLogger(__name__)
                logger.warning(f"Session save error: {e}")

    def get_conversation_context(self, user_id: int, max_context: int = 5) -> str:
        """
        Recupera contesto conversazione per utente.

        Args:
            user_id: ID utente
            max_context: Max messaggi da includere nel contesto

        Returns:
            Stringa con contesto conversazione formattato
        """
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

        # Reverse per ordine cronologico
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

    def cleanup_expired(self) -> int:
        """
        Rimuove conversazioni scadute (TTL).

        Returns:
            Numero di record eliminati
        """
        cutoff_time = (datetime.now() - timedelta(hours=self.ttl_hours)).isoformat()

        with get_db_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM sessions
                WHERE timestamp < ?
            """, (cutoff_time,))
            conn.commit()

            return cursor.rowcount

    def get_session_stats(self, user_id: int) -> dict:
        """
        Restituisce statistiche sessione utente.

        Returns:
            Dict con message_count, last_activity, first_message, session_active
        """
        cutoff_time = (datetime.now() - timedelta(hours=self.ttl_hours)).isoformat()

        with get_db_connection() as conn:
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as message_count,
                    MAX(timestamp) as last_activity,
                    MIN(timestamp) as first_message
                FROM sessions
                WHERE user_id = ? AND timestamp > ?
            """, (user_id, cutoff_time))

            result = cursor.fetchone()

        message_count = result[0] if result and result[0] else 0
        last_activity = result[1] if result and result[1] else None
        first_message = result[2] if result and result[2] else None

        return {
            'message_count': message_count,
            'last_activity': last_activity,
            'first_message': first_message,
            'session_active': message_count > 0
        }

    def get_user_chats(self, user_id: int, limit: int = 50) -> list:
        """Lista delle ultime chat/conversazioni per utente."""
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT user_message, timestamp
                FROM sessions
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, limit))
            rows = cursor.fetchall()
        chats = []
        for row in rows:
            chats.append({
                "title": row["user_message"][:80] + ("..." if len(row["user_message"]) > 80 else ""),
                "timestamp": row["timestamp"],
            })
        return chats

    def create_chat(self, user_id: int, chat_id: str):
        """Crea una nuova chat (placeholder, per compatibilità web)."""
        logger = logging.getLogger(__name__)
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
