# Contributing to OpenClaw OPC

感谢您对 OpenClaw OPC 的兴趣！我们欢迎各种形式的贡献。

---

## 🚀 如何贡献

### 报告 Bug

如果您发现了 Bug，请通过 GitHub Issues 报告：

1. 先搜索是否已有相关 Issue
2. 如果没有，创建新 Issue
3. 使用 Bug 报告模板
4. 提供详细的信息：
   - 复现步骤
   - 期望行为 vs 实际行为
   - 环境信息（OS、Python版本等）
   - 相关日志

### 提交功能请求

有新功能的想法？欢迎提交：

1. 描述功能的使用场景
2. 说明为什么这个功能有用
3. 如果可能，提供实现思路

### 提交代码

#### 开发环境设置

```bash
# 1. Fork 仓库并克隆
git clone https://github.com/YOUR_USERNAME/openclaw-opc.git
cd openclaw-opc

# 2. 创建虚拟环境
cd backend
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 安装开发依赖
pip install pytest pytest-asyncio black flake8 mypy

# 5. 启动服务
python3 -m uvicorn src.main:app --reload
```

#### 代码规范

- **Python**: 遵循 PEP 8
- **格式化**: 使用 `black` 自动格式化
- **类型检查**: 使用 `mypy` 进行类型检查
- **导入排序**: 使用 `isort`

```bash
# 格式化代码
black backend/src

# 类型检查
mypy backend/src

# 运行测试
pytest backend/tests
```

#### 提交规范

提交信息格式：

```
<type>(<scope>): <subject>

<body>

<footer>
```

**类型 (type)**:
- `feat`: 新功能
- `fix`: Bug修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具相关

**示例**:
```
feat(pixel-office): add personalized avatar system

- Add avatar_svg field to Agent model
- Integrate Vivago AI for avatar generation
- Update pixel-office.html to display custom avatars

Closes #123
```

#### Pull Request 流程

1. **创建分支**:
   ```bash
   git checkout -b feature/your-feature-name
   # 或
   git checkout -b fix/bug-description
   ```

2. **提交更改**:
   ```bash
   git add .
   git commit -m "feat: your feature description"
   ```

3. **推送到 Fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

4. **创建 PR**:
   - 在 GitHub 上创建 Pull Request
   - 填写 PR 模板
   - 关联相关 Issue

5. **代码审查**:
   - 等待维护者审查
   - 根据反馈修改
   - CI 通过后合并

---

## 📁 项目结构

```
openclaw-opc/
├── backend/           # FastAPI Core Service
│   ├── src/
│   │   ├── models/    # 数据库模型
│   │   ├── routers/   # API路由
│   │   ├── services/  # 业务逻辑
│   │   └── utils/     # 工具函数
│   └── tests/         # 测试
├── web/               # 前端页面
├── docs/              # 文档
├── skill/             # OPC Bridge Skill
└── docker-compose.yml # Docker配置
```

---

## 🧪 测试

### 运行测试

```bash
cd backend
pytest
```

### 测试覆盖

- 单元测试: `tests/unit/`
- 集成测试: `tests/integration/`
- E2E测试: `tests/e2e/`

### 添加测试

为新功能添加测试：

```python
# tests/test_your_feature.py
def test_your_feature():
    """Test description."""
    # Arrange
    input_data = {...}
    
    # Act
    result = your_function(input_data)
    
    # Assert
    assert result == expected_output
```

---

## 📝 文档

文档位于 `docs/` 目录：

- `README.md` - 项目介绍
- `ROADMAP.md` - 开发路线图
- `PROJECT_REVIEW.md` - 项目Review
- `TECHNICAL.md` - 技术方案

更新代码时，请同步更新相关文档。

---

## 💬 交流

- **GitHub Issues**: Bug报告、功能请求
- **GitHub Discussions**: 一般讨论、问答
- **Discord**: 实时交流（如有）

---

## 🏆 贡献者

感谢所有贡献者！

<!-- 贡献者列表将由 GitHub Actions 自动生成 -->

---

## 📜 行为准则

- 尊重他人，友善交流
- 接受建设性批评
- 关注社区最佳利益

---

## ❓ 常见问题

**Q: 我需要先开 Issue 才能提 PR 吗？**  
A: 小的修复（如拼写错误）可以直接提 PR。大的功能建议先开 Issue 讨论。

**Q: 我的 PR 为什么被拒绝了？**  
A: 可能是因为：
- 与项目方向不符
- 代码质量不达标
- 缺少测试
- 文档不完整

**Q: 如何成为维护者？**  
A: 持续贡献代码、帮助审查 PR、参与社区讨论，我们会主动邀请。

---

*感谢您对 OpenClaw OPC 的贡献！*
