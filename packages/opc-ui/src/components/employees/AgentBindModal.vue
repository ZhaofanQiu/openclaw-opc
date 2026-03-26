<template>
  <div class="modal-overlay" @click.self="close">
    <div class="modal-content">
      <div class="modal-header">
        <h3>绑定 OpenClaw Agent</h3>
        <button class="close-btn" @click="close">×</button>
      </div>
      
      <div class="modal-body">
        <!-- 创建新 Agent 模式 -->
        <div v-if="mode === 'create'" class="create-agent-section">
          <div class="warning-box">
            <p>⚠️ <strong>重要提示</strong></p>
            <p>创建新 Agent 需要：</p>
            <ul>
              <li>修改 OpenClaw 配置文件</li>
              <li>重启 OpenClaw Gateway</li>
              <li>等待约 30 秒完成重启</li>
            </ul>
            <p>此操作会中断当前所有对话，请确认后再继续。</p>
          </div>
          
          <div class="form-group">
            <label>Agent ID *</label>
            <input 
              v-model="newAgentId" 
              placeholder="例如：opc_worker_1"
              maxlength="50"
            />
            <p class="hint">必须以 opc_ 或 opc- 开头，只能包含字母、数字、下划线、连字符</p>
          </div>
          
          <div class="form-group">
            <label>显示名称</label>
            <input 
              v-model="newAgentName" 
              placeholder="例如：研发专员"
              maxlength="50"
            />
          </div>
          
          <div class="form-group checkbox-group">
            <label class="checkbox-label">
              <input type="checkbox" v-model="confirmRestart" />
              <span>我已了解，确认要创建 Agent 并重启 Gateway</span>
            </label>
          </div>
          
          <div v-if="creating" class="creating-progress">
            <div class="spinner"></div>
            <p>{{ createStatus }}</p>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: createProgress + '%' }"></div>
            </div>
          </div>
        </div>
        
        <!-- 选择现有 Agent 模式 -->
        <template v-else>
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
            <p class="hint">点击下方按钮创建新 Agent</p>
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
          
          <!-- 创建新 Agent 按钮 -->
          <div class="create-agent-option">
            <div class="divider">
              <span>或</span>
            </div>
            <button type="button" class="btn btn-secondary btn-block" @click="switchToCreateMode">
              <span class="icon">+</span> 创建新 Agent
            </button>
          </div>
        </template>
      </div>
      
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" @click="close">
          取消
        </button>
        
        <!-- 创建模式按钮 -->
        <template v-if="mode === 'create'">
          <button 
            type="button" 
            class="btn btn-secondary" 
            @click="mode = 'select'"
            :disabled="creating"
          >
            返回选择
          </button>
          <button 
            type="button" 
            class="btn btn-primary" 
            :disabled="!canCreate || creating"
            @click="handleCreate"
          >
            {{ creating ? '创建中...' : '确认创建' }}
          </button>
        </template>
        
        <!-- 选择模式按钮 -->
        <button 
          v-else
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

// 模式：'select' | 'create'
const mode = ref('select')

// 选择现有 Agent
const availableAgents = ref([])
const selectedAgent = ref('')
const loadingAgents = ref(false)
const binding = ref(false)
const error = ref(null)

// 创建新 Agent
const newAgentId = ref('')
const newAgentName = ref('')
const confirmRestart = ref(false)
const creating = ref(false)
const createStatus = ref('')
const createProgress = ref(0)

// 获取所有员工，检查哪些 Agent 已被绑定
const allEmployees = computed(() => employeeStore.employees)

const canCreate = computed(() => {
  const id = newAgentId.value.trim()
  if (!id) return false
  if (!(id.startsWith('opc_') || id.startsWith('opc-'))) return false
  if (id === 'main' || id === 'default') return false
  if (!confirmRestart.value) return false
  return true
})

function isBound(agentId) {
  return allEmployees.value.some(
    e => e.id !== props.employee.id && e.openclaw_agent_id === agentId
  )
}

function switchToCreateMode() {
  mode.value = 'create'
  // 自动生成建议的 ID
  const existingIds = allEmployees.value
    .filter(e => e.openclaw_agent_id)
    .map(e => e.openclaw_agent_id)
  
  let nextNum = 1
  while (existingIds.includes(`opc_worker_${nextNum}`)) {
    nextNum++
  }
  newAgentId.value = `opc_worker_${nextNum}`
  newAgentName.value = `Worker ${nextNum}`
}

async function fetchAvailableAgents() {
  loadingAgents.value = true
  error.value = null
  try {
    const response = await api.get('/employees/openclaw/available')
    
    if (response?.agents && response.agents.length > 0) {
      availableAgents.value = response.agents
    } else {
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

async function handleCreate() {
  if (!canCreate.value) return
  
  creating.value = true
  createProgress.value = 0
  createStatus.value = '正在创建 Agent...'
  
  // 模拟进度条
  const progressInterval = setInterval(() => {
    if (createProgress.value < 90) {
      createProgress.value += 2
    }
  }, 600)
  
  try {
    const response = await api.post('/employees/openclaw/create-agent', {
      agent_id: newAgentId.value.trim(),
      name: newAgentName.value.trim() || newAgentId.value.trim(),
      confirm_restart: true
    })
    
    clearInterval(progressInterval)
    createProgress.value = 100
    createStatus.value = '创建完成！'
    
    // 等待一下让用户看到完成状态
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // 切换回选择模式并刷新列表
    mode.value = 'select'
    await fetchAvailableAgents()
    
    // 自动选中新创建的 Agent
    selectedAgent.value = newAgentId.value.trim()
    
    alert('Agent 创建成功！请确认绑定。')
    
  } catch (err) {
    clearInterval(progressInterval)
    alert('创建失败: ' + (err.message || '未知错误'))
  } finally {
    creating.value = false
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
  employeeStore.fetchEmployees()
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
  max-height: 60vh;
  overflow-y: auto;
}

/* 创建 Agent 部分 */
.warning-box {
  background: #fff3e0;
  border: 1px solid #ffb74d;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 20px;
  color: #e65100;
}

.warning-box p {
  margin: 0 0 8px 0;
}

.warning-box ul {
  margin: 8px 0;
  padding-left: 20px;
}

.warning-box li {
  margin-bottom: 4px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #333);
  margin-bottom: 6px;
}

.form-group input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-color, #ddd);
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
}

.form-group input:focus {
  outline: none;
  border-color: var(--color-primary, #1976d2);
}

.checkbox-group {
  margin-top: 20px;
}

.checkbox-label {
  display: flex !important;
  align-items: flex-start;
  gap: 8px;
  cursor: pointer;
}

.checkbox-label input {
  width: auto;
  margin-top: 2px;
}

.checkbox-label span {
  font-size: 14px;
  color: var(--text-primary, #333);
  line-height: 1.4;
}

.hint {
  font-size: 12px;
  color: var(--text-secondary, #999);
  margin-top: 4px;
}

/* 创建进度 */
.creating-progress {
  text-align: center;
  padding: 20px;
}

.creating-progress .spinner {
  margin: 0 auto 12px;
}

.creating-progress p {
  margin: 0 0 12px 0;
  color: var(--text-primary, #333);
}

.progress-bar {
  height: 6px;
  background: var(--bg-secondary, #f5f5f5);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--color-primary, #1976d2);
  border-radius: 3px;
  transition: width 0.3s;
}

/* 员工预览 */
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

/* 加载和空状态 */
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

/* Agent 列表 */
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

/* 创建新 Agent 选项 */
.create-agent-option {
  margin-top: 20px;
}

.divider {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
  color: var(--text-secondary, #999);
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border-color, #e0e0e0);
}

.divider span {
  padding: 0 12px;
  font-size: 13px;
}

.btn-block {
  width: 100%;
}

.icon {
  margin-right: 4px;
}

/* 底部按钮 */
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
