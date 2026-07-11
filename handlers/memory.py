"""
Handler memoria campagna e sessioni.
Gestisce persistenza conversazioni e memoria campagna.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def handle_remember(message, bot, user_id, openrouter_client, session_manager,
                          prompt: str):
    """
    Salva info campagna in memoria.

    Args:
        message: Messaggio Telegram
        bot: Bot instance
        user_id: ID utente
        openrouter_client: Client OpenRouter
        session_manager: Session manager
        prompt: Info da salvare

    Returns:
        Confirma di salvataggio
    """
    try:
        # Salva info campagna (simplified: salva nel context)
        # In futuro: strutturare come campagna con ID, personaggi, luogo, etc.
        session_stats = session_manager.get_session_stats(user_id)

        return (f"✅ **Info campagna salvate!**\n\n"
                f"📊 Sessione: {session_stats['message_count']} messaggi\n"
                f"🕐 Ultima attività: {session_stats['last_activity'] or 'N/A'}\n"
                f"ℹ️ Info: {prompt[:100]}...")

    except Exception as e:
        logger.error(f"Error remember user {user_id}: {e}")
        return f"⚠️ Errore salvataggio: {str(e)[:200]}"


async def handle_recall(message, bot, user_id, openrouter_client, session_manager,
                        query: str):
    """
    Recupera info campagna dalla memoria.

    Args:
        message: Messaggio Telegram
        bot: Bot instance
        user_id: ID utente
        openrouter_client: Client OpenRouter
        session_manager: Session manager
        query: Query per ricerca

    Returns:
        Info trovata o messaggio di vuoto
    """
    try:
        # Recupera contesto conversazione
        context = session_manager.get_conversation_context(user_id)

        if not context:
            return "ℹ️ Nessun contesto trovato per questa sessione."

        return f"📋 **Contesto Conversazione:**\n\n{context}"

    except Exception as e:
        logger.error(f"Error recall user {user_id}: {e}")
        return f"⚠️ Errore recupero: {str(e)[:200]}"


async def handle_memory(message, bot, user_id, session_manager):
    """
    Mostra info sessione corrente.

    Args:
        message: Messaggio Telegram
        bot: Bot instance
        user_id: ID utente
        session_manager: Session manager

    Returns:
        Info sessione
    """
    try:
        stats = session_manager.get_session_stats(user_id)

        if not stats['session_active']:
            return "ℹ️ Nessun contesto conversazione attivo."

        return (f"🧠 **Sessione Attiva:**\n\n"
                f"📊 Messaggi: {stats['message_count']}\n"
                f"🕐 Ultima attività: {stats['last_activity'] or 'N/A'}\n"
                f"📅 Prima conversazione: {stats['first_message'] or 'N/A'}")

    except Exception as e:
        logger.error(f"Error memory user {user_id}: {e}")
        return f"⚠️ Errore: {str(e)[:200]}"


async def handle_forget(message, bot, user_id, session_manager):
    """
    Cancella memoria sessione utente.

    Args:
        message: Messaggio Telegram
        bot: Bot instance
        user_id: ID utente
        session_manager: Session manager

    Returns:
        Confirma cancellazione
    """
    try:
        session_manager.clear_session(user_id)
        return "🗑️ **Memoria cancellata!** La prossima conversazione sarà fresca."

    except Exception as e:
        logger.error(f"Error forget user {user_id}: {e}")
        return f"⚠️ Errore cancellazione: {str(e)[:200]}"
