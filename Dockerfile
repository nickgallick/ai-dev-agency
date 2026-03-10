# Production Dockerfile for Railway deployment
# Combined backend + frontend in a single container

FROM node:20-alpine AS frontend-builder

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --only=production || npm install
COPY frontend/ ./
RUN npm run build

# Final production image
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python requirements
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy backend code
COPY backend/ ./backend/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY config/ ./config/

# Copy built frontend
COPY --from=frontend-builder /frontend/dist /app/static

# Copy nginx config for static files
COPY nginx-railway.conf /etc/nginx/sites-available/default

# Copy startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Expose port (Railway uses PORT env var)
EXPOSE 8000

# Run startup script
CMD ["/app/start.sh"]
