"""
opc-core: Uvicorn 入口文件

用于直接启动 uvicorn (需确保已以 editable 模式安装本包及依赖):
    cd packages/opc-core
    uvicorn main:app --host 0.0.0.0 --port 8080

作者: OpenClaw OPC Team
版本: 0.4.6
"""

from opc_core.app import create_app

app = create_app()
