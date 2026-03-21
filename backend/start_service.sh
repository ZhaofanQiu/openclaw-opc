#!/bin/bash
cd /root/.openclaw/workspace/openclaw-opc/backend
while true; do
    echo "$(date): Starting uvicorn..." >> service_monitor.log
    python3 -m uvicorn src.main:app --host 127.0.0.1 --port 8080 >> app.log 2>&1
    echo "$(date): uvicorn exited with code $?" >> service_monitor.log
    sleep 2
done
