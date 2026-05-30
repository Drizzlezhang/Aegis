#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# Aegis-Trader Local Smoke Test — Startup
# ============================================================================
# Starts backend API server and verifies health endpoint.
# Prerequisites: Python 3.12+, pip install -e ".[dev]"
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

PID_FILE="/tmp/aegis-smoke-api.pid"
LOG_FILE="/tmp/aegis-smoke-api.log"
API_PORT="${AEGIS_API_PORT:-8000}"
API_HOST="${AEGIS_API_HOST:-127.0.0.1}"
MAX_WAIT="${AEGIS_SMOKE_MAX_WAIT:-30}"

echo "=== Aegis-Trader Local Smoke Test ==="
echo "Project:  $PROJECT_DIR"
echo "API:      http://${API_HOST}:${API_PORT}"
echo "Log:      $LOG_FILE"
echo ""

# ── Step 1: Check prerequisites ──────────────────────────────────────────
echo "[1/6] Checking prerequisites..."

if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install Python 3.12+."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "  Python: $PYTHON_VERSION"

if ! python3 -c 'import fastapi' 2>/dev/null; then
    echo "ERROR: fastapi not installed. Run: pip install -e \".[dev]\""
    exit 1
fi
echo "  FastAPI: OK"

# ── Step 2: Create runtime directories ────────────────────────────────────
echo "[2/6] Creating runtime directories..."
mkdir -p ~/.aegis-trader/data
mkdir -p ~/.aegis-trader/cache
mkdir -p ~/.aegis-trader/logs
echo "  Directories: OK"

# ── Step 3: Run database migrations ───────────────────────────────────────
echo "[3/6] Running database migrations..."
if python3 -m alembic upgrade heads 2>&1; then
    echo "  Migrations: OK"
else
    echo "  WARNING: alembic migration failed (may be first run, continuing...)"
fi

# ── Step 4: Kill any existing instance ────────────────────────────────────
echo "[4/6] Checking for existing instances..."
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "  Killing existing instance (PID=$OLD_PID)..."
        kill "$OLD_PID" 2>/dev/null || true
        sleep 1
    fi
    rm -f "$PID_FILE"
fi
# Also kill anything on our port
if lsof -ti:"$API_PORT" &>/dev/null; then
    echo "  Killing process on port $API_PORT..."
    lsof -ti:"$API_PORT" | xargs kill 2>/dev/null || true
    sleep 1
fi
echo "  Port $API_PORT: free"

# ── Step 5: Start API server ──────────────────────────────────────────────
echo "[5/6] Starting API server..."
AEGIS_ENVIRONMENT=development \
AEGIS_LOG_LEVEL=DEBUG \
AEGIS_DEBUG=true \
AEGIS_SCHEDULER__ENABLED=false \
AEGIS_SCHEDULER__PERSISTENT_JOBSTORE=false \
python3 -m uvicorn src.api.main:app \
    --host "$API_HOST" \
    --port "$API_PORT" \
    --log-level info \
    > "$LOG_FILE" 2>&1 &

API_PID=$!
echo "$API_PID" > "$PID_FILE"
echo "  PID: $API_PID"

# ── Step 6: Wait for health check ─────────────────────────────────────────
echo "[6/6] Waiting for health check (max ${MAX_WAIT}s)..."
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -sf "http://${API_HOST}:${API_PORT}/api/health" > /dev/null 2>&1; then
        echo ""
        echo "=== Smoke Test PASSED ==="
        echo "API is healthy at http://${API_HOST}:${API_PORT}/api/health"
        echo "PID: $API_PID"
        echo "Log: $LOG_FILE"
        echo ""
        echo "To stop: bash scripts/local-smoke-down.sh"
        exit 0
    fi
    sleep 1
    WAITED=$((WAITED + 1))
    if [ $((WAITED % 5)) -eq 0 ]; then
        echo "  Still waiting... (${WAITED}s)"
    fi
done

echo ""
echo "=== Smoke Test FAILED ==="
echo "API did not become healthy within ${MAX_WAIT}s."
echo "Check logs: tail -50 $LOG_FILE"
echo ""
echo "Last 20 log lines:"
tail -20 "$LOG_FILE" 2>/dev/null || echo "(no log output)"
exit 1
