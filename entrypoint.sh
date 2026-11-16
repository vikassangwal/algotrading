#!/bin/bash
set -e

# ELCO Trader Entrypoint Script
# Handles initialization, migrations, and service startup

echo "🚀 Starting ELCO Trader..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Wait for database to be ready
wait_for_db() {
    log_info "Waiting for PostgreSQL..."
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if pg_isready -h postgres -U elco -d elco_trader > /dev/null 2>&1; then
            log_info "PostgreSQL is ready!"
            return 0
        fi
        log_info "Attempt $attempt/$max_attempts: PostgreSQL not ready yet..."
        sleep 2
        attempt=$((attempt + 1))
    done

    log_error "PostgreSQL did not become ready in time"
    return 1
}

# Wait for Redis to be ready
wait_for_redis() {
    log_info "Waiting for Redis..."
    local max_attempts=20
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if redis-cli -h redis ping > /dev/null 2>&1; then
            log_info "Redis is ready!"
            return 0
        fi
        log_info "Attempt $attempt/$max_attempts: Redis not ready yet..."
        sleep 1
        attempt=$((attempt + 1))
    done

    log_error "Redis did not become ready in time"
    return 1
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."
    cd /app

    if alembic upgrade head; then
        log_info "Migrations completed successfully"
    else
        log_error "Migration failed"
        return 1
    fi
}

# Initialize application data
init_app_data() {
    log_info "Initializing application data..."
    cd /app

    python -c "
from app.db import init_db
init_db()
print('Database initialized')
" || {
        log_error "Failed to initialize database"
        return 1
    }
}

# Create necessary directories
setup_directories() {
    log_info "Setting up directories..."
    mkdir -p /app/data /var/log/nginx /var/log/supervisor /app/uploads
    chown -R elco:elco /app/data /var/log/nginx /var/log/supervisor /app/uploads 2>/dev/null || true
}

# Validate configuration
validate_config() {
    log_info "Validating configuration..."

    # Check required environment variables
    local required_vars=("ELCO_SECRET_KEY" "POSTGRES_PASSWORD")
    local missing_vars=()

    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done

    if [ ${#missing_vars[@]} -gt 0 ]; then
        log_warn "Missing environment variables: ${missing_vars[*]}"
        log_warn "Using defaults - NOT RECOMMENDED FOR PRODUCTION"
    fi

    # Validate secret key length
    if [ ${#ELCO_SECRET_KEY} -lt 32 ]; then
        log_warn "ELCO_SECRET_KEY should be at least 32 characters"
    fi
}

# Health check endpoint setup
setup_health_check() {
    log_info "Setting up health check endpoint..."
    # The health check is handled by the FastAPI app
}

# Graceful shutdown handler
shutdown() {
    log_info "Received shutdown signal, stopping services..."
    supervisorctl stop all
    exit 0
}

trap shutdown SIGTERM SIGINT

# Main initialization sequence
main() {
    log_info "ELCO Trader v$(cat /app/VERSION 2>/dev/null || echo 'dev')"
    log_info "Environment: ${ENVIRONMENT:-development}"

    setup_directories
    validate_config

    # Wait for dependencies in production
    if [ "${ENVIRONMENT}" = "production" ]; then
        wait_for_db || exit 1
        wait_for_redis || exit 1
        run_migrations || exit 1
    fi

    init_app_data || exit 1
    setup_health_check

    log_info "Starting services with supervisord..."
    exec supervisord -c /etc/supervisor/conf.d/supervisord.conf
}

main "$@"