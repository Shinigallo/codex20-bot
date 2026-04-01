# 🎲 Codex20 v2.0 - The Complete D&D Companion

**The ultimate Telegram bot for D&D 5e - now with integrated Adventure Creator!**

*Powered by Gemini 2.0 Flash + 34MB official 5etools database*

---

## ✨ Features

### 📖 **Rules & Content Lookup** 
- **Monster stats** - Query any creature from official sources
- **Spell details** - Complete spell descriptions and mechanics  
- **Equipment & Items** - Magic items, weapons, armor stats
- **Rules clarification** - Official 5e rule interpretations

### 👤 **Character Generation**
- **Complete character sheets** - Auto-generated PDF forms
- **Balanced builds** - Level-appropriate stats and abilities
- **Official content** - Uses authentic 5e races, classes, spells
- **PDF export** - Professional fillable character sheets

### 🗺️ **Adventure Creator** *(NEW in v2.0!)*
- **Balanced encounters** - CR calculations per DMG guidelines
- **Complete adventures** - 4 encounters + NPCs + treasure + background
- **Intelligent analysis** - Auto-detects party level, size, setting, theme
- **Multiple formats** - Quick summary + Homebrewery-ready markdown
- **Official content** - Uses authentic monsters, spells, items from RAG database

---

## 🎮 Usage Examples

### Adventure Creation
```
/adventure Grotta goblin per 4 PCs livello 3
→ Complete balanced adventure with encounters, NPCs, treasure

/adventure_md Torre del mago abbandonata livello 5  
→ Full adventure + Homebrewery markdown file

"Castello infestato dai fantasmi per party esperto"
→ Smart intent detection creates adventure automatically
```

### Character Generation  
```
"Crea un mago elfo livello 5"
→ Complete character sheet PDF with spells, stats, equipment

"Genera un ranger halfling per party livello 3"
→ Balanced character appropriate for party level
```

### Rules Lookup
```
"Cos'è un Beholder?"
→ Complete monster stats and abilities

"Come funziona Fireball?"  
→ Spell description, damage, range, components
```

---

## 🎯 Adventure Creator Capabilities

### **Intelligent Prompt Analysis**
- **Party Level**: Detects "livello 3", "level 5", "lv 4"
- **Party Size**: Recognizes "4 PCs", "6 giocatori", "party"  
- **Setting**: Cave, tower, forest, city, ship, dungeon
- **Theme**: Goblins, undead, dragons, bandits, magical

### **Balanced Content Generation**
- **4 Encounters** per adventure (easy → medium → hard → boss)
- **CR Calculations** using official Dungeon Master's Guide formulas
- **XP Budget** appropriate for party level and size
- **Level-appropriate treasure** including magic items

### **Professional Output**
- **Quick Summary** - Essential info for immediate use
- **Homebrewery Markdown** - Copy to homebrewery.naturalcrit.com for PDF
- **Complete NPCs** - Names, roles, personalities, stat references
- **Adventure Background** - Hooks, setting details, plot structure

---

## 🔧 Technical Architecture

### **RAG System Integration**
```
User Prompt → Intelligent Analysis → 5etools Database Query → Content Generation
     ↓              ↓                       ↓                    ↓
"Goblin cave    Party: 4 lv3         Official Goblin Stats    Balanced Adventure
 level 3"       Setting: Cave         CR 1-4 Monsters         Ready for Play
                Theme: Goblinoids     Magic Items Database
```

### **Data Sources** 
- **34MB Official Content** from 5etools project
- **Monster Manual** - Complete bestiary with official stats
- **Player's Handbook** - Spells, classes, races, equipment  
- **Dungeon Master's Guide** - Magic items, encounter building rules
- **Adventure Modules** - Reference content for authentic feel

### **API Resilience**
- **Multiple Gemini keys** with automatic rotation
- **Rate limit handling** - Seamless failover on HTTP 429
- **Error recovery** - Graceful degradation on service issues

---

## 📋 Commands Reference

### Core Commands
- `/adventure <prompt>` - Generate complete D&D adventure
- `/adventure_md <prompt>` - Generate adventure with Homebrewery markdown
- `/help` - Show all available commands and examples
- `/mappa` - Debug utility for PDF field mapping

### Natural Language
- **Adventure requests** - Automatic detection without commands
- **Character generation** - "Crea un [classe] [razza] livello [N]"  
- **Rules queries** - Ask about any D&D content naturally
- **Help requests** - "aiuto", "help", "cosa puoi fare"

---

## 🎲 Installation & Setup

### Prerequisites
```bash
pip install aiogram google-generativeai python-dotenv pypdf reportlab
```

### Environment Variables
```bash
# .env file
TELEGRAM_TOKEN=your_bot_token_here
GEMINI_API_KEYS=key1,key2,key3  # Multiple keys for resilience
```

### File Structure
```
codex20-bot/
├── bot.py                    # Main bot with integrated Adventure Creator
├── data/5etools/            # 34MB official D&D database  
├── 5E_CharacterSheet_Fillable.pdf  # Template for character sheets
├── .env                     # API keys and tokens
└── README.md               # This file
```

### Run
```bash
python bot.py
```

---

## 🎨 Adventure Examples

### Generated Adventure Output
```
🎲 Le Grotte Oscure

📊 Dettagli Avventura:
• Party: 4 caratteri livello 3
• Ambientazione: Cave • Tema: Goblinoids  
• Durata: 4-6 ore (sessione lunga)

⚔️ Encounters (4):
1. Scontro 1 - Goblin
2. Scontro 2 - Hobgoblin  
3. Scontro 3 - Bugbear
4. Boss Finale - Ogre

👥 NPCs (2):
• Anziano del Villaggio (Quest Giver)
• Mercante Catturato (NPC da Salvare)

💰 Tesoro: 200-400 gp, Pozione di Cura, Pergamena Magica

🎭 Adventure Hook:
I locali segnalano viaggiatori scomparsi e strani suoni dalle grotte.

🎯 XP Budget: 1200 XP
```

---

## 🌟 Version History

### **v2.0** - Adventure Creator Integration *(Latest)*
- ✨ Complete adventure generation system
- 🎯 Intelligent prompt analysis and content generation  
- 📄 Homebrewery markdown export for professional PDFs
- 🧠 Smart intent recognition for natural language requests
- 🔧 Seamless integration with existing RAG system

### **v1.x** - Character Creator & Rules Engine
- 👤 Automated character sheet generation with PDF export
- 📖 Comprehensive D&D 5e rules lookup system
- 🎲 Integration with official 5etools database
- 🔄 Gemini API rotation for reliability

---

## 🤝 Contributing

This bot represents a complete D&D 5e toolkit with professional-grade content generation. The Adventure Creator uses the same authoritative database as the rules engine, ensuring authentic and balanced content.

**Key Integration Points:**
- Uses existing `search_5etools()` function for content queries
- Leverages established Gemini API rotation for resilience  
- Maintains consistent PDF generation pipeline for both characters and adventures
- Extends natural language processing for adventure intent detection

---

## 📜 License & Credits

**Built with:**
- [5etools](https://5e.tools/) - Official D&D 5e content database
- [Gemini 2.0 Flash](https://ai.google.dev/) - AI language model
- [aiogram](https://docs.aiogram.dev/) - Telegram Bot API framework
- [ReportLab](https://www.reportlab.com/) - PDF generation

*Codex20 v2.0 - Your complete digital Dungeon Master* 🎲