# 开发者标准

> **必读**: 所有开发者在修改代码前必须阅读本文档

## 目录

1. [开发前必读](#1-开发前必读)
2. [代码规范](#2-代码规范)
3. [修改代码流程](#3-修改代码流程)
4. [文档更新规范](#4-文档更新规范)
5. [测试要求](#5-测试要求)

---

## 1. 开发前必读

### 1.1 全局开发者

| 文档 | 目的 |
|------|------|
| `DEVELOPMENT.md` (本文档) | 理解整体开发规范 |
| `ARCHITECTURE.md` | 全局架构设计 |
| `DEPLOYMENT.md` | 部署方式 |

### 1.2 模块开发者

根据你要修改的模块，阅读对应文档：

**修改 `packages/opc-database/`:**
- `packages/opc-database/README.md`
- `packages/opc-database/ARCHITECTURE.md`
- `packages/opc-database/API.md` (Repository接口)

**修改 `packages/opc-openclaw/`:**
- `packages/opc-openclaw/README.md`
- `packages/opc-openclaw/ARCHITECTURE.md`
- `packages/opc-openclaw/API.md` (Agent管理接口)

**修改 `packages/opc-core/`:**
- `packages/opc-core/README.md`
- `packages/opc-core/ARCHITECTURE.md`
- `packages/opc-core/API.md` (RESTful API)

**修改 `packages/opc-ui/`:**
- `packages/opc-ui/README.md`
- `packages/opc-ui/ARCHITECTURE.md`
- `packages/opc-ui/COMPONENT.md` (组件库)
- `packages/opc-ui/API.md` (与后端接口)

---

## 2. 代码规范

### 2.1 Python代码规范 (opc-database/openclaw/core)

#### 文件头模板

```python
"""
opc-module-name: 简短描述

功能: 详细功能说明
作者: 开发者名称
创建日期: YYYY-MM-DD
最后更新: YYYY-MM-DD

API文档: 链接到API.md相关章节
测试: 链接到tests/

变更记录:
- YYYY-MM-DD: 初始版本
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel
```

#### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 类名 | PascalCase | `EmployeeRepository`, `TaskService` |
| 函数/方法 | snake_case | `get_by_id()`, `create_task()` |
| 变量 | snake_case | `employee_id`, `task_list` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT`, `DEFAULT_TIMEOUT` |
| 私有 | _leading_underscore | `_internal_helper()`, `_cache` |
| 模块名 | snake_case | `employee_repo.py`, `task_service.py` |

#### 类型注解

**必须**使用类型注解：

```python
from typing import Optional, List, Dict, Any

async def get_employee(
    employee_id: str,
    include_inactive: bool = False
) -> Optional[EmployeeModel]:
    """根据ID获取员工"""
    pass

def calculate_budget(
    employees: List[EmployeeModel]
) -> Dict[str, float]:
    """计算预算分布"""
    pass
```

#### 异常处理

```python
from opc_database.exceptions import DatabaseError, NotFoundError

try:
    result = await repo.get_by_id(id)
except NotFoundError:
    logger.warning(f"Employee {id} not found")
    return None
except DatabaseError as e:
    logger.error(f"Database error: {e}")
    raise
```

### 2.2 前端代码规范 (opc-ui)

#### Vue3 + Composition API 规范

```vue
<!--
组件名: ComponentName
功能: 组件功能描述
作者: 开发者名称
创建日期: YYYY-MM-DD

API文档: 链接到COMPONENT.md
-->

<script setup>
/**
 * 员工卡片组件
 * 
 * @example
 * <EmployeeCard 
 *   :employee="employeeData" 
 *   @click="handleClick" 
 * />
 */
import { ref, computed, onMounted } from 'vue'
import { useEmployeeStore } from '@/stores/employee'

// Props 定义
const props = defineProps({
  employee: {
    type: Object,
    required: true,
    validator: (value) => value.id && value.name
  },
  showBudget: {
    type: Boolean,
    default: true
  }
})

// Emits 定义
const emit = defineEmits(['click', 'update'])

// 组合式函数 (命名: useXXX)
const employeeStore = useEmployeeStore()

// 响应式状态
const isLoading = ref(false)
const errorMessage = ref('')

// 计算属性
const displayName = computed(() => {
  return props.employee.name || '未命名'
})

// 方法
const handleClick = () => {
  emit('click', props.employee.id)
}

// 生命周期
onMounted(() => {
  console.log('EmployeeCard mounted:', props.employee.id)
})
</script>
```

#### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 组件名 | PascalCase | `EmployeeCard.vue`, `TaskList.vue` |
| 组合式函数 | camelCase, use前缀 | `useEmployee()`, `useTask()` |
| Props | camelCase | `employeeId`, `isLoading` |
| 事件 | kebab-case | `@employee-click`, `@task-update` |
| Store ID | camelCase | `useEmployeeStore`, `useTaskStore` |
| 路由名 | kebab-case | `employee-detail`, `task-list` |

#### i18n 规范

所有用户可见文本必须使用 i18n：

```vue
<template>
  <div>
    <h1>{{ $t('employee.title') }}</h1>
    <p>{{ $t('employee.description', { count: 5 }) }}</p>
    <button>{{ $t('common.confirm') }}</button>
  </div>
</template>
```

```javascript
// src/i18n/locales/zh-CN.js
export default {
  employee: {
    title: '员工管理',
    description: '共 {count} 名员工'
  },
  common: {
    confirm: '确认',
    cancel: '取消'
  }
}
```

---

## 3. 修改代码流程

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 阅读相关模块文档                                          │
│    - README.md                                              │
│    - ARCHITECTURE.md                                        │
│    - API.md                                                 │
└───────────────────────┬─────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. 理解现有代码                                              │
│    - 运行现有测试确保通过                                    │
│    - 阅读相关代码文件                                        │
└───────────────────────┬─────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. 修改代码 (遵循规范)                                       │
│    - 添加类型注解                                            │
│    - 添加必要的注释                                          │
│    - 保持代码简洁                                            │
└───────────────────────┬─────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. 添加/更新测试                                             │
│    - 单元测试覆盖率 ≥70%                                     │
│    - 集成测试覆盖接口                                        │
└───────────────────────┬─────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. 更新文档                                                  │
│    - 如有接口变更 → 更新 API.md                             │
│    - 如有架构变更 → 更新 ARCHITECTURE.md                    │
│    - Bug修复 → 更新 CHANGELOG.md                            │
└───────────────────────┬─────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. 验证                                                      │
│    - 运行模块独立测试 → 全部通过                            │
│    - 代码检查 (ruff/mypy/eslint) → 无错误                   │
└───────────────────────┬─────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. 提交代码                                                  │
│    - 写清晰的 commit message                                │
│    - 关联相关 issue                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. 文档更新规范

### 4.1 什么情况下必须更新文档

| 修改类型 | 必须更新的文档 | 位置 |
|---------|---------------|------|
| 新增API | API.md | 模块根目录 |
| 修改接口参数 | API.md + CHANGELOG.md | 模块 + 项目根目录 |
| 新增数据表 | ARCHITECTURE.md | 模块内 |
| 新增组件 | COMPONENT.md | opc-ui根目录 |
| 新增Hook | ARCHITECTURE.md | opc-ui根目录 |
| Bug修复 | CHANGELOG.md | 项目根目录 |
| 破坏性变更 | API.md + CHANGELOG.md + MIGRATION.md | 模块 + 项目根目录 |
| 性能优化 | CHANGELOG.md | 项目根目录 |
| 重构代码 | ARCHITECTURE.md (如架构变化) | 模块内 |

### 4.2 Commit Message 规范

```
类型(范围): 简短描述

详细说明（可选）

关联: #issue编号
```

**类型:**
- `feat`: 新功能
- `fix`: Bug修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具

**示例:**
```
feat(opc-database): 添加员工预算历史记录

- 新增 BudgetHistory 模型
- 在 EmployeeRepository 添加 get_budget_history 方法
- 添加相关单元测试

关联: #123
```

---

## 5. 测试要求

### 5.1 每个模块的测试要求

#### Python模块 (database/openclaw/core)

```bash
# 在每个模块根目录下运行
cd packages/opc-database

# 运行所有测试
pytest tests/

# 仅单元测试
pytest tests/unit/

# 仅集成测试
pytest tests/integration/

# 生成覆盖率报告
pytest --cov=src --cov-report=html tests/
```

**要求:**
- 单元测试覆盖率 ≥70%
- 所有测试必须通过
- 集成测试覆盖所有对外接口
- 使用 Mock 隔离外部依赖

#### 前端模块 (opc-ui)

```bash
cd packages/opc-ui

# 运行单元测试
npm run test:unit

# 运行组件测试
npm run test:component

# 运行e2e测试
npm run test:e2e
```

**要求:**
- 组件测试覆盖所有Props和Events
- 关键逻辑单元测试
- e2e测试覆盖主要用户流程

### 5.2 测试文件命名

| 类型 | 命名规范 | 示例 |
|------|---------|------|
| 单元测试 | `test_*.py` 或 `*.test.js` | `test_employee_repo.py` |
| 集成测试 | `test_integration_*.py` | `test_integration_api.py` |
| e2e测试 | `*.spec.js` | `dashboard.spec.js` |

### 5.3 Mock规范

**Python Mock:**

```python
# tests/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_db_session():
    """Mock数据库会话"""
    session = AsyncMock()
    return session

@pytest.fixture
def mock_openclaw_client():
    """Mock OpenClaw客户端"""
    client = MagicMock()
    client.send_message = AsyncMock(return_value={"status": "ok"})
    return client
```

**JavaScript Mock:**

```javascript
// tests/mocks/api.js
import { vi } from 'vitest'

export const mockEmployeeApi = {
  getEmployees: vi.fn(() => Promise.resolve({ data: [] })),
  createEmployee: vi.fn(() => Promise.resolve({ data: {} }))
}
```

---

## 6. 代码审查清单

提交PR前自检:

- [ ] 已阅读相关模块文档
- [ ] 代码符合命名规范
- [ ] 已添加类型注解
- [ ] 已添加/更新测试
- [ ] 测试覆盖率 ≥70%
- [ ] 所有测试通过
- [ ] 已更新相关文档
- [ ] Commit message 符合规范
- [ ] 无调试代码 (console.log, print)
- [ ] 无敏感信息泄露

---

## 7. 联系方式

如有问题，请:
1. 先查阅相关模块的文档
2. 查看 `archive/` 中的旧版本实现参考
3. 在 Issue 中提问

---

**记住: 写文档和写代码同等重要！**
