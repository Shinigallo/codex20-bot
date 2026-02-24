import os
import json
import random
import glob
import asyncio
import logging
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
from google import generativeai as genai
from dotenv import load_dotenv
from fpdf import FPDF

# Configurazione
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEYS = os.getenv("GEMINI_API_KEYS", "").split(",")
current_key_index = 0

def get_model():
    global current_key_index
    key = API_KEYS[current_key_index].strip()
    genai.configure(api_key=key)
    return genai.GenerativeModel("gemini-2.0-flash")

bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
dp = Dispatcher()

async def generate_content_safe(prompt):
    global current_key_index
    for _ in range(len(API_KEYS)):
        try:
            model = get_model()
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                current_key_index = (current_key_index + 1) % len(API_KEYS)
                continue
            raise e
    return None

# --- LOGICA RICERCA TOMI (5ETOOLS) ---
def search_5etools(query):
    data_dir = os.path.join("data", "5etools")
    if not os.path.exists(data_dir): return ""
    found_data = ""
    keywords = [k.lower() for k in query.split() if len(k) > 3]
    if not keywords: return ""
    
    for file_path in glob.glob(os.path.join(data_dir, "**", "*.json"), recursive=True):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = json.load(f)
                for key, collection in content.items():
                    if isinstance(collection, list) and key not in ["_meta", "linkedFile"]:
                        for item in collection:
                            if isinstance(item, dict) and "name" in item:
                                if any(k in item["name"].lower() for k in keywords):
                                    found_data += f"\n[{key.upper()} - {os.path.basename(file_path)}]:\n{json.dumps(item, indent=2)}\n"
                                    if len(found_data) > 6000: break # Limite per non intasare il prompt
                        if len(found_data) > 6000: break
        except: continue
        if len(found_data) > 6000: break
    return f"\n\nDATI TECNICI DAI TOMI (5ETOOLS):\n{found_data}" if found_data else ""

def get_personality_context():
    context = """Sei Codex20, un assistente digitale evoluto e Dungeon Master esperto. Rispondi in italiano.\n
    IMPORTANTE: Se l'utente ti chiede di creare un personaggio o una scheda, genera i dati tecnici completi e rispondi fornendo un blocco JSON racchiuso tra ```json e ``` contenente tutte le chiavi necessarie (nome, razza, classe, livello, background, forza, destrezza, costituzione, intelligenza, saggezza, carisma, competenze, equipaggiamento, descrizione_breve).
    Usa i dati forniti dai Tomi per essere accurato con le regole di D&D 5e."""
    data_dir = "data"
    for file_name in ["SOUL.md", "IDENTITY.md", "USER.md"]:
        path = os.path.join(data_dir, file_name)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                context += f"\nINFORMAZIONI DI PERSONALITÀ:\n{f.read()}\n"
    return context

system_context_base = get_personality_context()

def create_pdf(char, user_id):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 20)
    pdf.cell(0, 15, "CODEX20 - SCHEDA PERSONAGGIO", align="C")
    pdf.ln(15)
    
    pdf.set_font("helvetica", "B", 12)
    lvl = char.get('livello', '1')
    pdf.cell(0, 10, f"NOME: {char.get('nome')} | RAZZA: {char.get('razza')} | CLASSE: {char.get('classe')} (Liv. {lvl})", border=1)
    pdf.ln(10)
    pdf.cell(0, 10, f"BACKGROUND: {char.get('background')}", border=1)
    pdf.ln(15)
    
    stats = [("FOR", "forza"), ("DES", "destrezza"), ("COS", "costituzione"), ("INT", "intelligenza"), ("SAG", "saggezza"), ("CAR", "carisma")]
    for label, key in stats:
        val = char.get(key, 10)
        mod = (val - 10) // 2
        pdf.cell(30, 15, f"{label}: {val} ({'+' if mod>=0 else ''}{mod})", border=1)
    pdf.ln(25)
    
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, "COMPETENZE ED EQUIPAGGIAMENTO:")
    pdf.ln(10)
    pdf.set_font("helvetica", "", 10)
    content = f"Competenze: {char.get('competenze', 'N/A')}\n\nEquipaggiamento: {char.get('equipaggiamento', 'N/A')}"
    pdf.multi_cell(0, 6, content, border=1)
    pdf.ln(10)
    
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, "DESCRIZIONE:")
    pdf.ln(10)
    pdf.set_font("helvetica", "I", 10)
    pdf.multi_cell(0, 6, char.get('descrizione_breve', 'N/A'), border=1)
    
    path = f"data/pg_{user_id}.pdf"
    pdf.output(path)
    return path

@dp.message(F.text)
async def chat_handler(message: types.Message):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    # Ricerca nei Tomi basata sul messaggio dell'utente
    tomi_context = search_5etools(message.text)
    prompt = f"{system_context_base}{tomi_context}\n\nUtente: {message.text}"
    
    try:
        response_text = await generate_content_safe(prompt)
        if not response_text: return

        # Cerchiamo se Gemini ha generato un JSON per una scheda
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL)
        
        if json_match:
            try:
                char_data = json.loads(json_match.group(1))
                pdf_path = create_pdf(char_data, message.from_user.id)
                clean_text = re.sub(r"```json.*?```", "", response_text, flags=re.DOTALL).strip()
                if clean_text: await message.answer(clean_text)
                
                await message.answer_document(
                    FSInputFile(pdf_path), 
                    caption=f"Ecco la scheda di *{char_data.get('nome')}*! 🎲",
                    parse_mode="Markdown"
                )
                if os.path.exists(pdf_path): os.remove(pdf_path)
                return
            except Exception as e:
                logger.error(f"Errore JSON/PDF: {e}")

        # Risposta standard con Markdown
        if len(response_text) > 4000:
            await message.answer(f"{response_text[:4000]}...")
        else:
            await message.answer(f"{response_text}\n\n🎲", parse_mode="Markdown")
            
    except Exception as e:
        logger.error(f"Errore generale: {e}")
        await message.answer("Spiacente, Codex20 ha avuto un glitch. 🎲")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
