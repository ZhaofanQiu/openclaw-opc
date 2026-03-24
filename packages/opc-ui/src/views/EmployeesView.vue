<template>
  <div class="view">
    <div class="page-header">
      <h1>{{ $t('employees.title') }}</h1>
      <button class="btn btn-primary" @click="showCreateModal = true">
        {{ $t('employees.create') }}
      </button>
    </div>
    
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
    </div>
    
    <div v-else-if="employees.length === 0" class="empty-state">
      <div class="empty-state-icon">👥</div>
      <p>{{ $t('common.noData') }}</p>
    </div>
    
    <div v-else class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>{{ $t('employees.name') }}</th>
            <th>{{ $t('employees.status') }}</th>
            <th>{{ $t('employees.budget') }}</th>
            <th>{{ $t('employees.tasks') }}</th>
            <th>{{ $t('common.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="emp in employees" :key="emp.id">
            <td>
              <router-link :to="`/employees/${emp.id}`" class="employee-link">
                <span class="employee-emoji">{{ emp.emoji }}</span>
                {{ emp.name }}
              </router-link>
            </td>
            <td>
              <span :class="['badge', getStatusClass(emp.status)]">
                {{ $t(`employees.statusTypes.${emp.status}`) }}
              </span>
            </td>
            <td>
              <div class="budget-bar">
                <div
                  class="budget-fill"
                  :style="{ width: `${emp.budget_percentage}%` }"
                  :class="{ 'budget-warning': emp.budget_percentage > 80 }"
                ></div>
              </div>
              <span class="budget-text">
                ¥{{ formatNumber(emp.used_budget) }} / ¥{{ formatNumber(emp.monthly_budget) }}
              </span>
            </td>
            <td>{{ emp.completed_tasks }}</td>
            <td>
              <button class="btn btn-sm btn-secondary" @click="editEmployee(emp)">
                {{ $t('common.edit') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useEmployeeStore } from '@/stores/employees'

const employeeStore = useEmployeeStore()
const employees = computed(() => employeeStore.employees)
const loading = computed(() => employeeStore.loading)

const showCreateModal = ref(false)

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

function editEmployee(emp) {
  // TODO: 打开编辑弹窗
}

onMounted(() => {
  employeeStore.fetchEmployees()
})
</script>

<script>
import { ref } from 'vue'
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 24px;
  font-weight: 600;
}

.employee-link {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-primary);
  text-decoration: none;
}

.employee-link:hover {
  color: var(--color-primary);
}

.employee-emoji {
  font-size: 20px;
}

.budget-bar {
  width: 100px;
  height: 6px;
  background: var(--bg-tertiary);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 4px;
}

.budget-fill {
  height: 100%;
  background: var(--color-success);
  transition: width 0.3s;
}

.budget-fill.budget-warning {
  background: var(--color-warning);
}

.budget-text {
  font-size: 12px;
  color: var(--text-secondary);
}
</style>
