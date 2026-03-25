"""
opc-core: Uvicorn 入口文件

用于直接启动 uvicorn:
    uvicorn main:app --host 0.0.0.0 --port 8080

作者: OpenClaw OPC Team
创建日期: 2026-03-25
版本: 0.4.1
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/openclaw-opc/packages/opc-core/src')
sys.path.insert(0, '/root/.openclaw/workspace/openclaw-opc/packages/opc-database/src')
sys.path.insert(0, '/root/.openclaw/workspace/openclaw-opc/packages/opc-openclaw/src')

from opc_core.app import create_app

app = create_app()
