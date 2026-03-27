# v0.4.6 子功能2: 前端界面改造

## 概述

将工作流创建界面从页面路由改为弹窗形式，与任务创建界面对齐，支持双模式（手动创建 + AI辅助创建）。

## 设计目标

1. **界面一致性** - 与 TaskCreateModal 保持相同的视觉风格和交互模式
2. **双模式支持** - 手动创建和AI辅助创建两种模式
3. **步骤手册配置** - 每步可折叠展开的手册配置区域
4. **实时预览** - AI辅助模式支持方案预览和应用

## 组件结构

```
WorkflowCreateModal.vue
├── 头部
│   ├── 标题: "创建工作流"
│   ├── 关闭按钮
│   └── 标签切换: 手动创建 / AI辅助
│
├── 手动创建模式 (manual)
│   ├── 工作流基本信息
│   │   ├── 名称输入
│   │   └── 描述输入
│   │
│   ├── 步骤列表
│   │   └── StepCard (可复用组件)
│   │       ├── 步骤标题
│   │       ├── 员工选择
│   │       ├── 预估成本
│   │       ├── 描述输入
│   │       └── 手册配置 (可折叠)
│   │           ├── manual_content (textarea)
│   │           ├── input_requirements (input)
│   │           └── output_deliverables (input)
│   │
│   ├── 添加步骤按钮
│   ├── 成本统计
│   └── 提交按钮
│
└── AI辅助模式 (assist)
    ├── 需求描述输入
    ├── 预算限制输入
    ├── 生成按钮
    ├── 加载状态
    ├── 方案预览面板
    │   ├── 工作流名称
    │   ├── 描述
    │   ├── 步骤列表预览
    │   └── 总预估成本
    └── 应用方案按钮
```

## 技术实现

### Props

```typescript
interface Props {
  visible: boolean;  // v-model 控制显示
}
```

### Emits

```typescript
interface Emits {
  (e: 'update:visible', value: boolean): void;
  (e: 'created', workflow: Workflow): void;
}
```

### State

```typescript
// 弹窗显示
const showModal = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val)
});

// 当前标签
const activeTab = ref<'manual' | 'assist'>('manual');

// 手动模式表单
const form = reactive({
  name: '',
  description: '',
  steps: []  // WorkflowStepFormItem[]
});

// AI辅助模式
const assistForm = reactive({
  description: '',
  budgetLimit: 1000
});

// AI生成结果
const workflowPlan = ref<WorkflowPlan | null>(null);
```

### 步骤表单结构

```typescript
interface WorkflowStepFormItem {
  employee_id: string;
  title: string;
  description: string;
  estimated_cost: number;
  // v0.4.6 新增
  manual_content: string;
  input_requirements: string;
  output_deliverables: string;
  // UI状态
  showManual: boolean;  // 控制手册区域展开/折叠
}
```

## 核心功能

### 1. 动态步骤管理

```typescript
// 添加步骤
const addStep = () => {
  if (form.steps.length >= 10) {
    showToast('最多10个步骤', 'warning');
    return;
  }
  form.steps.push({
    employee_id: '',
    title: `步骤 ${form.steps.length + 1}`,
    description: '',
    estimated_cost: 100,
    manual_content: '',
    input_requirements: '',
    output_deliverables: '',
    showManual: false
  });
};

// 删除步骤
const removeStep = (index: number) => {
  if (form.steps.length <= 2) {
    showToast('至少保留2个步骤', 'warning');
    return;
  }
  form.steps.splice(index, 1);
};
```

### 2. 手册配置区域

```vue
<!-- 可折叠的手册配置 -->
<div class="manual-section">
  <div class="manual-header" @click="step.showManual = !step.showManual">
    <span>📚 执行手册配置</span>
    <span class="toggle-icon">{{ step.showManual ? '▼' : '▶' }}</span>
  </div>
  
  <div v-show="step.showManual" class="manual-content">
    <div class="form-group">
      <label>执行手册 (Markdown)</label>
      <textarea 
        v-model="step.manual_content"
        placeholder="详细的执行步骤和注意事项..."
        rows="4"
      />
    </div>
    
    <div class="form-group">
      <label>输入要求</label>
      <input 
        v-model="step.input_requirements"
        placeholder="执行此步骤需要什么输入数据..."
      />
    </div>
    
    <div class="form-group">
      <label>输出交付物</label>
      <input 
        v-model="step.output_deliverables"
        placeholder="此步骤需要交付什么成果..."
      />
    </div>
  </div>
</div>
```

### 3. AI辅助创建

```typescript
// 调用API获取工作流方案
const generateWorkflow = async () => {
  loading.value = true;
  try {
    const response = await workflowStore.assistCreateWorkflow({
      description: assistForm.description,
      budget_limit: assistForm.budgetLimit
    });
    workflowPlan.value = response.workflow_plan;
  } catch (error) {
    showToast('生成失败', 'error');
  } finally {
    loading.value = false;
  }
};

// 应用方案到表单
const applyPlan = () => {
  if (!workflowPlan.value) return;
  
  form.name = workflowPlan.value.name;
  form.description = workflowPlan.value.description;
  form.steps = workflowPlan.value.steps.map(step => ({
    ...step,
    showManual: false  // 默认折叠手册区域
  }));
  
  // 切换到手动模式继续编辑
  activeTab.value = 'manual';
  showToast('方案已应用，可以继续编辑', 'success');
};
```

### 4. 提交创建

```typescript
const submitForm = async () => {
  // 验证
  if (!form.name.trim()) {
    showToast('请输入工作流名称', 'warning');
    return;
  }
  if (form.steps.some(s => !s.employee_id || !s.title)) {
    showToast('请完善所有步骤信息', 'warning');
    return;
  }
  
  try {
    const response = await workflowStore.createWorkflow({
      name: form.name,
      description: form.description,
      steps: form.steps.map(s => ({
        employee_id: s.employee_id,
        title: s.title,
        description: s.description,
        estimated_cost: s.estimated_cost,
        manual_content: s.manual_content,
        input_requirements: s.input_requirements,
        output_deliverables: s.output_deliverables
      })),
      initial_input: {}
    });
    
    showToast('工作流创建成功', 'success');
    emit('created', response);
    showModal.value = false;
    resetForm();
  } catch (error) {
    showToast('创建失败', 'error');
  }
};
```

## WorkflowsView 集成

```vue
<template>
  <div class="workflows-view">
    <!-- 工具栏 -->
    <div class="toolbar">
      <h1>工作流管理</h1>
      <button class="btn-primary" @click="openCreateModal">
        + 创建工作流
      </button>
    </div>
    
    <!-- 工作流列表 -->
    <WorkflowList />
    
    <!-- 创建弹窗 -->
    <WorkflowCreateModal
      v-model:visible="showCreateModal"
      @created="onWorkflowCreated"
    />
  </div>
</template>

<script setup>
const showCreateModal = ref(false);

const openCreateModal = () => {
  showCreateModal.value = true;
};

const onWorkflowCreated = (workflow) => {
  // 刷新列表
  workflowStore.fetchWorkflows();
};
</script>
```

## API 集成

### Store 方法

```typescript
// workflowStore.ts

// AI辅助创建工作流
async assistCreateWorkflow(params: {
  description: string;
  budget_limit: number;
}) {
  const response = await api.post('/workflows/assist', params);
  return response.data;
}

// 创建工作流
async createWorkflow(data: {
  name: string;
  description: string;
  steps: WorkflowStep[];
  initial_input: object;
}) {
  const response = await api.post('/workflows', data);
  return response.data;
}
```

## 样式规范

```css
/* 与 TaskCreateModal 保持一致 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-container {
  background: var(--surface-color);
  border-radius: var(--radius-lg);
  width: 90%;
  max-width: 800px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-body {
  padding: var(--spacing-lg);
  overflow-y: auto;
  flex: 1;
}

/* 步骤卡片 */
.step-card {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

/* 手册区域 */
.manual-section {
  margin-top: var(--spacing-md);
  border-top: 1px solid var(--border-color);
  padding-top: var(--spacing-md);
}

.manual-header {
  display: flex;
  justify-content: space-between;
  cursor: pointer;
  color: var(--primary-color);
}
```

## 文件位置

```
packages/opc-ui/src/
├── components/workflows/
│   └── WorkflowCreateModal.vue    # 新增
├── views/
│   └── WorkflowsView.vue          # 修改
└── stores/
    └── workflow.ts                # 已有，调用assistCreateWorkflow
```

## 测试

### 功能验证清单

| 功能 | 验证点 | 状态 |
|------|--------|------|
| 弹窗显示/隐藏 | 点击创建按钮打开，点击关闭/X隐藏 | ✅ |
| 标签切换 | 手动/AI辅助标签正常切换 | ✅ |
| 动态步骤 | 添加/删除步骤，2-10步限制 | ✅ |
| 手册配置 | 折叠展开，字段输入 | ✅ |
| AI辅助 | 生成方案，预览，应用 | ✅ |
| 表单提交 | 验证，提交，成功回调 | ✅ |

### 运行测试

```bash
# 前端构建测试
cd packages/opc-ui
npm run build

# 类型检查
npm run type-check
```

## 注意事项

1. **向后兼容** - 不传手册字段时，后端不会创建手册文件
2. **员工选择** - 从 employeeStore 获取员工列表
3. **成本统计** - 实时计算所有步骤预估成本总和
4. **错误处理** - 表单验证失败时显示友好提示

---

*文档版本: v0.4.6*  
*最后更新: 2026-03-28*
