"""
Codex20 - Il Custode dei Tomi 🎲
Bot Telegram basato su AI per Dungeon Master e Giocatori di D&D 5e.
Integra Gemini 2.0 Flash, consultazione dinamica dei tomi (5etools) e
generazione automatica di schede personaggio in formato PDF.
"""

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

# SESSION MEMORY - IMMEDIATE FIX
from collections import defaultdict, deque
from datetime import datetime, timedelta

class QuickSessionManager:
    """Session memory veloce per fix immediato"""
    
    def __init__(self):
        self.sessions = defaultdict(lambda: deque(maxlen=10))  # Max 10 messaggi per user
        self.last_activity = defaultdict(lambda: datetime.now())
    
    def add_message(self, user_id: int, user_msg: str, bot_response: str):
        """Aggiunge messaggio alla memoria"""
        self.last_activity[user_id] = datetime.now()
        self.sessions[user_id].append({
            'user': user_msg[:500],  # Limita lunghezza per context window
            'bot': bot_response[:800], 
            'time': datetime.now()
        })
    
    def get_context(self, user_id: int) -> str:
        """Recupera contesto conversazione"""
        if user_id not in self.sessions or not self.sessions[user_id]:
            return ""
        
        # Prendi ultimi 3 messaggi
        recent = list(self.sessions[user_id])[-3:]
        
        context = "\n\nCONVERSAZIONE PRECEDENTE:\n"
        for msg in recent:
            context += f"User: {msg['user']}\nCodex20: {msg['bot']}\n\n"
        
        return context
    
    def clear_session(self, user_id: int):
        """Cancella sessione"""
        if user_id in self.sessions:
            del self.sessions[user_id]
        if user_id in self.last_activity:
            del self.last_activity[user_id]

# Inizializza session manager
session_memory = QuickSessionManager()

# ==========================================
# CONFIGURAZIONE INIZIALE E LOGGING
# ==========================================
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sistema di Resilienza: Rotazione automatica API Keys per aggirare i rate-limits (HTTP 429)
API_KEYS = os.getenv("GEMINI_API_KEYS", "").split(",")
current_key_index = 0

def get_model():
    """
    Configura e restituisce l'istanza del modello Gemini corrente.
    Utilizza la chiave API selezionata tramite rotazione.
    """
    global current_key_index
    key = API_KEYS[current_key_index].strip()
    genai.configure(api_key=key)
    return genai.GenerativeModel("gemini-2.0-flash")

# Inizializzazione Bot Telegram (Aiogram 3.x)
bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
dp = Dispatcher()

async def generate_content_safe(prompt):
    """
    Invia un prompt a Gemini in modo sicuro.
    Gestisce automaticamente l'errore 429 (Quota Exceeded) ruotando 
    la chiave API alla successiva disponibile e riprovando.
    """
    global current_key_index
    for _ in range(len(API_KEYS)):
        try:
            model = get_model()
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                logger.warning(f"Quota superata per la chiave {current_key_index}, rotazione in corso...")
                current_key_index = (current_key_index + 1) % len(API_KEYS)
                continue
            raise e
    return None

# ==========================================
# LOGICA RAG: RICERCA NEI TOMI (5ETOOLS)
# ==========================================
def search_5etools(query):
    """
    Scansiona ricorsivamente i file JSON nella directory dei tomi (5etools).
    Estrae dati rilevanti basati sulle keyword per fare "grounding" delle
    risposte dell'AI, garantendo fedeltà alle regole ufficiali.
    """
    data_dir = os.path.join("data", "5etools")
    if not os.path.exists(data_dir): 
        return ""
    
    found_data = ""
    # Estrae parole chiave significative ignorando congiunzioni brevi
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
                                    # Limite per non eccedere la context window del modello AI
                                    if len(found_data) > 6000: break 
                        if len(found_data) > 6000: break
        except Exception as e: 
            continue
        if len(found_data) > 6000: break
            
    return f"\n\nDATI TECNICI DAI TOMI (5ETOOLS):\n{found_data}" if found_data else ""

def get_personality_context():
    """
    Carica e assembla il System Prompt.
    Istruisce Gemini sul suo ruolo, sul formato output (JSON) richiesto
    per la generazione dei PDF, e carica ulteriori tratti di personalità
    dai file SOUL.md, IDENTITY.md, USER.md se presenti.
    """
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

# ==========================================
# ADVENTURE CREATOR INTEGRATION
# ==========================================

import tempfile

class AdventureCreator:
    """Adventure creator integrato in Codex20 usando RAG esistente"""
    
    def create_adventure(self, prompt: str):
        """Crea avventura usando il sistema RAG esistente"""
        
        # Analisi prompt
        requirements = self._analyze_prompt(prompt)
        
        # Usa la funzione search_5etools esistente per ottenere dati
        monster_data = search_5etools(f"CR {requirements['party_level']} monster")
        
        # Genera avventura
        adventure = {
            'title': self._generate_title(requirements),
            'requirements': requirements,
            'encounters': self._create_encounters(requirements),
            'npcs': self._create_npcs(requirements),
            'treasure': self._create_treasure(requirements),
            'background': self._create_background(requirements),
            'estimated_duration': self._estimate_duration(requirements),
            'xp_budget': self._calculate_xp_budget(requirements)
        }
        
        return adventure
    
    def _analyze_prompt(self, prompt: str):
        """Estrae requisiti dal prompt"""
        
        # Estrai livello party
        level_match = re.search(r'(?:livello?|level?|lv\.?)\s*(\d+)', prompt.lower())
        party_level = int(level_match.group(1)) if level_match else 3
        
        # Estrai dimensione party
        size_match = re.search(r'(\d+)\s*(?:pcs?|giocatori|characters?|players?)', prompt.lower())
        party_size = int(size_match.group(1)) if size_match else 4
        
        # Estrai ambientazione
        setting = 'dungeon'  # default
        setting_keywords = {
            'grotta': 'cave', 'cave': 'cave',
            'torre': 'tower', 'tower': 'tower',
            'castello': 'castle', 'castle': 'castle',
            'foresta': 'forest', 'forest': 'forest',
            'bosco': 'forest', 'woods': 'forest',
            'città': 'city', 'city': 'city',
            'nave': 'ship', 'ship': 'ship',
            'dungeon': 'dungeon'
        }
        
        for keyword, setting_type in setting_keywords.items():
            if keyword in prompt.lower():
                setting = setting_type
                break
        
        # Estrai tema
        theme = 'mixed'  # default
        theme_keywords = {
            'goblin': 'goblinoids', 'orchi': 'goblinoids',
            'non morti': 'undead', 'undead': 'undead', 'fantasmi': 'undead',
            'drago': 'dragons', 'dragon': 'dragons',
            'banditi': 'bandits', 'briganti': 'bandits',
            'mago': 'magical', 'magic': 'magical', 'wizard': 'magical',
            'cultist': 'cult', 'culto': 'cult'
        }
        
        for keyword, theme_type in theme_keywords.items():
            if keyword in prompt.lower():
                theme = theme_type
                break
        
        return {
            'party_level': party_level,
            'party_size': party_size,
            'setting': setting,
            'theme': theme,
            'focus': 'balanced'
        }
    
    def _generate_title(self, req):
        """Genera titolo avventura"""
        setting_names = {
            'cave': ['Le Grotte Oscure', 'Le Caverne Nascoste', 'Gli Antichi Sotterranei'],
            'tower': ['La Torre Misteriosa', 'La Guglia del Mago', 'La Torre Perduta'],
            'castle': ['Il Castello Infestato', 'La Fortezza in Rovina', 'Il Maniero Abbandonato'],
            'forest': ['Il Bosco Sussurrante', 'La Foresta Oscura', 'Il Boschetto Incantato'],
            'city': ['Ombre in Città', 'Il Mistero Urbano', 'Città di Segreti'],
            'ship': ['La Nave Fantasma', 'Pirati dell\'Alto Mare', 'Il Vascello Perduto'],
            'dungeon': ['Il Dungeon Dimenticato', 'Profondità del Pericolo', 'Le Antiche Rovine']
        }
        
        titles = setting_names.get(req['setting'], ['L\'Avventura Misteriosa'])
        return random.choice(titles)
    
    def _create_encounters(self, req):
        """Crea encounters bilanciati"""
        
        encounters = []
        party_level = req['party_level']
        
        # Encounters base per livello
        if party_level <= 2:
            encounter_types = ['easy', 'medium', 'hard', 'medium']
            base_monsters = ['Goblin', 'Bandit', 'Wolf', 'Orc']
        elif party_level <= 5:
            encounter_types = ['medium', 'hard', 'hard', 'deadly']
            base_monsters = ['Hobgoblin', 'Bugbear', 'Owlbear', 'Ogre']
        else:
            encounter_types = ['hard', 'deadly', 'hard', 'deadly']
            base_monsters = ['Young Dragon', 'Troll', 'Giant', 'Vampire Spawn']
        
        for i, difficulty in enumerate(encounter_types):
            encounter = {
                'title': f'Scontro {i+1}' if i < 3 else 'Boss Finale',
                'type': 'combat' if i < 3 else 'boss',
                'difficulty': difficulty,
                'description': f'Uno scontro di difficoltà {difficulty} appropriato per il party.',
                'monsters': [{'name': base_monsters[i % len(base_monsters)], 'cr': max(1, party_level - 1 + i)}],
                'cr_total': max(1, party_level - 1 + i)
            }
            encounters.append(encounter)
        
        return encounters
    
    def _create_npcs(self, req):
        """Crea NPCs"""
        npcs = [
            {
                'name': 'Anziano del Villaggio',
                'role': 'Quest Giver',
                'description': 'Un umano anziano che fornisce la missione iniziale.',
                'personality': 'Saggio ma preoccupato per gli eventi recenti.',
                'stats': 'Usa le statistiche del Nobile (Monster Manual)'
            }
        ]
        
        if req['theme'] == 'magical':
            npcs.append({
                'name': 'Apprendista Mago',
                'role': 'Alleato',
                'description': 'Un giovane mago che può aiutare il party.',
                'personality': 'Entusiasta ma inesperto.',
                'stats': 'Usa le statistiche del Mage (Monster Manual)'
            })
        else:
            npcs.append({
                'name': 'Mercante Catturato',
                'role': 'NPC da Salvare',
                'description': 'Un halfling mercante preso prigioniero.',
                'personality': 'Grato ma traumatizzato dalla prigionia.',
                'stats': 'Usa le statistiche del Commoner'
            })
        
        return npcs
    
    def _create_treasure(self, req):
        """Crea tesoro appropriato al livello"""
        level = req['party_level']
        
        # Oro basato sul livello (per DMG guidelines)
        gold_amounts = {
            1: '50-100', 2: '100-200', 3: '200-400', 4: '400-800', 5: '800-1200'
        }
        
        # Magic items per livello
        magic_items = []
        if level >= 2:
            magic_items.append('Pozione di Cura')
        if level >= 3:
            magic_items.append('Pergamena Magica')
        if level >= 4:
            magic_items.append('Arma +1')
        if level >= 5:
            magic_items.append('Mantello di Protezione')
        
        return {
            'gold': gold_amounts.get(level, '100-200'),
            'magic_items': magic_items,
            'consumables': ['Pozione di Cura', 'Antidoto'],
            'special': 'Mappa antica con agganci per future avventure'
        }
    
    def _create_background(self, req):
        """Crea background avventura"""
        setting = req['setting']
        theme = req['theme']
        
        backgrounds = {
            'cave': {
                'background': f'Una rete di grotte è diventata pericolosa a causa dell\'attività di {theme}.',
                'hook': 'I locali segnalano viaggiatori scomparsi e strani suoni dalle grotte.',
                'setting_details': 'Grotte calcaree buie con multiple camere e corsi d\'acqua sotterranei.'
            },
            'tower': {
                'background': f'Una torre di mago abbandonata mostra segni di presenza {theme}.',
                'hook': 'Disturbi magici emanano dalla torre presumibilmente vuota.',
                'setting_details': 'Una torre di pietra alta con multipli piani e trappole magiche.'
            },
            'castle': {
                'background': f'Un antico castello nasconde una minaccia legata a {theme}.',
                'hook': 'Strani eventi si verificano nel castello che si credeva disabitato.',
                'setting_details': 'Un castello medievale con torri, cortili e segrete sotterranee.'
            }
        }
        
        return backgrounds.get(setting, {
            'background': f'Eventi recenti legati a {theme} minacciano l\'area locale.',
            'hook': 'Il party viene avvicinato dalle autorità riguardo a una minaccia crescente.',
            'setting_details': f'L\'avventura si svolge in un ambiente di tipo {setting}.'
        })
    
    def _estimate_duration(self, req):
        """Stima durata sessione"""
        encounters = 4  # Standard
        
        if encounters <= 2:
            return "2-3 ore (sessione breve)"
        elif encounters <= 4:
            return "4-6 ore (sessione lunga)"
        else:
            return "6+ ore (sessioni multiple)"
    
    def _calculate_xp_budget(self, req):
        """Calcola budget XP per encounters"""
        # XP budget per personaggio per livello (semplificato)
        xp_per_level = {
            1: 75, 2: 150, 3: 225, 4: 300, 5: 375
        }
        
        base_xp = xp_per_level.get(req['party_level'], 150)
        return base_xp * req['party_size']
    
    def format_quick_summary(self, adventure):
        """Formatta avventura come riassunto rapido"""
        req = adventure['requirements']
        
        summary = f"""🎲 **{adventure['title']}**

📊 **Dettagli Avventura:**
• Party: {req['party_size']} caratteri livello {req['party_level']}
• Ambientazione: {req['setting'].title()}
• Tema: {req['theme'].title()}
• Durata: {adventure['estimated_duration']}

⚔️ **Encounters ({len(adventure['encounters'])}):**"""
        
        for i, enc in enumerate(adventure['encounters'], 1):
            monsters = [m['name'] for m in enc.get('monsters', [])]
            summary += f"\n{i}. **{enc['title']}** - {', '.join(monsters)}"
        
        summary += f"""

👥 **NPCs ({len(adventure['npcs'])}):**"""
        for npc in adventure['npcs']:
            summary += f"\n• **{npc['name']}** ({npc['role']})"
        
        summary += f"""

💰 **Tesoro:** {adventure['treasure']['gold']} gp"""
        if adventure['treasure']['magic_items']:
            summary += f", {', '.join(adventure['treasure']['magic_items'][:2])}"
        
        summary += f"""

🎭 **Adventure Hook:**
_{adventure['background']['hook']}_

🎯 **XP Budget:** {adventure.get('xp_budget', 'Variable')} XP

_Usa `/adventure_md` per markdown completo! 🎲_
"""
        
        return summary
    
    def format_homebrewery_markdown(self, adventure):
        """Formatta avventura come Homebrewery markdown"""
        req = adventure['requirements']
        
        markdown = f"""# {adventure['title']}
*Un'avventura per {req['party_size']} personaggi di livello {req['party_level']}*

## Panoramica dell'Avventura
{adventure['background']['background']}

### Adventure Hook
> {adventure['background']['hook']}

### Dettagli Ambientazione
{adventure['background']['setting_details']}

---

## Encounters

"""
        
        for i, enc in enumerate(adventure['encounters'], 1):
            markdown += f"""### {enc['title']}
**Tipo:** {enc['type'].title()}  
**Difficoltà:** {enc['difficulty'].title()}  
**CR Totale:** {enc.get('cr_total', '?')}

{enc['description']}

**Creature:**"""
            
            for monster in enc.get('monsters', []):
                markdown += f"""
- **{monster['name']}** (CR {monster.get('cr', '?')})"""
            
            markdown += "\n\n---\n\n"
        
        markdown += f"""## NPCs

"""
        for npc in adventure['npcs']:
            markdown += f"""### {npc['name']}
*{npc['role']}*

**Descrizione:** {npc['description']}  
**Personalità:** {npc['personality']}  
**Statistiche:** {npc['stats']}

"""
        
        markdown += f"""## Tesoro e Ricompense

- **Oro:** {adventure['treasure']['gold']} gp per personaggio"""
        
        if adventure['treasure']['magic_items']:
            markdown += f"""
- **Oggetti Magici:** {', '.join(adventure['treasure']['magic_items'])}"""
        
        markdown += f"""
- **Consumabili:** {', '.join(adventure['treasure']['consumables'])}
- **Speciale:** {adventure['treasure']['special']}

---

*Generato da Codex20 Adventure Creator*
"""
        
        return markdown

# Inizializza Adventure Creator
adventure_creator = AdventureCreator()

# ==========================================
# FUNZIONI DI UTILITÀ D&D
# ==========================================
def calculate_modifier(score):
    """Calcola il modificatore di caratteristica D&D 5e."""
    return (score - 10) // 2

def get_proficiency_bonus(level):
    """Calcola il bonus di competenza in base al livello."""
    try:
        lvl = int(level)
        return 2 + (lvl - 1) // 4
    except:
        return 2

# ==========================================
# GENERAZIONE SCHEDA PDF
# ==========================================
def create_pdf(char, user_id):
    """
    Riceve il dizionario JSON generato da Gemini e lo mappa sui
    campi AcroForm del PDF interattivo '5E_CharacterSheet_Fillable.pdf'.
    Genera un file temporaneo per l'utente, pronto per l'invio su Telegram.
    """
    template_path = "5E_CharacterSheet_Fillable.pdf"
    output_path = f"data/pg_{user_id}.pdf"
    
    if not os.path.exists(template_path):
        logger.error(f"Template PDF non trovato in {template_path}")
        return None

    prof_bonus = get_proficiency_bonus(char.get('livello', 1))
    
    # Mapping base informazioni generali
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

    # Mapping Caratteristiche, Modificatori e Tiri Salvezza
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
        
        save_val = mod
        if stat_ita in comp_salvezza:
            save_val += prof_bonus
            field_data[pdf_check] = "Yes"
        field_data[pdf_save] = f"+{save_val}" if save_val >= 0 else str(save_val)

    # Mapping Abilità (Skills)
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

    # Spell Slots (Livelli 1-9)
    slots_data = char.get('slot_incantesimi', {})
    for lvl in range(1, 10):
        s_val = str(slots_data.get(str(lvl), ''))
        if s_val:
            field_data[f'SlotsTotal {18+lvl}'] = s_val
            field_data[f'SlotsRemaining {18+lvl}'] = s_val

    # Mapping Meticoloso per gli ID dei campi Spells sulla scheda PDF ufficiale
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

    # --- Generazione Overlay Grafico ---
    # Poiché pypdf puro non "scrive" i campi testuali per la visualizzazione normale, 
    # creiamo un layer grafico sovrapposto (con reportlab) che riempie visivamente i form.
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
                                # Inserisce un pallino al centro della checkbox
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
            del page["/Annots"] # Rimuove le annots originali per rendere il PDF flat
        writer.add_page(page)
    
    with open(output_path, 'wb') as f:
        writer.write(f)
    
    return output_path

# ==========================================
# HANDLERS TELEGRAM
# ==========================================
@dp.message(Command("mappa"))
async def send_map_debug(message: types.Message):
    """Comando di utilità/debug: invia un file mappa (se esistente) per il mapping dei campi."""
    map_path = "data/MAPPA_CAMPI_SPELL.pdf"
    if os.path.exists(map_path):
        await message.answer_document(FSInputFile(map_path), caption="Ecco la mappa tecnica dei campi Spell. Dimmi quali ID corrispondono ai vari livelli!")
    else:
        await message.answer("File mappa non trovato. Generazione in corso, riprova tra 5 secondi.")

@dp.message(Command("adventure"))
async def adventure_handler(message: types.Message):
    """Crea avventura D&D da prompt - INTEGRATO IN CODEX20"""
    
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    prompt = message.text.replace("/adventure", "").strip()
    if not prompt:
        await message.answer(
            "🎲 **CODEX20 ADVENTURE CREATOR**\n\n"
            "Genera avventure D&D complete usando i dati ufficiali!\n\n"
            "**Esempi:**\n"
            "`/adventure Grotta goblin per 4 PCs livello 3`\n"
            "`/adventure Torre mago per 6 giocatori livello 5`\n"
            "`/adventure Castello fantasmi livello 4`\n"
            "`/adventure Nave pirata per party esperto`\n\n"
            "_Powered by 5etools database + Gemini 2.0 Flash_ 🎲",
            parse_mode="Markdown"
        )
        return
    
    try:
        logger.info(f"Generazione avventura: {prompt}")
        
        # Genera avventura usando RAG esistente
        adventure = adventure_creator.create_adventure(prompt)
        
        # Formatta risposta
        response = adventure_creator.format_quick_summary(adventure)
        
        await message.answer(response, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Errore creazione avventura: {e}")
        await message.answer("❌ Glitch arcano nell'Adventure Creator! Riprova 🎲")

@dp.message(Command("adventure_md"))
async def adventure_markdown_handler(message: types.Message):
    """Genera markdown Homebrewery completo"""
    
    await bot.send_chat_action(chat_id=message.chat.id, action="upload_document")
    
    prompt = message.text.replace("/adventure_md", "").strip()
    if not prompt:
        await message.answer(
            "📄 Specifica il prompt per l'avventura completa!\n\n"
            "**Esempio:** `/adventure_md Torre mago livello 5`"
        )
        return
    
    try:
        logger.info(f"Generazione markdown: {prompt}")
        
        adventure = adventure_creator.create_adventure(prompt)
        
        # Crea Homebrewery markdown
        markdown = adventure_creator.format_homebrewery_markdown(adventure)
        
        # Invia riassunto prima
        summary = adventure_creator.format_quick_summary(adventure)
        await message.answer(summary, parse_mode="Markdown")
        
        # Crea file temporaneo
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(markdown)
            md_file = f.name
        
        # Invia file
        await message.answer_document(
            FSInputFile(md_file),
            caption=f"📄 **{adventure['title']} - Homebrewery Ready**\n\n"
                   f"Copia su homebrewery.naturalcrit.com per PDF professionale! 🎲",
            parse_mode="Markdown"
        )
        
        # Cleanup
        os.unlink(md_file)
        
    except Exception as e:
        logger.error(f"Errore generazione markdown: {e}")
        await message.answer("❌ Errore nella generazione markdown!")

@dp.message(Command("help"))
async def help_handler(message: types.Message):
    """Comando help aggiornato con Adventure Creator e Session Memory"""
    
    help_text = """🎲 **CODEX20 - IL CUSTODE DEI TOMI**
*Versione 2.1 con Session Memory*

📖 **CONSULTAZIONE D&D 5E:**
Chiedi qualsiasi cosa su regole, mostri, incantesimi, equipaggiamento!
*"Cos'è un Beholder?"* - *"Come funziona Fireball?"*

👤 **GENERAZIONE PERSONAGGI:**
*"Crea un mago elfo livello 3"* → Scheda PDF completa

🗺️ **ADVENTURE CREATOR:**
• `/adventure <prompt>` - Avventura completa bilanciata
• `/adventure_md <prompt>` - Con markdown Homebrewery

🧠 **GESTIONE MEMORIA (NUOVO!):**
• `/memory` - Info sulla memoria della conversazione
• `/forget` - Cancella la memoria e ricomincia da capo

**Esempi Adventures:**
• `/adventure Grotta goblin per 4 PCs livello 3`
• `/adventure Torre mago abbandonata livello 5`  
• `/adventure Castello infestato dai fantasmi`
• `/adventure Nave pirata per party esperto`

🔧 **UTILITÀ:**
• `/mappa` - Debug mapping campi PDF
• `/help` - Questo messaggio

*Powered by Gemini 2.0 Flash + 34MB 5etools database*
*Ora con memoria di conversazione per interazioni più fluide!* 🎲"""
    
    await message.answer(help_text, parse_mode="Markdown")

@dp.message(Command("memory"))
async def memory_command(message: types.Message):
    """Mostra info sessione corrente"""
    user_id = message.from_user.id
    
    session_count = len(session_memory.sessions.get(user_id, []))
    last_activity = session_memory.last_activity.get(user_id)
    
    if last_activity:
        last_activity_str = last_activity.strftime('%H:%M del %d/%m')
    else:
        last_activity_str = "Mai"
    
    await message.answer(
        f"🧠 **Memoria Sessione**\n\n"
        f"• Messaggi salvati: {session_count}/10\n"
        f"• Ultima attività: {last_activity_str}\n"
        f"• Sessione attiva: {'Sì' if session_count > 0 else 'No'}\n\n"
        f"_La memoria mantiene gli ultimi 10 messaggi per conversazioni più fluide._",
        parse_mode="Markdown"
    )

@dp.message(Command("forget"))
async def forget_command(message: types.Message):
    """Cancella memoria sessione"""
    user_id = message.from_user.id
    session_memory.clear_session(user_id)
    
    await message.answer(
        "🧠 **Memoria cancellata!**\n\n"
        "La conversazione ripartirà da zero dal prossimo messaggio. 🎲"
    )

@dp.message(F.text)
async def chat_handler(message: types.Message):
    """
    Handler principale: ascolta i messaggi, interroga i tomi e comunica con Gemini.
    Esegue il parsing della risposta: se rileva un blocco JSON, lo invia al modulo PDF
    e restituisce la scheda personaggio generata in chat.
    """
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    # Controllo per adventure intent senza comando esplicito
    adventure_keywords = [
        'avventura', 'adventure', 'dungeon', 'quest', 'missione',
        'grotta', 'torre', 'castello', 'bosco', 'foresta', 'nave',
        'goblin', 'orchi', 'fantasmi', 'non morti', 'drago', 'banditi'
    ]
    
    # Check se il messaggio contiene "help" o parole chiave help
    if any(word in message.text.lower() for word in ['help', 'aiuto', 'comandi', 'cosa puoi fare']):
        await help_handler(message)
        return
    
    # Check per adventure intent
    if any(keyword in message.text.lower() for keyword in adventure_keywords):
        # Se contiene anche indicatori di livello/party, probabile adventure request
        if any(indicator in message.text.lower() for indicator in ['livello', 'level', 'lv', 'pcs', 'giocatori', 'party']):
            try:
                # Genera avventura direttamente
                adventure = adventure_creator.create_adventure(message.text)
                response = adventure_creator.format_quick_summary(adventure)
                await message.answer(
                    f"🎯 **Rilevata richiesta avventura!**\n\n{response}",
                    parse_mode="Markdown"
                )
                return
            except Exception as e:
                logger.error(f"Errore adventure intent: {e}")
                # Continua con normale processing
    
    # 1. Ricerca Dinamica nei manuali (5etools)
    tomi_context = search_5etools(message.text)
    
    # 2. Composizione del Prompt (Personalità + Regole + Richiesta Utente)
    prompt = f"{system_context_base}{tomi_context}\n\nUtente: {message.text}"
    
    try:
        response_text = await generate_content_safe(prompt)
        if not response_text: return

        # Cerchiamo se l'AI ha generato il payload JSON per la scheda personaggio
        # Supporta ```json {JSON} ```, ``` {JSON} ``` e {JSON} (senza backticks)
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```|(\{.*?\})", response_text, re.DOTALL)
        
        if json_match:
            try:
                # Seleziona il gruppo corretto in base a quale parte della regex ha matchato
                json_str = json_match.group(1) if json_match.group(1) else json_match.group(2)
                char_data = json.loads(json_str)
                
                # Crea fisicamente il PDF sul disco temporaneo
                pdf_path = create_pdf(char_data, message.from_user.id)
                
                # Rimuove il blocco JSON dalla stringa in modo che l'utente non veda il codice RAW
                clean_text = re.sub(r"```(?:json)?.*?```", "", response_text, flags=re.DOTALL).strip()
                # Se non c'erano backticks, prova a rimuovere il JSON nudo (se è alla fine o all'inizio)
                if clean_text == response_text.strip():
                     clean_text = response_text.replace(json_str, "").strip()

                if clean_text: 
                    try:
                        await message.answer(clean_text, parse_mode="Markdown")
                    except Exception:
                        await message.answer(clean_text)
                
                if pdf_path:
                    # Invia il Documento generato
                    try:
                        await message.answer_document(
                            FSInputFile(pdf_path), 
                            caption=f"Ecco la scheda di *{char_data.get('nome')}*! 🎲",
                            parse_mode="Markdown"
                        )
                    except Exception:
                        await message.answer_document(
                            FSInputFile(pdf_path), 
                            caption=f"Ecco la scheda di {char_data.get('nome')}! 🎲"
                        )
                    
                    # Cleanup del file temporaneo
                    if os.path.exists(pdf_path): 
                        os.remove(pdf_path)
                else:
                    await message.answer("Dati generati correttamente, ma c'è stato un problema nella creazione fisica del PDF. 🎲")
                return
            
            except Exception as e:
                logger.error(f"Errore parsing JSON o generazione PDF: {e}")
                # Se il parsing fallisce, proseguiamo trattando come risposta testuale

        # Se non c'era JSON o se c'è stato un errore nel parsing, tratta come risposta standard
        response_text = response_text.strip()
        if len(response_text) > 4000:
            await message.answer(f"{response_text[:4000]}...")
        else:
            try:
                await message.answer(f"{response_text}\n\n🎲", parse_mode="Markdown")
            except Exception:
                await message.answer(f"{response_text}\n\n🎲")
            
    except Exception as e:
        logger.error(f"Errore generale: {e}")
        await message.answer("Spiacente, Codex20 ha subito un glitch arcano. Riprova! 🎲")

# ==========================================
# BOOTSTRAP
# ==========================================
async def setup_bot_commands():
    """Registra i comandi del bot con Telegram all'avvio"""
    
    commands = [
        types.BotCommand(command="help", description="📖 Guida completa e lista comandi"),
        types.BotCommand(command="adventure", description="🎲 Crea avventura completa bilanciata"),
        types.BotCommand(command="adventure_md", description="📜 Avventura con markdown Homebrewery"),
        types.BotCommand(command="memory", description="🧠 Info sulla memoria conversazione"),
        types.BotCommand(command="forget", description="🗑️ Cancella memoria e ricomincia"),
        types.BotCommand(command="mappa", description="🔧 Debug mapping campi PDF"),
    ]
    
    try:
        await bot.set_my_commands(commands, scope=types.BotCommandScopeDefault())
        logger.info("✅ Bot commands registered successfully!")
    except Exception as e:
        logger.error(f"❌ Error registering commands: {e}")

async def main():
    logger.info("Avvio di Codex20 - Il Custode dei Tomi")
    
    # Register bot commands on startup
    await setup_bot_commands()
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
