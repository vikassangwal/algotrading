# Multi-stage Dockerfile for ELCO Trader
# Build stage for frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --prefer-offline --no-audit

COPY frontend/ ./
RUN npm run build

# Build stage for backend
FROM python:3.11-slim AS backend-builder

WORKDIR /app
COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY app/ ./app/
COPY alembic.ini ./
COPY migrations/ ./migrations/

# Final stage
FROM python:3.11-slim AS production

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash elco

WORKDIR /app

# Copy Python dependencies
COPY --from=backend-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --from=backend-builder /app/app ./app
COPY --from=backend-builder /app/alembic.ini ./
COPY --from=backend-builder /app/migrations ./migrations

# Copy built frontend
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Copy configuration files
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh && \
    chown -R elco:elco /app && \
    mkdir -p /var/log/supervisor /var/log/nginx /app/data && \
    chown -R elco:elco /var/log/supervisor /var/log/nginx /app/data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 80 8000

USER elco

ENTRYPOINT ["/entrypoint.sh"]