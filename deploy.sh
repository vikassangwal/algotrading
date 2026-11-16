#!/bin/bash
set -e

# ELCO Trader Deployment Script
# Usage: ./deploy.sh [environment] [action]
# Environments: development, staging, production
# Actions: up, down, restart, logs, status, backup, restore

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${1:-development}"
ACTION="${2:-up}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Validate environment
validate_env() {
    case $ENVIRONMENT in
        development|staging|production) ;;
        *) log_error "Invalid environment: $ENVIRONMENT"; exit 1 ;;
    esac
}

# Load environment file
load_env() {
    ENV_FILE="$PROJECT_ROOT/.env.$ENVIRONMENT"
    if [[ -f "$ENV_FILE" ]]; then
        log_info "Loading environment from $ENV_FILE"
        set -a
        source "$ENV_FILE"
        set +a
    else
        log_warn "Environment file $ENV_FILE not found"
    fi
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker not installed"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose not installed"
        exit 1
    fi

    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon not running"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Build images
build_images() {
    log_info "Building Docker images..."
    cd "$PROJECT_ROOT"

    docker-compose -f docker-compose.yml \
        -f docker-compose.${ENVIRONMENT}.yml \
        build --parallel

    log_success "Images built successfully"
}

# Start services
start_services() {
    log_info "Starting services for $ENVIRONMENT..."
    cd "$PROJECT_ROOT"

    docker-compose -f docker-compose.yml \
        -f docker-compose.${ENVIRONMENT}.yml \
        up -d --remove-orphans

    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    sleep 10

    # Check health
    check_health

    log_success "Services started successfully"
}

# Stop services
stop_services() {
    log_info "Stopping services..."
    cd "$PROJECT_ROOT"

    docker-compose -f docker-compose.yml \
        -f docker-compose.${ENVIRONMENT}.yml \
        down --remove-orphans

    log_success "Services stopped"
}

# Restart services
restart_services() {
    log_info "Restarting services..."
    stop_services
    start_services
}

# Show logs
show_logs() {
    cd "$PROJECT_ROOT"

    SERVICE="${3:-}"
    if [[ -n "$SERVICE" ]]; then
        docker-compose -f docker-compose.yml \
            -f docker-compose.${ENVIRONMENT}.yml \
            logs -f "$SERVICE"
    else
        docker-compose -f docker-compose.yml \
            -f docker-compose.${ENVIRONMENT}.yml \
            logs -f --tail=100
    fi
}

# Show status
show_status() {
    cd "$PROJECT_ROOT"

    echo "=== Service Status ==="
    docker-compose -f docker-compose.yml \
        -f docker-compose.${ENVIRONMENT}.yml \
        ps

    echo ""
    echo "=== Health Checks ==="
    check_health
}

# Health check
check_health() {
    local max_attempts=30
    local attempt=1

    while [[ $attempt -le $max_attempts ]]; do
        if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
            log_success "API health check passed"
            return 0
        fi

        if [[ $attempt -eq $max_attempts ]]; then
            log_error "Health check failed after $max_attempts attempts"
            return 1
        fi

        log_info "Waiting for API to be healthy... (attempt $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
}

# Backup database
backup_database() {
    log_info "Creating database backup..."
    cd "$PROJECT_ROOT"

    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="backups/backup_${ENVIRONMENT}_${TIMESTAMP}.sql"

    mkdir -p "$(dirname "$BACKUP_FILE")"

    docker-compose -f docker-compose.yml \
        -f docker-compose.${ENVIRONMENT}.yml \
        exec -T postgres pg_dump -U elco elco_trader > "$BACKUP_FILE"

    # Compress
    gzip "$BACKUP_FILE"

    # Clean old backups (keep last 7 days)
    find backups -name "backup_${ENVIRONMENT}_*.sql.gz" -mtime +7 -delete

    log_success "Backup created: ${BACKUP_FILE}.gz"
}

# Restore database
restore_database() {
    BACKUP_FILE="${3:-}"

    if [[ -z "$BACKUP_FILE" ]]; then
        log_error "Backup file not specified"
        log_info "Usage: ./deploy.sh $ENVIRONMENT restore <backup_file>"
        exit 1
    fi

    if [[ ! -f "$BACKUP_FILE" ]]; then
        log_error "Backup file not found: $BACKUP_FILE"
        exit 1
    fi

    log_warn "This will overwrite the current database!"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Restore cancelled"
        exit 0
    fi

    log_info "Restoring database from $BACKUP_FILE..."
    cd "$PROJECT_ROOT"

    # Decompress if needed
    if [[ "$BACKUP_FILE" == *.gz ]]; then
        gunzip -c "$BACKUP_FILE" | docker-compose -f docker-compose.yml \
            -f docker-compose.${ENVIRONMENT}.yml \
            exec -T postgres psql -U elco -d elco_trader
    else
        cat "$BACKUP_FILE" | docker-compose -f docker-compose.yml \
            -f docker-compose.${ENVIRONMENT}.yml \
            exec -T postgres psql -U elco -d elco_trader
    fi

    log_success "Database restored"
}

# Run migrations
run_migrations() {
    log_info "Running database migrations..."
    cd "$PROJECT_ROOT"

    docker-compose -f docker-compose.yml \
        -f docker-compose.${ENVIRONMENT}.yml \
        exec -T elco-trader alembic upgrade head

    log_success "Migrations completed"
}

# Seed database
seed_database() {
    log_info "Seeding database with initial data..."
    cd "$PROJECT_ROOT"

    docker-compose -f docker-compose.yml \
        -f docker-compose.${ENVIRONMENT}.yml \
        exec -T elco-trader python -m app.db.seed

    log_success "Database seeded"
}

# Scale services
scale_services() {
    SERVICE="${3:-}"
    REPLICAS="${4:-}"

    if [[ -z "$SERVICE" || -z "$REPLICAS" ]]; then
        log_error "Usage: ./deploy.sh $ENVIRONMENT scale <service> <replicas>"
        exit 1
    fi

    log_info "Scaling $SERVICE to $REPLICAS replicas..."
    cd "$PROJECT_ROOT"

    docker-compose -f docker-compose.yml \
        -f docker-compose.${ENVIRONMENT}.yml \
        up -d --scale "$SERVICE=$REPLICAS"

    log_success "Scaled $SERVICE to $REPLICAS replicas"
}

# Update images
update_images() {
    log_info "Pulling latest images..."
    cd "$PROJECT_ROOT"

    docker-compose -f docker-compose.yml \
        -f docker-compose.${ENVIRONMENT}.yml \
        pull

    log_info "Restarting services with new images..."
    docker-compose -f docker-compose.yml \
        -f docker-compose.${ENVIRONMENT}.yml \
        up -d --remove-orphans

    check_health
    log_success "Images updated"
}

# Clean up
clean_up() {
    log_warn "This will remove all containers, networks, and volumes!"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Clean up cancelled"
        exit 0
    fi

    cd "$PROJECT_ROOT"

    docker-compose -f docker-compose.yml \
        -f docker-compose.${ENVIRONMENT}.yml \
        down -v --remove-orphans

    docker system prune -f

    log_success "Clean up completed"
}

# Main execution
main() {
    validate_env
    load_env
    check_prerequisites

    case $ACTION in
        up)
            build_images
            start_services
            ;;
        down)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        logs)
            show_logs "$@"
            ;;
        status)
            show_status
            ;;
        backup)
            backup_database
            ;;
        restore)
            restore_database "$@"
            ;;
        migrate)
            run_migrations
            ;;
        seed)
            seed_database
            ;;
        scale)
            scale_services "$@"
            ;;
        update)
            update_images
            ;;
        clean)
            clean_up
            ;;
        health)
            check_health
            ;;
        *)
            log_error "Unknown action: $ACTION"
            echo "Usage: $0 [environment] [action]"
            echo "Environments: development, staging, production"
            echo "Actions: up, down, restart, logs, status, backup, restore, migrate, seed, scale, update, clean, health"
            exit 1
            ;;
    esac
}

main "$@"