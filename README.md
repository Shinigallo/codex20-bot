# 🎲 Codex20 OpenRouter

Assistente D&D 5e con interfaccia web e Telegram, powered by OpenRouter AI.

## 🚀 Installazione Rapida

### Prerequisiti
- Docker e Docker Compose
- OpenRouter API Key (gratuita su https://openrouter.ai)

### Setup Interattivo (Prima volta)
```bash
# Clona il repository
git clone https://github.com/tu-username/codex20-openrouter.git
cd codex20-openrouter

# Avvia il wizard di setup
python setup.py
```

Il wizard ti guiderà attraverso:
1. Creazione utente admin
2. Iniezione API key OpenRouter
3. Selezione modello AI
4. Generazione configurazione

### Avvio Servizio
```bash
# Avvia il servizio principale
docker compose up -d

# Controlla lo stato
docker compose logs -f
```

## 🌐 Interfaccia Web

Accedi all'interfaccia web:
- **URL**: http://localhost:8085
- **Login**: Utente creato durante il setup

### Funzionalità
- 💬 Chat con assistente AI
- 📁 Upload/Download materiale campagna
- 👥 Multi-utente con autenticazione
- 🔄 Fallback automatico modelli

## 📱 Bot Telegram

### Configurazione
1. Crea un bot su Telegram con @BotFather
2. Ottieni il token
3. Aggiungi al .env:
```bash
TELEGRAM_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
```

### Avvio Bot
```bash
docker compose run --rm bot
```

## ⚙️ Configurazione

### Variabili d'Ambiente
| Variabile | Descrizione | Default |
|-----------|-------------|---------|
| `OPENROUTER_API_KEY` | API key OpenRouter | - |
| `MODEL_NAME` | Modello AI principale | `google/gemma-4-31b-it:free` |
| `BACKUP_MODEL_NAME` | Modello di backup | `nvidia/nemotron-3-ultra-550b-a55b:free` |
| `ADMIN_USERNAME` | Username admin | `admin` |
| `ADMIN_PASSWORD` | Password admin (hash) | - |

### Modelli Disponibili
```bash
# Modifica .env con il modello desiderato
MODEL_NAME=google/gemma-4-31b-it:free
# Oppure:
MODEL_NAME=qwen/qwen3.5:free
MODEL_NAME=meta-llama/llama-3.3-70b-instruct:free
```

## 🛠️ Sviluppo

### Struttura Progetto
```
codex20-openrouter/
├── app.py              # FastAPI backend
├── setup.py            # Setup wizard
├── bot.py              # Telegram bot
├── core/
│   ├── api_client.py   # OpenRouter client
│   ├── session.py      # Gestione sessioni
│   ├── users.py        # Gestione utenti
│   └── rag.py          # RAG regole D&D
├── static/
│   └── index.html      # Interfaccia web
├── data/               # Database SQLite
└── logs/               # Log applicativi
```

### Avvio Locale
```bash
# Installa dipendenze
pip install -r requirements.txt

# Avvia setup
python setup.py

# Avvia server
uvicorn app:app --host 0.0.0.0 --port 8084
```

## 🔒 Sicurezza

- Password hashate con SHA256
- JWT tokens per autenticazione
- API key non esposte nei log
- CORS configurato per produzione

## 📊 Monitoraggio

```bash
# Controlla log
docker compose logs -f codex20

# Stato API
curl http://localhost:8085/api/status

# Test connessione
curl http://localhost:8085/api/test
```

## 🐛 Troubleshooting

### Container non avvia
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

### API 429 Rate Limit
Il sistema usa automaticamente il modello di backup quando il principale è rate-limited.

### Password dimenticata
```bash
docker exec -it codex20-python python -c "
from core.users import register_user
register_user('admin', 'nuova-password')
"
```

## 📝 License

MIT License - Vedi LICENSE file

## 🤝 Contributi

1. Fork il progetto
2. Crea branch feature
3. Commit cambiamenti
4. Push e Pull Request

---

**Created with ❤️ by Dario & Codex20 Team**
