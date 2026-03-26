<template>
  <div class="modal-overlay" @click.self="close">
    <div class="modal-content">
      <div class="modal-header">
        <h3>绑定 OpenClaw Agent</h3>
        <button class="close-btn" @click="close">×</button>
      </div>
      
      <div class="modal-body">
        <div v-if="employee" class="employee-preview">
          <span class="employee-emoji">{{ employee.emoji || '👤' }}</span>
          <div class="employee-info">
            <strong>{{ employee.name }}</strong>
            <span>{{ employee.position_title }}</span>
          </div>
        </div>
        
        <div v-if="loadingAgents" class="loading-state">
          <div class="spinner"></div>
          <p>加载可用 Agent 列表...</p>
        </div>
        
        <div v-else-if="error" class="error-state">
          <p>⚠️ {{ error }}</p>
          <p class="hint">请确保 OpenClaw 已正确安装和配置</p>
        </div>

        <div v-else-if="availableAgents.length === 0" class="empty-state">
          <p>没有可用的 Agent</p>
          <p class="hint">请在 OpenClaw 配置中添加 Agent 后重试</p>
        </div>
        
        <div v-else class="agent-list">
          <label>选择要绑定的 Agent</label>
          
          <div
            v-for="agent in availableAgents"
            :key="agent.id"
            :class="['agent-card', { selected: selectedAgent === agent.id, bound: isBound(agent.id) }]"
            @click="!isBound(agent.id) && (selectedAgent = agent.id)"
          >
            <div class="agent-main">
              <div class="agent-name">
                {{ agent.name || agent.id }}
                <span v-if="isBound(agent.id)" class="bound-tag">已绑定</span>
              </div>
              <div class="agent-model">{{ agent.model || '默认模型' }}</div>
            </div>
            
            <div v-if="selectedAgent === agent.id && !isBound(agent.id)" class="selected-indicator">
              ✓
            </div>
          </div>
        </div>
      </div>
      
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" @click="close">
          取消
        </button>
        <button 
          type="button" 
          class="btn btn-primary" 
          :disabled="!selectedAgent || binding"
          @click="handleBind"
        >
          {{ binding ? '绑定中...' : '确认绑定' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useEmployeeStore } from '@/stores/employees'
import { api } from '@/utils/api'

const props = defineProps({
  employee: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['close', 'bound'])

const employeeStore = useEmployeeStore()

const availableAgents = ref([])
const selectedAgent = ref('')
const loadingAgents = ref(false)
const binding = ref(false)
const error = ref(null)

// 获取所有员工，检查哪些 Agent 已被绑定
const allEmployees = computed(() => employeeStore.employees)

function isBound(agentId) {
  return allEmployees.value.some(
    e => e.id !== props.employee.id && e.openclaw_agent_id === agentId
  )
}

async function fetchAvailableAgents() {
  loadingAgents.value = true
  error.value = null
  try {
    // 从后端 API 获取可用的 OpenClaw Agent 列表
    const response = await api.get('/employees/openclaw/available')
    
    if (response?.agents && response.agents.length > 0) {
      availableAgents.value = response.agents
    } else {
      // 如果后端返回空列表，显示提示
      availableAgents.value = []
      if (response?.error) {
        error.value = `获取 Agent 列表失败: ${response.error}`
      }
    }
  } catch (err) {
    console.error('Failed to fetch agents:', err)
    error.value = '获取 Agent 列表失败，请检查 OpenClaw 配置'
    availableAgents.value = []
  } finally {
    loadingAgents.value = false
  }
}

async function handleBind() {
  if (!selectedAgent.value) return
  
  binding.value = true
  try {
    await employeeStore.bindAgent(props.employee.id, selectedAgent.value)
    emit('bound')
    close()
  } catch (err) {
    alert('绑定失败: ' + err.message)
  } finally {
    binding.value = false
  }
}

function close() {
  emit('close')
}

onMounted(() => {
  fetchAvailableAgents()
  employeeStore.fetchEmployees() // 获取所有员工以检查绑定状态
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-primary, #fff);
  border-radius: 8px;
  width: 90%;
  max-width: 480px;
  max-height: 90vh;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color, #e0e0e0);
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: var(--text-secondary, #666);
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
}

.close-btn:hover {
  background: var(--bg-secondary, #f5f5f5);
}

.modal-body {
  padding: 20px;
  max-height: 50vh;
  overflow-y: auto;
}

.employee-preview {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--bg-secondary, #f5f5f5);
  border-radius: 8px;
  margin-bottom: 20px;
}

.employee-emoji {
  font-size: 32px;
}

.employee-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.employee-info strong {
  font-size: 16px;
}

.employee-info span {
  font-size: 13px;
  color: var(--text-secondary, #666);
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px;
  gap: 16px;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-color, #e0e0e0);
  border-top-color: var(--color-primary, #1976d2);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-state {
  text-align: center;
  padding: 40px;
}

.empty-state p {
  margin: 0 0 8px 0;
  color: var(--text-secondary, #666);
}

.error-state {
  text-align: center;
  padding: 40px;
  color: var(--color-danger, #f44336);
}

.error-state p {
  margin: 0 0 8px 0;
}

.hint {
  font-size: 13px;
  color: var(--text-secondary, #999);
}

.agent-list label {
  display: block;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #333);
}

.agent-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border: 2px solid var(--border-color, #e0e0e0);
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.agent-card:hover:not(.bound) {
  border-color: var(--color-primary, #1976d2);
  background: var(--bg-secondary, #f5f5f5);
}

.agent-card.selected {
  border-color: var(--color-primary, #1976d2);
  background: var(--color-primary-bg, #e3f2fd);
}

.agent-card.bound {
  opacity: 0.5;
  cursor: not-allowed;
  background: var(--bg-secondary, #f5f5f5);
}

.agent-name {
  font-weight: 500;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.bound-tag {
  padding: 2px 8px;
  background: var(--color-warning-bg, #fff3e0);
  color: var(--color-warning, #f57c00);
  font-size: 11px;
  border-radius: 4px;
}

.agent-model {
  font-size: 13px;
  color: var(--text-secondary, #666);
}

.selected-indicator {
  width: 24px;
  height: 24px;
  background: var(--color-primary, #1976d2);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid var(--border-color, #e0e0e0);
}

.btn {
  padding: 10px 20px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--bg-secondary, #f5f5f5);
  color: var(--text-primary, #333);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-tertiary, #e0e0e0);
}

.btn-primary {
  background: var(--color-primary, #1976d2);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-dark, #1565c0);
}
</style>
