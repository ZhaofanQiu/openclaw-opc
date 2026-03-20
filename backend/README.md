# OpenClaw OPC Core Service

Backend service for OpenClaw One-Person Company.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn src.main:app --reload --port 8080

# API docs
open http://localhost:8080/docs
```

## Architecture

- FastAPI + SQLite (MVP)
- Partner Agent + OPC Bridge Skill pattern
- HTTP API for Agent reporting

## API Endpoints

- `POST /api/agents/report` - Agent task completion report
- `GET /api/tasks` - List tasks
- `POST /api/tasks` - Create task
- `GET /api/budget` - Budget status

## Database

SQLite at `./data/opc.db`

## Environment

```bash
OPC_DB_PATH=./data/opc.db
OPC_LOG_LEVEL=info
```
