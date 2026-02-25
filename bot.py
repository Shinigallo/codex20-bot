import os
import json
import random
import glob
import asyncio
import logging
import re
import io
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
from google import generativeai as genai
from dotenv import load_dotenv
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

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
    IMPORTANTE: Se l'utente ti chiede di creare un personaggio o una scheda, genera i dati tecnici completi e rispondi fornendo un blocco JSON racchiuso tra ```json e ``` contenente tutte le chiavi necessarie:
    (nome, razza, classe, livello, background, forza, destrezza, costituzione, intelligenza, saggezza, carisma, 
    competenze_salvezza: [lista di stats],
    competenze_abilita: [lista di abilità],
    ca, iniziativa, velocita, hp_max,
    incantesimi: { "0": ["lista cantrips"], "1": ["lista liv 1"], ... "9": ["lista liv 9"] },
    slot_incantesimi: { "1": 4, "2": 3, ... },
    caratteristica_incantesimi: "Intelligenza/Saggezza/Carisma",
    competenze: "stringa descrittiva", 
    equipaggiamento, descrizione_breve).
    
    Usa i nomi standard in italiano per le abilità: acrobazia, addestrare animali, arcano, atletica, furtività, indagare, inganno, intuizione, intimidire, medicina, natura, percezione, perspicacia, persuasione, rapidità di mano, religione, sopravvivenza, storia.
    Usa i dati forniti dai Tomi per essere accurato con le regole di D&D 5e."""
    data_dir = "data"
    for file_name in ["SOUL.md", "IDENTITY.md", "USER.md"]:
        path = os.path.join(data_dir, file_name)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                context += f"\nINFORMAZIONI DI PERSONALITÀ:\n{f.read()}\n"
    return context

system_context_base = get_personality_context()

def calculate_modifier(score):
    return (score - 10) // 2

def get_proficiency_bonus(level):
    try:
        lvl = int(level)
        return 2 + (lvl - 1) // 4
    except:
        return 2

def create_pdf(char, user_id):
    template_path = "5E_CharacterSheet_Fillable.pdf"
    output_path = f"data/pg_{user_id}.pdf"
    
    if not os.path.exists(template_path):
        logger.error(f"Template PDF non trovato in {template_path}")
        return None

    prof_bonus = get_proficiency_bonus(char.get('livello', 1))
    
    # Mapping base
    field_data = {
        'CharacterName': char.get('nome', ''),
        'Race ': char.get('razza', ''),
        'ClassLevel': f"{char.get('classe', '')} {char.get('livello', '1')}",
        'Background': char.get('background', ''),
        'ProfBonus': f"+{prof_bonus}",
        'AC': str(char.get('ca', 10)),
        'Initiative': str(char.get('iniziativa', 0)),
        'Speed': str(char.get('velocita', 30)),
        'HPMax': str(char.get('hp_max', 10)),
        'HPCurrent': str(char.get('hp_max', 10)),
    }

    # Caratteristiche e Modificatori
    stats_map = {
        'forza': ('STR', 'STRmod', 'ST Strength', 'Check Box 11'),
        'destrezza': ('DEX', 'DEXmod ', 'ST Dexterity', 'Check Box 18'),
        'costituzione': ('CON', 'CONmod', 'ST Constitution', 'Check Box 19'),
        'intelligenza': ('INT', 'INTmod', 'ST Intelligence', 'Check Box 20'),
        'saggezza': ('WIS', 'WISmod', 'ST Wisdom', 'Check Box 21'),
        'carisma': ('CHA', 'CHamod', 'ST Charisma', 'Check Box 22')
    }

    comp_salvezza = [s.lower() for s in char.get('competenze_salvezza', [])]
    
    for stat_ita, (pdf_score, pdf_mod, pdf_save, pdf_check) in stats_map.items():
        val = char.get(stat_ita, 10)
        mod = calculate_modifier(val)
        field_data[pdf_score] = str(val)
        field_data[pdf_mod] = f"+{mod}" if mod >= 0 else str(mod)
        
        # Tiri Salvezza
        save_val = mod
        if stat_ita in comp_salvezza:
            save_val += prof_bonus
            field_data[pdf_check] = "Yes"
        field_data[pdf_save] = f"+{save_val}" if save_val >= 0 else str(save_val)

    # Abilità (Skills)
    skills_map = {
        'acrobazia': ('Acrobatics', 'Check Box 23', 'destrezza'),
        'addestrare animali': ('Animal', 'Check Box 24', 'saggezza'),
        'arcano': ('Arcana', 'Check Box 25', 'intelligenza'),
        'atletica': ('Athletics', 'Check Box 26', 'forza'),
        'inganno': ('Deception ', 'Check Box 27', 'carisma'),
        'storia': ('History ', 'Check Box 28', 'intelligenza'),
        'intuizione': ('Insight', 'Check Box 29', 'saggezza'),
        'intimidire': ('Intimidation', 'Check Box 30', 'carisma'),
        'indagare': ('Investigation ', 'Check Box 31', 'intelligenza'),
        'medicina': ('Medicine', 'Check Box 32', 'saggezza'),
        'natura': ('Nature', 'Check Box 33', 'intelligenza'),
        'percezione': ('Perception ', 'Check Box 34', 'saggezza'),
        'performance': ('Performance', 'Check Box 35', 'carisma'),
        'persuasione': ('Persuasion', 'Check Box 36', 'carisma'),
        'religione': ('Religion', 'Check Box 37', 'intelligenza'),
        'rapidità di mano': ('SleightofHand', 'Check Box 38', 'destrezza'),
        'furtività': ('Stealth ', 'Check Box 39', 'destrezza'),
        'sopravvivenza': ('Survival', 'Check Box 40', 'saggezza')
    }

    comp_abilita = [a.lower() for a in char.get('competenze_abilita', [])]
    for abil_ita, (pdf_field, pdf_check, base_stat) in skills_map.items():
        stat_val = char.get(base_stat, 10)
        mod = calculate_modifier(stat_val)
        if abil_ita in comp_abilita:
            mod += prof_bonus
            field_data[pdf_check] = "Yes"
        field_data[pdf_field] = f"+{mod}" if mod >= 0 else str(mod)
        
        # Percezione Passiva
        if abil_ita == 'percezione':
            field_data['Passive'] = str(10 + mod)

    # --- INCANTESIMI E SLOT ---
    spell_ability = char.get('caratteristica_incantesimi', 'Saggezza').lower()
    spell_stat_val = char.get(spell_ability, 10)
    spell_mod = calculate_modifier(spell_stat_val)
    
    field_data['Spellcasting Class 2'] = char.get('classe', '')
    field_data['SpellcastingAbility 2'] = spell_ability.capitalize()
    field_data['SpellSaveDC  2'] = str(8 + prof_bonus + spell_mod)
    field_data['SpellAtkBonus 2'] = f"+{prof_bonus + spell_mod}"

    # Nuova mappatura Spell Slots (Livelli 1-9)
    # Seguiamo la numerazione 19-27 della scheda (SlotsTotal 19, SlotsRemaining 19, ecc.)
    slots_data = char.get('slot_incantesimi', {})
    for lvl in range(1, 10):
        s_val = str(slots_data.get(str(lvl), ''))
        if s_val:
            field_data[f'SlotsTotal {18+lvl}'] = s_val
            field_data[f'SlotsRemaining {18+lvl}'] = s_val

    # Nuova mappatura nomi incantesimi secondo l'ordine richiesto dall'utente
    spell_names_mapping = {
        '0': ['Spells 1014', 'Spells 1016', 'Spells 1017', 'Spells 1018', 'Spells 1019', 'Spells 1020', 'Spells 1021', 'Spells 1022'],
        '1': ['Spells 1015', 'Spells 1023', 'Spells 1024', 'Spells 1025', 'Spells 1026', 'Spells 1027', 'Spells 1028', 'Spells 1029', 'Spells 1030', 'Spells 1031', 'Spells 1032', 'Spells 1033'],
        '2': ['Spells 1046', 'Spells 1034', 'Spells 1035', 'Spells 1036', 'Spells 1037', 'Spells 1038', 'Spells 1039', 'Spells 1040', 'Spells 1041', 'Spells 1042', 'Spells 1043', 'Spells 1044', 'Spells 1045'],
        '3': ['Spells 1048', 'Spells 1047', 'Spells 1049', 'Spells 1050', 'Spells 1051', 'Spells 1052', 'Spells 1053', 'Spells 1054', 'Spells 1055', 'Spells 1056', 'Spells 1057', 'Spells 1058', 'Spells 1059'],
        '4': ['Spells 1060', 'Spells 1061', 'Spells 1062', 'Spells 1063', 'Spells 1064', 'Spells 1065', 'Spells 1066', 'Spells 1067', 'Spells 1068', 'Spells 1069', 'Spells 1070', 'Spells 1071', 'Spells 1072'],
        '5': ['Spells 1074', 'Spells 1073', 'Spells 1075', 'Spells 1076', 'Spells 1077', 'Spells 1078', 'Spells 1079', 'Spells 1080', 'Spells 1081'],
        '6': ['Spells 1083', 'Spells 1082', 'Spells 1084', 'Spells 1085', 'Spells 1086', 'Spells 1087', 'Spells 1088', 'Spells 1089', 'Spells 1090'],
        '7': ['Spells 1091', 'Spells 1092', 'Spells 1093', 'Spells 1094', 'Spells 1095', 'Spells 1096', 'Spells 1097', 'Spells 1098', 'Spells 1099'],
        '8': ['Spells 10101', 'Spells 10100', 'Spells 10102', 'Spells 10103', 'Spells 10104', 'Spells 10105', 'Spells 10106'],
        '9': ['Spells 10108', 'Spells 10107', 'Spells 10109', 'Spells 101010', 'Spells 101011', 'Spells 101012', 'Spells 101013']
    }
    
    incantesimi_dict = char.get('incantesimi', {})
    for lvl_str, field_list in spell_names_mapping.items():
        lista = incantesimi_dict.get(lvl_str, [])
        for i, spell_name in enumerate(lista):
            if i < len(field_list):
                field_data[field_list[i]] = spell_name

    field_data['ProficienciesLanguages'] = char.get('competenze', '')
    field_data['Equipment'] = char.get('equipaggiamento', '')
    field_data['Backstory'] = char.get('descrizione_breve', '')

    # Generazione Overlay
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    reader = PdfReader(template_path)
    
    for page in reader.pages:
        if "/Annots" in page:
            for annot in page["/Annots"]:
                obj = annot.get_object()
                if "/T" in obj:
                    field_name = obj["/T"]
                    if field_name in field_data:
                        text = str(field_data[field_name])
                        rect = obj.get("/Rect")
                        if rect:
                            x1, y1, x2, y2 = map(float, rect)
                            width, height = x2 - x1, y2 - y1
                            
                            if "Check Box" in field_name:
                                # Pallino per i checkbox
                                can.setFont("Helvetica", 12)
                                can.drawString(x1 + (width-8)/2, y1 + (height-8)/2, "•")
                            else:
                                font_size = min(height * 0.6, 10)
                                can.setFont("Helvetica", font_size)
                                can.drawString(x1 + 2, y1 + (height - font_size) / 2 + 1, text)
        can.showPage()
    
    can.save()
    packet.seek(0)
    new_pdf = PdfReader(packet)
    writer = PdfWriter()
    
    for i, page in enumerate(reader.pages):
        if i < len(new_pdf.pages):
            page.merge_page(new_pdf.pages[i])
        if "/Annots" in page:
            del page["/Annots"]
        writer.add_page(page)
    
    with open(output_path, 'wb') as f:
        writer.write(f)
    
    return output_path

@dp.message(Command("mappa"))
async def send_map_debug(message: types.Message):
    map_path = "data/MAPPA_CAMPI_SPELL.pdf"
    if os.path.exists(map_path):
        await message.answer_document(FSInputFile(map_path), caption="Ecco la mappa tecnica dei campi Spell. Dimmi quali ID corrispondono ai vari livelli!")
    else:
        await message.answer("File mappa non trovato. Generazione in corso, riprova tra 5 secondi.")

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
        response_text = response_text.strip()\n        if len(response_text) > 4000:
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
