# 🎲 Codex20 - Il Custode dei Tomi

Codex20 è un assistente digitale evoluto per Dungeon Master e giocatori di D&D 5e, ora migrato interamente in **Python** per una gestione superiore della logica di gioco e dei documenti.

## 🧠 Caratteristiche Principali

- **Mente Gemini 2.0 Flash:** Integra i modelli più avanzati di Google per risposte rapide, creative e contestualizzate.
- **Custode dei Tomi (5etools):** Consulta automaticamente un database espanso di file JSON (razze, classi, mostri, incantesimi) per fornire risposte basate sulle regole ufficiali.
- **Forgia degli Eroi Avanzata:** Generazione istantanea di schede personaggio in formato **PDF** sia casuali che specifiche tramite linguaggio naturale.
- **Resilienza API:** Logica di rotazione automatica multi-chiave per gestire i limiti di quota delle API Gemini.

## 🛠️ Comandi e Funzionalità

- `/randompg` - Consulta i Tomi e forgia un nuovo eroe casuale di livello 1.
- **Creazione Intelligente:** Chiedi a Codex20 in linguaggio naturale, ad esempio: 
  - *"Creati un mago umano di livello 5"*
  - *"Fammi la scheda di un ladro tiefling livello 3"*
  Codex20 genererà automaticamente il PDF completo con statistiche, competenze ed equipaggiamento.
- **Consultazione Regole:** Chiedi dettagli su mostri, incantesimi o regole specifiche (es. *"Cosa fa l'incantesimo Palla di Fuoco?"*), il bot cercherà nei manuali (5etools) per darti la risposta corretta.

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
Il bot si aspetta di trovare i dati di 5etools nella cartella `data/5etools/`. Supporta la scansione ricorsiva di tutti i file JSON per trovare informazioni su razze, classi e background. Il bot utilizza questi dati per fare **grounding** delle risposte fornite dall'AI.

---
*Codex20 è in continua evoluzione. Che il tuo d20 possa sempre segnare 20!* 🎲
