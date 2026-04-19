#!/bin/bash
# Codex20 v2.2 Container Deployment Script
# Enhanced D&D Bot with Owner Privileges and API Proxy

set -e

echo "🐳 CODEX20 V2.2 - CONTAINER DEPLOYMENT SCRIPT"
echo "============================================="

# Configuration
CONTAINER_NAME="codex20-python"
IMAGE_NAME="codex20-bot-work-python-bot"
BACKUP_DIR="/tmp/codex20-backup-$(date +%Y%m%d-%H%M%S)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_warning "Running as root. This is fine for Docker operations."
    fi
}

# Function to check Docker availability
check_docker() {
    log_info "Checking Docker availability..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running or not accessible"
        exit 1
    fi
    
    log_success "Docker is available and running"
}

# Function to backup existing container
backup_container() {
    log_info "Checking for existing container..."
    
    if docker ps -a --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        log_warning "Found existing container: ${CONTAINER_NAME}"
        
        # Create backup directory
        mkdir -p "${BACKUP_DIR}"
        
        # Backup data directory if it exists
        if docker exec ${CONTAINER_NAME} test -d /app/data 2>/dev/null; then
            log_info "Backing up container data..."
            docker cp ${CONTAINER_NAME}:/app/data "${BACKUP_DIR}/"
            log_success "Data backed up to: ${BACKUP_DIR}/data"
        fi
        
        # Stop and remove container
        log_info "Stopping existing container..."
        docker stop ${CONTAINER_NAME} || true
        docker rm ${CONTAINER_NAME} || true
        log_success "Existing container removed"
    else
        log_info "No existing container found"
    fi
}

# Function to build new image
build_image() {
    log_info "Building new container image..."
    
    if [[ ! -f "Dockerfile" ]]; then
        log_error "Dockerfile not found in current directory"
        exit 1
    fi
    
    if [[ ! -f ".env" ]]; then
        log_error ".env file not found. Please create it with required API keys."
        exit 1
    fi
    
    # Build with proper tagging
    docker build -t ${IMAGE_NAME}:latest -t ${IMAGE_NAME}:v2.2 .
    
    log_success "Container image built successfully"
}

# Function to create necessary directories
prepare_directories() {
    log_info "Preparing directories..."
    
    # Create data and logs directories if they don't exist
    mkdir -p ./data ./logs
    chmod 755 ./data ./logs
    
    # Restore backup data if available
    if [[ -d "${BACKUP_DIR}/data" ]]; then
        log_info "Restoring backed up data..."
        cp -r "${BACKUP_DIR}/data/"* ./data/ 2>/dev/null || true
        log_success "Data restored from backup"
    fi
    
    log_success "Directories prepared"
}

# Function to start container using docker-compose
start_container() {
    log_info "Starting container with docker-compose..."
    
    if [[ ! -f "docker-compose.yml" ]]; then
        log_error "docker-compose.yml not found"
        exit 1
    fi
    
    # Start the container
    docker-compose up -d
    
    log_success "Container started"
}

# Function to verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    # Wait for container to be ready
    sleep 5
    
    # Check if container is running
    if docker ps --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        log_success "Container is running"
        
        # Check health status
        health_status=$(docker inspect --format='{{.State.Health.Status}}' ${CONTAINER_NAME} 2>/dev/null || echo "no-healthcheck")
        log_info "Health status: ${health_status}"
        
        # Show container logs (last 10 lines)
        log_info "Recent container logs:"
        docker logs --tail 10 ${CONTAINER_NAME}
        
        log_success "Deployment verified successfully"
    else
        log_error "Container is not running"
        log_info "Container logs:"
        docker logs ${CONTAINER_NAME} 2>/dev/null || echo "No logs available"
        exit 1
    fi
}

# Function to show deployment info
show_info() {
    log_success "🎲 CODEX20 V2.2 DEPLOYMENT COMPLETED!"
    echo
    echo "📊 CONTAINER INFO:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" --filter "name=${CONTAINER_NAME}"
    echo
    echo "🔧 USEFUL COMMANDS:"
    echo "  • View logs:     docker logs -f ${CONTAINER_NAME}"
    echo "  • Enter container: docker exec -it ${CONTAINER_NAME} /bin/bash"
    echo "  • Stop container:  docker-compose down"
    echo "  • Restart:         docker-compose restart"
    echo "  • Update:          docker-compose pull && docker-compose up -d"
    echo
    echo "📂 DATA PERSISTENCE:"
    echo "  • Data directory:  $(pwd)/data"
    echo "  • Logs directory:  $(pwd)/logs"
    echo "  • Backup location: ${BACKUP_DIR}"
    echo
    echo "🎯 OWNER ACCESS: User 323785285 (Dario) has permanent admin access"
    echo "🔄 API PROXY: Intelligent rotation with automatic failover enabled"
    echo "🛡️ SECURITY: User registration system with personal API keys active"
}

# Main deployment flow
main() {
    echo
    log_info "Starting Codex20 v2.2 container deployment..."
    
    check_root
    check_docker
    backup_container
    prepare_directories
    build_image
    start_container
    verify_deployment
    show_info
    
    log_success "🚀 Deployment completed successfully!"
}

# Run main function
main "$@"