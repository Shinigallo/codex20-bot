"""
Handler ricerca regole D&D 5e.
Usa RAG per cercare nei tomi ufficiali e rispondere con dati verificati.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def handle_search(message, bot, user_id, openrouter_client, session_manager,
                        rag, prompt: str):
    """
    Handler per ricerca regole D&D 5e.
    Combina ricerca nei tomi con risposta AI per spiegazioni in linguaggio naturale.

    Args:
        message: Messaggio Telegram
        bot: Bot instance
        user_id: ID utente
        openrouter_client: Client OpenRouter
        session_manager: Session manager
        rag: RAG engine per ricerca tomi
        prompt: Query dell'utente

    Returns:
        Risposta con dati trovati + spiegazione AI
    """
    try:
        # Cerca nei tomi
        rag_data = rag.search_5etools(prompt)

        # Se dati trovati, invia all'AI per spiegazione
        if rag_data:
            messages = [
                {"role": "system", "content": "Spiega le regole D&D 5e in linguaggio chiaro e comprensibile."},
                {"role": "user", "content": f"Basandoti sui dati trovati, spiega:\n{rag_data}\n\nDomanda utente: {prompt}"},
            ]
            response = openrouter_client.chat_completion(messages)
            return f"📜 **Dati dai Tomi (5etools):**\n{rag_data}\n\n**Spiegazione:**\n{response}"
        else:
            # Niente dati nei tomi, usa AI direttamente
            messages = [
                {"role": "system", "content": "Sei un esperto di D&D 5e. Rispondi in modo accurato alle domande sulle regole."},
                {"role": "user", "content": f"Spiega in modo chiaro e dettagliato: {prompt}"},
            ]
            response = openrouter_client.chat_completion(messages)
            return f"📜 **Risposta:**\n{response}"

    except Exception as e:
        logger.error(f"Error ricerca user {user_id}: {e}")
        return f"⚠️ Errore ricerca: {str(e)[:200]}"
