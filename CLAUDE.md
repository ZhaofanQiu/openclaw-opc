# OpenClaw OPC - AI Agent 开发规范

> 本文件适用于所有通过 Claude Code / Kimi / 其他 AI Agent 参与 OpenClaw OPC 开发的会话。
> **规则优先于任何单次任务的目标。** 如果任务指令与本文档冲突，必须遵循本文档。

---

## 一、开发前必读（Non-negotiable）

在任何编码工作开始之前，AI Agent 必须：

1. **阅读根目录 `README.md`** —— 了解项目的宏观定位、技术栈、当前功能状态。
2. **阅读 `/docs/ARCHITECTURE.md`** —— 了解系统架构、模块边界、数据流。如果该文件与代码明显不符（例如声称 React 但实际 Vue），必须立即向用户报告，而不是基于错误假设继续开发。
3. **查看根目录 `VERSION` 文件** —— 确认当前目标版本号。
4. **查看 `packages/*/pyproject.toml` 和 `packages/opc-ui/package.json`** —— 确认依赖关系和版本一致性。
5. **查看最近一次 git commit message 和变更** —— 了解当前代码基线的状态。

**禁止**：在未阅读上述文档前，直接回答"我知道了"并开始修改代码。

---

## 二、新功能开发流程（Feature Development Lifecycle）

### 2.1 Phase 0: 范围冻结（Scoping）
- **明确功能的边界**：这个功能涉及哪些模块？（database / core / openclaw / ui）
- **明确接口契约**：新增哪些 API 端点？数据库模型有何变更？前后端交互的数据结构是什么？
- **评估是否需要 Plan Mode**：如果改动超过 2 个文件，或涉及架构决策，**必须进入 Plan Mode**，让用户先审批方案。

### 2.2 Phase 1: 测试先行（Test-First）
- 在写实现代码之前，先写失败的测试用例；或在同一 commit 中同时提交测试和实现。
- 测试必须放入正确的位置：
  - Python 后端测试 → `packages/<module>/tests/`
  - 前端测试 → `packages/opc-ui/src/**/__tests__/` 或组件同级 `.test.js`
  - **禁止**在根目录新建 `test_*.py` 临时脚本。

### 2.3 Phase 2: 分层实现（Layered Implementation）

严守以下模块边界：

| 模块 | 职责 | 红线 |
|------|------|------|
| `opc-database` | 数据库模型、Repository、迁移脚本 | **禁止**调用 HTTP 客户端、文件 I/O、subprocess |
| `opc-openclaw` | OpenClaw 集成、HTTP/CLI 客户端、Agent 生命周期 | **禁止**直接依赖 FastAPI 或 SQLAlchemy 的 web 层 |
| `opc-core` | FastAPI 路由、业务 Service、事务编排 | API Router 禁止直接做文件 I/O 或 subprocess；必须委托给下层 |
| `opc-ui` | Vue 3 组件、Pinia Store、视图层 | **禁止**直接调用 OpenClaw CLI 或后端文件系统 |

**依赖方向定律**：
```
opc-ui → opc-core (via HTTP API)
opc-core → opc-database, opc-openclaw
opc-openclaw → (独立，可被 core 调用)
opc-database → (底层，不依赖其他包)
```
**禁止循环依赖**。如果预感会出现循环导入，使用事件总线（EventBus）或接口抽象，而不是延迟导入 hack。

### 2.4 Phase 3: 文档同步（Documentation Sync）
- 任何 API 变更必须更新对应模块的 `API.md`（`packages/opc-core/API.md`、`packages/opc-openclaw/API.md`、`packages/opc-database/API.md`）。
- 任何架构变更必须更新 `/docs/ARCHITECTURE.md`。
- 功能完成后，必须向用户说明是否有文档需要同步，并主动执行。

---

## 三、编码规范（Development Standards）

### 3.1 禁止硬编码路径
- **严禁**使用 `sys.path.insert(0, '/root/.openclaw/workspace/...')`。
- **严禁**在代码中硬编码绝对路径指向 monorepo 内部文件（如 `__file__.parent.parent.parent.parent / "opc-ui" / "dist"`）。
- 正确做法：使用环境变量、配置文件、或 Python 包内的相对导入。

### 3.2 版本号规范
- 单一版本源：**根目录 `VERSION` 文件**。
- 每完成一个功能迭代（release），必须同步以下文件中的版本号：
  - `VERSION`
  - `packages/opc-core/pyproject.toml`
  - `packages/opc-core/src/opc_core/__init__.py`
  - `packages/opc-database/pyproject.toml`
  - `packages/opc-database/src/opc_database/__init__.py`
  - `packages/opc-openclaw/pyproject.toml`
  - `packages/opc-openclaw/src/opc_openclaw/__init__.py`
  - `packages/opc-ui/package.json`
  - `README.md` 中的版本声明
- **版本号不一致是 CI 失败项**。

### 3.3 ORM 与模型规范
- 所有 SQLAlchemy 模型必须使用 SQLAlchemy 2.0 的声明式风格：
  ```python
  class MyModel(Base):
      __tablename__ = "my_model"
      id: Mapped[str] = mapped_column(String(32), primary_key=True)
  ```
- **禁止**混合使用旧式 `Column(...)` 风格（除非在遗留迁移脚本中）。

### 3.4 API 端点规范
- 废弃的 API 必须**从 `api/__init__.py` 中解绑并删除文件**，而不是保留 `deprecated=True` 继续挂载。
- 新增路由必须注册在 `packages/opc-core/src/opc_core/api/` 下，并在 `api/__init__.py` 中显式引入。
- 所有外部接口必须返回一致的 JSON 结构，避免 raw string 或空列表的歧义行为。

### 3.5 不要留 stub
- **禁止**提交明知不可用的函数体（如直接 `return []`、`pass`、`# TODO: implement`）。
- 如果功能确实无法在本次完成：
  - 选项 A：不提交该函数/端点。
  - 选项 B：返回明确的 `501 Not Implemented` HTTP 状态码。

---

## 四、测试规范（Testing Standards）

### 4.1 测试位置
- Python 测试：**只准**放在 `packages/<module>/tests/` 目录下。
- 前端测试：**只准**放在 `packages/opc-ui/` 内的合理位置。
- **根目录禁止**出现任何新的 `test_*.py`、`test_e2e.sh`、`run_workflow_tests.sh` 等脚本。如发现有临时测试脚本，应将其迁移到正规测试目录。

### 4.2 测试分类
- `unit/` — 不依赖数据库/外部服务的纯逻辑测试。
- `integration/` — 依赖数据库或跨模块集成的测试。
- `api/` — 使用 `TestClient` 测试 FastAPI 端点的测试。
- `e2e/` — 端到端流程测试（尽量少而精）。

### 4.3 测试可移植性
- 测试不能依赖特定机器上的文件路径或环境。
- 数据库测试应使用 `pytest-asyncio` + 内存 `aiosqlite` 或测试专用 schema。

---

## 五、文档维护规范（Documentation Standards）

### 5.1 文档层次结构
```
/docs/
  ├── INDEX.md           # 文档入口索引
  ├── ARCHITECTURE.md    # 系统架构（必须与代码一致）
  ├── DEVELOPMENT.md     # 本地开发 setup 指南
  └── DEPLOYMENT.md      # 部署指南

packages/
  ├── opc-core/API.md    # Core 模块 API 文档
  ├── opc-openclaw/API.md # OpenClaw 模块 API 文档
  └── opc-database/API.md # Database 模块 API 文档
```

### 5.2 禁止文档繁殖
- **禁止**为每个小版本新建独立的文档目录（如 `/docs/v0.4.5/`）。
- **禁止**在根目录堆积一次性报告文件（如 `P0_COMPLETION_REPORT.md`、`PLAN_v0.4.x.md`）。
- 计划/报告类内容应使用 Git commit message 和 Issue/PR 描述来记录，而不是新建 markdown 文件。

### 5.3 文档更新义务
- 修改了 API → 更新 `API.md`
- 修改了架构/模块边界 → 更新 `ARCHITECTURE.md`
- 修改了本地启动方式 → 更新 `DEVELOPMENT.md`
- 发布了新版本 → 更新 `README.md` 和 `CHANGELOG.md`

---

## 六、版本控制规范（Git & Repository）

### 6.1 禁止将 archive 当垃圾桶
- Git 本身就是 archive。旧的代码版本如果需要找回，可以通过 `git checkout <commit>` 或 tag 获取。
- **禁止**手动创建 `archive/`、`backup/`、`old/` 目录来保留"以防万一"的旧代码。
- 如果代码已确定废弃，直接删除。

### 6.2 不要提交生成文件/大文件
- 必须确保 `.gitignore` 包含：`node_modules/`、`dist/`、`.venv/`、`venv/`、`__pycache__/`、`.pytest_cache/`、`.DS_Store`、`.env`、以及任何大于 1MB 的 PNG/JPG/二进制文件（除非它们是产品必需的静态资源）。
- **禁止**提交虚拟环境、编译后的 `.so`/`.dll`、打包后的 `index.html`。

### 6.3 Commit Message
- 使用语义化 commit message：
  - `feat:` 新功能
  - `fix:` 修复
  - `docs:` 文档变更
  - `refactor:` 重构（无功能变更）
  - `test:` 测试相关
  - `chore:` 构建/工具/杂项
- **禁止**无意义的 commit message（如 `"update"`、`"fix"`、`"123"`）。

---

## 七、每次 AI 会话结束时的 Checklist

在告知用户"任务完成"之前，AI Agent 必须执行以下自检：

- [ ] 是否有新的根目录临时文件/脚本？如果有，删除或迁移。
- [ ] `pyproject.toml` / `package.json` 的版本号是否与 `VERSION` 文件一致？
- [ ] 是否有硬编码的绝对路径（`/root/...`）被引入？
- [ ] 新增/修改的 API 是否已在对应模块的 `API.md` 中体现？
- [ ] 是否存在 `TODO` / `FIXME` / `return []` 等未完成的 stub？
- [ ] 测试是否通过？（运行 `pytest` 或 `npm run test`）
- [ ] `git diff` 中是否包含不应提交的生成文件/大文件？
- [ ] 是否确认没有破坏已有功能？（至少本地 smoke test 通过）

**如果任何一项未通过，必须向用户说明，而不是声称"已完成"。**

---

## 八、禁止事项（Red Lines）

以下行为一经发现，必须立即停止并回滚：

1. **在 API Router 中直接调用 `subprocess.run` 或操作文件系统。**
2. **新建根目录测试脚本（`test_*.py`、`test_*.sh`）而不是放入 `packages/*/tests/`。**
3. **提交明知不可用的函数 stub 到生产分支。**
4. **版本号不一致就宣称发布完成。**
5. **在 `/docs/` 中新建版本隔离的子目录来存放文档副本。**
6. **将废弃代码放入 `archive/` 而非直接删除。**
7. **未查看 `ARCHITECTURE.md` 和 `README.md` 就开始架构级修改。**

---

## 九、向用户汇报的格式

每次任务完成后，AI Agent 的汇报应包含：

1. **改动摘要**：修改了哪些文件，核心变更是什么。
2. **架构影响**：是否跨越了模块边界？是否有新增依赖？
3. **测试状态**：运行了哪些测试，结果如何。
4. **文档同步**：更新了哪些文档，或有待用户确认补充的文档项。
5. **遗留问题**：是否有 TODO、未处理的 edge case、或需要后续跟进的点。

---

## 十、规范演进

本文档本身也是项目的一部分。如果用户或开发者发现规范有漏洞，应直接修改 `CLAUDE.md` 并同步版本号。每次修改规范后，应在第一条 summary 中说明变更内容。

---

*规范版本: v0.1.0*
*生效日期: 2026-04-03*
