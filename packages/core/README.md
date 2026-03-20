# OPC Core Service

后端服务，提供公司管理、预算追踪、任务调度等 API。

## 技术栈

- Python 3.10+
- FastAPI
- SQLAlchemy
- SQLite/PostgreSQL

## 开发

```bash
# 安装依赖
pip install -r requirements.txt

# 启动开发服务器
uvicorn src.main:app --reload --port 8080

# 运行测试
pytest
```

## API 文档

启动后访问: http://localhost:8080/docs
