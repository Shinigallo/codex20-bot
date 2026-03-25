# Codex20 - Il Custode dei Tomi 🎲🐉

**Codex20** è un avanzato assistente digitale per Dungeon Master e giocatori di **Dungeons & Dragons 5e**, sviluppato in Python. Sfrutta l'intelligenza artificiale generativa per fornire risposte rapide, creare schede personaggio complete in PDF e consultare in tempo reale i manuali ufficiali.

---

## 🎯 Funzionalità Principali

### 1. 🧠 Mente AI (Gemini 2.0 Flash)
Codex20 è alimentato dall'avanzato modello **Google Gemini 2.0 Flash**. Questo gli permette di comprendere il linguaggio naturale, gestire contesti complessi e mantenere il ruolo di un esperto Dungeon Master con una forte personalità.

### 2. 📚 Custode dei Tomi (Integrazione 5etools)
Il bot non si basa solo sulla conoscenza pregressa dell'AI. Interroga attivamente e dinamicamente un vasto database di file JSON basati su **5etools** (mostri, incantesimi, classi, razze, oggetti).
Questo assicura che ogni risposta tecnica (es. le statistiche di un incantesimo o i danni di un mostro) sia fedele al 100% alle regole ufficiali di D&D 5e (Meccanismo RAG - Retrieval-Augmented Generation).

### 3. 🛡️ Forgia degli Eroi (Generazione PDF Dinamica)
Chiedendo semplicemente a Codex20 di creare un personaggio (es. *"Creami un chierico mezzelfo di livello 3 specializzato in cure"*), il bot farà due cose:
1. **Genererà tutte le statistiche:** Caratteristiche, abilità, bonus di competenza, incantesimi ed equipaggiamento in base alle regole.
2. **Compilerà una Scheda Ufficiale PDF:** Il bot mapperà i dati e compilerà automaticamente tutti i campi della classica scheda personaggio di D&D 5e, inviando all'utente il file PDF pronto da stampare.

### 4. 🔄 Resilienza e API Rotation
Per prevenire problemi di rate-limit (Errore HTTP 429) o esaurimento delle quote, Codex20 implementa un sistema di **rotazione automatica delle API Keys**. Se una chiave raggiunge il limite, il bot passa istantaneamente alla successiva senza interrompere il servizio per l'utente.

---

## 🚀 Esempi di Utilizzo

- **Creazione Personaggio:** *"Ho bisogno di una scheda per un ladro tiefling di livello 5, caotico neutrale."* (Il bot risponderà con un PDF compilato)
- **Consultazione Regole:** *"Come funziona esattamente l'incantesimo Palla di Fuoco?"*
- **Generazione Rapida:** `/randompg` (Genera un personaggio di livello 1 casuale)
- **Gestione Master:** *"Creami un incontro per un party di 4 giocatori di livello 3 in una palude."*

---

## 🛠️ Stack Tecnologico

- **Linguaggio:** Python 3.10+
- **Librerie Core:**
  - `aiogram` - Per l'integrazione fluida e asincrona con Telegram
  - `google-generativeai` - Per l'interfacciamento con Gemini API
  - `pypdf` & `reportlab` - Per la lettura, modifica e generazione della scheda PDF
- **Database:** JSON strutturati (5etools schema)
- **Deployment:** Docker e Docker Compose per un rilancio rapido in qualsiasi ambiente

---

## ⚙️ Installazione e Setup (Docker)

1. **Clona il repository:**
   ```bash
   git clone https://github.com/Shinigallo/codex20-bot.git
   cd codex20-bot
   ```

2. **Configura le variabili d'ambiente:**
   Copia il file di esempio e inserisci le tue chiavi.
   ```bash
   cp .env.example .env
   ```
   Nel file `.env` inserisci:
   ```env
   TELEGRAM_TOKEN=il_tuo_token_telegram
   GEMINI_API_KEYS=chiave_1,chiave_2,chiave_3
   ```

3. **Struttura Dati (Tomi):**
   Assicurati che la cartella `data/5etools/` contenga i file JSON (es. `spells.json`, `bestiary.json`). Il bot scansionerà ricorsivamente tutti i JSON presenti per fare grounding delle risposte.

4. **Avvia il bot con Docker:**
   ```bash
   docker-compose up -d --build
   ```

---

## 📂 Struttura del Progetto

```
codex20-bot/
├── bot.py                  # Core logic, Telegram handlers e AI integration
├── 5E_CharacterSheet_Fillable.pdf  # Template PDF ufficiale D&D
├── Dockerfile              # Immagine Docker
├── docker-compose.yml      # Configurazione multi-container
├── requirements.txt        # Dipendenze Python
└── data/                   # Dati persistenti
    ├── 5etools/            # (Opzionale) File JSON del compendio
    ├── SOUL.md             # Personalità e prompt di sistema
    └── pg_*.pdf            # (Temporanei) PDF generati
```

---

*Che i tuoi dadi possano sempre rotolare sul 20!* 🎲
