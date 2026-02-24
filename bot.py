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

API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)
# Usiamo il modello 2.0-flash confermato funzionante
model = genai.GenerativeModel("gemini-2.0-flash")

bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
dp = Dispatcher()

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
    if not os.path.exists(data_dir):
        return ""
    
    found_data = ""
    keywords = [k.lower() for k in query.split() if len(k) > 3]
    if not keywords:
        return ""
    
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
        
    return f"\n\nDATI TECNICI DA 5ETOOLS (usa questi per rispondere con precisione):\n{found_data}" if found_data else ""

# Estrazione dati casuali per grounding
def get_random_5etools_data():
    data_dir = os.path.join("data", "5etools")
    samples = {}
    categories = ["race", "class", "background"]
    for cat in categories:
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

# Generazione Personaggio "Grounded"
async def generate_character_with_data():
    samples = get_random_5etools_data()
    prompt = f"""Genera un personaggio di D&D 5e di livello 1.
    Usa queste opzioni tratte dai manuali se possibile:
    Razze suggerite: {samples.get('race', 'Qualsiasi')}
    Classi suggerite: {samples.get('class', 'Qualsiasi')}
    Background suggeriti: {samples.get('background', 'Qualsiasi')}

    Restituisci un oggetto JSON con:
    nome, razza, classe, background, forza, destrezza, costituzione, intelligenza, saggezza, carisma, competenze, equipaggiamento, descrizione_breve.
    Rispondi SOLO con il JSON."""
    
    try:
        response = model.generate_content(prompt)
        raw_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(raw_text)
    except Exception as e:
        logger.error(f"Errore generazione: {e}")
        return None

# Creazione PDF con pypdf-friendly syntax
def create_pdf(char, user_id):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 20)
    pdf.cell(0, 15, "CODEX20 - SCHEDA PERSONAGGIO", align="C")
    pdf.ln(15)
    
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, f"NOME: {char.get('nome')} | RAZZA: {char.get('razza')} | CLASSE: {char.get('classe')}", border=1)
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

@dp.message(Command("randompg"))
async def cmd_randompg(message: types.Message):
    await message.answer("📖 Codex20 consulta i Tomi per forgiare il tuo eroe...")
    char = await generate_character_with_data()
    if char:
        try:
            pdf_path = create_pdf(char, message.from_user.id)
            await message.answer_document(FSInputFile(pdf_path), caption=f"Eroe pronto: *{char['nome']}*! 🎲", parse_mode="Markdown")
            if os.path.exists(pdf_path): os.remove(pdf_path)
        except Exception as e:
            logger.error(f"Errore PDF/Telegram: {e}")
            await message.answer("Errore nell'invio della scheda. 🎲")
    else:
        await message.answer("Errore nella lettura dei Tomi. 🎲")

@dp.message(F.text)
async def chat_handler(message: types.Message):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    user_query = message.text
    additional_context = search_5etools(user_query)
    final_prompt = f"{system_context_base}{additional_context}\n\nUtente: {user_query}"
    
    try:
        response = model.generate_content(final_prompt)
        text = response.text or "Codex20 non ha prodotto risposta."
        
        # Gestione lunghezza e parse_mode
        try:
            if len(text) > 4000:
                await message.answer(f"{text[:4000]}...")
            else:
                await message.answer(f"{text}\n\n🎲", parse_mode="Markdown")
        except Exception as te:
            logger.warning(f"Errore Markdown, riprovo plain text: {te}")
            await message.answer(f"{text}\n\n🎲")
            
    except Exception as e:
        logger.error(f"Errore Gemini: {e}")
        await message.answer("Spiacente, Codex20 ha avuto un glitch di comunicazione. 🎲")

async def main():
    logger.info("Codex20 Python Bot ONLINE")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
