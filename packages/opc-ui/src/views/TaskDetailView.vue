<template>
  <div class="view">
    <div class="page-header">
      <router-link to="/tasks" class="back-link">← {{ $t('common.back') }}</router-link>
      <h1>{{ task?.title || '任务详情' }}</h1>
    </div>

    <div v-if="loading" class="loading">
      <div class="spinner"></div>
    </div>

    <div v-else-if="task" class="task-detail">
      <div class="detail-card">
        <div class="task-header">
          <h2>{{ task.title }}</h2>
          <span :class="['badge', getStatusClass(task.status)]">
            {{ $t(`tasks.status.${task.status}`) }}
          </span>
        </div>

        <p class="task-description">{{ task.description || '无描述' }}</p>

        <div class="detail-grid">
          <div class="detail-item">
            <label>优先级</label>
            <span :class="['badge', getPriorityClass(task.priority)]">
              {{ $t(`tasks.priority.${task.priority}`) }}
            </span>
          </div>
          <div class="detail-item">
            <label>分配</label>
            <value>{{ task.assigned_to || '未分配' }}</value>
          </div>
          <div class="detail-item">
            <label>预估成本</label>
            <value>¥{{ task.estimated_cost }}</value>
          </div>
          <div class="detail-item">
            <label>实际成本</label>
            <value>¥{{ task.actual_cost || 0 }}</value>
          </div>
        </div>

        <div v-if="task.result" class="result-section">
          <h3>执行结果</h3>
          <p>{{ task.result }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useTaskStore } from '@/stores/tasks'

const route = useRoute()
const taskStore = useTaskStore()

const task = computed(() => taskStore.currentTask)
const loading = computed(() => taskStore.loading)

function getStatusClass(status) {
  const map = {
    pending: 'badge-info',
    assigned: 'badge-warning',
    in_progress: 'badge-warning',
    completed: 'badge-success',
    failed: 'badge-danger',
  }
  return map[status] || 'badge-info'
}

function getPriorityClass(priority) {
  const map = {
    low: 'badge-info',
    normal: 'badge-success',
    high: 'badge-danger',
  }
  return map[priority] || 'badge-info'
}

onMounted(() => {
  taskStore.fetchTask(route.params.id)
})
</script>

<style scoped>
.page-header {
  margin-bottom: 24px;
}

.back-link {
  display: inline-block;
  margin-bottom: 16px;
  color: var(--text-secondary);
  text-decoration: none;
}

.back-link:hover {
  color: var(--color-primary);
}

.task-detail {
  max-width: 800px;
}

.detail-card {
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  padding: 24px;
  border: 1px solid var(--border-color);
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.task-header h2 {
  font-size: 20px;
}

.task-description {
  color: var(--text-secondary);
  margin-bottom: 24px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--border-color);
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 24px;
  margin-bottom: 24px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-item label {
  font-size: 12px;
  color: var(--text-secondary);
  text-transform: uppercase;
}

.detail-item value {
  font-size: 16px;
  font-weight: 500;
}

.result-section {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid var(--border-color);
}

.result-section h3 {
  font-size: 16px;
  margin-bottom: 12px;
}

.result-section p {
  color: var(--text-secondary);
  white-space: pre-wrap;
}
</style>
