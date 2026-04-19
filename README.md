# 🎲 Codex20 - Il Custode dei Tomi

**Advanced D&D 5e Telegram Bot with AI-Powered Semantic Memory and Campaign Management**

---

## 🌟 Features

### 🧠 **Dual Memory System**
- **Short-term Sessions:** SQLite-based persistent sessions (20 messages, 72-hour TTL)
- **Long-term Semantic Memory:** MemPalace integration for D&D knowledge and campaign continuity
- **Session Commands:** `/memory` (view session) and `/forget` (clear session)

### 🎲 **Advanced D&D Capabilities**
- **Semantic D&D Search:** `/search_rules [query]` - Natural language SRD lookup
- **Campaign Memory:** `/remember_campaign [details]` - Store campaign information permanently
- **Campaign Recall:** `/recall_campaign [query]` - Retrieve campaign memories with context
- **Monster Database:** `/monster_lookup [creature]` - Enhanced creature database
- **Spell Discovery:** `/spell_search [query]` - Advanced spell search with similarities
- **NPC Memory:** `/npc_memory [name] [details]` - Track NPCs and relationships

### 🤖 **AI-Powered Intelligence**
- **Google Gemini 2.0 Flash** integration with automatic API key rotation
- **Context-aware responses** remembering entire campaign history
- **Multi-turn D&D consultations** with persistent memory
- **Intelligent rule clarification** and tactical advice

### 📚 **Complete D&D 5e Integration**
- **System Reference Document** fully indexed for semantic search
- **Monster Manual** with tactical advice and encounter suggestions
- **Spell Compendium** with cross-references and similar spell discovery
- **Equipment Database** including magic items and properties
- **Campaign Templates** with adventure hooks and scenarios

---

## 🏗️ Architecture

### **Hybrid Memory System:**
```
┌─────────────────┐    ┌─────────────────────┐
│   SQLite        │    │    MemPalace        │
│   Sessions      │    │   Semantic Store    │
│                 │    │                     │
│ • 20 messages   │◄──►│ • D&D Knowledge     │
│ • 72h TTL       │    │ • Campaign Memory   │
│ • User context  │    │ • NPC Database      │
└─────────────────┘    └─────────────────────┘
```

### **Performance:**
- **Session Management:** Instant retrieval from SQLite
- **Semantic Queries:** <200ms response time via MemPalace
- **Persistent Storage:** Campaign data survives bot restarts
- **Scalable Architecture:** Handles multiple users and campaigns

---

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Telegram Bot Token (from @BotFather)
- Google Gemini API Key

### Installation
```bash
# Clone repository
git clone https://github.com/Shinigallo/codex20-bot.git
cd codex20-bot

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Deploy with Docker
docker compose up -d --build
```

### Environment Variables
```env
TELEGRAM_TOKEN=your_telegram_bot_token_here
GEMINI_API_KEYS=your_gemini_api_key_here,optional_second_key
AUTHORIZED_USER_ID=your_telegram_user_id
```

---

## 🎮 Usage

### **Basic Commands**
- `/start` - Initialize bot and show welcome
- `/help` - Display all available commands
- `/memory` - View current session information
- `/forget` - Clear current session memory

### **D&D Knowledge Commands**
```
/search_rules fireball spell mechanics
/monster_lookup ancient red dragon
/spell_search spells similar to healing word
```

### **Campaign Management**
```
/remember_campaign The party met Elara the elf ranger in Neverwinter. She's seeking her missing brother who was taken by orcs to the Sword Mountains.

/recall_campaign Who is Elara?

/npc_memory Elara Elf ranger from Neverwinter, missing brother taken by orcs, party ally since session 1
```

---

## 🔧 Technical Details

### **Session Management**
- **PersistentSessionManager:** SQLite-based storage with configurable limits
- **Automatic cleanup:** Removes expired sessions (72-hour default TTL)
- **User isolation:** Each user has independent session storage
- **Context building:** Last 3 messages included in AI prompts

### **MemPalace Integration**
- **Semantic Search:** ChromaDB-powered similarity search
- **D&D Content:** Complete SRD indexed with metadata
- **Campaign Storage:** Structured campaign data with user/group isolation
- **Performance Optimization:** Cached queries and efficient indexing

### **AI Integration**
- **Multi-key Support:** Automatic rotation to handle rate limits
- **Context Enhancement:** Combines session + semantic memory
- **Error Handling:** Graceful fallback and retry mechanisms
- **Token Management:** Efficient prompt construction and truncation

---

## 📊 Bot Statistics

### **Memory Capabilities**
- **Session Storage:** 20 messages per user (configurable)
- **Campaign Memory:** Unlimited semantic storage via MemPalace
- **D&D Knowledge Base:** Complete SRD + expanded content
- **Query Performance:** <200ms semantic search response

### **Supported Content**
- **Rules & Mechanics:** All D&D 5e SRD content
- **Monsters:** 400+ creatures with full stat blocks
- **Spells:** 300+ spells with cross-references
- **Equipment:** Magic items, weapons, armor
- **Campaign Data:** NPCs, locations, plot threads

---

## 🎯 Use Cases

### **For Dungeon Masters**
- Quick rule lookups during gameplay
- Monster stat and tactical information
- Campaign continuity tracking
- NPC relationship management
- Plot thread organization

### **For Players**
- Spell and ability clarification
- Character build optimization
- Campaign history reference
- Rules question resolution
- Collaborative storytelling

### **For Groups**
- Shared campaign memory
- Session recap generation
- Character interaction tracking
- World-building assistance
- Adventure planning support

---

## 🔮 Advanced Features

### **Intelligent Context**
- Remembers previous conversations and campaign details
- Maintains character relationships and plot developments
- Provides context-aware rule interpretations
- Suggests tactical options based on campaign history

### **Natural Language Processing**
- Understands complex D&D queries in natural language
- Cross-references related content automatically
- Provides similar content suggestions
- Contextualizes responses to current campaign

### **Multi-User Campaign Support**
- Group-specific campaign memories
- Shared NPC and location databases
- Collaborative world-building
- Session-to-session continuity

---

## 📈 Version History

### **v2.2 - MemPalace Integration (2026-04-19)**
- ✅ **MemPalace Integration:** Semantic D&D knowledge base
- ✅ **Campaign Memory System:** Persistent NPC/location/plot storage
- ✅ **Enhanced Commands:** `/search_rules`, `/remember_campaign`, `/recall_campaign`
- ✅ **Performance Optimization:** <200ms semantic query response
- ✅ **Complete SRD Integration:** All D&D 5e content indexed

### **v2.1 - Session Memory (2026-04-01)**
- ✅ **Persistent Sessions:** SQLite-based session storage
- ✅ **Memory Commands:** `/memory` and `/forget` functionality
- ✅ **Context Building:** Multi-turn conversation support
- ✅ **Session Management:** 20 messages per user with TTL

### **v2.0 - Foundation (2026-03-25)**
- ✅ **Core Bot:** Telegram integration with Gemini AI
- ✅ **D&D Features:** Basic rules and content assistance
- ✅ **Docker Deployment:** Containerized application
- ✅ **API Integration:** Google Generative AI support

---

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines and open issues for ways to help improve Codex20.

### **Development Setup**
```bash
# Local development
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python bot.py
```

---

## 📄 License

MIT License - see LICENSE file for details.

---

## 🙏 Acknowledgments

- **OpenSlaw Multi-Agent Framework** - AI specialist deployment system
- **MemPalace** - Semantic memory and knowledge management
- **Google Gemini** - Advanced AI capabilities
- **D&D 5e SRD** - Comprehensive rule system integration

---

**🎲 The most intelligent D&D companion bot ever created - with persistent semantic memory and complete campaign management capabilities!**