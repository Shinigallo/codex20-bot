#!/bin/bash
# Codex20 OpenRouter - Deploy Script
# Script di deploy rapido per produzione

set -e

# Colori
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         🚀 Codex20 Deploy Script             ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"
echo ""

# Verifica prerequisiti
echo -e "${YELLOW}Verifica prerequisiti...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker non installato${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose non installato${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisiti verificati${NC}"
echo ""

# Verifica .env
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}File .env non trovato. Copia .env.example...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}Modifica .env con le tue configurazioni${NC}"
    echo -e "${YELLOW}Edita: nano .env${NC}"
    read -p "Premi Enter quando hai finito di configurare..."
fi

# Verifica variabili richieste
if ! grep -q "^OPENROUTER_API_KEY=" .env || grep -q "^OPENROUTER_API_KEY=sk-or-v1-YOUR_API_KEY_HERE" .env; then
    echo -e "${RED}❌ OPENROUTER_API_KEY non configurata${NC}"
    echo -e "${YELLOW}Modifica .env con la tua API key${NC}"
    exit 1
fi

if ! grep -q "^ADMIN_PASSWORD_HASH=" .env || grep -q "^ADMIN_PASSWORD_HASH=" .env; then
    echo -e "${RED}❌ ADMIN_PASSWORD_HASH non configurato${NC}"
    echo -e "${YELLOW}Genera hash: python -c \"import hashlib; print(hashlib.sha256('password'.encode()).hexdigest())\"${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Configurazione verificata${NC}"
echo ""

# Build e avvio
echo -e "${BLUE}Avvio servizio Codex20...${NC}"
docker-compose down
docker-compose build
docker-compose up -d

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         ✅ Deploy Completato!                ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Interfaccia web:${NC} http://localhost:8085"
echo -e "${BLUE}Controlla log:${NC} docker-compose logs -f"
echo ""
echo -e "${YELLOW}Prossimi passi:${NC}"
echo -e "1. Accedi a http://localhost:8085"
echo -e "2. Login con utente admin configurato"
echo -e "3. Verifica connessione API con /api/test"
echo ""
