# 🎲 Codex20 - Il Custode dei Tomi

Codex20 è un assistente digitale evoluto per Dungeon Master e giocatori di D&D 5e, ora migrato interamente in **Python** per una gestione superiore della logica di gioco e dei documenti.

## 🧠 Caratteristiche Principali

- **Mente Gemini 2.0 Flash:** Integra i modelli più avanzati di Google per risposte rapide, creative e contestualizzate.
- **Custode dei Tomi (5etools):** Consulta automaticamente un database espanso di file JSON (razze, classi, mostri, incantesimi) per fornire risposte basate sulle regole ufficiali.
- **Forgia degli Eroi:** Generazione istantanea di schede personaggio in formato **PDF** tramite il comando `/randompg`.
- **Resilienza API:** Logica di rotazione automatica multi-chiave per gestire i limiti di quota delle API Gemini.

## 🛠️ Comandi Disponibili

- `/randompg` - Consulta i Tomi e forgia un nuovo eroe casuale di livello 1, inviando una scheda PDF completa.
- `[Messaggio di testo]` - Chiedi a Codex20 qualsiasi cosa riguardo regole, lore o aiuto per la tua campagna.

## 🚀 Installazione (Docker)

1. Clona il repository.
2. Crea un file `.env` basato sul seguente schema:
   ```env
   TELEGRAM_TOKEN=il_tuo_token_telegram
   GEMINI_API_KEYS=chiave1,chiave2,chiave3
   ```
3. Avvia con Docker Compose:
   ```bash
   docker compose up -d --build
   ```

## 📂 Struttura Dati
Il bot si aspetta di trovare i dati di 5etools nella cartella `data/5etools/`. Supporta la scansione ricorsiva di tutti i file JSON per trovare informazioni su razze, classi e background.

---
*Codex20 è in continua evoluzione. Che il tuo d20 possa sempre segnare 20!* 🎲
