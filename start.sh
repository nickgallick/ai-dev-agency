#!/bin/bash
set -e

# Use PORT from Railway or default to 8000
export PORT=${PORT:-8000}

# Run database migrations
echo "Running database migrations..."
cd /app
python -c "from backend.models import Base, engine; Base.metadata.create_all(bind=engine)"

# Start nginx in background for static files (if needed)
# nginx

# Start the backend API server
echo "Starting API server on port $PORT..."
cd /app/backend
exec gunicorn main:app \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:$PORT \
    --access-logfile - \
    --error-logfile - \
    --timeout 120
