<template>
  <div class="view">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1>{{ $t('tasks.title') }}</h1>
      <button class="btn btn-primary" @click="showCreateModal = true">
        <span class="icon">+</span> {{ $t('tasks.create') }}
      </button>
    </div>
    
    <!-- 执行中任务提示横幅 -->
    <div v-if="runningTasks.length > 0" class="running-banner">
      <span class="spinner-sm"></span>
      <span>{{ runningTasks.length }} 个任务正在执行中</span>
      <button class="btn-text" @click="scrollToRunning">查看</button>
    </div>
    
    <!-- 筛选器 -->
    <div class="filters">
      <div class="filter-group">
        <label>状态:</label>
        <select v-model="filterStatus" @change="handleFilter">
          <option value="">全部</option>
          <option value="pending">待分配</option>
          <option value="assigned">准备中</option>
          <option value="in_progress">执行中</option>
          <option value="completed">已完成</option>
          <option value="failed">失败</option>
          <option value="needs_review">需检查</option>
        </select>
      </div>
      
      <div class="filter-group">
        <label>员工:</label>
        <select v-model="filterEmployee" @change="handleFilter">
          <option value="">全部</option>
          <option v-for="emp in employees" :key="emp.id" :value="emp.id">
            {{ emp.name }}
          </option>
        </select>
      </div>
      
      <button v-if="hasFilter" class="btn-text" @click="clearFilter">清除筛选</button>
    </div>
    
    <!-- 加载状态 -->
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>
    
    <!-- 空状态 -->
    <div v-else-if="filteredTasks.length === 0" class="empty-state">
      <div class="empty-icon">📋</div>
      <p>{{ emptyMessage }}</p>
      <button v-if="hasFilter" class="btn btn-secondary" @click="clearFilter">
        清除筛选
      </button>
    </div>
    
    <!-- 任务列表 -->
    <div v-else class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>任务</th>
            <th>状态</th>
            <th>员工</th>
            <th>进度</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr 
            v-for="task in filteredTasks" 
            :key="task.id"
            :class="{ 'running-row': isRunning(task) }"
            :id="`task-${task.id}`"
          >
            <td>
              <router-link :to="`/tasks/${task.id}`" class="task-link">
                <span class="task-title">{{ task.title }}</span>
                <span v-if="task.description" class="task-desc">
                  {{ task.description }}
                </span>
              </router-link>
            </td>
            <td>
              <TaskStatusBadge :status="task.status" />
            </td>
            <td>
              <span v-if="task.assigned_to" class="employee-name">
                {{ getEmployeeName(task.assigned_to) }}
              </span>
              <span v-else class="text-muted">未分配</span>
            </td>
            <td>
              <TaskProgress 
                v-if="isRunning(task)" 
                :task="task" 
                :show-time="true"
              />
              <span v-else-if="task.status === 'completed'" class="completed-indicator">
                ✅ {{ formatDuration(task.started_at, task.completed_at) }}
              </span>
              <span v-else class="text-muted">-</span>
            </td>
            <td>
              <div class="actions">
                <button
                  v-if="task.status === 'pending'"
                  class="btn btn-sm btn-primary"
                  @click="openAssignModal(task)"
                >
                  分配
                </button>
                <button
                  v-if="['failed', 'needs_review'].includes(task.status)"
                  class="btn btn-sm btn-warning"
                  @click="retryTask(task)"
                >
                  重试
                </button>
                <button
                  v-if="isRunning(task)"
                  class="btn btn-sm btn-secondary"
                  @click="viewTask(task)"
                >
                  查看
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    
    <!-- 创建任务弹窗 -->
    <TaskCreateModal
      v-if="showCreateModal"
      :submitting="creating"
      @close="showCreateModal = false"
      @submit="handleCreateTask"
    />
    <TaskAssignModal
      v-if="showAssignModal"
      :task="selectedTask"
      @close="showAssignModal = false"
      @assigned="onTaskAssigned"
    />
    
    <!-- Toast 通知容器 -->
    <div class="toast-container">
      <div
        v-for="toast in notifications"
        :key="toast.id"
        :class="['toast', `toast-${toast.type}`]"
      >
        {{ toast.message }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTaskStore } from '@/stores/tasks'
import { useEmployeeStore } from '@/stores/employees'
import TaskStatusBadge from '@/components/tasks/TaskStatusBadge.vue'
import TaskProgress from '@/components/tasks/TaskProgress.vue'
import TaskAssignModal from '@/components/tasks/TaskAssignModal.vue'
import TaskCreateModal from '@/components/tasks/TaskCreateModal.vue'

const router = useRouter()
const taskStore = useTaskStore()
const employeeStore = useEmployeeStore()

// 状态
const showCreateModal = ref(false)
const showAssignModal = ref(false)
const selectedTask = ref(null)
const creating = ref(false)
const filterStatus = ref('')
const filterEmployee = ref('')

// 从 store 获取
const tasks = computed(() => taskStore.tasks)
const employees = computed(() => employeeStore.employees)
const loading = computed(() => taskStore.loading)
const notifications = computed(() => taskStore.notifications)
const runningTasks = computed(() => taskStore.runningTasks)

// 筛选后的任务
const filteredTasks = computed(() => {
  let result = tasks.value
  
  if (filterStatus.value) {
    result = result.filter(t => t.status === filterStatus.value)
  }
  
  if (filterEmployee.value) {
    result = result.filter(t => t.assigned_to === filterEmployee.value)
  }
  
  // 排序：执行中在前，然后按创建时间倒序
  result = [...result].sort((a, b) => {
    const aRunning = isRunning(a) ? 1 : 0
    const bRunning = isRunning(b) ? 1 : 0
    if (aRunning !== bRunning) return bRunning - aRunning
    return new Date(b.created_at) - new Date(a.created_at)
  })
  
  return result
})

const hasFilter = computed(() => filterStatus.value || filterEmployee.value)

const emptyMessage = computed(() => {
  if (hasFilter.value) return '没有找到符合条件的任务'
  return '暂无任务，点击右上角创建新任务'
})

// 方法
function isRunning(task) {
  return ['assigned', 'in_progress'].includes(task.status)
}

function getEmployeeName(employeeId) {
  const emp = employees.value.find(e => e.id === employeeId)
  return emp?.name || employeeId
}

function formatDuration(start, end) {
  if (!start || !end) return '-'
  const duration = Math.floor((new Date(end) - new Date(start)) / 1000)
  const minutes = Math.floor(duration / 60)
  const seconds = duration % 60
  if (minutes > 0) return `${minutes}分${seconds}秒`
  return `${seconds}秒`
}

function openAssignModal(task) {
  selectedTask.value = task
  showAssignModal.value = true
}

function onTaskAssigned(task) {
  showAssignModal.value = false
  selectedTask.value = null
}

async function handleCreateTask(data) {
  creating.value = true
  try {
    await taskStore.createTask(data)
    showCreateModal.value = false
  } catch (err) {
    alert('创建任务失败: ' + err.message)
  } finally {
    creating.value = false
  }
}

async function retryTask(task) {
  if (!confirm(`确定要重试任务 "${task.title}" 吗？`)) return
  try {
    await taskStore.retryTask(task.id)
  } catch (err) {
    alert('重试失败: ' + err.message)
  }
}

function viewTask(task) {
  router.push(`/tasks/${task.id}`)
}

function handleFilter() {
  // 筛选变化时自动处理
}

function clearFilter() {
  filterStatus.value = ''
  filterEmployee.value = ''
}

function scrollToRunning() {
  const firstRunning = document.querySelector('.running-row')
  if (firstRunning) {
    firstRunning.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

// 生命周期
onMounted(async () => {
  // 加载数据
  await Promise.all([
    taskStore.fetchTasks(),
    employeeStore.fetchEmployees()
  ])
  
  // 请求通知权限
  taskStore.requestNotificationPermission()
  
  // 恢复对执行中任务的轮询
  taskStore.resumePollingForRunningTasks()
})

onUnmounted(() => {
  // 页面卸载时停止所有轮询
  taskStore.stopAllPolling()
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.icon {
  margin-right: 4px;
}

/* 执行中横幅 */
.running-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: linear-gradient(90deg, #fff3e0 0%, #ffe0b2 100%);
  border: 1px solid #ffb74d;
  border-radius: 8px;
  margin-bottom: 20px;
  color: #e65100;
  font-weight: 500;
}

.spinner-sm {
  width: 16px;
  height: 16px;
  border: 2px solid #f57c00;
  border-right-color: transparent;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.btn-text {
  background: none;
  border: none;
  color: #f57c00;
  cursor: pointer;
  font-size: 14px;
  text-decoration: underline;
}

/* 筛选器 */
.filters {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-group label {
  font-size: 14px;
  color: var(--text-secondary, #666);
}

.filter-group select {
  padding: 8px 12px;
  border: 1px solid var(--border-color, #ddd);
  border-radius: 6px;
  font-size: 14px;
  background: var(--bg-primary, #fff);
  color: var(--text-primary, #333);
  min-width: 120px;
}

/* 加载状态 */
.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 16px;
}

.loading .spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-color, #e0e0e0);
  border-top-color: var(--color-primary, #1976d2);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 60px 20px;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-state p {
  color: var(--text-secondary, #666);
  margin-bottom: 20px;
}

/* 表格 */
.table-container {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid var(--border-color, #e0e0e0);
}

.data-table th {
  font-weight: 500;
  color: var(--text-secondary, #666);
  font-size: 13px;
  text-transform: uppercase;
}

.data-table tbody tr:hover {
  background: var(--bg-secondary, #f5f5f5);
}

.running-row {
  background: rgba(255, 243, 224, 0.3) !important;
}

.task-link {
  display: flex;
  flex-direction: column;
  text-decoration: none;
  color: inherit;
}

.task-title {
  font-weight: 500;
  color: var(--text-primary, #333);
}

.task-desc {
  font-size: 13px;
  color: var(--text-secondary, #666);
  margin-top: 4px;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.text-muted {
  color: var(--text-secondary, #999);
}

.employee-name {
  font-weight: 500;
}

.completed-indicator {
  font-size: 13px;
  color: var(--color-success, #388e3c);
}

.actions {
  display: flex;
  gap: 8px;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 13px;
}

/* Toast 容器 */
.toast-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 2000;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.toast {
  padding: 12px 20px;
  border-radius: 6px;
  color: white;
  font-size: 14px;
  animation: slideIn 0.3s ease;
  max-width: 300px;
}

.toast-info {
  background: var(--color-info, #1976d2);
}

.toast-success {
  background: var(--color-success, #388e3c);
}

.toast-warning {
  background: var(--color-warning, #f57c00);
}

.toast-error {
  background: var(--color-danger, #d32f2f);
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

/* 按钮样式 */
.btn {
  padding: 10px 20px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--color-primary, #1976d2);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-dark, #1565c0);
}

.btn-secondary {
  background: var(--bg-secondary, #f5f5f5);
  color: var(--text-primary, #333);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-tertiary, #e0e0e0);
}

.btn-warning {
  background: var(--color-warning, #f57c00);
  color: white;
}

.btn-warning:hover:not(:disabled) {
  background: #e65100;
}
</style>
