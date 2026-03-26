<template>
  <div class="view">
    <div class="page-header">
      <h1>{{ $t('reports.title') }}</h1>
    </div>
    
    <div class="report-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="tab-btn"
        :class="{ active: currentTab === tab.key }"
        @click="currentTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>
    
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
    </div>
    
    <div v-else-if="currentTab === 'employees' && employeeReport" class="report-content">
      <table class="data-table">
        <thead>
          <tr>
            <th>员工</th>
            <th>状态</th>
            <th>预算</th>
            <th>已用</th>
            <th>剩余</th>
            <th>完成任务</th>
            <th>效率</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="emp in employeeReport.employees" :key="emp.id">
            <td class="employee-cell">
              <EmployeeAvatar :employee="emp" size="small" />
              <span class="employee-name">{{ emp.name }}</span>
            </td>
            <td>
              <span :class="['badge', getStatusClass(emp.status)]">
                {{ $t(`employees.statusTypes.${emp.status}`) }}
              </span>
            </td>
            <td>¥{{ formatNumber(emp.budget) }}</td>
            <td>¥{{ formatNumber(emp.used) }}</td>
            <td>¥{{ formatNumber(emp.remaining) }}</td>
            <td>{{ emp.completed_tasks }}</td>
            <td>{{ emp.efficiency }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    
    <div v-else-if="currentTab === 'tasks' && taskReport" class="report-content">
      <div class="stats-summary">
        <div class="stat-item">
          <span class="stat-label">总任务</span>
          <span class="stat-value">{{ taskReport.summary.total_tasks }}</span>
        </div>
        
        <div class="stat-item">
          <span class="stat-label">完成率</span>
          <span class="stat-value">{{ (taskReport.summary.completion_rate * 100).toFixed(1) }}%</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useReportStore } from '@/stores/reports'
import EmployeeAvatar from '@/components/avatar/EmployeeAvatar.vue'

const reportStore = useReportStore()
const loading = computed(() => reportStore.loading)
const employeeReport = computed(() => reportStore.employeeReport)
const taskReport = computed(() => reportStore.taskReport)

const currentTab = ref('employees')
const tabs = [
  { key: 'employees', label: '员工绩效' },
  { key: 'tasks', label: '任务统计' },
]

function getStatusClass(status) {
  const map = {
    idle: 'badge-success',
    working: 'badge-warning',
    offline: 'badge-danger',
  }
  return map[status] || 'badge-info'
}

function formatNumber(num) {
  return num?.toLocaleString() || '0'
}

onMounted(() => {
  reportStore.fetchEmployeeReport()
  reportStore.fetchTaskReport()
})
</script>

<style scoped>
.page-header {
  margin-bottom: 24px;
}

.report-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 16px;
}

.tab-btn {
  padding: 8px 16px;
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: var(--radius-md);
  transition: all 0.2s;
}

.tab-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.tab-btn.active {
  background: var(--color-primary);
  color: white;
}

.stats-summary {
  display: flex;
  gap: 32px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-label {
  font-size: 12px;
  color: var(--text-secondary);
  text-transform: uppercase;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
}

.employee-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.employee-name {
  font-weight: 500;
}
</style>
