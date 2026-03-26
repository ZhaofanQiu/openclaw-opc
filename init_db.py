#!/usr/bin/env python3
"""初始化 OPC 数据库"""
import asyncio
import sys
sys.path.insert(0, '/root/.openclaw/workspace/openclaw-opc/packages/opc-database/src')
sys.path.insert(0, '/root/.openclaw/workspace/openclaw-opc/packages/opc-core/src')
sys.path.insert(0, '/root/.openclaw/workspace/openclaw-opc/packages/opc-openclaw/src')

from opc_database.connection import init_db

async def main():
    print("Initializing database...")
    await init_db()
    print("Database initialized successfully!")

if __name__ == "__main__":
    asyncio.run(main())
