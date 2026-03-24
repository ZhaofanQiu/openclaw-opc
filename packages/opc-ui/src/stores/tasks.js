import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { api } from '@/utils/api'

export const useTaskStore = defineStore('tasks', () => {
  // State
  const tasks = ref([])
  const currentTask = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const taskCount = computed(() => tasks.value.length)
  const pendingCount = computed(() =>
    tasks.value.filter(t => t.status === 'pending').length
  )
  const inProgressCount = computed(() =>
    tasks.value.filter(t => t.status === 'in_progress').length
  )
  const completedCount = computed(() =>
    tasks.value.filter(t => t.status === 'completed').length
  )

  // Actions
  async function fetchTasks(params = {}) {
    loading.value = true
    error.value = null
    try {
      const query = new URLSearchParams(params).toString()
      const url = query ? `/tasks?${query}` : '/tasks'
      const response = await api.get(url)
      tasks.value = response.tasks || []
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchTask(id) {
    loading.value = true
    error.value = null
    try {
      const response = await api.get(`/tasks/${id}`)
      currentTask.value = response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createTask(data) {
    loading.value = true
    try {
      const response = await api.post('/tasks', data)
      await fetchTasks()
      return response
    } finally {
      loading.value = false
    }
  }

  async function updateTask(id, data) {
    loading.value = true
    try {
      const response = await api.put(`/tasks/${id}`, data)
      await fetchTasks()
      return response
    } finally {
      loading.value = false
    }
  }

  async function deleteTask(id) {
    loading.value = true
    try {
      await api.delete(`/tasks/${id}`)
      await fetchTasks()
    } finally {
      loading.value = false
    }
  }

  async function assignTask(taskId, employeeId) {
    loading.value = true
    try {
      const response = await api.post(`/tasks/${taskId}/assign`, {
        employee_id: employeeId
      })
      await fetchTasks()
      return response
    } finally {
      loading.value = false
    }
  }

  async function startTask(taskId) {
    loading.value = true
    try {
      const response = await api.post(`/tasks/${taskId}/start`)
      await fetchTask(taskId)
      return response
    } finally {
      loading.value = false
    }
  }

  async function completeTask(taskId, result, actualCost) {
    loading.value = true
    try {
      const response = await api.post(`/tasks/${taskId}/complete`, {
        result,
        actual_cost: actualCost
      })
      await fetchTask(taskId)
      return response
    } finally {
      loading.value = false
    }
  }

  async function failTask(taskId, reason) {
    loading.value = true
    try {
      const response = await api.post(`/tasks/${taskId}/fail?reason=${encodeURIComponent(reason)}`)
      await fetchTask(taskId)
      return response
    } finally {
      loading.value = false
    }
  }

  async function reworkTask(taskId, feedback) {
    loading.value = true
    try {
      const response = await api.post(`/tasks/${taskId}/rework?feedback=${encodeURIComponent(feedback)}`)
      await fetchTask(taskId)
      return response
    } finally {
      loading.value = false
    }
  }

  return {
    tasks,
    currentTask,
    loading,
    error,
    taskCount,
    pendingCount,
    inProgressCount,
    completedCount,
    fetchTasks,
    fetchTask,
    createTask,
    updateTask,
    deleteTask,
    assignTask,
    startTask,
    completeTask,
    failTask,
    reworkTask,
  }
})
