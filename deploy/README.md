# Aegis-Trader Deployment Guide

## Production Environment

- **Cloud**: AWS Singapore (ap-southeast-1)
- **OS**: Ubuntu 24.04 LTS
- **Instance**: t3.small (2 vCPU, 2GB RAM)
- **Container**: Docker + docker-compose
- **Process Management**: systemd + supervisord

## Quick Start

### 1. Provision Server

Launch an EC2 instance:
- AMI: Ubuntu 24.04 LTS
- Type: t3.small (minimum)
- Storage: 20GB gp3
- Security Group: Allow SSH (22), HTTP (80), HTTPS (443), 3000, 8001

### 2. Initial Setup

SSH into the server and run:

```bash
curl -fsSL https://raw.githubusercontent.com/Drizzlezhang/Aegis-Trader/master/deploy/setup-aws.sh | sudo bash
```

This installs:
- Docker + docker-compose
- UFW firewall
- fail2ban
- Log rotation
- systemd service

### 3. Deploy Application

```bash
sudo su - ubuntu
cd /opt/aegis-trader
git clone https://github.com/Drizzlezhang/Aegis-Trader.git .
cp .env.example .env
# Edit .env with production API keys
nano .env

# Deploy
./deploy/deploy.sh
```

### 4. Verify

```bash
# Check containers
docker compose ps

# Check logs
docker compose logs -f

# Health check
curl http://localhost:8001/api/health
```

## Environment Variables

Create `.env` from `.env.example`:

```bash
# Required
AEGIS_ENVIRONMENT=production
AEGIS_LOG_LEVEL=INFO

# Data Sources
YFINANCE_ENABLED=true
ALPHA_VANTAGE_API_KEY=your_key
ALPHA_VANTAGE_ENABLED=true

# LLM
LLM_PROVIDER=deepseek
LLM_API_KEY=your_key
LLM_REASONING_MODEL=deepseek-chat

# Memory
CHROMA_PERSIST_DIR=/app/data/chroma
```

## Operations

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f aegis-trader

# Host logs
sudo tail -f /opt/aegis-trader/logs/*.log
```

### Restart Services

```bash
sudo systemctl restart aegis-trader
# or
docker compose restart
```

### Update

```bash
cd /opt/aegis-trader
git pull origin master
./deploy/deploy.sh
```

### Backup

```bash
# Backup data directory
sudo tar czf aegis-backup-$(date +%Y%m%d).tar.gz /opt/aegis-trader/data /opt/aegis-trader/logs
```

## Troubleshooting

### Out of Memory

If the container is killed (exit code 137):

```bash
# Check memory usage
docker stats

# Reduce memory limit in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 1.2G
```

### Port Conflicts

```bash
# Check port usage
sudo lsof -i :3000
sudo lsof -i :8001

# Change ports in docker-compose.yml
```

### SSL/HTTPS

For production HTTPS, place an ALB or Nginx in front:

```bash
# Install certbot
sudo apt install certbot

# Or use AWS ACM + ALB (recommended)
```

## Architecture

```
┌─────────────────────────────────────┐
│           AWS EC2 (t3.small)         │
│  ┌───────────────────────────────┐  │
│  │     Docker Container          │  │
│  │  ┌─────────┐  ┌────────────┐ │  │
│  │  │ Next.js │  │   FastAPI  │ │  │
│  │  │ :3000   │  │   :8001    │ │  │
│  │  └────┬────┘  └─────┬──────┘ │  │
│  │       │             │        │  │
│  │  ┌────┴─────────────┴──────┐ │  │
│  │  │      supervisord        │ │  │
│  │  └─────────────────────────┘ │  │
│  └───────────────────────────────┘  │
│              Ubuntu 24.04            │
└─────────────────────────────────────┘
```
