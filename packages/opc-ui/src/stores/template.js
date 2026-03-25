"""
opc-ui: 工作流模板 Store (v0.4.2-P2)
"""

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useApi } from '@/composables/useApi'

export const useTemplateStore = defineStore('template', () => {
  const api = useApi()
  
  // State
  const templates = ref([])
  const categories = ref([])
  const currentTemplate = ref(null)
  const loading = ref(false)
  
  // Actions
  const listTemplates = async (params = {}) => {
    const query = new URLSearchParams()
    if (params.category) query.append('category', params.category)
    if (params.sort_by) query.append('sort_by', params.sort_by)
    if (params.is_public !== undefined) query.append('is_public', params.is_public)
    
    const res = await api.get(`/workflow-templates?${query.toString()}`)
    return res.data
  }
  
  const getTemplate = async (id) => {
    const res = await api.get(`/workflow-templates/${id}`)
    currentTemplate.value = res.data.data
    return res.data
  }
  
  const createTemplate = async (data) => {
    const res = await api.post('/workflow-templates', data)
    return res.data
  }
  
  const updateTemplate = async (id, data) => {
    const res = await api.put(`/workflow-templates/${id}`, data)
    return res.data
  }
  
  const deleteTemplate = async (id) => {
    const res = await api.delete(`/workflow-templates/${id}`)
    return res.data
  }
  
  const searchTemplates = async (query, limit = 50) => {
    const res = await api.get(`/workflow-templates/search?q=${encodeURIComponent(query)}&limit=${limit}`)
    return res.data
  }
  
  const getPopularTemplates = async (limit = 10) => {
    const res = await api.get(`/workflow-templates/popular?limit=${limit}`)
    return res.data
  }
  
  const getTopRatedTemplates = async (limit = 10) => {
    const res = await api.get(`/workflow-templates/top-rated?limit=${limit}`)
    return res.data
  }
  
  const getCategoriesAndTags = async () => {
    const res = await api.get('/workflow-templates/categories')
    return res.data
  }
  
  const createWorkflowFromTemplate = async (templateId, data) => {
    const res = await api.post(`/workflow-templates/${templateId}/create-workflow`, data)
    return res.data
  }
  
  const forkTemplate = async (templateId, data) => {
    const res = await api.post(`/workflow-templates/${templateId}/fork`, data)
    return res.data
  }
  
  const rateTemplate = async (templateId, data) => {
    const res = await api.post(`/workflow-templates/${templateId}/rate`, data)
    return res.data
  }
  
  const getTemplateRatings = async (templateId, limit = 20, offset = 0) => {
    const res = await api.get(`/workflow-templates/${templateId}/ratings?limit=${limit}&offset=${offset}`)
    return res.data
  }
  
  const getUserRating = async (templateId) => {
    const res = await api.get(`/workflow-templates/${templateId}/my-rating`)
    return res.data
  }
  
  return {
    // State
    templates,
    categories,
    currentTemplate,
    loading,
    // Actions
    listTemplates,
    getTemplate,
    createTemplate,
    updateTemplate,
    deleteTemplate,
    searchTemplates,
    getPopularTemplates,
    getTopRatedTemplates,
    getCategoriesAndTags,
    createWorkflowFromTemplate,
    forkTemplate,
    rateTemplate,
    getTemplateRatings,
    getUserRating,
  }
})
