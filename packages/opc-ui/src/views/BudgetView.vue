<template>
  <div class="view">
    <div class="page-header">
      <h1>{{ $t('budget.title') }}</h1>
    </div>
    
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
    </div>
    
    <div v-else-if="companyBudget" class="budget-overview">
      <div class="budget-cards">
        <div class="budget-card">
          <div class="budget-label">{{ $t('budget.monthly') }}</div>
          <div class="budget-value">¥{{ formatNumber(companyBudget.total_budget) }}</div>
        </div>
        
        <div class="budget-card">
          <div class="budget-label">{{ $t('budget.used') }}</div>
          <div class="budget-value text-danger">¥{{ formatNumber(companyBudget.total_used) }}</div>
        </div>
        
        <div class="budget-card">
          <div class="budget-label">{{ $t('budget.remaining') }}</div>
          <div class="budget-value text-success">¥{{ formatNumber(companyBudget.total_remaining) }}</div>
        </div>
      </div>
      
      <h2 class="section-title">员工预算</h2>
      
      <div v-if="employeeBudgets.length === 0" class="empty-state">
        <p>{{ $t('common.noData') }}</p>
      </div>
      
      <div v-else class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>员工</th>
              <th>预算</th>
              <th>已使用</th>
              <th>剩余</th>
              <th>心情</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="emp in employeeBudgets" :key="emp.id">
              <td>{{ emp.emoji }} {{ emp.name }}</td>
              <td>¥{{ formatNumber(emp.monthly_budget) }}</td>
              <td>¥{{ formatNumber(emp.used_budget) }}</td>
              <td :class="{ 'text-danger': emp.remaining < 100 }">
                ¥{{ formatNumber(emp.remaining) }}
              </td>
              <td class="mood">{{ emp.mood }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useBudgetStore } from '@/stores/budget'

const budgetStore = useBudgetStore()
const companyBudget = computed(() => budgetStore.companyBudget)
const employeeBudgets = computed(() => budgetStore.employeeBudgets)
const loading = computed(() => budgetStore.loading)

function formatNumber(num) {
  return num?.toLocaleString() || '0'
}

onMounted(() => {
  budgetStore.fetchCompanyBudget()
  budgetStore.fetchEmployeeBudgets()
})
</script>

<style scoped>
.page-header {
  margin-bottom: 24px;
}

.budget-overview {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.budget-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
}

.budget-card {
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  padding: 24px;
  border: 1px solid var(--border-color);
}

.budget-label {
  font-size: 12px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.budget-value {
  font-size: 28px;
  font-weight: 700;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 16px;
}

.mood {
  font-size: 20px;
}
</style>
