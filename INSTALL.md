# 📦 Installazione Codex20 OpenRouter

Guida completa per installare Codex20 su GitHub.

## 🚀 Quick Start (3 minuti)

### 1. Clona il repository
```bash
git clone https://github.com/tu-username/codex20-openrouter.git
cd codex20-openrouter
```

### 2. Configura le variabili d'ambiente
```bash
# Copia il template
cp .env.example .env

# Modifica con le tue configurazioni
nano .env
```

**Campi obbligatori:**
- `OPENROUTER_API_KEY` - La tua chiave API OpenRouter
- `ADMIN_PASSWORD_HASH` - Hash SHA256 della password admin

### 3. Avvia il servizio
```bash
# Opzione A: Script di deploy automatico
chmod +x deploy.sh
./deploy.sh

# Opzione B: Comandi manuali
docker-compose build
docker-compose up -d
```

### 4. Accedi
```
URL: http://localhost:8085
Username: admin
Password: <quella che hai impostato>
```

---

## 🔧 Installazione Dettagliata

### Prerequisiti

- **Docker** v20.10+
- **Docker Compose** v2.0+
- **OpenRouter API Key** (gratuita su [openrouter.ai](https://openrouter.ai))

### Passo 1: Clona il Repository

```bash
git clone https://github.com/tu-username/codex20-openrouter.git
cd codex20-openrouter
```

### Passo 2: Configurazione

#### Opzione A: Setup Interattivo (Consigliato per prima volta)
```bash
python setup.py
```

Il wizard ti guiderà attraverso:
1. Creazione utente admin
2. Inserimento API key
3. Selezione modello AI
4. Generazione configurazione

#### Opzione B: Configurazione Manuale
```bash
# Copia il template
cp .env.example .env

# Modifica il file
nano .env
```

**Campi da compilare:**

| Variabile | Descrizione | Obbligatoria |
|-----------|-------------|--------------|
| `OPENROUTER_API_KEY` | Chiave API OpenRouter | ✅ |
| `ADMIN_PASSWORD_HASH` | Hash SHA256 password | ✅ |
| `ADMIN_USERNAME` | Username admin | ❌ (default: admin) |
| `MODEL_NAME` | Modello AI principale | ❌ (default: gemma-4) |
| `BACKUP_MODEL_NAME` | Modello di backup | ❌ (default: nemotron) |

#### Opzione C: Deploy Automatico
```bash
# Script di deploy pronto all'uso
chmod +x deploy.sh
./deploy.sh
```

### Passo 3: Verifica Configurazione

```bash
# Controlla che il file .env sia valido
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

required = ['OPENROUTER_API_KEY', 'ADMIN_PASSWORD_HASH']
missing = [k for k in required if not os.getenv(k)]
if missing:
    print(f'Missing: {missing}')
    exit(1)
print('✅ Config OK')
"
```

### Passo 4: Build e Avvio

```bash
# Build immagine Docker
docker-compose build

# Avvia servizi
docker-compose up -d

# Verifica stato
docker-compose ps
```

### Passo 5: Test Connessione

```bash
# Test API
curl http://localhost:8085/api/test

# Status
curl http://localhost:8085/api/status
```

---

## 🤖 Selezione Modello AI

### Modelli Disponibili

| ID | Modello | Dimensione | Descrizione |
|----|---------|------------|-------------|
| `1` | `google/gemma-4-31b-it:free` | 31B | Default, ottimo per D&D |
| `2` | `qwen/qwen3.5:free` | 7B | Leggero e veloce |
| `3` | `meta-llama/llama-3.3-70b-instruct:free` | 70B | Più potente |
| `4` | `nvidia/nemotron-3-ultra-550b-a55b:free` | 550B | Backup consigliato |

### Come Cambiare Modello

Modifica `.env`:
```bash
MODEL_NAME=qwen/qwen3.5:free
BACKUP_MODEL_NAME=nvidia/nemotron-3-ultra-550b-a55b:free
```

Riavvia:
```bash
docker-compose restart
```

---

## 🔐 Sicurezza

### Genera Hash Password

```bash
python -c "
import hashlib
password = 'tua-password-sicura'
hash_value = hashlib.sha256(password.encode()).hexdigest()
print(f'ADMIN_PASSWORD_HASH={hash_value}')
"
```

### Genera JWT Secret

```bash
python -c "
import secrets
print(f'JWT_SECRET={secrets.token_hex(32)}')
"
```

### Best Practices

1. **Mai committare `.env`** - Aggiunto a `.gitignore`
2. **Usa password forti** - Minimo 12 caratteri
3. **Cambia JWT_SECRET** - Genera casuale in produzione
4. **Aggiorna regolarmente** - `git pull && docker-compose pull`

---

## 🐳 Docker Compose

### Struttura

```yaml
services:
  setup:        # Setup wizard (prima volta)
  codex20:      # Servizio principale
```

### Profili

```bash
# Avvia solo setup
docker-compose --profile setup run --rm setup

# Avvia solo servizio
docker-compose --profile app up -d
```

### Comandi Utili

```bash
# Avvia servizio
docker-compose up -d

# Ferma servizio
docker-compose down

# Riavvia
docker-compose restart

# Mostra log
docker-compose logs -f

# Verifica stato
docker-compose ps

# Aggiorna
docker-compose pull
docker-compose up -d
```

---

## 🛠️ Troubleshooting

### Errore: "OPENROUTER_API_KEY non configurata"

```bash
# Verifica .env
cat .env | grep OPENROUTER_API_KEY

# Deve mostrare: OPENROUTER_API_KEY=sk-or-v1-...
```

### Errore: "429 Rate Limited"

Il sistema usa automaticamente il backup model. Per risolvere:

1. Attendi 1-2 minuti
2. O cambia modello principale in `.env`
3. Riavvia: `docker-compose restart`

### Errore: Container non avvia

```bash
# Pulisci tutto
docker-compose down -v
docker system prune -f

# Ricostruisci
docker-compose build --no-cache
docker-compose up -d
```

### Verifica Stato API

```bash
# Test connessione
curl http://localhost:8085/api/test

# Status completo
curl http://localhost:8085/api/status
```

---

## 📊 Monitoraggio

```bash
# Log in tempo reale
docker-compose logs -f

# Statistiche container
docker stats

# Uso risorse
docker-compose top
```

---

## 🔄 Aggiornamento

```bash
# 1. Salva configurazione
cp .env .env.backup

# 2. Pull nuovi cambiamenti
git pull

# 3. Confronta nuove variabili
diff .env.example .env

# 4. Aggiorna .env se necessario
nano .env

# 5. Ricostruisci e riavvia
docker-compose build
docker-compose up -d
```

---

## 🆘 Supporto

- **Issues**: [GitHub Issues](https://github.com/tu-username/codex20-openrouter/issues)
- **API Key**: [OpenRouter Dashboard](https://openrouter.ai/keys)
- **Documentazione**: [OpenRouter Docs](https://openrouter.ai/docs)

---

**Pronto per giocare! 🎲**
