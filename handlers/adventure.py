"""
Handler avventure D&D 5e.
Genera avventure complete con background, incontri, NPC, tesori.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def handle_adventure(message, bot, user_id, openrouter_client, session_manager,
                            rag, adventure_creator, prompt: str, adventure_type: str = None):
    """
    Handler per creazione avventure.
    Invia prompt all'AI per generare avventura completa.

    Args:
        message: Messaggio Telegram
        bot: Bot instance
        user_id: ID utente
        openrouter_client: Client OpenRouter
        session_manager: Session manager
        rag: RAG engine per ricerca tomi
        adventure_creator: Creator avventure (base o advanced)
        prompt: Prompt utente per l'avventura
        adventure_type: Tipo avventura (nulla = completa, "quick" = rapida, "md" = markdown)

    Returns:
        Risposta dell'AI con avventura, o messaggio di errore
    """
    try:
        # Costruisci prompt per l'AI
        if adventure_type == "quick":
            prompt = f"Crea una avventura D&D 5e rapida (massimo 3 incontri, riassunto). Contesto: {prompt}"
        elif adventure_type == "md":
            prompt = f"Crea una avventura D&D 5e con formato Markdown Homebrewery. Contesto: {prompt}"
        else:
            prompt = f"Crea una avventura D&D 5e completa con background, incontri, NPC, tesori. Contesto: {prompt}"

        # Aggiungi dati dai tomi se rilevanti
        rag_data = rag.search_5etools(prompt)
        if rag_data:
            prompt += rag_data

        # Invia prompt all'AI
        logger.info(f"Generazione avventura per user {user_id}, tipo: {adventure_type}")

        # Usa adventure_creator se disponibile
        if adventure_creator:
            adventure = adventure_creator.create_complete_adventure(prompt, user_id)
        else:
            # Fallback: invia direttamente all'AI
            messages = [
                {"role": "system", "content": "Sei un Dungeon Master esperto di D&D 5e. Crea avventure coinvolgenti e ben strutturate."},
                {"role": "user", "content": prompt},
            ]
            adventure = openrouter_client.chat_completion(messages)

        return adventure if adventure else "⚠️ Impossibile generare l'avventura. Riprova."

    except Exception as e:
        logger.error(f"Error generazione avventura user {user_id}: {e}")
        return f"⚠️ Errore generazione: {str(e)[:200]}"
