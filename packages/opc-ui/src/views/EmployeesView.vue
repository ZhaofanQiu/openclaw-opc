<template>
  <div class="view">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1>员工管理</h1>
      <button class="btn btn-primary" @click="showCreateModal = true">
        <span class="icon">+</span> 雇佣员工
      </button>
    </div>
    
    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-value">{{ employees.length }}</div>
        <div class="stat-label">员工总数</div>
      </div>
      <div class="stat-card">
        <div class="stat-value text-success">{{ onlineCount }}</div>
        <div class="stat-label">空闲中</div>
      </div>
      <div class="stat-card">
        <div class="stat-value text-warning">{{ workingCount }}</div>
        <div class="stat-label">工作中</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ boundCount }}</div>
        <div class="stat-label">已绑定 Agent</div>
      </div>
    </div>
    
    <!-- 加载状态 -->
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>
    
    <!-- 空状态 -->
    <div v-else-if="employees.length === 0" class="empty-state">
      <div class="empty-icon">👥</div>
      <p>还没有员工</p>
      <p class="hint">点击右上角雇佣你的第一个员工</p>
    </div>
    
    <!-- 员工列表 -->
    <div v-else class="employee-grid">
      <div
        v-for="emp in employees"
        :key="emp.id"
        class="employee-card"
        @click="viewEmployee(emp)"
      >
        <div class="card-header">
          <span class="employee-emoji">{{ emp.emoji || '👤' }}</span>
          <div class="employee-status">
            <span :class="['status-dot', emp.status]"></span>
            {{ statusText(emp.status) }}
          </div>
        </div>
        
        <div class="card-body">
          <h3>{{ emp.name }}</h3>
          <p class="position">{{ emp.position_title }}</p>
          
          <div class="budget-bar">
            <div 
              class="budget-fill"
              :style="{ width: `${budgetPercentage(emp)}%` }"
              :class="{ 'budget-warning': budgetPercentage(emp) > 80 }"
            ></div>
          </div>
          <p class="budget-text">
            ¥{{ formatNumber(emp.used_budget) }} / ¥{{ formatNumber(emp.monthly_budget) }}
          </p>
        </div>
        
        <div class="card-footer">
          <div class="stats">
            <span>📝 {{ emp.completed_tasks || 0 }} 任务</span>
          </div>
          
          <button
            v-if="!emp.openclaw_agent_id"
            class="btn btn-sm btn-primary"
            @click.stop="openBindModal(emp)"
          >
            绑定 Agent
          </button>
          <span v-else class="agent-badge">
            🤖 已绑定
          </span>
        </div>
      </div>
    </div>
    
    <!-- 创建员工弹窗 -->
    <EmployeeCreateModal
      v-if="showCreateModal"
      @close="showCreateModal = false"
      @created="onEmployeeCreated"
    />
    
    <!-- 绑定 Agent 弹窗 -->
    <AgentBindModal
      v-if="showBindModal"
      :employee="selectedEmployee"
      @close="showBindModal = false"
      @bound="onAgentBound"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useEmployeeStore } from '@/stores/employees'
import EmployeeCreateModal from '@/components/employees/EmployeeCreateModal.vue'
import AgentBindModal from '@/components/employees/AgentBindModal.vue'

const router = useRouter()
const employeeStore = useEmployeeStore()

// 状态
const showCreateModal = ref(false)
const showBindModal = ref(false)
const selectedEmployee = ref(null)

// 从 store 获取
const employees = computed(() => employeeStore.employees)
const loading = computed(() => employeeStore.loading)

const onlineCount = computed(() => 
  employees.value.filter(e => e.status === 'idle').length
)

const workingCount = computed(() =>
  employees.value.filter(e => e.status === 'working').length
)

const boundCount = computed(() =>
  employees.value.filter(e => e.openclaw_agent_id).length
)

// 方法
function statusText(status) {
  const map = {
    'idle': '空闲',
    'working': '工作中',
    'offline': '离线'
  }
  return map[status] || status
}

function budgetPercentage(emp) {
  if (!emp.monthly_budget) return 0
  return Math.min(100, (emp.used_budget / emp.monthly_budget) * 100)
}

function formatNumber(num) {
  return num?.toLocaleString() || '0'
}

function viewEmployee(emp) {
  router.push(`/employees/${emp.id}`)
}

function openBindModal(emp) {
  selectedEmployee.value = emp
  showBindModal.value = true
}

function onEmployeeCreated() {
  showCreateModal.value = false
  employeeStore.fetchEmployees()
}

function onAgentBound() {
  showBindModal.value = false
  selectedEmployee.value = null
  employeeStore.fetchEmployees()
}

onMounted(() => {
  employeeStore.fetchEmployees()
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

/* 统计行 */
.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: var(--bg-primary, #fff);
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: var(--text-primary, #333);
  margin-bottom: 4px;
}

.stat-value.text-success {
  color: var(--color-success, #388e3c);
}

.stat-value.text-warning {
  color: var(--color-warning, #f57c00);
}

.stat-label {
  font-size: 13px;
  color: var(--text-secondary, #666);
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
  margin: 0 0 8px 0;
}

.hint {
  font-size: 14px;
  color: var(--text-secondary, #666);
}

/* 员工卡片网格 */
.employee-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.employee-card {
  background: var(--bg-primary, #fff);
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;
}

.employee-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.employee-emoji {
  font-size: 40px;
}

.employee-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary, #666);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.idle {
  background: var(--color-success, #4caf50);
}

.status-dot.working {
  background: var(--color-warning, #ff9800);
  animation: pulse 2s infinite;
}

.status-dot.offline {
  background: var(--color-danger, #f44336);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.card-body {
  margin-bottom: 16px;
}

.card-body h3 {
  margin: 0 0 4px 0;
  font-size: 18px;
  font-weight: 600;
}

.position {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: var(--text-secondary, #666);
}

.budget-bar {
  height: 6px;
  background: var(--bg-secondary, #f5f5f5);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 8px;
}

.budget-fill {
  height: 100%;
  background: var(--color-success, #4caf50);
  border-radius: 3px;
  transition: width 0.3s;
}

.budget-fill.budget-warning {
  background: var(--color-warning, #ff9800);
}

.budget-text {
  margin: 0;
  font-size: 13px;
  color: var(--text-secondary, #666);
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 16px;
  border-top: 1px solid var(--border-color, #e0e0e0);
}

.stats {
  font-size: 13px;
  color: var(--text-secondary, #666);
}

.agent-badge {
  font-size: 13px;
  color: var(--color-success, #388e3c);
  background: var(--color-success-bg, #e8f5e9);
  padding: 4px 12px;
  border-radius: 4px;
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

.btn-sm {
  padding: 6px 12px;
  font-size: 13px;
}

.btn-primary {
  background: var(--color-primary, #1976d2);
  color: white;
}

.btn-primary:hover {
  background: var(--color-primary-dark, #1565c0);
}
</style>
