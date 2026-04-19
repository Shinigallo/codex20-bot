#!/bin/bash
# Codex20 Container Health Monitor
# Real-time monitoring and management for containerized bot

set -e

CONTAINER_NAME="codex20-python"
LOG_FILE="/tmp/codex20-health.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_with_timestamp() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

show_status() {
    clear
    echo "🐳 CODEX20 CONTAINER HEALTH DASHBOARD"
    echo "====================================="
    echo
    
    # Container status
    if docker ps --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        echo -e "${GREEN}🟢 STATUS: RUNNING${NC}"
        
        # Uptime
        uptime=$(docker inspect --format='{{.State.StartedAt}}' $CONTAINER_NAME)
        echo "⏰ Started: $uptime"
        
        # Health check
        health=$(docker inspect --format='{{.State.Health.Status}}' $CONTAINER_NAME 2>/dev/null || echo "no-healthcheck")
        if [[ "$health" == "healthy" ]]; then
            echo -e "${GREEN}❤️  Health: HEALTHY${NC}"
        elif [[ "$health" == "unhealthy" ]]; then
            echo -e "${RED}💔 Health: UNHEALTHY${NC}"
        else
            echo -e "${YELLOW}❓ Health: $health${NC}"
        fi
        
        # Resource usage
        echo
        echo "📊 RESOURCE USAGE:"
        docker stats --no-stream --format "table {{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" $CONTAINER_NAME
        
    else
        echo -e "${RED}🔴 STATUS: STOPPED${NC}"
        echo "❌ Container is not running"
    fi
    
    echo
    echo "📋 RECENT LOGS (last 5 lines):"
    echo "================================"
    docker logs --tail 5 $CONTAINER_NAME 2>/dev/null || echo "No logs available"
    
    echo
    echo "🔧 COMMANDS:"
    echo "  r) Restart container"
    echo "  l) View full logs" 
    echo "  s) Shell into container"
    echo "  h) Show this status"
    echo "  q) Quit monitor"
    echo
}

restart_container() {
    log_with_timestamp "Restarting container..."
    docker-compose restart
    log_with_timestamp "Container restarted"
    sleep 3
}

view_logs() {
    echo "📋 FULL CONTAINER LOGS:"
    echo "======================="
    docker logs $CONTAINER_NAME
    echo
    read -p "Press Enter to return to dashboard..."
}

shell_into_container() {
    echo "🐚 Entering container shell..."
    docker exec -it $CONTAINER_NAME /bin/bash || docker exec -it $CONTAINER_NAME /bin/sh
}

# Interactive monitoring loop
monitor() {
    while true; do
        show_status
        
        read -t 10 -n 1 -s input || input=""
        
        case $input in
            r|R)
                restart_container
                ;;
            l|L)
                view_logs
                ;;
            s|S)
                shell_into_container
                ;;
            h|H)
                continue
                ;;
            q|Q)
                echo "👋 Exiting monitor..."
                exit 0
                ;;
            *)
                # Auto-refresh every 10 seconds if no input
                ;;
        esac
    done
}

# Check if container exists
if ! docker ps -a --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
    echo "❌ Container '$CONTAINER_NAME' not found"
    echo "Run deployment script first: ./deploy.sh"
    exit 1
fi

# Start monitoring
log_with_timestamp "Starting health monitor for $CONTAINER_NAME"
monitor