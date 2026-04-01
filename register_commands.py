# Codex20 - Telegram Bot Commands Registration
# Questo script registra i comandi del bot con l'API Telegram

from aiogram import Bot, types
import asyncio
import os
from dotenv import load_dotenv

# Carica variabili ambiente
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

async def set_bot_commands():
    """Registra i comandi del bot con Telegram per mostrarli nel menu"""
    
    bot = Bot(token=TELEGRAM_TOKEN)
    
    # Define bot commands
    commands = [
        types.BotCommand(command="help", description="📖 Guida completa e lista comandi"),
        types.BotCommand(command="adventure", description="🎲 Crea avventura completa bilanciata"),
        types.BotCommand(command="adventure_md", description="📜 Avventura con markdown Homebrewery"),
        types.BotCommand(command="memory", description="🧠 Info sulla memoria conversazione"),
        types.BotCommand(command="forget", description="🗑️ Cancella memoria e ricomincia"),
        types.BotCommand(command="mappa", description="🔧 Debug mapping campi PDF"),
    ]
    
    try:
        # Set commands for all users
        await bot.set_my_commands(commands, scope=types.BotCommandScopeDefault())
        print("✅ Bot commands registered successfully!")
        
        # Print registered commands
        print("\n📋 Registered commands:")
        for cmd in commands:
            print(f"  /{cmd.command} - {cmd.description}")
            
    except Exception as e:
        print(f"❌ Error registering commands: {e}")
    
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(set_bot_commands())