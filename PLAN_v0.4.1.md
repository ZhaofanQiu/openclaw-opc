# v0.4.1 测试规划 - 四模块独立闭环测试

## 目标

确保四个模块各自独立可测试、可运行，不依赖其他模块的实际实现。

## 测试策略

| 模块 | 测试类型 | 隔离方式 | 目标覆盖率 |
|------|----------|----------|------------|
| opc-database | 单元 + 集成 | SQLite 内存数据库 | ≥80% |
| opc-openclaw | 单元 + Mock | respx Mock HTTP | ≥80% |
| opc-core | API + 服务 | TestClient + Mock dependencies | ≥75% |
| opc-ui | 单元 + 组件 | Vitest + jsdom | ≥70% |

---

## 1. opc-database 测试

### 测试范围
- [ ] 数据库连接管理
- [ ] 所有模型定义
- [ ] Repository 层所有方法
- [ ] 事务处理

### 测试实现

```python
# tests/unit/test_connection.py
# tests/unit/test_models.py
# tests/unit/test_employee_repo.py
# tests/unit/test_task_repo.py
```

### 关键测试点
1. **连接测试**: 使用 `create_async_engine("sqlite+aiosqlite:///:memory:")`
2. **模型测试**: 验证字段定义、关系、约束
3. **Repository 测试**: CRUD、过滤、分页、事务
4. **并发测试**: 异步会话隔离

### 运行命令
```bash
cd packages/opc-database
pip install -e ".[dev]"
pytest tests/ -v --cov=opc_database --cov-report=term-missing
```

---

## 2. opc-openclaw 测试

### 测试范围
- [ ] HTTP Client 基础功能
- [ ] Agent 生命周期管理
- [ ] Messenger 消息发送
- [ ] Skill 定义验证

### 隔离方式
使用 `respx` Mock 所有 HTTP 请求:

```python
import respx

@respx.mock
def test_create_agent():
    route = respx.post("http://localhost:8080/agents").mock(
        return_value=httpx.Response(200, json={"id": "agent_001"})
    )
    ...
```

### 关键测试点
1. **Client 测试**: 重试机制、超时处理、错误处理
2. **Agent Manager**: 创建、删除、状态查询
3. **Messenger**: 消息发送、会话管理
4. **Lifecycle**: 绑定、解绑、健康检查

### 运行命令
```bash
cd packages/opc-openclaw
pip install -e ".[dev]"
pytest tests/ -v --cov=opc_openclaw --cov-report=term-missing
```

---

## 3. opc-core 测试

### 测试范围
- [ ] FastAPI 端点 (使用 TestClient)
- [ ] 服务层业务逻辑
- [ ] 依赖注入配置
- [ ] 路由集成

### 隔离方式
使用 `unittest.mock` Mock database 和 openclaw:

```python
# conftest.py
@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.fixture
def mock_openclaw():
    return AsyncMock()

@pytest.fixture
def app(mock_db, mock_openclaw):
    # 覆盖依赖注入
    app.dependency_overrides[get_db] = lambda: mock_db
    return app
```

### 关键测试点
1. **API 测试**: 所有 46 个端点的请求/响应
2. **服务层**: 业务逻辑、异常处理
3. **依赖注入**: 正确解析和 Mock
4. **认证**: API Key 验证

### 运行命令
```bash
cd packages/opc-core
pip install -e ".[dev]"
pytest tests/ -v --cov=opc_core --cov-report=term-missing
```

---

## 4. opc-ui 测试

### 测试范围
- [ ] 组件渲染 (Vue Test Utils)
- [ ] Pinia Store (行为测试)
- [ ] 路由导航
- [ ] API 工具函数

### 隔离方式
使用 `msw` (Mock Service Worker) 或 `vitest` Mock:

```typescript
// tests/setup.ts
import { config } from '@vue/test-utils'

config.global.stubs = {
  'router-link': true,
  'router-view': true
}
```

### 关键测试点
1. **组件**: 渲染、事件、props
2. **Store**: state、getters、actions
3. **路由**: 导航守卫、路由匹配
4. **API**: axios Mock、错误处理

### 运行命令
```bash
cd packages/opc-ui
npm install
npm run test
```

---

## 实施计划

### Phase 1: 基础设施 (1 天)
- [ ] 完善各模块的 pytest/vitest 配置
- [ ] 创建统一的测试工具函数
- [ ] 设置 CI 脚本

### Phase 2: opc-database (1 天)
- [ ] 补充 Repository 测试
- [ ] 添加模型验证测试
- [ ] 达到 80% 覆盖率

### Phase 3: opc-openclaw (1 天)
- [ ] 使用 respx Mock HTTP
- [ ] 测试 Agent 生命周期
- [ ] 测试 Messenger

### Phase 4: opc-core (1.5 天)
- [ ] 创建 Mock fixtures
- [ ] 测试所有 API 端点
- [ ] 测试服务层

### Phase 5: opc-ui (1.5 天)
- [ ] 配置 Vitest + Vue Test Utils
- [ ] 测试关键组件
- [ ] 测试 Store

### Phase 6: 集成验证 (0.5 天)
- [ ] 创建 `scripts/run_all_tests.sh`
- [ ] 验证各模块独立运行
- [ ] 生成覆盖率报告

---

## 验收标准

1. ✅ 每个模块 `pytest/npm test` 可独立运行
2. ✅ 模块测试不依赖其他模块的实际服务
3. ✅ 覆盖率达标
4. ✅ CI 通过

---

## 新增文件清单

```
packages/opc-database/
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_connection.py
│   │   ├── test_models.py
│   │   ├── test_employee_repo.py
│   │   └── test_task_repo.py
│   └── integration/
│       └── test_repository_flow.py

packages/opc-openclaw/
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_client.py
│   │   ├── test_agent_manager.py
│   │   ├── test_messenger.py
│   │   └── test_skill.py
│   └── mocks/
│       └── openclaw_responses.py

packages/opc-core/
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_employees.py (补充)
│   │   ├── test_tasks.py (补充)
│   │   ├── test_budget.py (新增)
│   │   └── test_skill_api.py (补充)
│   └── integration/
│       └── test_api_flow.py

packages/opc-ui/
├── tests/
│   ├── setup.ts
│   ├── unit/
│   │   ├── components/
│   │   │   ├── AppHeader.spec.ts
│   │   │   └── AppSidebar.spec.ts
│   │   ├── stores/
│   │   │   ├── auth.spec.ts
│   │   │   ├── employees.spec.ts
│   │   │   └── tasks.spec.ts
│   │   └── utils/
│   │       └── api.spec.ts
│   └── mocks/
│       └── api.ts

scripts/
└── run_all_tests.sh      # 运行所有模块测试
```
