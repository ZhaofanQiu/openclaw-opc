/**
 * opc-ui: Agent 日志 Store
 *
 * 管理 Agent 交互日志的状态和 API 调用
 *
 * 作者: OpenClaw OPC Team
 * 创建日期: 2026-03-27
 * 版本: 0.4.5
 */

import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { useAuthStore } from './auth'

const API_BASE = '/api/v1'

export const useAgentLogsStore = defineStore('agentLogs', () => {
  const authStore = useAuthStore()
  
  // ============ State ============
  const logs = ref([])
  const stats = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const total = ref(0)
  
  // ============ Getters ============
  const hasLogs = computed(() => logs.value.length > 0)
  const successRate = computed(() => stats.value?.success_rate || 0)
  const totalLogs = computed(() => stats.value?.total_logs || 0)
  
  // ============ Actions ============
  
  async function fetchLogs(params = {}) {
    loading.value = true
    error.value = null
    
    try {
      const queryParams = new URLSearchParams()
      
      if (params.agent_id) queryParams.set('agent_id', params.agent_id)
      if (params.interaction_type) queryParams.set('interaction_type', params.interaction_type)
      if (params.direction) queryParams.set('direction', params.direction)
      if (params.task_id) queryParams.set('task_id', params.task_id)
      if (params.hours) queryParams.set('hours', params.hours.toString())
      if (params.limit) queryParams.set('limit', params.limit.toString())
      if (params.offset !== undefined) queryParams.set('offset', params.offset.toString())
      
      const response = await fetch(`${API_BASE}/agent-logs?${queryParams}`, {
        headers: {
          'X-API-Key': authStore.apiKey,
        },
      })
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      
      const data = await response.json()
      logs.value = data.logs || []
      total.value = data.total || 0
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }
  
  async function fetchStats(params = {}) {
    loading.value = true
    error.value = null
    
    try {
      const queryParams = new URLSearchParams()
      
      if (params.agent_id) queryParams.set('agent_id', params.agent_id)
      if (params.hours) queryParams.set('hours', params.hours.toString())
      
      const response = await fetch(`${API_BASE}/agent-logs/stats?${queryParams}`, {
        headers: {
          'X-API-Key': authStore.apiKey,
        },
      })
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      
      const data = await response.json()
      stats.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }
  
  async function fetchLogDetail(logId) {
    loading.value = true
    error.value = null
    
    try {
      const response = await fetch(`${API_BASE}/agent-logs/${logId}`, {
        headers: {
          'X-API-Key': authStore.apiKey,
        },
      })
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      
      return await response.json()
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }
  
  async function clearLogs(agentId = null) {
    loading.value = true
    error.value = null
    
    try {
      const queryParams = agentId ? `?agent_id=${encodeURIComponent(agentId)}` : ''
      
      const response = await fetch(`${API_BASE}/agent-logs${queryParams}`, {
        method: 'DELETE',
        headers: {
          'X-API-Key': authStore.apiKey,
        },
      })
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      
      const data = await response.json()
      
      // 清空后刷新列表
      logs.value = []
      total.value = 0
      
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }
  
  // ============ Return ============
  return {
    // State
    logs,
    stats,
    loading,
    error,
    total,
    // Getters
    hasLogs,
    successRate,
    totalLogs,
    // Actions
    fetchLogs,
    fetchStats,
    fetchLogDetail,
    clearLogs,
  }
})
