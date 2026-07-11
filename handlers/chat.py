"""
Handler chat generico con persistenza sessione.
Risponde a messaggi normali (non comandi) con AI.
"""

import logging

from core.session import PersistentSessionManager

logger = logging.getLogger(__name__)


async def handle_chat(message, bot, user_id, openrouter_client, session_manager,
                       rag, prompt: str, bot_response: str):
    """
    Handler per chat generica con persistenza sessione.
    Invia prompt all'AI per rispondere e salva nel database.

    Args:
        message: Messaggio Telegram
        bot: Bot instance
        user_id: ID utente
        openrouter_client: Client OpenRouter
        session_manager: Session manager
        rag: RAG engine per ricerca tomi
        prompt: Prompt utente
        bot_response: Risposta dell'AI

    Returns:
        Risposta dell'AI, o messaggio di errore
    """
    try:
        # Aggiungi contesto RAG se rilevante
        rag_data = ""
        if rag:
            rag_data = rag.search_5etools(prompt)
        if rag_data:
            prompt += rag_data

        # Costruisci conversazione
        messages = [
            {"role": "system", "content": "Sei un assistente esperto di D&D 5e. Rispondi in modo completo e dettagliato."},
            {"role": "user", "content": prompt},
        ]

        # Invia all'AI
        logger.info(f"Chat generica per user {user_id}: {prompt[:100]}...")
        response = openrouter_client.chat_completion(messages)

        # SALVA SESSIONE nel database
        session_manager.add_message(user_id, prompt, response if response else "⚠️ Errore generazione risposta.")

        return response if response else "⚠️ Errore generazione risposta. Riprova."

    except Exception as e:
        logger.error(f"Error chat generica user {user_id}: {e}")
        return f"⚠️ Errore: {str(e)[:200]}"
