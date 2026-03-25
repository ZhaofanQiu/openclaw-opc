"""
opc-ui: 工作流分析 Store (v0.4.2-P2)
"""

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useApi } from '@/composables/useApi'

export const useAnalyticsStore = defineStore('analytics', () => {
  const api = useApi()
  
  // State
  const stats = ref(null)
  const stepAnalysis = ref([])
  const dailyTrend = ref([])
  const employeeRankings = ref([])
  const loading = ref(false)
  
  // Actions
  const getWorkflowStats = async (days = 30) => {
    const res = await api.get(`/analytics/workflows?days=${days}`)
    stats.value = res.data.data
    return res.data
  }
  
  const getStepAnalysis = async (days = 30) => {
    const res = await api.get(`/analytics/workflows/step-analysis?days=${days}`)
    stepAnalysis.value = res.data.data
    return res.data
  }
  
  const getDailyTrend = async (days = 30) => {
    const res = await api.get(`/analytics/workflows/daily-trend?days=${days}`)
    dailyTrend.value = res.data.data
    return res.data
  }
  
  const getEmployeeRankings = async (days = 30, limit = 10) => {
    const res = await api.get(`/analytics/workflows/employee-ranking?days=${days}&limit=${limit}`)
    employeeRankings.value = res.data.data
    return res.data
  }
  
  const getSingleWorkflowStats = async (workflowId) => {
    const res = await api.get(`/workflows/${workflowId}/stats`)
    return res.data
  }
  
  return {
    // State
    stats,
    stepAnalysis,
    dailyTrend,
    employeeRankings,
    loading,
    // Actions
    getWorkflowStats,
    getStepAnalysis,
    getDailyTrend,
    getEmployeeRankings,
    getSingleWorkflowStats,
  }
})
