<template>
  <div class="view">
    <!-- 返回按钮 -->
    <div class="page-header">
      <router-link to="/tasks" class="back-link">
        ← 返回任务列表
      </router-link>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>

    <!-- 任务详情 -->
    <div v-else-if="task" class="task-detail">
      <!-- 头部信息 -->
      <div class="detail-header">
        <div class="header-main">
          <h1>{{ task.title }}</h1>
          <TaskStatusBadge :status="task.status" size="large" />
        </div>
        <div class="header-actions">
          <button
            v-if="task.status === 'pending'"
            class="btn btn-primary"
            @click="showAssignModal = true"
          >
            分配任务
          </button>
          <button
            v-if="['failed', 'needs_review'].includes(task.status)"
            class="btn btn-warning"
            @click="retryTask"
          >
            重新执行
          </button>
          <button
            class="btn btn-danger"
            @click="deleteTask"
          >
            删除任务
          </button>
        </div>
      </div>

      <!-- 执行中提示 -->
      <div v-if="isRunning" class="running-panel">
        <div class="running-indicator">
          <div class="spinner-lg"></div>
          <div class="running-info">
            <h3>Agent 正在执行任务</h3>
            <p>已用时: {{ elapsedTime }}</p>
            <p class="hint">您可以离开此页面，任务将在后台继续执行</p>
          </div>
        </div>
        <div class="progress-bar">
          <div class="progress-fill indeterminate"></div>
        </div>
      </div>

      <!-- 基本信息卡片 -->
      <div class="detail-card">
        <h3>基本信息</h3>
        <div class="detail-grid">
          <div class="detail-item">
            <label>描述</label>
            <p class="description">{{ task.description || '暂无描述' }}</p>
          </div>
          <div class="detail-item">
            <label>分配员工</label>
            <p v-if="employee">{{ employee.name }} ({{ employee.position_title }})</p>
            <p v-else class="text-muted">未分配</p>
          </div>
          <div class="detail-item">
            <label>预估成本</label>
            <p>{{ task.estimated_cost || 0 }} OC币</p>
          </div>
          <div class="detail-item">
            <label>实际消耗</label>
            <p :class="{ 'text-success': task.actual_cost }">
              {{ task.actual_cost ? `${task.actual_cost} OC币` : '-' }}
            </p>
          </div>
          <div class="detail-item">
            <label>创建时间</label>
            <p>{{ formatDateTime(task.created_at) }}</p>
          </div>
          <div class="detail-item" v-if="task.completed_at">
            <label>完成时间</label>
            <p>{{ formatDateTime(task.completed_at) }}</p>
          </div>
          <div class="detail-item" v-if="task.rework_count > 0">
            <label>重试次数</label>
            <p>{{ task.rework_count }} / {{ task.max_rework }}</p>
          </div>
        </div>
      </div>

      <!-- 执行结果 -->
      <div v-if="task.result || task.status === 'completed'" class="result-card">
        <h3>执行结果</h3>
        
        <!-- 成功完成 -->
        <div v-if="task.status === 'completed'" class="result-success">
          <div class="result-icon">✅</div>
          <div class="result-content">
            <p class="result-summary">{{ task.result || '任务已完成' }}</p>
            <div v-if="task.tokens_output" class="result-meta">
              <span>Token 消耗: {{ task.tokens_output }}</span>
            </div>
            <!-- 结果文件列表 -->
            <div v-if="task.result_files && task.result_files.length > 0" class="result-files">
              <label>📎 输出文件:</label>
              <ul class="file-list">
                <li v-for="(file, index) in task.result_files" :key="index" class="file-item">
                  <a v-if="isUrl(file)" :href="file" target="_blank" class="file-link">
                    {{ formatFileName(file) }}
                  </a>
                  <span v-else class="file-name">{{ file }}</span>
                </li>
              </ul>
            </div>
            <!-- 员工反馈（非结构化内容） -->
            <div v-if="task.feedback" class="feedback-section">
              <label>📝 员工反馈:</label>
              <div class="feedback-content markdown-body" v-html="renderMarkdown(task.feedback)"></div>
            </div>
          </div>
        </div>

        <!-- 执行失败 -->
        <div v-else-if="task.status === 'failed'" class="result-failed">
          <div class="result-icon">❌</div>
          <div class="result-content">
            <p class="error-title">任务执行失败</p>
            <pre class="error-detail">{{ task.result }}</pre>
          </div>
        </div>

        <!-- 需要返工 -->
        <div v-else-if="task.status === 'needs_revision'" class="result-revision">
          <div class="result-icon">🔄</div>
          <div class="result-content">
            <p class="revision-title">需要返工</p>
            <p class="revision-reason">{{ task.result }}</p>
          </div>
        </div>

        <!-- 需要人工检查 -->
        <div v-else-if="task.status === 'needs_review'" class="result-review">
          <div class="result-icon">⚠️</div>
          <div class="result-content">
            <p class="review-title">无法解析 Agent 响应</p>
            <p class="review-desc">Agent 返回的数据格式不符合预期，需要人工检查</p>
            <div class="raw-response">
              <label>原始响应内容:</label>
              <pre>{{ task.result }}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 未找到 -->
    <div v-else class="not-found">
      <div class="not-found-icon">🔍</div>
      <h2>任务未找到</h2>
      <p>该任务可能已被删除或不存在</p>
      <router-link to="/tasks" class="btn btn-primary">
        返回任务列表
      </router-link>
    </div>

    <!-- 分配弹窗 -->
    <TaskAssignModal
      v-if="showAssignModal"
      :task="task"
      @close="showAssignModal = false"
      @assigned="onTaskAssigned"
    />

    <!-- Toast 通知 -->
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
import { useRoute, useRouter } from 'vue-router'
import { marked } from 'marked'
import { useTaskStore } from '@/stores/tasks'
import { useEmployeeStore } from '@/stores/employees'
import TaskStatusBadge from '@/components/tasks/TaskStatusBadge.vue'
import TaskAssignModal from '@/components/tasks/TaskAssignModal.vue'

const route = useRoute()
const router = useRouter()
const taskStore = useTaskStore()
const employeeStore = useEmployeeStore()

// 状态
const showAssignModal = ref(false)
const elapsedTime = ref('00:00')
let timeInterval = null

// 从 store 获取
const task = computed(() => taskStore.currentTask)
const loading = computed(() => taskStore.loading)
const notifications = computed(() => taskStore.notifications)

const employee = computed(() => {
  if (!task.value?.assigned_to) return null
  return employeeStore.employees.find(e => e.id === task.value.assigned_to)
})

const isRunning = computed(() => 
  ['assigned', 'in_progress'].includes(task.value?.status)
)

// 方法
function formatDateTime(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

function isUrl(str) {
  if (!str) return false
  return str.startsWith('http://') || str.startsWith('https://') || str.startsWith('/')
}

function formatFileName(file) {
  if (!file) return ''
  if (isUrl(file)) {
    try {
      const url = new URL(file)
      return url.pathname.split('/').pop() || file
    } catch {
      return file.split('/').pop()
    }
  }
  return file
}

// 使用 marked 渲染 Markdown
function renderMarkdown(text) {
  if (!text) return ''
  return marked.parse(text, {
    gfm: true,        // GitHub Flavored Markdown
    breaks: true,     // 换行符转为 <br>
    headerIds: false, // 不自动生成标题 ID
    mangle: false     // 不转义邮件地址
  })
}

function updateElapsedTime() {
  if (!task.value?.started_at) {
    elapsedTime.value = '00:00'
    return
  }
  
  const start = new Date(task.value.started_at).getTime()
  const now = Date.now()
  const elapsed = Math.floor((now - start) / 1000)
  
  const minutes = Math.floor(elapsed / 60)
  const seconds = elapsed % 60
  
  elapsedTime.value = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
}

function onTaskAssigned() {
  showAssignModal.value = false
  // 开始轮询
  taskStore.startPolling(route.params.id)
}

async function retryTask() {
  if (!confirm('确定要重新执行此任务吗？')) return
  try {
    await taskStore.retryTask(route.params.id)
    // 重试后开始轮询
    taskStore.startPolling(route.params.id)
  } catch (err) {
    alert('重试失败: ' + err.message)
  }
}

async function deleteTask() {
  if (!confirm('确定要删除此任务吗？删除后无法恢复。')) return
  try {
    await taskStore.deleteTask(route.params.id)
    // 删除后返回任务列表
    router.push('/tasks')
  } catch (err) {
    alert('删除失败: ' + err.message)
  }
}

// 生命周期
onMounted(async () => {
  const taskId = route.params.id
  
  // 加载任务详情
  await taskStore.fetchTask(taskId)
  
  // 加载员工列表
  await employeeStore.fetchEmployees()
  
  // 如果任务在执行中，开始轮询和时间更新
  if (isRunning.value) {
    taskStore.startPolling(taskId)
    timeInterval = setInterval(updateElapsedTime, 1000)
    updateElapsedTime()
  }
})

onUnmounted(() => {
  // 停止轮询
  taskStore.stopPolling(route.params.id)
  
  // 停止时间更新
  if (timeInterval) {
    clearInterval(timeInterval)
  }
})
</script>

<style scoped>
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--text-secondary, #666);
  text-decoration: none;
  font-size: 14px;
  margin-bottom: 16px;
}

.back-link:hover {
  color: var(--color-primary, #1976d2);
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  gap: 16px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-color, #e0e0e0);
  border-top-color: var(--color-primary, #1976d2);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 详情头部 */
.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  gap: 16px;
}

.header-main {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.header-main h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 12px;
}

/* 执行中面板 */
.running-panel {
  background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
  border: 1px solid #ffb74d;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
}

.running-indicator {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 16px;
}

.spinner-lg {
  width: 48px;
  height: 48px;
  border: 4px solid rgba(245, 124, 0, 0.2);
  border-top-color: #f57c00;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.running-info h3 {
  margin: 0 0 8px 0;
  color: #e65100;
}

.running-info p {
  margin: 0 0 4px 0;
  font-size: 18px;
  font-weight: 500;
  font-family: monospace;
}

.hint {
  font-size: 13px;
  color: #f57c00;
  opacity: 0.8;
}

.progress-bar {
  height: 6px;
  background: rgba(245, 124, 0, 0.2);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #f57c00;
  border-radius: 3px;
}

.indeterminate {
  width: 50%;
  animation: indeterminate 1.5s infinite ease-in-out;
}

@keyframes indeterminate {
  0% { transform: translateX(-100%); }
  50% { transform: translateX(100%); }
  100% { transform: translateX(-100%); }
}

/* 卡片样式 */
.detail-card,
.result-card {
  background: var(--bg-primary, #fff);
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
}

.detail-card h3,
.result-card h3 {
  margin: 0 0 20px 0;
  font-size: 18px;
  font-weight: 600;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-color, #e0e0e0);
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
}

.detail-item label {
  display: block;
  font-size: 13px;
  color: var(--text-secondary, #666);
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.detail-item p {
  margin: 0;
  font-size: 15px;
  color: var(--text-primary, #333);
}

.detail-item .description {
  line-height: 1.6;
  white-space: pre-wrap;
}

.text-muted {
  color: var(--text-secondary, #999);
}

.text-success {
  color: var(--color-success, #388e3c);
}

/* 结果展示 */
.result-success,
.result-failed,
.result-revision,
.result-review {
  display: flex;
  gap: 16px;
}

.result-icon {
  font-size: 32px;
  flex-shrink: 0;
}

.result-content {
  flex: 1;
}

.result-summary {
  margin: 0;
  font-size: 15px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.result-meta {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-color, #e0e0e0);
  font-size: 13px;
  color: var(--text-secondary, #666);
}

/* 结果文件列表 */
.result-files {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color, #e0e0e0);
}

.result-files label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary, #333);
  margin-bottom: 8px;
}

.file-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.file-item {
  margin-bottom: 8px;
  padding: 8px 12px;
  background: var(--bg-secondary, #f5f5f5);
  border-radius: 6px;
}

.file-link {
  color: var(--color-primary, #1976d2);
  text-decoration: none;
}

.file-link:hover {
  text-decoration: underline;
}

.file-name {
  color: var(--text-primary, #333);
  font-family: monospace;
  font-size: 13px;
}

.error-title,
.revision-title,
.review-title {
  margin: 0 0 8px 0;
  font-weight: 600;
  color: var(--color-danger, #d32f2f);
}

.revision-title {
  color: var(--color-warning, #f57c00);
}

.review-title {
  color: var(--color-warning, #f57c00);
}

.error-detail,
.revision-reason {
  margin: 0;
  padding: 12px;
  background: var(--bg-secondary, #f5f5f5);
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  overflow-x: auto;
}

.review-desc {
  margin: 0 0 16px 0;
  color: var(--text-secondary, #666);
}

.raw-response {
  margin-top: 16px;
}

.raw-response label {
  display: block;
  font-size: 12px;
  color: var(--text-secondary, #666);
  margin-bottom: 8px;
}

.raw-response pre {
  margin: 0;
  padding: 16px;
  background: var(--bg-secondary, #f5f5f5);
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  overflow-x: auto;
  max-height: 400px;
  overflow-y: auto;
}

/* 员工反馈区域 */
.feedback-section {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color, #e0e0e0);
}

.feedback-section label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary, #333);
  margin-bottom: 12px;
}

.feedback-content {
  padding: 16px;
  background: var(--bg-secondary, #f8f9fa);
  border-radius: 8px;
  border-left: 4px solid var(--color-primary, #1976d2);
  font-size: 14px;
  line-height: 1.8;
}

.feedback-content :deep(pre) {
  background: #f5f5f5;
  padding: 12px 16px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 12px 0;
}

.feedback-content :deep(pre code) {
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  background: transparent;
  padding: 0;
}

.feedback-content :deep(code) {
  background: #f0f0f0;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
}

.feedback-content :deep(h1) {
  font-size: 1.5em;
  font-weight: 600;
  margin: 1em 0 0.5em;
  color: var(--text-primary, #333);
}

.feedback-content :deep(h2) {
  font-size: 1.3em;
  font-weight: 600;
  margin: 1em 0 0.5em;
  color: var(--text-primary, #333);
}

.feedback-content :deep(h3) {
  font-size: 1.1em;
  font-weight: 600;
  margin: 1em 0 0.5em;
  color: var(--text-primary, #333);
}

.feedback-content :deep(hr) {
  border: none;
  border-top: 1px solid #e0e0e0;
  margin: 16px 0;
}

.feedback-content :deep(ul),
.feedback-content :deep(ol) {
  margin: 0.5em 0;
  padding-left: 1.5em;
}

.feedback-content :deep(li) {
  margin: 0.25em 0;
}

.feedback-content :deep(blockquote) {
  border-left: 4px solid #ddd;
  padding-left: 1em;
  margin: 1em 0;
  color: #666;
}

.feedback-content :deep(a) {
  color: var(--color-primary, #1976d2);
  text-decoration: none;
}

.feedback-content :deep(a:hover) {
  text-decoration: underline;
}

.feedback-content :deep(p) {
  margin: 0.5em 0;
}

.feedback-content :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 1em 0;
}

.feedback-content :deep(th),
.feedback-content :deep(td) {
  border: 1px solid #e0e0e0;
  padding: 8px 12px;
  text-align: left;
}

.feedback-content :deep(th) {
  background: #f5f5f5;
  font-weight: 600;
}

/* 未找到 */
.not-found {
  text-align: center;
  padding: 80px 20px;
}

.not-found-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.not-found h2 {
  margin: 0 0 8px 0;
  font-size: 24px;
}

.not-found p {
  color: var(--text-secondary, #666);
  margin-bottom: 24px;
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
  text-decoration: none;
}

.btn-primary {
  background: var(--color-primary, #1976d2);
  color: white;
}

.btn-primary:hover {
  background: var(--color-primary-dark, #1565c0);
}

.btn-warning {
  background: var(--color-warning, #f57c00);
  color: white;
}

.btn-warning:hover {
  background: #e65100;
}
</style>
