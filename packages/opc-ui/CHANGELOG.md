# opc-ui 变更日志

所有 opc-ui 模块的变更记录。

## [0.4.2] - 2026-03-25

### Workflow UI

- **WorkflowsView** - 工作流列表
  - 显示所有工作流
  - 状态可视化
  - 进度条显示

- **WorkflowCreateView** - 创建工作流
  - 可视化步骤配置
  - 员工选择
  - 预算估算

- **WorkflowDetailView** - 工作流详情
  - 流程图展示
  - 实时状态更新
  - 步骤详情

### 模板系统 UI (P2)

- **TemplateMarketView** - 模板市场
  - 模板浏览和搜索
  - 评分和评论
  - Fork 功能
  - 从模板创建工作流

- **WorkflowTimelineView** - 执行时间线
  - 可视化时间线
  - 步骤详情
  - 事件过滤

- **WorkflowAnalyticsView** - 分析看板
  - 统计图表 (Chart.js)
  - 趋势分析
  - 员工效率排名

### Store 扩展

- **templateStore** - 模板状态管理
- **analyticsStore** - 分析数据管理

---

## [0.4.1] - 2026-03-25

### 任务管理增强

- **TaskCreateModal 组件**
  - 新增任务创建弹窗
  - 支持选择员工、输入标题和描述
  - 创建后自动分配任务

- **任务列表优化**
  - 自动刷新任务状态
  - 显示实际成本 (OC币)
  - 状态标签可视化

- **轮询机制**
  - 自动轮询任务状态 (5秒间隔)
  - 任务完成后停止轮询
  - Toast 通知任务完成

### 修复

- 单位显示：tokens → OC币
- 时间戳格式：添加 Z 后缀，正确解析 UTC
- 员工状态实时显示

### 测试

- 35 个单元测试全部通过
  - stores/auth.spec.js (5)
  - stores/employees.spec.js (12)
  - composables/useStatus.spec.js (9)
  - utils/api.spec.js (9)

---

## [0.4.0] - 2026-03-24

### 新增

- 初始化模块
- Vue 3 + Vite 项目结构
- 完整的路由配置
- Pinia 状态管理
- Vue I18n 国际化 (zh-CN/en-US)

### 页面

- **Login**: API Key 登录
- **Dashboard**: 数据概览统计
- **Employees**: 员工列表/详情
- **Tasks**: 任务列表/详情
- **Budget**: 预算管理
- **Reports**: 绩效报表
- **Settings**: 设置

### 组件

- AppHeader: 顶部导航 + API Key 输入
- AppSidebar: 侧边栏导航

### 样式

- CSS Variables 主题系统
- 暗黑主题（默认）
- 响应式布局
