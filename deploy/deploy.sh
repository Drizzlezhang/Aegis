#!/usr/bin/env bash
set -euo pipefail

# Aegis-Trader AWS Deployment Script
# Target: Ubuntu 24.04 on AWS Singapore (t3.small / 2GB RAM)
# Usage: ./deploy/deploy.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
APP_NAME="aegis-trader"
DEPLOY_DIR="/opt/$APP_NAME"
BACKUP_DIR="/opt/$APP_NAME-backups"
REPO_URL="https://github.com/Drizzlezhang/Aegis-Trader.git"
BRANCH="master"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# Check if running on Ubuntu
if [[ ! -f /etc/os-release ]] || ! grep -q 'Ubuntu' /etc/os-release; then
    log_warn "This script is designed for Ubuntu 24.04. Continuing anyway..."
fi

# Install Docker if not present
install_docker() {
    if command -v docker &> /dev/null; then
        log_info "Docker already installed: $(docker --version)"
        return 0
    fi

    log_info "Installing Docker..."
    apt-get update
    apt-get install -y ca-certificates curl gnupg lsb-release

    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Enable and start Docker
    systemctl enable docker
    systemctl start docker

    log_info "Docker installed successfully"
}

# Install docker-compose (plugin or standalone)
install_docker_compose() {
    if docker compose version &> /dev/null; then
        log_info "Docker Compose plugin already available"
        return 0
    fi

    log_info "Installing Docker Compose..."
    apt-get install -y docker-compose-plugin || {
        # Fallback to standalone binary
        COMPOSE_VERSION="v2.27.0"
        curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" \
            -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
        ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    }
    log_info "Docker Compose installed"
}

# Create deployment directories
setup_directories() {
    log_info "Setting up directories..."
    mkdir -p "$DEPLOY_DIR" "$BACKUP_DIR" "$DEPLOY_DIR/data" "$DEPLOY_DIR/cache" "$DEPLOY_DIR/logs"

    # Ensure .env exists (user must provide it)
    if [[ ! -f "$DEPLOY_DIR/.env" ]]; then
        log_warn ".env file not found at $DEPLOY_DIR/.env"
        log_warn "Please copy .env.example and configure before deploying:"
        log_warn "  cp $DEPLOY_DIR/.env.example $DEPLOY_DIR/.env"
        log_warn "  vim $DEPLOY_DIR/.env"
    fi
}

# Backup current deployment
backup_current() {
    if [[ -d "$DEPLOY_DIR/src" ]] || [[ -d "$DEPLOY_DIR/skills" ]]; then
        local backup_name="backup-$(date +%Y%m%d-%H%M%S)"
        log_info "Creating backup: $backup_name"
        mkdir -p "$BACKUP_DIR/$backup_name"
        cp -r "$DEPLOY_DIR" "$BACKUP_DIR/$backup_name/" 2>/dev/null || true
        log_info "Backup saved to $BACKUP_DIR/$backup_name"
    fi
}

# Pull latest code
pull_code() {
    log_info "Pulling latest code from $BRANCH..."
    if [[ -d "$DEPLOY_DIR/.git" ]]; then
        cd "$DEPLOY_DIR"
        git fetch origin
        git reset --hard "origin/$BRANCH"
    else
        git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$DEPLOY_DIR"
    fi
}

# Build and start services
deploy_services() {
    cd "$DEPLOY_DIR"

    log_info "Building Docker image..."
    docker compose build --no-cache

    log_info "Starting services..."
    docker compose up -d

    log_info "Waiting for health check..."
    sleep 10

    if docker compose ps | grep -q "healthy"; then
        log_info "Deployment successful! Services are healthy."
    else
        log_warn "Health check may still be pending. Check logs with: docker compose logs -f"
    fi
}

# Simple rollback to last backup
rollback() {
    local latest_backup
    latest_backup=$(ls -td "$BACKUP_DIR"/* 2>/dev/null | head -n 1 || true)

    if [[ -z "$latest_backup" ]]; then
        log_error "No backups found for rollback"
        exit 1
    fi

    log_warn "Rolling back to: $latest_backup"
    cd "$DEPLOY_DIR"
    docker compose down || true

    # Restore from backup
    rsync -a --delete "$latest_backup/$(basename "$DEPLOY_DIR")/" "$DEPLOY_DIR/" 2>/dev/null || \
        cp -r "$latest_backup/$(basename "$DEPLOY_DIR")"/* "$DEPLOY_DIR/" 2>/dev/null || true

    docker compose up -d
    log_info "Rollback completed"
}

# Show status
status() {
    cd "$DEPLOY_DIR" 2>/dev/null || { log_error "Not deployed yet"; exit 1; }
    docker compose ps
    docker compose logs --tail=50
}

# Main
case "${1:-deploy}" in
    install)
        install_docker
        install_docker_compose
        setup_directories
        ;;
    deploy)
        install_docker
        install_docker_compose
        setup_directories
        backup_current
        pull_code
        deploy_services
        log_info "Deployment complete!"
        log_info "Logs: docker compose -f $DEPLOY_DIR/docker-compose.yml logs -f"
        ;;
    rollback)
        rollback
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $0 {install|deploy|rollback|status}"
        echo ""
        echo "Commands:"
        echo "  install   - Install Docker and dependencies"
        echo "  deploy    - Full deploy (backup, pull, build, start)"
        echo "  rollback  - Rollback to last backup"
        echo "  status    - Show service status and recent logs"
        exit 1
        ;;
esac
