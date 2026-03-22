# PostgreSQL Migration Guide

This guide explains how to migrate OpenClaw OPC from SQLite (development) to PostgreSQL (production).

## Why PostgreSQL?

- **Better concurrency**: Supports multiple simultaneous connections
- **Production-ready**: More robust for production deployments
- **Scalability**: Better performance with large datasets
- **Features**: Advanced querying, indexing, and backup capabilities

## Quick Start

### Option 1: Using the Setup Script (Recommended)

```bash
# 1. Initialize PostgreSQL
./scripts/setup_postgres.sh init

# 2. Migrate data from SQLite (optional)
./scripts/setup_postgres.sh migrate

# 3. Switch to PostgreSQL
./scripts/setup_postgres.sh switch-postgres

# 4. Restart the application
docker-compose up -d
```

### Option 2: Manual Setup

#### Step 1: Start PostgreSQL

```bash
# Start PostgreSQL container
docker-compose --profile postgres up -d postgres

# Wait for it to be ready
docker-compose ps
```

#### Step 2: Create Tables

```bash
cd backend
python3 -c "
from src.database import init_db
init_db()
print('Tables created')
"
```

#### Step 3: Migrate Data (Optional)

If you have existing data in SQLite:

```bash
cd backend
python3 migrations/migrate_sqlite_to_postgres.py \
    --source ./data/opc.db \
    --target postgresql://opc:opc_password@localhost:5432/openclaw_opc \
    --yes
```

#### Step 4: Update Configuration

Edit `.env` file:

```bash
# Switch to PostgreSQL
DB_TYPE=postgresql
PG_HOST=localhost
PG_PORT=5432
PG_USER=opc
PG_PASSWORD=opc_password
PG_DATABASE=openclaw_opc
```

#### Step 5: Restart Application

```bash
docker-compose up -d
```

## Configuration Reference

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_TYPE` | Database type (`sqlite` or `postgresql`) | `sqlite` |
| `DATABASE_URL` | Full database URL (overrides other settings) | - |
| `OPC_DB_PATH` | SQLite database file path | `./data/opc.db` |
| `PG_HOST` | PostgreSQL host | `localhost` |
| `PG_PORT` | PostgreSQL port | `5432` |
| `PG_USER` | PostgreSQL username | `opc` |
| `PG_PASSWORD` | PostgreSQL password | `opc_password` |
| `PG_DATABASE` | PostgreSQL database name | `openclaw_opc` |

### Docker Compose Profiles

- **Default**: `docker-compose up -d` - SQLite only
- **With PostgreSQL**: `docker-compose --profile postgres up -d` - Both PostgreSQL and backend
- **Full stack**: `docker-compose --profile full up -d` - Everything including PostgreSQL

## Migration Script Usage

```bash
# Basic migration
python3 migrations/migrate_sqlite_to_postgres.py --target postgresql://user:pass@host/db

# With custom source
python3 migrations/migrate_sqlite_to_postgres.py \
    --source ./custom/path/opc.db \
    --target postgresql://user:pass@host/db

# Skip confirmation prompts
python3 migrations/migrate_sqlite_to_postgres.py \
    --target postgresql://user:pass@host/db \
    --yes
```

## Switching Back to SQLite

```bash
# Using the helper script
./scripts/setup_postgres.sh switch-sqlite

# Or manually edit .env
DB_TYPE=sqlite
OPC_DB_PATH=./data/opc.db
```

Then restart the application.

## Troubleshooting

### Connection Refused

```
Error: Connection refused to PostgreSQL
```

**Solution**: Ensure PostgreSQL is running:
```bash
docker-compose --profile postgres ps
docker-compose logs postgres
```

### Authentication Failed

```
Error: authentication failed for user "opc"
```

**Solution**: Check credentials in `.env` and ensure they match docker-compose.yml

### Migration Fails

If migration fails mid-way:

1. Check the error message for the specific table
2. Fix any data issues in SQLite
3. Drop and recreate PostgreSQL database:
   ```bash
   docker-compose down -v
   docker-compose --profile postgres up -d postgres
   ```
4. Retry migration

## Production Deployment

For production, ensure:

1. **Secure passwords**: Change default `opc_password`
2. **SSL/TLS**: Enable encryption for database connections
3. **Backups**: Set up regular PostgreSQL backups
4. **Monitoring**: Monitor database performance and connections
5. **Firewall**: Restrict database access to application servers only

Example production `.env`:

```bash
DB_TYPE=postgresql
PG_HOST=db.internal.company.com
PG_PORT=5432
PG_USER=opc_production
PG_PASSWORD=your-very-secure-password-here
PG_DATABASE=openclaw_opc_prod
```

## Data Type Differences

| SQLite | PostgreSQL | Notes |
|--------|------------|-------|
| `INTEGER` | `INTEGER` | Same |
| `REAL` | `REAL` | Same |
| `TEXT` | `TEXT` | Same |
| `BOOLEAN` (0/1) | `BOOLEAN` | Auto-converted during migration |
| `DATETIME` | `TIMESTAMP` | Auto-converted |

The migration script handles all type conversions automatically.
