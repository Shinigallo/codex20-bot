# 🎲 Codex20 v2.2 - Enhanced D&D Assistant Bot

**Advanced Telegram bot for Dungeon Masters and D&D 5e players with AI-powered assistance, persistent sessions, and semantic D&D knowledge integration.**

## 🐳 **CONTAINER-FIRST ARCHITECTURE**

### **✅ Always Containerized Deployment**
- **Docker-based** - No bare metal installations
- **docker-compose orchestration** - Professional container management
- **Health monitoring** - Built-in container health checks
- **Persistent volumes** - Data survives container updates
- **Resource limits** - Controlled CPU/memory usage

---

## 🚀 **Quick Start (Container Deployment)**

### **1. Prerequisites**
```bash
# Ensure Docker and docker-compose are installed
docker --version
docker-compose --version
```

### **2. Environment Setup**
```bash
# Create .env file with your credentials
cp .env.example .env
# Edit .env with your API keys:
# TELEGRAM_TOKEN=your_bot_token_here
# GEMINI_API_KEYS=key1,key2,key3  # Multiple keys for rotation
```

### **3. Deploy Container**
```bash
# One-command deployment
./deploy.sh

# Or manual deployment
docker-compose up -d
```

### **4. Monitor Container**
```bash
# Interactive health dashboard
./monitor.sh

# View logs
docker logs -f codex20-python
```

---

## 👑 **OWNER PRIVILEGES & SECURITY**

### **🔐 Owner Access (Dario)**
- **User ID:** `323785285` - **PERMANENT ACCESS**
- **System API Keys** - Uses proxy rotation (no personal limits)
- **Admin Commands** - Full bot management capabilities
- **Zero Rate Limits** - Intelligent API key rotation

### **🛡️ Multi-User Security System**
- **New Users** → Must register with personal Gemini API key
- **Registration Flow** → `/register AIzaSyC...your-key-here`
- **API Validation** → Live testing of provided keys
- **Cost Distribution** → Each user provides own API quota

---

## 🎯 **ENHANCED FEATURES V2.2**

### **🧠 Persistent Session Memory**
- **SQLite Database** - Conversation persistence across restarts
- **20 Messages per User** - Contextual memory retention
- **72-Hour TTL** - Automatic cleanup of old sessions
- **Campaign Tracking** - Long-term campaign information storage

### **🔄 Intelligent API Proxy System**
- **Multi-Key Rotation** - Automatic failover on rate limits
- **Health Monitoring** - Real-time API key status tracking
- **Load Balancing** - Optimal distribution across available keys
- **Emergency Protocols** - Graceful handling of system-wide limits

### **📚 Semantic D&D Knowledge**
- **5etools Integration** - Official D&D 5e rule grounding
- **Semantic Search** - `/search_rules <query>` for rule lookups
- **Campaign Memory** - `/remember_campaign` and `/recall_campaign`
- **MemPalace Ready** - Future integration with semantic knowledge base

---

## 🎲 **COMMAND REFERENCE**

### **🎯 Core D&D Commands**
```
/adventure <prompt>     - Generate detailed D&D adventures
/adventure_quick        - Quick adventure summaries
/search_rules <query>   - Semantic D&D 5e rule lookup
/remember_campaign      - Store campaign information
/recall_campaign        - Retrieve campaign memories
```

### **👑 Owner/Admin Commands**
```
/admin_users           - List authorized users
/admin_add_user <id>   - Add user to allowlist
/proxy_status          - API proxy system health
```

### **🔐 User Management**
```
/start                 - Bot introduction and access check
/register <api-key>    - Register with personal Gemini key
/help                  - Complete command guide
```

---

## 🐳 **CONTAINER ARCHITECTURE**

### **📁 Directory Structure**
```
codex20-bot/
├── Dockerfile              # Container definition
├── docker-compose.yml      # Orchestration config  
├── deploy.sh              # Automated deployment
├── monitor.sh             # Health monitoring
├── bot.py                 # Main application
├── persistent_sessions.py # Session management
├── requirements.txt       # Python dependencies
├── .env                  # Environment variables
└── data/                 # Persistent data volume
    ├── sessions.db       # Session database
    └── 5etools/         # D&D rule data
```

### **🔧 Container Features**
- **Base Image:** `python:3.12-slim`
- **Health Checks:** SQLite database connectivity
- **Volume Mounts:** Persistent data and logs
- **Resource Limits:** CPU/Memory constraints
- **Automatic Restart:** `unless-stopped` policy
- **Logging:** JSON file driver with rotation

---

## 📊 **MONITORING & MANAGEMENT**

### **🔍 Health Dashboard**
```bash
./monitor.sh  # Interactive monitoring interface
```

### **📋 Container Operations**
```bash
# View status
docker-compose ps

# View logs
docker logs -f codex20-python

# Restart container
docker-compose restart

# Update deployment
docker-compose pull && docker-compose up -d

# Shell access
docker exec -it codex20-python /bin/bash
```

### **💾 Data Management**
```bash
# Backup data
docker cp codex20-python:/app/data ./backup-$(date +%Y%m%d)

# Restore data  
docker cp ./backup-data codex20-python:/app/data

# Database access
docker exec -it codex20-python sqlite3 /app/data/sessions.db
```

---

## ⚡ **DEPLOYMENT BENEFITS**

### **🛡️ Security Advantages**
- **Isolated Environment** - Container sandboxing
- **No System Dependencies** - Self-contained deployment
- **Controlled Access** - Only exposed ports and volumes
- **Easy Updates** - Replace container without system changes

### **🚀 Operational Benefits**
- **Consistent Deployment** - Same environment across hosts
- **Easy Scaling** - Container replication and load balancing
- **Health Monitoring** - Built-in health checks and monitoring
- **Resource Control** - CPU and memory limitations
- **Backup/Restore** - Simple data volume management

### **💰 Cost Efficiency**
- **Multi-User Architecture** - Each user provides own API keys
- **Intelligent Proxy** - Maximizes free tier usage
- **Owner Privileges** - System keys for unlimited owner access
- **Resource Optimization** - Minimal container resource usage

---

## 🎯 **PRODUCTION DEPLOYMENT**

### **🔧 PiNas Installation**
```bash
# SSH into PiNas
ssh dario@192.168.8.11

# Navigate to bot directory  
cd /root/codex20-bot-work/

# Deploy enhanced version
./deploy.sh

# Monitor deployment
./monitor.sh
```

### **📈 Scaling Considerations**
- **Multiple API Keys** - Add more keys to proxy pool for higher limits
- **Container Resources** - Adjust CPU/memory limits based on usage
- **Database Optimization** - Monitor SQLite performance and size
- **Log Management** - Configure log rotation and retention policies

---

## 🎲 **INTEGRATION FEATURES**

### **🧠 MemPalace Integration (Future)**
- **Semantic Memory** - Enhanced D&D knowledge retrieval
- **Campaign Knowledge Base** - Long-term campaign information storage
- **Rule Grounding** - Accurate D&D 5e rule references
- **Performance Target** - <200ms semantic queries

### **📚 5etools Data**
- **Official Rules** - Complete D&D 5e rule integration
- **JSON Parsing** - Structured data extraction from official sources
- **Semantic Search** - Keyword-based rule lookup
- **Context Grounding** - AI responses backed by official data

---

## 🛠️ **TROUBLESHOOTING**

### **🔍 Common Issues**
```bash
# Container won't start
docker logs codex20-python

# API key issues
docker exec -it codex20-python python -c "from bot import get_model; print(get_model())"

# Database problems
docker exec -it codex20-python sqlite3 /app/data/sessions.db ".tables"

# Permission issues
sudo chown -R $(id -u):$(id -g) ./data ./logs
```

### **🚑 Recovery Procedures**
```bash
# Full container rebuild
docker-compose down
docker rmi codex20-bot-work-python-bot
./deploy.sh

# Database reset
docker exec -it codex20-python rm /app/data/sessions.db
docker-compose restart
```

---

**🎲 Ready to enhance your D&D campaigns with AI-powered assistance!**

**Container-first architecture ensures reliable, scalable, and maintainable deployment across any Docker-capable host.**