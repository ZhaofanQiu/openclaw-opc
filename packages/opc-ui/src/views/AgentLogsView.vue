<template>
  <div class="view">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1>{{ $t('agentLogs.title') }}</h1>
      <div class="header-actions">
        <button class="btn btn-secondary" @click="refreshStats" :disabled="store.loading">
          {{ store.loading ? $t('common.loading') : $t('common.refresh') }}
        </button>
        <button class="btn btn-danger" @click="showClearConfirm = true" :disabled="store.loading || !store.hasLogs">
          {{ $t('agentLogs.clear') }}
        </button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div v-if="store.stats" class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">{{ store.stats.total_logs }}</div>
        <div class="stat-label">{{ $t('agentLogs.stats.total') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" :class="{ 'success': store.successRate >= 80, 'warning': store.successRate >= 50 && store.successRate < 80, 'danger': store.successRate < 50 }">
          {{ (store.successRate * 100).toFixed(1) }}%
        </div>
        <div class="stat-label">{{ $t('agentLogs.stats.successRate') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ store.stats.success_count }}</div>
        <div class="stat-label">{{ $t('agentLogs.stats.success') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ store.stats.agents?.length || 0 }}</div>
        <div class="stat-label">{{ $t('agentLogs.stats.agents') }}</div>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <select v-model="filters.agent_id" class="filter-select" @change="applyFilters">
        <option value="">{{ $t('agentLogs.filters.allAgents') }}</option>
        <option v-for="agent in agentOptions" :key="agent.id" :value="agent.id">
          {{ agent.name }}
        </option>
      </select>

      <select v-model="filters.interaction_type" class="filter-select" @change="applyFilters">
        <option value="">{{ $t('agentLogs.filters.allTypes') }}</option>
        <option value="partner_chat">{{ $t('agentLogs.types.partner_chat') }}</option>
        <option value="task_assignment">{{ $t('agentLogs.types.task_assignment') }}</option>
        <option value="assist_employee">{{ $t('agentLogs.types.assist_employee') }}</option>
        <option value="assist_task">{{ $t('agentLogs.types.assist_task') }}</option>
        <option value="assist_workflow">{{ $t('agentLogs.types.assist_workflow') }}</option>
        <option value="assist_manual">{{ $t('agentLogs.types.assist_manual') }}</option>
      </select>

      <select v-model="filters.direction" class="filter-select" @change="applyFilters">
        <option value="">{{ $t('agentLogs.filters.allDirections') }}</option>
        <option value="outgoing">{{ $t('agentLogs.directions.outgoing') }}</option>
        <option value="incoming">{{ $t('agentLogs.directions.incoming') }}</option>
      </select>

      <select v-model="filters.hours" class="filter-select" @change="applyFilters">
        <option :value="24">{{ $t('agentLogs.filters.last24h') }}</option>
        <option :value="168">{{ $t('agentLogs.filters.last7d') }}</option>
      </select>

      <input
        v-model="filters.task_id"
        type="text"
        class="filter-input"
        :placeholder="$t('agentLogs.filters.taskIdPlaceholder')"
        @keyup.enter="applyFilters"
      />
    </div>

    <!-- 日志表格 -->
    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>{{ $t('agentLogs.table.time') }}</th>
            <th>{{ $t('agentLogs.table.agent') }}</th>
            <th>{{ $t('agentLogs.table.type') }}</th>
            <th>{{ $t('agentLogs.table.direction') }}</th>
            <th>{{ $t('agentLogs.table.content') }}</th>
            <th>{{ $t('agentLogs.table.tokens') }}</th>
            <th>{{ $t('agentLogs.table.status') }}</th>
            <th>{{ $t('common.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="store.loading && !store.hasLogs">
            <td colspan="8" class="text-center">{{ $t('common.loading') }}</td>
          </tr>
          <tr v-else-if="!store.hasLogs">
            <td colspan="8" class="text-center">{{ $t('agentLogs.noData') }}</td>
          </tr>
          <tr v-for="log in store.logs" :key="log.id">
            <td class="time-cell">{{ formatTime(log.created_at) }}</td>
            <td>
              <div class="agent-cell">
                <span class="agent-name">{{ log.agent_name || log.agent_id }}</span>
                <span v-if="log.task_id" class="task-badge" @click="goToTask(log.task_id)">
                  #{{ log.task_id.slice(-6) }}
                </span>
              </div>
            </td>
            <td>
              <span class="type-tag" :class="log.interaction_type">
                {{ $t(`agentLogs.types.${log.interaction_type}`) || log.interaction_type }}
              </span>
            </td>
            <td>
              <span class="direction-badge" :class="log.direction">
                {{ $t(`agentLogs.directions.${log.direction}`) }}
              </span>
            </td>
            <td class="content-cell">
              {{ truncate(log.content, 60) }}
            </td>
            <td>
              <span v-if="log.metadata?.tokens_input || log.metadata?.tokens_output" class="tokens">
                {{ (log.metadata.tokens_input || 0) + (log.metadata.tokens_output || 0) }}
              </span>
              <span v-else>-</span>
            </td>
            <td>
              <span v-if="log.direction === 'incoming'" class="status-badge" :class="log.metadata?.success ? 'success' : 'error'">
                {{ log.metadata?.success ? $t('agentLogs.status.success') : $t('agentLogs.status.failed') }}
              </span>
              <span v-else>-</span>
            </td>
            <td>
              <button class="btn-icon" @click="viewDetail(log)" title="View Detail">
                👁️
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- 分页 -->
      <div v-if="store.total > limit" class="pagination">
        <button
          class="btn btn-sm"
          :disabled="offset === 0"
          @click="prevPage"
        >
          ← {{ $t('agentLogs.pagination.prev') }}
        </button>
        <span class="page-info">
          {{ offset + 1 }} - {{ Math.min(offset + limit, store.total) }} / {{ store.total }}
        </span>
        <button
          class="btn btn-sm"
          :disabled="offset + limit >= store.total"
          @click="nextPage"
        >
          {{ $t('agentLogs.pagination.next') }} →
        </button>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <div v-if="selectedLog" class="modal-overlay" @click.self="selectedLog = null">
      <div class="modal modal-lg">
        <div class="modal-header">
          <h3>{{ $t('agentLogs.detail.title') }}</h3>
          <button class="btn-icon" @click="selectedLog = null">✕</button>
        </div>
        <div class="modal-body">
          <div class="detail-section">
            <div class="detail-meta">
              <div class="meta-item">
                <label>{{ $t('agentLogs.detail.time') }}</label>
                <span>{{ formatTimeFull(selectedLog.created_at) }}</span>
              </div>
              <div class="meta-item">
                <label>{{ $t('agentLogs.detail.agent') }}</label>
                <span>{{ selectedLog.agent_name || selectedLog.agent_id }}</span>
              </div>
              <div class="meta-item">
                <label>{{ $t('agentLogs.detail.type') }}</label>
                <span class="type-tag" :class="selectedLog.interaction_type">
                  {{ $t(`agentLogs.types.${selectedLog.interaction_type}`) || selectedLog.interaction_type }}
                </span>
              </div>
              <div class="meta-item">
                <label>{{ $t('agentLogs.detail.direction') }}</label>
                <span class="direction-badge" :class="selectedLog.direction">
                  {{ $t(`agentLogs.directions.${selectedLog.direction}`) }}
                </span>
              </div>
              <div v-if="selectedLog.metadata?.duration_ms" class="meta-item">
                <label>{{ $t('agentLogs.detail.duration') }}</label>
                <span>{{ selectedLog.metadata.duration_ms }}ms</span>
              </div>
              <div v-if="selectedLog.metadata?.tokens_input || selectedLog.metadata?.tokens_output" class="meta-item">
                <label>{{ $t('agentLogs.detail.tokens') }}</label>
                <span>
                  {{ $t('agentLogs.detail.in') }}: {{ selectedLog.metadata.tokens_input || 0 }}
                  {{ $t('agentLogs.detail.out') }}: {{ selectedLog.metadata.tokens_output || 0 }}
                </span>
              </div>
              <div v-if="selectedLog.task_id" class="meta-item">
                <label>{{ $t('agentLogs.detail.task') }}</label>
                <a :href="`/tasks/${selectedLog.task_id}`" class="link">{{ selectedLog.task_id }}</a>
              </div>
            </div>
          </div>

          <div class="detail-section">
            <h4>{{ $t('agentLogs.detail.content') }}</h4>
            <pre class="code-block">{{ selectedLog.content }}</pre>
          </div>

          <div v-if="selectedLog.response" class="detail-section">
            <h4>{{ $t('agentLogs.detail.response') }}</h4>
            <pre class="code-block">{{ selectedLog.response }}</pre>
          </div>

          <div v-if="selectedLog.metadata?.error_message" class="detail-section">
            <h4 class="error-title">{{ $t('agentLogs.detail.error') }}</h4>
            <pre class="code-block error">{{ selectedLog.metadata.error_message }}</pre>
          </div>
        </div>
      </div>
    </div>

    <!-- 清空确认弹窗 -->
    <div v-if="showClearConfirm" class="modal-overlay" @click.self="showClearConfirm = false">
      <div class="modal modal-sm">
        <div class="modal-header">
          <h3>{{ $t('agentLogs.clearConfirm.title') }}</h3>
          <button class="btn-icon" @click="showClearConfirm = false">✕</button>
        </div>
        <div class="modal-body">
          <p class="warning-text">{{ $t('agentLogs.clearConfirm.message') }}</p>
          <div class="modal-actions">
            <button class="btn btn-secondary" @click="showClearConfirm = false">
              {{ $t('common.cancel') }}
            </button>
            <button class="btn btn-danger" @click="confirmClear" :disabled="store.loading">
              {{ store.loading ? $t('common.loading') : $t('agentLogs.clearConfirm.confirm') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAgentLogsStore } from '@/stores/agentLogs'
import { useEmployeeStore } from '@/stores/employees'

const router = useRouter()
const store = useAgentLogsStore()
const employeesStore = useEmployeeStore()

// ============ 数据 ============
const filters = ref({
  agent_id: '',
  interaction_type: '',
  direction: '',
  hours: 24,
  task_id: '',
})

const limit = ref(50)
const offset = ref(0)
const selectedLog = ref(null)
const showClearConfirm = ref(false)

// ============ 计算属性 ============
const agentOptions = computed(() => {
  return employeesStore.employees.map(e => ({
    id: e.openclaw_agent_id,
    name: e.name
  })).filter(e => e.id)
})

// ============ 方法 ============
function formatTime(isoString) {
  if (!isoString) return '-'
  const date = new Date(isoString)
  return date.toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatTimeFull(isoString) {
  if (!isoString) return '-'
  const date = new Date(isoString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function truncate(str, length) {
  if (!str) return ''
  return str.length > length ? str.slice(0, length) + '...' : str
}

async function applyFilters() {
  offset.value = 0
  await fetchData()
}

async function fetchData() {
  await store.fetchLogs({
    ...filters.value,
    limit: limit.value,
    offset: offset.value,
  })
}

async function refreshStats() {
  await Promise.all([
    store.fetchStats({ hours: filters.value.hours }),
    fetchData(),
  ])
}

function prevPage() {
  offset.value = Math.max(0, offset.value - limit.value)
  fetchData()
}

function nextPage() {
  offset.value += limit.value
  fetchData()
}

function viewDetail(log) {
  selectedLog.value = log
}

function goToTask(taskId) {
  router.push(`/tasks/${taskId}`)
}

async function confirmClear() {
  await store.clearLogs(filters.value.agent_id || null)
  showClearConfirm.value = false
  await refreshStats()
}

// ============ 生命周期 ============
onMounted(async () => {
  await employeesStore.fetchEmployees()
  await refreshStats()
})

// 监听筛选变化时重置分页
watch([() => filters.value.agent_id, () => filters.value.interaction_type, () => filters.value.direction], () => {
  offset.value = 0
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
}

.header-actions {
  display: flex;
  gap: 12px;
}

/* 统计卡片 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: var(--bg-primary);
  padding: 20px;
  border-radius: 12px;
  text-align: center;
}

.stat-value {
  font-size: 32px;
  font-weight: 600;
  color: var(--color-primary);
}

.stat-value.success { color: #4ade80; }
.stat-value.warning { color: #fbbf24; }
.stat-value.danger { color: #f87171; }

.stat-label {
  font-size: 14px;
  color: var(--text-secondary);
  margin-top: 4px;
}

/* 筛选栏 */
.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.filter-select,
.filter-input {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 14px;
}

.filter-select {
  min-width: 140px;
}

.filter-input {
  min-width: 200px;
}

/* 表格 */
.table-container {
  background: var(--bg-primary);
  border-radius: 12px;
  overflow: hidden;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid var(--border-color);
}

.data-table th {
  font-weight: 500;
  color: var(--text-secondary);
  font-size: 14px;
}

.data-table td {
  font-size: 14px;
}

.time-cell {
  font-family: monospace;
  font-size: 13px;
  color: var(--text-secondary);
}

.agent-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.agent-name {
  font-weight: 500;
}

.task-badge {
  display: inline-block;
  padding: 2px 8px;
  background: var(--bg-secondary);
  border-radius: 4px;
  font-size: 12px;
  color: var(--color-primary);
  cursor: pointer;
}

.task-badge:hover {
  background: var(--color-primary);
  color: white;
}

/* 标签 */
.type-tag {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
}

.type-tag.partner_chat { background: #3b82f6; color: white; }
.type-tag.task_assignment { background: #8b5cf6; color: white; }
.type-tag.assist_employee { background: #10b981; color: white; }
.type-tag.assist_task { background: #f59e0b; color: white; }
.type-tag.assist_workflow { background: #ec4899; color: white; }
.type-tag.assist_manual { background: #6366f1; color: white; }

.direction-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
}

.direction-badge.outgoing {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}

.direction-badge.incoming {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.content-cell {
  max-width: 300px;
  color: var(--text-secondary);
  font-size: 13px;
}

.tokens {
  font-family: monospace;
  font-size: 13px;
  color: var(--text-secondary);
}

.status-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
}

.status-badge.success {
  background: rgba(74, 222, 128, 0.1);
  color: #4ade80;
}

.status-badge.error {
  background: rgba(248, 113, 113, 0.1);
  color: #f87171;
}

/* 分页 */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  padding: 16px;
}

.page-info {
  color: var(--text-secondary);
  font-size: 14px;
}

/* 按钮 */
.btn-sm {
  padding: 6px 12px;
  font-size: 13px;
}

/* 弹窗 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: var(--bg-primary);
  border-radius: 12px;
  max-height: 90vh;
  overflow: auto;
}

.modal-lg {
  width: 90%;
  max-width: 900px;
}

.modal-sm {
  width: 400px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
}

.modal-body {
  padding: 24px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
}

/* 详情样式 */
.detail-meta {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-item label {
  font-size: 12px;
  color: var(--text-secondary);
}

.meta-item span:not(.type-tag):not(.direction-badge) {
  font-size: 14px;
  color: var(--text-primary);
}

.detail-section {
  margin-top: 24px;
}

.detail-section h4 {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 12px;
  color: var(--text-secondary);
}

.detail-section h4.error-title {
  color: #f87171;
}

.code-block {
  background: var(--bg-secondary);
  padding: 16px;
  border-radius: 8px;
  font-family: 'Fira Code', monospace;
  font-size: 13px;
  line-height: 1.6;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 400px;
  overflow-y: auto;
}

.code-block.error {
  background: rgba(248, 113, 113, 0.1);
  color: #f87171;
}

.link {
  color: var(--color-primary);
  text-decoration: underline;
}

.warning-text {
  color: #f87171;
  text-align: center;
}

.text-center {
  text-align: center;
  padding: 40px;
  color: var(--text-secondary);
}
</style>
