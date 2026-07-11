"""
Handler admin e utility.
Gestisce comandi admin, proxy status, e utility.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


async def handle_admin_users(message, bot, user_id, authorized_user_ids: set):
    """
    Lista utenti autorizzati.

    Args:
        message: Messaggio Telegram
        bot: Bot instance
        user_id: ID mittente
        authorized_user_ids: Set di ID autorizzati

    Returns:
        Lista utenti autorizzati
    """
    try:
        if user_id not in authorized_user_ids:
            return "⚠️ Accesso non autorizzato."

        users = [uid for uid in authorized_user_ids]
        return f"👥 **Utenti Autorizzati:**\n{users}"

    except Exception as e:
        logger.error(f"Error admin_users: {e}")
        return f"⚠️ Errore: {str(e)[:200]}"


async def handle_admin_add_user(message, bot, user_id, authorized_user_ids: set,
                                 new_user_id: str):
    """
    Aggiungi utente alla allowlist.

    Args:
        message: Messaggio Telegram
        bot: Bot instance
        user_id: ID mittente (deve essere admin)
        authorized_user_ids: Set di ID autorizzati
        new_user_id: ID utente da aggiungere

    Returns:
        Confirma aggiunta
    """
    try:
        if user_id not in authorized_user_ids:
            return "⚠️ Solo admin può aggiungere utenti."

        new_id = int(new_user_id)
        authorized_user_ids.add(new_id)

        return f"✅ **Utente aggiunto!** ID: {new_user_id}"

    except ValueError:
        return "⚠️ ID utente deve essere un numero."
    except Exception as e:
        logger.error(f"Error admin_add_user: {e}")
        return f"⚠️ Errore: {str(e)[:200]}"


async def handle_proxy_status(message, bot, user_id, authorized_user_ids: set, openrouter_client):
    """
    Mostra status sistema API.

    Args:
        message: Messaggio Telegram
        bot: Bot instance
        user_id: ID mittente
        authorized_user_ids: Set di ID autorizzati
        openrouter_client: Client OpenRouter

    Returns:
        Status API e stats
    """
    try:
        if user_id not in authorized_user_ids:
            return "⚠️ Solo admin può vedere lo status."

        status = openrouter_client.get_status()

        # Genera API key display (non esporre key vera)
        key_display = (
            f"***" if not status["api_key_count"] else
            f"{status['api_key_count']} key configurata"
        )

        return (f"📡 **Status API:**\n\n"
                f"🔑 Chiavi API: {key_display}\n"
                f"🤖 Modello: {status['model']}\n"
                f"📊 Cache risposte: {status['cache_size']}\n"
                f"⏱️ Timeout: {status['timeout']}s")

    except Exception as e:
        logger.error(f"Error proxy_status: {e}")
        return f"⚠️ Errore: {str(e)[:200]}"


async def handle_help(message, bot, user_id, authorized_user_ids: set):
    """
    Mostra guida completa bot.

    Args:
        message: Messaggio Telegram
        bot: Bot instance
        user_id: ID mittente
        authorized_user_ids: Set di ID autorizzati

    Returns:
        Guida completa
    """
    try:
        if user_id not in authorized_user_ids:
            return "⚠️ Accesso non autorizzato."

        help_text = (
            "🎲 **Codex20 v3.1 - Guida Completa**\n\n"
            "📖 **Regole D&D 5e:**\n"
            "/search_rules <query> — Ricerca regole nei tomi ufficiali\n\n"
            "⚔️ **Avventure:**\n"
            "/adventure <prompt> — Avventura completa dettagliata\n"
            "/adventure_quick <prompt> — Avventura rapida (riassunto)\n"
            "/adventure_md <prompt> — Avventura con Markdown Homebrewery\n\n"
            "🧠 **Memoria:**\n"
            "/remember_campaign <info> — Salva info campagna\n"
            "/recall_campaign <query> — Ricorda info campagna\n"
            "/memory — Info sessione corrente\n"
            "/forget — Cancella memoria\n\n"
            "⚙️ **Admin:**\n"
            "/admin_users — Lista utenti autorizzati\n"
            "/admin_add_user <id> — Aggiungi utente\n"
            "/proxy_status — Status sistema API\n\n"
            "ℹ️ **Utility:**\n"
            "/help — Questa guida\n"
            "/version — Versione bot\n\n"
            "🔑 **Owner:** " + str(user_id)
        )
        return help_text

    except Exception as e:
        logger.error(f"Error help: {e}")
        return f"⚠️ Errore: {str(e)[:200]}"
