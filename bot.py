import os
import json
import random
import glob
import asyncio
import logging
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

# Caricamento chiavi multiple
API_KEYS = os.getenv("GEMINI_API_KEYS", "").split(",")
current_key_index = 0

def get_model():
    global current_key_index
    key = API_KEYS[current_key_index].strip()
    genai.configure(api_key=key)
    return genai.GenerativeModel("gemini-2.0-flash")

bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
dp = Dispatcher()

# Funzione helper per generare contenuto con rotazione chiavi
async def generate_content_safe(prompt):
    global current_key_index
    max_retries = len(API_KEYS)
    
    for _ in range(max_retries):
        try:
            model = get_model()
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                logger.warning(f"Quota ecceduta per la chiave {current_key_index}. Ruoto...")
                current_key_index = (current_key_index + 1) % len(API_KEYS)
                continue
            else:
                logger.error(f"Errore Gemini: {e}")
                raise e
    return None

# Caricamento Personalità
def get_personality_context():
    context = """Sei Codex20, un assistente digitale evoluto e Dungeon Master esperto. Rispondi in italiano.\n"""
    data_dir = "data"
    for file_name in ["SOUL.md", "IDENTITY.md", "USER.md"]:
        path = os.path.join(data_dir, file_name)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                context += f"\nINFORMAZIONI DA {file_name}:\n{f.read()}\n"
    return context

system_context_base = get_personality_context()

# Ricerca nei Tomi (5etools)
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
                                    if len(found_data) > 8000: break
                        if len(found_data) > 8000: break
        except: continue
        if len(found_data) > 8000: break
    return f"\n\nDATI TECNICI DA 5ETOOLS:\n{found_data}" if found_data else ""

# Estrazione dati casuali per grounding
def get_random_5etools_data():
    data_dir = os.path.join("data", "5etools")
    samples = {}
    for cat in ["race", "class", "background"]:
        files = glob.glob(os.path.join(data_dir, "**", f"*{cat}*.json"), recursive=True)
        if files:
            try:
                with open(random.choice(files), "r", encoding="utf-8") as f:
                    data = json.load(f)
                    key = next((k for k in data.keys() if k not in ["_meta", "linkedFile"]), None)
                    if key and isinstance(data[key], list):
                        items = [i.get("name") for i in data[key] if isinstance(i, dict) and "name" in i]
                        samples[cat] = random.sample(items, min(len(items), 5))
            except: continue
    return samples

# Generazione Personaggio
@dp.message(Command("randompg"))
async def cmd_randompg(message: types.Message):
    await message.answer("📖 Codex20 consulta i Tomi per forgiare il tuo eroe...")
    samples = get_random_5etools_data()
    prompt = f"""Genera un personaggio di D&D 5e di livello 1. JSON: nome, razza, classe, background, forza, destrezza, costituzione, intelligenza, saggezza, carisma, competenze, equipaggiamento, descrizione_breve. Usa: {samples}."""
    
    try:
        raw_json = await generate_content_safe(prompt)
        char = json.loads(raw_json.replace("```json", "").replace("```", "").strip())
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", "B", 16)
        pdf.cell(0, 10, f"Scheda Personaggio: {char['nome']}", ln=1, align="C")
        pdf.set_font("helvetica", "", 12)
        pdf.multi_cell(0, 8, f"Razza: {char['razza']} | Classe: {char['classe']}\nBackground: {char['background']}")
        pdf.ln(5)
        for s in ["forza", "destrezza", "costituzione", "intelligenza", "saggezza", "carisma"]:
            pdf.cell(40, 8, f"{s.upper()}: {char.get(s, 10)}")
        pdf.ln(10)
        pdf.multi_cell(0, 6, f"Competenze: {char.get('competenze')}\nEquipaggiamento: {char.get('equipaggiamento')}\n\nDescrizione: {char.get('descrizione_breve')}")
        
        pdf_path = f"data/pg_{message.from_user.id}.pdf"
        pdf.output(pdf_path)
        await message.answer_document(FSInputFile(pdf_path), caption=f"Eroe pronto: *{char['nome']}*! 🎲", parse_mode="Markdown")
        if os.path.exists(pdf_path): os.remove(pdf_path)
    except Exception as e:
        logger.error(f"Errore PG: {e}")
        await message.answer("Errore durante la creazione. 🎲")

# Gestione Chat
@dp.message(F.text)
async def chat_handler(message: types.Message):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    context = search_5etools(message.text)
    prompt = f"{system_context_base}{context}\n\nUtente: {message.text}"
    
    try:
        response_text = await generate_content_safe(prompt)
        if response_text:
            if len(response_text) > 4000:
                await message.answer(f"{response_text[:4000]}...")
            else:
                await message.answer(f"{response_text}\n\n🎲", parse_mode="Markdown")
    except:
        await message.answer("Spiacente, Codex20 ha avuto un glitch di comunicazione. 🎲")

async def main():
    logger.info(f"Codex20 ONLINE con {len(API_KEYS)} chiavi Gemini.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
