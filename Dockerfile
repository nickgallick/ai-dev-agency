# Simplified Railway Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy frontend and build
COPY frontend/package*.json ./frontend/
WORKDIR /app/frontend
RUN npm ci --only=production || npm install
COPY frontend/ ./
RUN npm run build

# Copy backend code
WORKDIR /app
COPY backend/ ./backend/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY config/ ./config/

# Move built frontend to backend static folder
RUN mkdir -p /app/backend/static && cp -r /app/frontend/dist/* /app/backend/static/

WORKDIR /app/backend

# Expose port
EXPOSE 8000

# Set environment variable for production
ENV PRODUCTION=true

# Run the application
CMD ["sh", "-c", "python -c 'from models import Base, engine; Base.metadata.create_all(bind=engine)' && gunicorn main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000}"]
