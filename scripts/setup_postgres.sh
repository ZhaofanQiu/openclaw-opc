#!/bin/bash
# PostgreSQL Setup and Migration Script for OpenClaw OPC
# Usage: ./scripts/setup_postgres.sh [init|migrate|status|switch-sqlite|switch-postgres]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_DIR/backend"
DATA_DIR="$PROJECT_DIR/data"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running in Docker
is_docker() {
    if [ -f /.dockerenv ]; then
        return 0
    fi
    if grep -q docker /proc/1/cgroup 2>/dev/null; then
        return 0
    fi
    return 1
}

# Initialize PostgreSQL with Docker
init_postgres() {
    log_info "Initializing PostgreSQL with Docker..."
    
    cd "$PROJECT_DIR"
    
    # Check if docker-compose is available
    if ! command -v docker-compose &> /dev/null; then
        log_error "docker-compose not found. Please install Docker Compose."
        exit 1
    fi
    
    # Start PostgreSQL
    log_info "Starting PostgreSQL container..."
    docker-compose --profile postgres up -d postgres
    
    # Wait for PostgreSQL to be healthy
    log_info "Waiting for PostgreSQL to be ready..."
    for i in {1..30}; do
        if docker-compose ps postgres | grep -q "healthy"; then
            log_success "PostgreSQL is ready!"
            break
        fi
        sleep 2
    done
    
    # Create tables
    log_info "Creating database tables..."
    cd "$BACKEND_DIR"
    python3 -c "
import sys
sys.path.insert(0, '.')
from src.database import init_db
init_db()
print('Tables created successfully')
"
    
    log_success "PostgreSQL initialized!"
    log_info "Connection: postgresql://opc:opc_password@localhost:5432/openclaw_opc"
}

# Migrate data from SQLite to PostgreSQL
migrate_data() {
    log_info "Migrating data from SQLite to PostgreSQL..."
    
    SQLITE_DB="${DATA_DIR}/opc.db"
    
    if [ ! -f "$SQLITE_DB" ]; then
        log_warn "SQLite database not found at $SQLITE_DB"
        log_info "Starting with empty PostgreSQL database..."
        return 0
    fi
    
    log_info "Source: $SQLITE_DB"
    log_info "Target: postgresql://opc:opc_password@localhost:5432/openclaw_opc"
    
    cd "$BACKEND_DIR"
    python3 migrations/migrate_sqlite_to_postgres.py \
        --source "$SQLITE_DB" \
        --target "postgresql://opc:opc_password@localhost:5432/openclaw_opc" \
        --yes
    
    log_success "Migration complete!"
}

# Check database status
check_status() {
    log_info "Checking database status..."
    
    cd "$BACKEND_DIR"
    python3 -c "
import sys
sys.path.insert(0, '.')
from src.database import get_database_info

info = get_database_info()
print(f\"Database Type: {info['type']}\")
print(f\"Connection URL: {info['url']}\")
print(f\"Connection Status: {'✅ Connected' if info['connected'] else '❌ Failed'}\")
"
}

# Switch to PostgreSQL
switch_to_postgres() {
    log_info "Switching to PostgreSQL..."
    
    ENV_FILE="$PROJECT_DIR/.env"
    
    # Backup current .env
    if [ -f "$ENV_FILE" ]; then
        cp "$ENV_FILE" "$ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"
        log_info "Backed up current .env"
    fi
    
    # Update or create .env
    cat >> "$ENV_FILE" << 'EOF'

# PostgreSQL Configuration
DB_TYPE=postgresql
PG_HOST=localhost
PG_PORT=5432
PG_USER=opc
PG_PASSWORD=opc_password
PG_DATABASE=openclaw_opc
EOF
    
    log_success "Switched to PostgreSQL configuration"
    log_info "Please restart the application to use PostgreSQL"
}

# Switch to SQLite
switch_to_sqlite() {
    log_info "Switching to SQLite..."
    
    ENV_FILE="$PROJECT_DIR/.env"
    
    # Backup current .env
    if [ -f "$ENV_FILE" ]; then
        cp "$ENV_FILE" "$ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"
        log_info "Backed up current .env"
    fi
    
    # Update or create .env
    cat >> "$ENV_FILE" << 'EOF'

# SQLite Configuration (default)
DB_TYPE=sqlite
OPC_DB_PATH=./data/opc.db
EOF
    
    log_success "Switched to SQLite configuration"
    log_info "Please restart the application to use SQLite"
}

# Show help
show_help() {
    cat << 'EOF'
OpenClaw OPC PostgreSQL Management Script

Usage: ./scripts/setup_postgres.sh [command]

Commands:
    init              Initialize PostgreSQL with Docker
    migrate           Migrate data from SQLite to PostgreSQL
    status            Check database connection status
    switch-sqlite     Switch configuration to SQLite
    switch-postgres   Switch configuration to PostgreSQL
    help              Show this help message

Examples:
    # Initialize PostgreSQL and migrate data
    ./scripts/setup_postgres.sh init
    ./scripts/setup_postgres.sh migrate

    # Check current database status
    ./scripts/setup_postgres.sh status

    # Switch between databases
    ./scripts/setup_postgres.sh switch-postgres
    ./scripts/setup_postgres.sh switch-sqlite

EOF
}

# Main command handler
case "${1:-help}" in
    init)
        init_postgres
        ;;
    migrate)
        migrate_data
        ;;
    status)
        check_status
        ;;
    switch-sqlite)
        switch_to_sqlite
        ;;
    switch-postgres)
        switch_to_postgres
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
