#!/bin/bash
# Quick deploy script — run on the server to pull latest and rebuild
# Usage: ./deploy.sh [branch]
#   ./deploy.sh                          # deploys current branch
#   ./deploy.sh claude/code-audit-fixes  # deploys specific branch

set -e

BRANCH="${1:-$(git rev-parse --abbrev-ref HEAD)}"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

cd "$REPO_DIR"

echo "=== Deploying branch: $BRANCH ==="

# Fetch latest
echo "Fetching..."
git fetch origin "$BRANCH"

# Checkout and reset to remote
git checkout "$BRANCH" 2>/dev/null || git checkout -b "$BRANCH" "origin/$BRANCH"
git reset --hard "origin/$BRANCH"

echo "=== Current commit: $(git log --oneline -1) ==="

# Rebuild and restart
echo "Building containers..."
docker-compose up --build -d

# Cleanup
docker image prune -f 2>/dev/null || true

echo "=== Deploy complete ==="
echo "Waiting for health check..."
sleep 10

# Verify
if curl -sf http://localhost:8000/health > /dev/null; then
    echo "API is healthy!"
else
    echo "WARNING: API health check failed. Check logs with: docker-compose logs api --tail=50"
fi

docker-compose logs api --tail=10 | grep -E "QueueWorker|Redis|Started" || true
echo "=== Done ==="
