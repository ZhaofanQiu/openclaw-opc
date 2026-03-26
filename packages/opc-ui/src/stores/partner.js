import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/utils/api'

export const usePartnerStore = defineStore('partner', () => {
  // State
  const partnerId = ref(null)
  const messages = ref([])
  const isLoading = ref(false)
  const isInitialized = ref(false)

  // Getters
  const hasPartner = computed(() => !!partnerId.value)
  const showOnboarding = computed(() => isInitialized.value && !hasPartner.value)

  // Actions
  async function initialize() {
    try {
      // 检查 Partner 状态
      const status = await api.get('/partner/status')
      
      if (status.has_partner) {
        partnerId.value = status.partner_id
        await loadHistory()
      }
    } catch (error) {
      console.error('初始化 Partner 失败:', error)
    }
    
    isInitialized.value = true
  }

  async function loadHistory() {
    if (!partnerId.value) return
    
    try {
      const history = await api.get(`/partner/history?partner_id=${partnerId.value}&limit=50`)
      messages.value = history.map(msg => ({
        id: msg.id,
        role: msg.role,
        content: msg.content,
        action: msg.action_type,
        hasAction: msg.has_action,
        createdAt: msg.created_at
      }))
    } catch (error) {
      console.error('加载历史记录失败:', error)
    }
  }

  async function sendMessage(content) {
    if (!partnerId.value || isLoading.value) return
    
    // 乐观更新：立即显示用户消息
    messages.value.push({
      id: `temp_${Date.now()}`,
      role: 'user',
      content
    })
    
    isLoading.value = true
    
    try {
      const result = await api.post('/partner/chat', {
        partner_id: partnerId.value,
        message: content
      })
      
      // 添加 Partner 回复
      messages.value.push({
        id: `temp_${Date.now()}_reply`,
        role: 'partner',
        content: result.reply,
        action: result.action_executed,
        actionResult: result.action_result
      })
      
      return result
    } catch (error) {
      // 添加错误消息
      messages.value.push({
        id: `temp_${Date.now()}_error`,
        role: 'system',
        content: `❌ 发送失败: ${error.message || '未知错误'}`
      })
      throw error
    } finally {
      isLoading.value = false
    }
  }

  async function clearHistory() {
    if (!partnerId.value) return
    
    try {
      await api.delete(`/partner/history/${partnerId.value}`)
      messages.value = []
    } catch (error) {
      console.error('清空历史失败:', error)
      throw error
    }
  }

  // 智能辅助方法（Phase 2 实现）
  async function assistCreateEmployee(data) {
    return await api.post('/partner/assist/create-employee', data)
  }

  async function assistCreateTask(data) {
    return await api.post('/partner/assist/create-task', data)
  }

  async function assistCreateWorkflow(data) {
    return await api.post('/partner/assist/create-workflow', data)
  }

  async function assistUpdateManual(data) {
    return await api.post('/partner/assist/update-company-manual', data)
  }

  return {
    // State
    partnerId,
    messages,
    isLoading,
    isInitialized,
    // Getters
    hasPartner,
    showOnboarding,
    // Actions
    initialize,
    loadHistory,
    sendMessage,
    clearHistory,
    assistCreateEmployee,
    assistCreateTask,
    assistCreateWorkflow,
    assistUpdateManual
  }
})
