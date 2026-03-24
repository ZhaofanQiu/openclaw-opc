import { ref } from 'vue'
import { defineStore } from 'pinia'
import { api } from '@/utils/api'

export const useReportStore = defineStore('reports', () => {
  // State
  const dashboardData = ref(null)
  const employeeReport = ref(null)
  const taskReport = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // Actions
  async function fetchDashboardData() {
    loading.value = true
    error.value = null
    try {
      const response = await api.get('/reports/dashboard')
      dashboardData.value = response
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchEmployeeReport() {
    loading.value = true
    error.value = null
    try {
      const response = await api.get('/reports/employees')
      employeeReport.value = response
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchTaskReport() {
    loading.value = true
    error.value = null
    try {
      const response = await api.get('/reports/tasks')
      taskReport.value = response
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  return {
    dashboardData,
    employeeReport,
    taskReport,
    loading,
    error,
    fetchDashboardData,
    fetchEmployeeReport,
    fetchTaskReport,
  }
})
