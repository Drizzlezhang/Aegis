#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# Aegis-Trader Local Smoke Test — Shutdown
# ============================================================================
# Gracefully stops the API server started by local-smoke-up.sh.
# ============================================================================

PID_FILE="/tmp/aegis-smoke-api.pid"
API_PORT="${AEGIS_API_PORT:-8000}"

echo "=== Aegis-Trader Smoke Test — Shutdown ==="

# ── Stop by PID file ──────────────────────────────────────────────────────
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping API server (PID=$PID)..."
        kill "$PID" 2>/dev/null || true

        # Wait for graceful shutdown
        for i in $(seq 1 10); do
            if ! kill -0 "$PID" 2>/dev/null; then
                echo "API server stopped gracefully."
                break
            fi
            sleep 1
        done

        # Force kill if still running
        if kill -0 "$PID" 2>/dev/null; then
            echo "Force killing API server..."
            kill -9 "$PID" 2>/dev/null || true
        fi
    else
        echo "PID $PID is not running (stale PID file)."
    fi
    rm -f "$PID_FILE"
else
    echo "No PID file found at $PID_FILE."
fi

# ── Clean up any remaining process on the port ────────────────────────────
if lsof -ti:"$API_PORT" &>/dev/null 2>&1; then
    echo "Cleaning up remaining process on port $API_PORT..."
    lsof -ti:"$API_PORT" | xargs kill 2>/dev/null || true
fi

# ── Clean up temp files ───────────────────────────────────────────────────
rm -f /tmp/aegis-smoke-api.log

echo "Shutdown complete."
