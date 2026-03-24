<template>
  <div class="view">
    <div class="page-header">
      <h1>{{ $t('tasks.title') }}</h1>
      <button class="btn btn-primary" @click="showCreateModal = true">
        {{ $t('tasks.create') }}
      </button>
    </div>
    
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
    </div>
    
    <div v-else-if="tasks.length === 0" class="empty-state">
      <div class="empty-state-icon">📋</div>
      <p>{{ $t('common.noData') }}</p>
    </div>
    
    <div v-else class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>标题</th>
            <th>状态</th>
            <th>优先级</th>
            <th>分配</th>
            <th>成本</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="task in tasks" :key="task.id">
            <td>
              <router-link :to="`/tasks/${task.id}`" class="task-link">
                {{ task.title }}
              </router-link>
            </td>
            <td>
              <span :class="['badge', getStatusClass(task.status)]">
                {{ $t(`tasks.status.${task.status}`) }}
              </span>
            </td>
            <td>
              <span :class="['badge', getPriorityClass(task.priority)]">
                {{ $t(`tasks.priority.${task.priority}`) }}
              </span>
            </td>
            <td>{{ task.assigned_to || '-' }}</td>
            <td>
              ¥{{ task.actual_cost?.toFixed(2) || '0.00' }} /
              ¥{{ task.estimated_cost?.toFixed(2) }}
            </td>
            <td>
              <button
                v-if="task.status === 'pending'"
                class="btn btn-sm btn-primary"
                @click="assignTask(task)"
              >
                {{ $t('tasks.assign') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useTaskStore } from '@/stores/tasks'

const taskStore = useTaskStore()
const tasks = computed(() => taskStore.tasks)
const loading = computed(() => taskStore.loading)

const showCreateModal = ref(false)

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

function assignTask(task) {
  // TODO: 打开分配弹窗
}

onMounted(() => {
  taskStore.fetchTasks()
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.task-link {
  color: var(--text-primary);
  text-decoration: none;
}

.task-link:hover {
  color: var(--color-primary);
}
</style>
