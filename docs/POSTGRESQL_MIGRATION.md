# PostgreSQL Migration Guide

This guide explains how to migrate OpenClaw OPC from SQLite (default) to PostgreSQL for production use.

## Why PostgreSQL?

- **Concurrent Access**: Multiple users can access the database simultaneously
- **Better Performance**: Handles larger datasets more efficiently
- **Production Ready**: More robust for external deployments
- **Backup/Recovery**: Better tooling for backups and point-in-time recovery

## Quick Start with Docker

The easiest way to run PostgreSQL is using Docker Compose:

```bash
# Start with PostgreSQL support
docker-compose --profile postgres up -d

# Or use the full profile (includes all services)
docker-compose --profile full up -d
```

This will start:
- PostgreSQL database on port 5432
- Backend API on port 8080
- Frontend dashboard on port 3000

## Manual Setup

### 1. Install PostgreSQL

**macOS:**
```bash
brew install postgresql@16
brew services start postgresql@16
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql-16
sudo systemctl start postgresql
```

### 2. Create Database and User

```bash
sudo -u postgres psql
```

```sql
CREATE USER opc WITH PASSWORD 'your_secure_password';
CREATE DATABASE openclaw_opc OWNER opc;
GRANT ALL PRIVILEGES ON DATABASE openclaw_opc TO opc;
\q
```

### 3. Configure Environment

Create or update your `.env` file:

```bash
# Switch to PostgreSQL
DB_TYPE=postgresql

# Connection details
PG_HOST=localhost
PG_PORT=5432
PG_USER=opc
PG_PASSWORD=your_secure_password
PG_DATABASE=openclaw_opc

# Or use a full URL (overrides above)
# DATABASE_URL=postgresql://opc:password@localhost:5432/openclaw_opc
```

### 4. Run Migration

If you have existing data in SQLite:

```bash
cd backend

# Install psycopg2 if not already installed
pip install psycopg2-binary

# Run migration
python migrations/migrate_sqlite_to_postgres.py \
  --source ./data/opc.db \
  --target postgresql://opc:password@localhost:5432/openclaw_opc
```

### 5. Start Application

```bash
cd backend
python -m uvicorn src.main:app --reload
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_TYPE` | Database type: `sqlite` or `postgresql` | `sqlite` |
| `DATABASE_URL` | Full database URL (overrides other settings) | - |
| `PG_HOST` | PostgreSQL host | `localhost` |
| `PG_PORT` | PostgreSQL port | `5432` |
| `PG_USER` | PostgreSQL username | `opc` |
| `PG_PASSWORD` | PostgreSQL password | `opc_password` |
| `PG_DATABASE` | PostgreSQL database name | `openclaw_opc` |
| `OPC_DB_PATH` | SQLite database path | `./data/opc.db` |

## Migration Script Options

```bash
python migrations/migrate_sqlite_to_postgres.py --help

Options:
  --source TEXT   Source SQLite database path (default: ./data/opc.db)
  --target TEXT   Target PostgreSQL URL (required)
  -y, --yes       Skip confirmation prompts
```

## Verification

Check the health endpoint to verify PostgreSQL is connected:

```bash
curl http://localhost:8080/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": {
    "type": "postgresql",
    "connected": true
  },
  "version": "0.2.0-alpha"
}
```

## Troubleshooting

### Connection Refused

```
psycopg2.OperationalError: connection to server at "localhost", port 5432 failed
```

**Solution:**
- Ensure PostgreSQL is running: `sudo systemctl status postgresql`
- Check port: `sudo netstat -tlnp | grep 5432`
- Verify credentials in `.env`

### Authentication Failed

```
psycopg2.OperationalError: FATAL: password authentication failed
```

**Solution:**
- Verify password in `.env` matches the one set in PostgreSQL
- Check pg_hba.conf for authentication method

### Database Does Not Exist

```
psycopg2.OperationalError: FATAL: database "openclaw_opc" does not exist
```

**Solution:**
```bash
sudo -u postgres psql -c "CREATE DATABASE openclaw_opc OWNER opc;"
```

## Backup and Restore

### Backup

```bash
pg_dump -h localhost -U opc -d openclaw_opc > opc_backup.sql
```

### Restore

```bash
psql -h localhost -U opc -d openclaw_opc < opc_backup.sql
```

## Production Considerations

1. **Use strong passwords** for database users
2. **Enable SSL** for database connections
3. **Set up regular backups**
4. **Monitor database connections** (pool size is set to 5 with max 10 overflow)
5. **Use connection pooling** (PgBouncer) for high-traffic deployments

## Switching Back to SQLite

To switch back to SQLite:

```bash
# Update .env
DB_TYPE=sqlite
# Remove or comment out PG_* variables

# Restart application
```

SQLite data remains in `./data/opc.db` and is not affected by PostgreSQL migration.
