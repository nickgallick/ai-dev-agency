#!/bin/bash
# Auto-deploy script: pulls latest code and rebuilds Docker containers
# Called by the webhook listener or manually

set -e

REPO_DIR="/home/ubuntu/ai-dev-agency"
LOG_FILE="/var/log/ai-dev-agency-deploy.log"
BRANCH="${1:-master}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=== Deploy started (branch: $BRANCH) ==="

cd "$REPO_DIR"

# Pull latest changes
log "Pulling latest changes..."
git fetch origin "$BRANCH"
git reset --hard "origin/$BRANCH"

log "Pull complete. Latest commit: $(git log --oneline -1)"

# Rebuild and restart containers
log "Rebuilding containers..."
sudo docker-compose build --no-cache api
sudo docker-compose up -d

# Wait for health check
log "Waiting for health check..."
sleep 15

if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    log "=== Deploy successful ==="
else
    log "=== WARNING: Health check failed, check logs ==="
    sudo docker-compose logs --tail=20 api >> "$LOG_FILE" 2>&1
fi
