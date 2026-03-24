import { ref } from 'vue'
import { defineStore } from 'pinia'
import { api } from '@/utils/api'

export const useBudgetStore = defineStore('budget', () => {
  // State
  const companyBudget = ref(null)
  const employeeBudgets = ref([])
  const loading = ref(false)
  const error = ref(null)

  // Actions
  async function fetchCompanyBudget() {
    loading.value = true
    error.value = null
    try {
      const response = await api.get('/budget/company')
      companyBudget.value = response
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchEmployeeBudgets() {
    loading.value = true
    error.value = null
    try {
      const response = await api.get('/budget/employees')
      employeeBudgets.value = response.employees || []
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function addBudget(employeeId, amount, reason) {
    loading.value = true
    try {
      const response = await api.post(`/budget/employees/${employeeId}/add`, {
        amount,
        reason
      })
      await fetchEmployeeBudgets()
      return response
    } finally {
      loading.value = false
    }
  }

  return {
    companyBudget,
    employeeBudgets,
    loading,
    error,
    fetchCompanyBudget,
    fetchEmployeeBudgets,
    addBudget,
  }
})
