#!/bin/bash
set -euo pipefail

# Aegis-Trader Deployment Script
# Usage: ./deploy/deploy.sh [environment]
#   environment: production (default) | staging

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${1:-production}"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

error() {
    log "ERROR: $*" >&2
    exit 1
}

cd "$PROJECT_ROOT"

log "=========================================="
log "Deploying Aegis-Trader"
log "Environment: $ENVIRONMENT"
log "=========================================="

# ---------------------------------------------------------------------------
# 1. Validate Prerequisites
# ---------------------------------------------------------------------------
log "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    error "Docker not installed. Run deploy/setup-aws.sh first."
fi

if [ ! -f ".env" ]; then
    error ".env file not found. Copy .env.example and configure it."
fi

# Check required env vars
required_vars=("AEGIS_ENVIRONMENT" "AEGIS_LOG_LEVEL")
for var in "${required_vars[@]}"; do
    if ! grep -q "^${var}=" .env 2>/dev/null; then
        log "WARNING: $var not found in .env"
    fi
done

# ---------------------------------------------------------------------------
# 2. Pull Latest Code (if git repo)
# ---------------------------------------------------------------------------
if [ -d ".git" ]; then
    log "Pulling latest code..."
    git fetch origin
    git reset --hard origin/master || git reset --hard origin/main
    log "Code updated"
fi

# ---------------------------------------------------------------------------
# 3. Build and Deploy
# ---------------------------------------------------------------------------
log "Building Docker image..."
export DOCKER_BUILDKIT=1
docker compose -f "$COMPOSE_FILE" build --no-cache

log "Stopping existing containers..."
docker compose -f "$COMPOSE_FILE" down --remove-orphans

log "Starting containers..."
docker compose -f "$COMPOSE_FILE" up -d

# ---------------------------------------------------------------------------
# 4. Health Check
# ---------------------------------------------------------------------------
log "Waiting for services to start..."
sleep 10

HEALTH_RETRIES=12
HEALTH_INTERVAL=5

for i in $(seq 1 $HEALTH_RETRIES); do
    log "Health check attempt $i/$HEALTH_RETRIES..."

    BACKEND_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/api/health 2>/dev/null || echo "000")

    if [ "$BACKEND_HEALTH" = "200" ]; then
        log "Backend health check passed"
        break
    fi

    if [ "$i" -eq "$HEALTH_RETRIES" ]; then
        error "Backend health check failed after $HEALTH_RETRIES attempts"
    fi

    sleep $HEALTH_INTERVAL
done

# Check frontend
FRONTEND_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null || echo "000")
if [ "$FRONTEND_HEALTH" = "200" ] || [ "$FRONTEND_HEALTH" = "307" ]; then
    log "Frontend health check passed"
else
    log "WARNING: Frontend returned HTTP $FRONTEND_HEALTH"
fi

# ---------------------------------------------------------------------------
# 5. Cleanup
# ---------------------------------------------------------------------------
log "Cleaning up old images..."
docker image prune -f

log "=========================================="
log "Deployment Complete!"
log "=========================================="
log "Frontend: http://$(curl -s ifconfig.me 2>/dev/null || echo 'localhost'):3000"
log "Backend API: http://$(curl -s ifconfig.me 2>/dev/null || echo 'localhost'):8001/api"
log ""
log "Logs: docker compose logs -f"
log "Status: docker compose ps"
