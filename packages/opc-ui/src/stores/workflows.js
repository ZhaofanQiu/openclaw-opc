import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { api } from '@/utils/api'

export const useWorkflowStore = defineStore('workflows', () => {
  // State
  const workflows = ref([])
  const currentWorkflow = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const workflowCount = computed(() => workflows.value.length)
  const runningCount = computed(() =>
    workflows.value.filter(w => w.status === 'running').length
  )
  const completedCount = computed(() =>
    workflows.value.filter(w => w.status === 'completed').length
  )

  // Actions
  async function fetchWorkflows() {
    loading.value = true
    error.value = null
    try {
      const response = await api.get('/workflows')
      workflows.value = response.workflows || []
      return workflows.value
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchWorkflow(id) {
    loading.value = true
    error.value = null
    try {
      const response = await api.get(`/workflows/${id}`)
      currentWorkflow.value = response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchWorkflowProgress(id) {
    try {
      const response = await api.get(`/workflows/${id}/progress`)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function createWorkflow(data) {
    loading.value = true
    try {
      const response = await api.post('/workflows', data)
      await fetchWorkflows()
      return response
    } finally {
      loading.value = false
    }
  }

  async function deleteWorkflow(id) {
    loading.value = true
    try {
      await api.delete(`/workflows/${id}`)
      await fetchWorkflows()
    } finally {
      loading.value = false
    }
  }

  async function requestRework(workflowId, data) {
    loading.value = true
    try {
      const response = await api.post(`/workflows/${workflowId}/rework`, data)
      await fetchWorkflow(workflowId)
      return response
    } finally {
      loading.value = false
    }
  }

  // v0.4.2-P2: 时间线功能
  async function getTimeline(workflowId) {
    try {
      const response = await api.get(`/workflows/${workflowId}/timeline`)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function getTimelineSummary(workflowId) {
    try {
      const response = await api.get(`/workflows/${workflowId}/timeline/summary`)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  return {
    // State
    workflows,
    currentWorkflow,
    loading,
    error,
    // Getters
    workflowCount,
    runningCount,
    completedCount,
    // Actions
    fetchWorkflows,
    fetchWorkflow,
    fetchWorkflowProgress,
    createWorkflow,
    deleteWorkflow,
    requestRework,
    // v0.4.2-P2
    getTimeline,
    getTimelineSummary,
  }
})
