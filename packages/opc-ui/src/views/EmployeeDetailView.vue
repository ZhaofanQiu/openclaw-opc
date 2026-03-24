<template>
  <div class="view">
    <div class="page-header">
      <router-link to="/employees" class="back-link">← {{ $t('common.back') }}</router-link>
      <h1>{{ employee?.name || '员工详情' }}</h1>
    </div>

    <div v-if="loading" class="loading">
      <div class="spinner"></div>
    </div>

    <div v-else-if="employee" class="employee-detail">
      <div class="detail-card">
        <div class="employee-header">
          <span class="employee-emoji">{{ employee.emoji }}</span>
          <div class="employee-info">
            <h2>{{ employee.name }}</h2>
            <span :class="['badge', getStatusClass(employee.status)]">
              {{ $t(`employees.statusTypes.${employee.status}`) }}
            </span>
          </div>
        </div>

        <div class="detail-grid">
          <div class="detail-item">
            <label>月度预算</label>
            <value>¥{{ employee.monthly_budget?.toLocaleString() }}</value>
          </div>
          <div class="detail-item">
            <label>已使用</label>
            <value>¥{{ employee.used_budget?.toLocaleString() }}</value>
          </div>
          <div class="detail-item">
            <label>剩余</label>
            <value :class="{ 'text-danger': employee.budget_percentage > 80 }">
              ¥{{ employee.remaining_budget?.toLocaleString() }}
            </value>
          </div>
          <div class="detail-item">
            <label>已完成任务</label>
            <value>{{ employee.completed_tasks }}</value>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useEmployeeStore } from '@/stores/employees'

const route = useRoute()
const employeeStore = useEmployeeStore()

const employee = computed(() => employeeStore.currentEmployee)
const loading = computed(() => employeeStore.loading)

function getStatusClass(status) {
  const map = {
    idle: 'badge-success',
    working: 'badge-warning',
    offline: 'badge-danger',
  }
  return map[status] || 'badge-info'
}

onMounted(() => {
  employeeStore.fetchEmployee(route.params.id)
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

.employee-detail {
  max-width: 800px;
}

.detail-card {
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  padding: 24px;
  border: 1px solid var(--border-color);
}

.employee-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--border-color);
}

.employee-emoji {
  font-size: 48px;
}

.employee-info h2 {
  font-size: 20px;
  margin-bottom: 8px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 24px;
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
  font-size: 20px;
  font-weight: 600;
}
</style>
