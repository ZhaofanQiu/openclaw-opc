<template>
  <div class="modal-overlay" @click.self="close">
    <div class="modal-content">
      <div class="modal-header">
        <h3>📖 编辑公司手册</h3>
        <button class="close-btn" @click="close">×</button>
      </div>
      
      <div class="modal-body">
        <!-- 当前手册内容 -->
        <div class="current-content">
          <label>当前手册内容</label>
          <textarea
            v-model="currentContent"
            rows="8"
            placeholder="加载中..."
            :disabled="loading"
          ></textarea>
        </div>
        
        <!-- Partner 智能修改 -->
        <div class="assist-section">
          <div class="assist-header">
            <span class="assist-icon">✨</span>
            <span>Partner 智能修改</span>
          </div>
          
          <div class="assist-input">
            <input
              v-model="userRequest"
              placeholder="描述你的修改需求，例如：添加关于代码规范的新章节..."
              :disabled="assistLoading || loading"
            />
            <button
              type="button"
              class="btn-assist"
              :disabled="!canAssist || assistLoading || loading"
              @click="requestAssist"
            >
              <span v-if="assistLoading">修改中...</span>
              <span v-else>🚀 AI 修改</span>
            </button>
          </div>
          
          <!-- 修改预览 -->
          <div v-if="updatedContent" class="preview-section">
            <div class="preview-header">
              <span>📝 修改后的内容</span>
              <button type="button" class="btn-apply" @click="applyUpdate">
                应用修改
              </button>
            </div>            
            <textarea
              v-model="updatedContent"
              rows="8"
              class="preview-textarea"
            ></textarea>
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
          :disabled="saving || !currentContent.trim()"
          @click="saveManual"
        >
          <span v-if="saving">保存中...</span>
          <span v-else>保存手册</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { usePartnerStore } from '@/stores/partner'
import { api } from '@/utils/api'

const emit = defineEmits(['close', 'saved'])

const partnerStore = usePartnerStore()

// 状态
const currentContent = ref('')
const userRequest = ref('')
const updatedContent = ref('')
const loading = ref(false)
const saving = ref(false)
const assistLoading = ref(false)

const canAssist = computed(() => {
  return currentContent.value.trim() && userRequest.value.trim()
})

// 加载当前手册
onMounted(async () => {
  loading.value = true
  try {
    const response = await api.get('/manuals/company')
    currentContent.value = response.content || ''
  } catch (err) {
    console.error('加载手册失败:', err)
    // 如果加载失败，使用默认内容
    currentContent.value = '# 公司手册\n\n## 公司简介\n\n（待补充）\n\n## 工作规范\n\n（待补充）\n\n## 沟通方式\n\n（待补充）'
  } finally {
    loading.value = false
  }
})

// 请求 Partner 辅助修改
async function requestAssist() {
  if (!canAssist.value) return
  
  assistLoading.value = true
  updatedContent.value = ''
  
  try {
    const result = await partnerStore.assistUpdateManual({
      current_content: currentContent.value,
      user_request: userRequest.value
    })
    
    updatedContent.value = result.updated_content
  } catch (err) {
    alert('AI 修改失败: ' + (err.message || '未知错误'))
  } finally {
    assistLoading.value = false
  }
}

// 应用修改
function applyUpdate() {
  if (!updatedContent.value) return
  
  currentContent.value = updatedContent.value
  updatedContent.value = ''
  userRequest.value = ''
  
  alert('已应用修改！')
}

// 保存手册
async function saveManual() {
  if (!currentContent.value.trim()) return
  
  saving.value = true
  try {
    await api.put('/manuals/company', {
      content: currentContent.value
    })
    
    emit('saved')
    close()
  } catch (err) {
    alert('保存失败: ' + (err.message || '未知错误'))
  } finally {
    saving.value = false
  }
}

function close() {
  emit('close')
}
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
  border-radius: 12px;
  width: 90%;
  max-width: 700px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
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
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.current-content {
  margin-bottom: 24px;
}

.current-content label,
.assist-header {
  display: block;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #333);
}

.current-content textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid var(--border-color, #ddd);
  border-radius: 6px;
  font-size: 14px;
  font-family: monospace;
  line-height: 1.6;
  resize: vertical;
  min-height: 150px;
  box-sizing: border-box;
}

/* 辅助区域 */
.assist-section {
  padding: 16px;
  background: linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%);
  border-radius: 8px;
  border: 1px solid #e0e7ff;
}

.assist-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  color: #4f46e5;
}

.assist-icon {
  font-size: 18px;
}

.assist-input {
  display: flex;
  gap: 8px;
}

.assist-input input {
  flex: 1;
  padding: 10px 12px;
  border: 1px solid var(--border-color, #ddd);
  border-radius: 6px;
  font-size: 14px;
  background: white;
}

.assist-input input:focus {
  outline: none;
  border-color: #4f46e5;
}

.btn-assist {
  padding: 10px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: opacity 0.2s;
}

.btn-assist:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-assist:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 预览区域 */
.preview-section {
  margin-top: 16px;
  padding: 16px;
  background: white;
  border-radius: 8px;
  border: 1px solid var(--border-color, #e0e0e0);
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-weight: 500;
}

.btn-apply {
  padding: 6px 12px;
  background: var(--color-primary, #1976d2);
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-apply:hover {
  background: var(--color-primary-dark, #1565c0);
}

.preview-textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid var(--border-color, #ddd);
  border-radius: 6px;
  font-size: 14px;
  font-family: monospace;
  line-height: 1.6;
  resize: vertical;
  min-height: 150px;
  background: #f8f9fa;
  box-sizing: border-box;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
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
