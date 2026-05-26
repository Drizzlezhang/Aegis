# Aegis-Trader Dockerfile
# Multi-stage build for production
# Targets AWS Singapore (Ubuntu-like, 2GB RAM)

# ---------------------------------------------------------------------------
# Stage 1: Frontend builder
# ---------------------------------------------------------------------------
FROM node:25-slim AS frontend-builder

WORKDIR /app/web

COPY web/package*.json ./
RUN npm ci

COPY web/ ./
ENV API_BASE_URL=http://localhost:8001
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: Python builder
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS python-builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml CLAUDE.md ./
COPY src/ ./src/
COPY skills/ ./skills/

# Install only core runtime dependencies for production.
# Heavy semantic-search/LLM extras are intentionally excluded to keep
# the production image deployable on small AWS instances.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e "."

# ---------------------------------------------------------------------------
# Stage 3: Runtime
# ---------------------------------------------------------------------------
FROM python:3.13-slim

WORKDIR /app

# Install runtime deps: curl (healthcheck), Node.js (frontend), supervisor
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gnupg supervisor \
    && curl -fsSL https://deb.nodesource.com/setup_25.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 aegis \
    && chown -R aegis:aegis /app

# Copy Python packages from builder
COPY --from=python-builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=python-builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=aegis:aegis src/ ./src/
COPY --chown=aegis:aegis skills/ ./skills/
COPY --chown=aegis:aegis pyproject.toml CLAUDE.md ./

# Copy built frontend
COPY --from=frontend-builder --chown=aegis:aegis /app/web/package*.json ./web/
COPY --from=frontend-builder --chown=aegis:aegis /app/web/.next ./web/.next
COPY --chown=aegis:aegis web/next.config.js ./web/
COPY --chown=aegis:aegis web/tailwind.config.js ./web/
COPY --chown=aegis:aegis web/tsconfig.json ./web/
COPY --chown=aegis:aegis web/postcss.config.js ./web/

# Install production frontend deps (for next start)
RUN cd /app/web && npm ci --omit=dev

# Runtime dirs
RUN mkdir -p /app/data /app/cache /app/logs /app/web/logs \
    && chown -R aegis:aegis /app/data /app/cache /app/logs /app/web/logs

# Supervisor config
COPY --chown=root:root deploy/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Health check (FastAPI)
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://127.0.0.1:8001/api/health || exit 1

# Health check (Frontend)
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || exit 1

EXPOSE 3000 8001

USER root
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
