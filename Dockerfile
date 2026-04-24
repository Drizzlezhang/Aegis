# Aegis-Trader Dockerfile
# Multi-stage build for production
# Compatible with Python 3.12+ (uses 3.13 slim as stable base)

# Stage 1: Builder
FROM python:3.13-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first (leverage Docker cache)
COPY pyproject.toml ./
COPY CLAUDE.md ./

# Copy source so 'pip install -e .' can find packages
COPY src/ ./src/
COPY skills/ ./skills/

# Install project in editable mode with optional dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e ".[llm,data]"

# Stage 2: Runtime
FROM python:3.13-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 aegis && \
    chown -R aegis:aegis /app

# Copy installed Python packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code (only necessary directories)
COPY --chown=aegis:aegis src/ ./src/
COPY --chown=aegis:aegis skills/ ./skills/
COPY --chown=aegis:aegis pyproject.toml ./
COPY --chown=aegis:aegis CLAUDE.md ./

# Create runtime directories
RUN mkdir -p /app/data /app/cache /app/logs && \
    chown -R aegis:aegis /app/data /app/cache /app/logs

# Switch to non-root user
USER aegis

# Health check using CLI health command (no HTTP API yet)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -m src.cli health || exit 1

# Expose ports (reserved for future API / Web)
EXPOSE 8000
EXPOSE 3000

# Default command
CMD ["python", "-m", "src.cli", "status"]
