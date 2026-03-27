<template>
  <div class="view">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1>工作流</h1>
      <!-- v0.4.6: 改为打开弹窗 -->
      <button class="btn btn-primary" @click="showCreateModal = true">
        <span class="icon">+</span> 创建工作流
      </button>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">{{ workflowCount }}</div>
        <div class="stat-label">总工作流</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ runningCount }}</div>
        <div class="stat-label">进行中</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ completedCount }}</div>
        <div class="stat-label">已完成</div>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>

    <!-- 空状态 -->
    <div v-else-if="workflows.length === 0" class="empty-state">
      <div class="empty-icon">🔄</div>
      <p>暂无工作流，点击右上角创建</p>
    </div>

    <!-- 工作流列表 -->
    <div v-else class="workflow-list">
      <div
        v-for="workflow in workflows"
        :key="workflow.workflow_id"
        class="workflow-card"
        @click="viewWorkflow(workflow.workflow_id)"
      >
        <div class="workflow-header">
          <h3 class="workflow-name">{{ workflow.name }}</h3>
          <span :class="['badge', getStatusClass(workflow.status)]">
            {{ getStatusLabel(workflow.status) }}
          </span>
        </div>

        <div class="workflow-progress">
          <div class="progress-bar">
            <div
              class="progress-fill"
              :style="{ width: `${calculateProgress(workflow)}%` }"
            ></div>
          </div>
          <span class="progress-text">
            {{ workflow.completed_steps || 0 }} / {{ workflow.total_steps }} 步骤
          </span>
        </div>

        <div class="workflow-meta">
          <span class="meta-item">
            <span class="icon">📋</span>
            {{ workflow.task_count }} 个任务
          </span>
          <span class="meta-item">
            <span class="icon">📅</span>
            {{ formatDate(workflow.created_at) }}
          </span>
        </div>
      </div>
    </div>

    <!-- v0.4.6: 工作流创建弹窗 (放在最后，不影响条件渲染) -->
    <WorkflowCreateModal
      v-if="showCreateModal"
      @close="showCreateModal = false"
      @created="handleWorkflowCreated"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useWorkflowStore } from '@/stores/workflows'
import { formatDate } from '@/utils/api'
import WorkflowCreateModal from '@/components/workflows/WorkflowCreateModal.vue'

const router = useRouter()
const workflowStore = useWorkflowStore()
const { workflows, loading, workflowCount, runningCount, completedCount } = storeToRefs(workflowStore)

// v0.4.6: 弹窗状态
const showCreateModal = ref(false)

function viewWorkflow(id) {
  router.push(`/workflows/${id}`)
}

function handleWorkflowCreated(result) {
  // 可选：显示成功提示或跳转到详情页
  // router.push(`/workflows/${result.workflow_id}`)
}

function getStatusClass(status) {
  const map = {
    running: 'badge-warning',
    completed: 'badge-success',
    failed: 'badge-danger',
    pending: 'badge-info',
  }
  return map[status] || 'badge-info'
}

function getStatusLabel(status) {
  const map = {
    running: '进行中',
    completed: '已完成',
    failed: '失败',
    pending: '等待中',
  }
  return map[status] || status
}

function calculateProgress(workflow) {
  if (!workflow.total_steps) return 0
  const completed = workflow.completed_steps || 0
  return Math.round((completed / workflow.total_steps) * 100)
}

onMounted(() => {
  workflowStore.fetchWorkflows()
})
</script>

<style scoped>
.view {
  padding: 24px;
  min-height: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--space-md);
  margin-bottom: var(--space-lg);
}

.stat-card {
  background: var(--bg-secondary);
  padding: var(--space-md);
  border-radius: var(--radius-md);
  text-align: center;
}

.stat-value {
  font-size: 2rem;
  font-weight: bold;
  color: var(--primary);
}

.stat-label {
  font-size: 0.875rem;
  color: var(--text-muted);
  margin-top: var(--space-xs);
}

.workflow-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.workflow-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: var(--space-md);
  cursor: pointer;
  transition: all 0.2s ease;
}

.workflow-card:hover {
  border-color: var(--primary);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.workflow-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-sm);
}

.workflow-name {
  font-size: 1.125rem;
  font-weight: 600;
  margin: 0;
}

.workflow-progress {
  margin-bottom: var(--space-sm);
}

.progress-bar {
  height: 8px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  overflow: hidden;
  margin-bottom: var(--space-xs);
}

.progress-fill {
  height: 100%;
  background: var(--primary);
  border-radius: var(--radius-sm);
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 0.875rem;
  color: var(--text-muted);
}

.workflow-meta {
  display: flex;
  gap: var(--space-md);
  font-size: 0.875rem;
  color: var(--text-muted);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
}

.empty-state {
  text-align: center;
  padding: var(--space-xl);
  color: var(--text-muted);
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: var(--space-md);
}
</style>
