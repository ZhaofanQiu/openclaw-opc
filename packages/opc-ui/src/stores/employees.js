import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { api } from '@/utils/api'

export const useEmployeeStore = defineStore('employees', () => {
  // State
  const employees = ref([])
  const currentEmployee = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const employeeCount = computed(() => employees.value.length)
  const onlineCount = computed(() => 
    employees.value.filter(e => e.status === 'idle').length
  )
  const workingCount = computed(() =>
    employees.value.filter(e => e.status === 'working').length
  )

  // Actions
  async function fetchEmployees() {
    loading.value = true
    error.value = null
    try {
      const response = await api.get('/employees')
      employees.value = response.employees || []
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchEmployee(id) {
    loading.value = true
    error.value = null
    try {
      const response = await api.get(`/employees/${id}`)
      currentEmployee.value = response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createEmployee(data) {
    loading.value = true
    try {
      const response = await api.post('/employees', data)
      await fetchEmployees()
      return response
    } finally {
      loading.value = false
    }
  }

  async function updateEmployee(id, data) {
    loading.value = true
    try {
      const response = await api.put(`/employees/${id}`, data)
      await fetchEmployees()
      return response
    } finally {
      loading.value = false
    }
  }

  async function deleteEmployee(id) {
    loading.value = true
    try {
      await api.delete(`/employees/${id}`)
      await fetchEmployees()
    } finally {
      loading.value = false
    }
  }

  async function bindAgent(id, openclawAgentId) {
    loading.value = true
    try {
      const response = await api.post(`/employees/${id}/bind`, {
        openclaw_agent_id: openclawAgentId
      })
      await fetchEmployees()
      return response
    } finally {
      loading.value = false
    }
  }

  async function unbindAgent(id) {
    loading.value = true
    try {
      await api.post(`/employees/${id}/unbind`)
      await fetchEmployees()
    } finally {
      loading.value = false
    }
  }

  return {
    employees,
    currentEmployee,
    loading,
    error,
    employeeCount,
    onlineCount,
    workingCount,
    fetchEmployees,
    fetchEmployee,
    createEmployee,
    updateEmployee,
    deleteEmployee,
    bindAgent,
    unbindAgent,
  }
})
