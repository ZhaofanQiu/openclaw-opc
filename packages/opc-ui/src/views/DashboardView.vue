<template>
  <div class="view">
    <div class="page-header">
      <h1>{{ $t('dashboard.title') }}</h1>
    </div>
    
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
    </div>
    
    <div v-else-if="data" class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">{{ $t('dashboard.stats.totalEmployees') }}</div>
        <div class="stat-value">{{ data.employees.total }}</div>
      </div>
      
      <div class="stat-card">
        <div class="stat-label">{{ $t('dashboard.stats.onlineEmployees') }}</div>
        <div class="stat-value text-success">{{ data.employees.online }}</div>
      </div>
      
      <div class="stat-card">
        <div class="stat-label">{{ $t('dashboard.stats.totalTasks') }}</div>
        <div class="stat-value">{{ data.tasks.total_tasks }}</div>
      </div>
      
      <div class="stat-card">
        <div class="stat-label">{{ $t('dashboard.stats.completedTasks') }}</div>
        <div class="stat-value text-success">{{ data.tasks.completed_tasks }}</div>
      </div>
      
      <div class="stat-card">
        <div class="stat-label">{{ $t('dashboard.stats.totalBudget') }}</div>
        <div class="stat-value">¥{{ formatNumber(data.employees.total_budget) }}</div>
      </div>
      
      <div class="stat-card">
        <div class="stat-label">{{ $t('dashboard.stats.remainingBudget') }}</div>
        <div class="stat-value" :class="remainingBudgetClass">
          ¥{{ formatNumber(data.employees.total_remaining) }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useReportStore } from '@/stores/reports'

const reportStore = useReportStore()
const data = computed(() => reportStore.dashboardData)
const loading = computed(() => reportStore.loading)

const remainingBudgetClass = computed(() => {
  if (!data.value) return ''
  const remaining = data.value.employees.total_remaining
  const total = data.value.employees.total_budget
  const ratio = remaining / total
  if (ratio < 0.2) return 'text-danger'
  if (ratio < 0.5) return 'text-warning'
  return 'text-success'
})

function formatNumber(num) {
  if (num === undefined || num === null) return '-'
  return num.toLocaleString()
}

onMounted(() => {
  reportStore.fetchDashboardData()
})
</script>

<style scoped>
.page-header {
  margin-bottom: 32px;
}

.page-header h1 {
  font-size: 24px;
  font-weight: 600;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 20px;
}

.stat-card {
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  padding: 24px;
  border: 1px solid var(--border-color);
}

.stat-label {
  font-size: 12px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--text-primary);
}

.text-success {
  color: var(--color-success);
}

.text-warning {
  color: var(--color-warning);
}

.text-danger {
  color: var(--color-danger);
}
</style>
