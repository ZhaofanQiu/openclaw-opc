#!/bin/bash
cd /root/.openclaw/workspace/openclaw-opc/backend
source venv/bin/activate
exec uvicorn src.main:app --host 0.0.0.0 --port 8080