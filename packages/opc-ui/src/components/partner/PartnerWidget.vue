<template>
  <div class="partner-widget" :class="{ 'expanded': isOpen }" v-if="hasPartner">
    <!-- 头部（点击展开/收起） -->
    <div class="partner-widget-header" @click="toggleChat">
      <div class="partner-avatar">👑</div>
      <div class="partner-info">
        <div class="partner-name">Partner</div>
        <div class="partner-status">
          {{ isOpen ? '在线 - 点击收起' : '点击展开对话' }}
        </div>
      </div>
      <div class="partner-toggle">
        {{ isOpen ? '▼' : '▲' }}
      </div>
    </div>
    
    <!-- 聊天窗口 -->
    <div v-show="isOpen" class="partner-chat-container">
      <!-- 快捷操作栏 -->
      <div class="quick-actions-bar">
        <button 
          v-for="action in quickActions" 
          :key="action.id"
          @click.stop="handleQuickAction(action)"
          :title="action.description"
        >
          <span class="icon">{{ action.icon }}</span>
          <span class="label">{{ action.label }}</span>
        </button>
      </div>
      
      <!-- 消息列表 -->
      <div class="partner-chat-messages" ref="messagesContainer">
        <div 
          v-for="(msg, index) in messages" 
          :key="index"
          :class="['chat-message', msg.role]"
        >
          <div class="message-content" v-html="renderMarkdown(msg.content)"></div>
          <div v-if="msg.action" class="message-action">
            ✅ 已执行: {{ msg.action }}
          </div>
        </div>
        
        <!-- 加载状态 -->
        <div v-if="loading" class="chat-message partner loading">
          <span class="dot-flashing"></span>
        </div>
      </div>
      
      <!-- 输入框 -->
      <div class="partner-chat-input-area">
        <input 
          ref="inputRef"
          v-model="inputMessage" 
          @keyup.enter="sendMessage"
          placeholder="输入消息，或点击上方快捷按钮..."
          :disabled="loading"
        />
        <button 
          @click="sendMessage" 
          :disabled="!inputMessage.trim() || loading"
        >
          发送
        </button>
      </div>
    </div>
  </div>
  
  <!-- 无 Partner 时的引导 -->
  <div v-else-if="isInitialized" class="partner-widget partner-onboarding" @click="goToEmployees">
    <div class="partner-widget-header">
      <div class="partner-avatar">👑</div>
      <div class="partner-info">
        <div class="partner-name">创建 Partner</div>
        <div class="partner-status">点击创建合伙人</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { usePartnerStore } from '@/stores/partner'
import { marked } from 'marked'

const router = useRouter()
const partnerStore = usePartnerStore()

// 状态
const isOpen = ref(false)
const inputMessage = ref('')
const loading = ref(false)
const messagesContainer = ref(null)
const inputRef = ref(null)
const isInitialized = ref(false)

// 计算属性
const hasPartner = computed(() => partnerStore.hasPartner)
const messages = computed(() => partnerStore.messages)

// 快捷操作
const quickActions = [
  { 
    id: 'create_task', 
    icon: '📝', 
    label: '任务',
    description: '快速创建任务',
    handler: () => openCreateTaskDialog()
  },
  { 
    id: 'create_workflow', 
    icon: '🔄', 
    label: '工作流',
    description: '一句话创建工作流',
    handler: () => openCreateWorkflowDialog()
  },
  { 
    id: 'create_employee', 
    icon: '👤', 
    label: '员工',
    description: '智能创建员工',
    handler: () => openCreateEmployeeDialog()
  },
  { 
    id: 'update_manual', 
    icon: '📖', 
    label: '手册',
    description: '修改公司手册',
    handler: () => openUpdateManualDialog()
  },
  { 
    id: 'view_status', 
    icon: '📊', 
    label: '状态',
    description: '查看公司状态',
    handler: () => viewCompanyStatus()
  }
]

// 方法
const toggleChat = () => {
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    nextTick(() => {
      scrollToBottom()
      inputRef.value?.focus()
    })
  }
}

const sendMessage = async () => {
  if (!inputMessage.value.trim() || loading.value) return
  
  const message = inputMessage.value
  inputMessage.value = ''
  loading.value = true
  
  try {
    await partnerStore.sendMessage(message)
  } catch (error) {
    console.error('发送消息失败:', error)
  } finally {
    loading.value = false
    nextTick(scrollToBottom)
  }
}

const handleQuickAction = (action) => {
  action.handler()
}

const openCreateTaskDialog = () => {
  // 快速输入任务描述
  inputMessage.value = '帮我创建任务：'
  inputRef.value?.focus()
}

const openCreateWorkflowDialog = () => {
  inputMessage.value = '帮我创建工作流：'
  inputRef.value?.focus()
}

const openCreateEmployeeDialog = () => {
  inputMessage.value = '帮我创建员工：'
  inputRef.value?.focus()
}

const openUpdateManualDialog = () => {
  inputMessage.value = '帮我修改公司手册：'
  inputRef.value?.focus()
}

const viewCompanyStatus = async () => {
  loading.value = true
  try {
    await partnerStore.sendMessage('查看公司状态')
    nextTick(scrollToBottom)
  } finally {
    loading.value = false
  }
}

const goToEmployees = () => {
  router.push('/employees')
}

const renderMarkdown = (text) => {
  if (!text) return ''
  return marked.parse(text, { breaks: true, gfm: true })
}

const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// 监听消息变化
watch(messages, () => {
  nextTick(scrollToBottom)
}, { deep: true })

// 初始化
onMounted(async () => {
  await partnerStore.initialize()
  isInitialized.value = true
})
</script>

<style scoped>
.partner-widget {
  position: fixed;
  bottom: 20px;
  right: 20px;
  width: 60px;
  height: 60px;
  background: #1a1a2e;
  border: 1px solid #2a2a4a;
  border-radius: 30px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
  z-index: 1000;
  overflow: hidden;
  transition: all 0.3s ease;
}

.partner-widget.expanded {
  width: 380px;
  height: 500px;
  border-radius: 16px;
}

.partner-widget-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: linear-gradient(135deg, #667eea20 0%, #764ba220 100%);
  cursor: pointer;
  height: 60px;
  user-select: none;
}

.partner-avatar {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.partner-info {
  flex: 1;
  min-width: 0;
}

.partner-name {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
}

.partner-status {
  font-size: 12px;
  color: #888;
}

.partner-toggle {
  font-size: 12px;
  color: #888;
  transition: transform 0.3s;
}

.partner-chat-container {
  height: 440px;
  display: flex;
  flex-direction: column;
  background: #141425;
}

.quick-actions-bar {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-bottom: 1px solid #2a2a4a;
  overflow-x: auto;
}

.quick-actions-bar button {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border: 1px solid #667eea;
  background: transparent;
  color: #667eea;
  border-radius: 16px;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}

.quick-actions-bar button:hover {
  background: #667eea20;
}

.partner-chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chat-message {
  max-width: 85%;
  padding: 12px 16px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.5;
}

.chat-message.user {
  align-self: flex-end;
  background: #667eea;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.chat-message.partner {
  align-self: flex-start;
  background: #2a2a4a;
  color: #e0e0e0;
  border-bottom-left-radius: 4px;
}

.chat-message.loading {
  background: transparent;
}

.message-content :deep(p) {
  margin: 0 0 8px 0;
}

.message-content :deep(p:last-child) {
  margin-bottom: 0;
}

.message-content :deep(code) {
  background: #1a1a2e;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
}

.message-action {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #3a3a5a;
  font-size: 12px;
  color: #4ade80;
}

.partner-chat-input-area {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid #2a2a4a;
  background: #1a1a2e;
}

.partner-chat-input-area input {
  flex: 1;
  background: #252542;
  border: 1px solid #3a3a5a;
  color: #fff;
  padding: 10px 14px;
  border-radius: 20px;
  font-size: 14px;
  outline: none;
}

.partner-chat-input-area input:focus {
  border-color: #667eea;
}

.partner-chat-input-area button {
  padding: 10px 20px;
  background: #667eea;
  border: none;
  color: #fff;
  border-radius: 20px;
  font-size: 14px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.partner-chat-input-area button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 加载动画 */
.dot-flashing {
  position: relative;
  width: 10px;
  height: 10px;
  border-radius: 5px;
  background-color: #667eea;
  color: #667eea;
  animation: dot-flashing 1s infinite linear alternate;
  animation-delay: 0.5s;
}

@keyframes dot-flashing {
  0% { background-color: #667eea; }
  50%, 100% { background-color: #2a2a4a; }
}

/* 引导样式 */
.partner-onboarding {
  cursor: pointer;
}

.partner-onboarding .partner-avatar {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(102, 126, 234, 0.4); }
  50% { box-shadow: 0 0 0 10px rgba(102, 126, 234, 0); }
}
</style>
