#!/bin/bash
set -euo pipefail

# Aegis-Trader AWS Deployment Setup
# Targets: Ubuntu 24.04 on AWS Singapore (t3.small or similar, 2GB RAM)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="aegis-trader"
APP_DIR="/opt/${PROJECT_NAME}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

error() {
    log "ERROR: $*" >&2
    exit 1
}

# ---------------------------------------------------------------------------
# 1. System Update & Base Dependencies
# ---------------------------------------------------------------------------
log "Updating system packages..."
apt-get update
apt-get upgrade -y
apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg \
    lsb-release \
    git \
    unzip \
    htop \
    jq \
    ufw \
    fail2ban

# ---------------------------------------------------------------------------
# 2. Install Docker
# ---------------------------------------------------------------------------
log "Installing Docker..."
if ! command -v docker &> /dev/null; then
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
        > /etc/apt/sources.list.d/docker.list
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    usermod -aG docker ubuntu || true
    log "Docker installed successfully"
else
    log "Docker already installed, skipping"
fi

# ---------------------------------------------------------------------------
# 3. Install Docker Compose (standalone for compatibility)
# ---------------------------------------------------------------------------
log "Installing docker-compose..."
if ! command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_VERSION="v2.27.0"
    curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    log "docker-compose installed"
else
    log "docker-compose already installed, skipping"
fi

# ---------------------------------------------------------------------------
# 4. Configure Firewall
# ---------------------------------------------------------------------------
log "Configuring UFW..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 3000/tcp
ufw allow 8001/tcp
ufw --force enable
log "UFW configured"

# ---------------------------------------------------------------------------
# 5. Configure fail2ban
# ---------------------------------------------------------------------------
log "Configuring fail2ban..."
systemctl enable fail2ban
systemctl start fail2ban

# ---------------------------------------------------------------------------
# 6. Create Application Directory
# ---------------------------------------------------------------------------
log "Creating application directory..."
mkdir -p "${APP_DIR}"
mkdir -p "${APP_DIR}/data" "${APP_DIR}/cache" "${APP_DIR}/logs"
chown -R ubuntu:ubuntu "${APP_DIR}"

# ---------------------------------------------------------------------------
# 7. Configure System Limits for 2GB RAM
# ---------------------------------------------------------------------------
log "Configuring system limits..."
cat >> /etc/sysctl.conf << 'EOF'
# Aegis-Trader memory optimizations
vm.swappiness=10
vm.vfs_cache_pressure=50
EOF
sysctl -p

# ---------------------------------------------------------------------------
# 8. Setup Log Rotation
# ---------------------------------------------------------------------------
log "Configuring log rotation..."
cat > /etc/logrotate.d/aegis-trader << 'EOF'
/opt/aegis-trader/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 ubuntu ubuntu
}
EOF

# ---------------------------------------------------------------------------
# 9. Create systemd service for auto-start
# ---------------------------------------------------------------------------
log "Creating systemd service..."
cat > /etc/systemd/system/aegis-trader.service << EOF
[Unit]
Description=Aegis-Trader Multi-Agent Trading System
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${APP_DIR}
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
ExecReload=/usr/bin/docker compose up -d --build
TimeoutStartSec=300
User=ubuntu
Group=docker

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable aegis-trader

# ---------------------------------------------------------------------------
# 10. Setup SSH Hardening (optional but recommended)
# ---------------------------------------------------------------------------
log "Applying SSH hardening..."
sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart sshd

log "=========================================="
log "AWS Setup Complete!"
log "=========================================="
log "Next steps:"
log "  1. Clone repo: git clone <repo> ${APP_DIR}"
log "  2. Create .env file: cp ${APP_DIR}/.env.example ${APP_DIR}/.env"
log "  3. Edit .env with production API keys"
log "  4. Run deploy: ${APP_DIR}/deploy/deploy.sh"
log ""
log "Reboot recommended to apply all changes."
