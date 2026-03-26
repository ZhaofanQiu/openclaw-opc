<template>
  <div class="modal-overlay" @click.self="handleOverlayClick">
    <div class="modal-content" :class="{ 'assist-mode': showAssistPanel }" @click.stop>
      <div class="modal-header">
        <h3>创建新任务</h3>
        <button class="btn-close" @click="$emit('close')">×</button>
      </div>
      
      <form @submit.prevent="handleSubmit">
        <div class="form-row">
          <div class="form-group form-group-large">
            <label>任务标题 *</label>
            <input
              v-model="form.title"
              type="text"
              placeholder="输入任务标题"
              required
            />
          </div>
          
          <div class="form-group">
            <label>分配给 *</label>
            <select v-model="form.employee_id" required>
              <option value="">选择员工</option>
              <option
                v-for="emp in employees"
                :key="emp.id"
                :value="emp.id"
              >
                {{ emp.name }} ({{ emp.position_name }})
              </option>
            </select>
          </div>
        </div>
        
        <!-- Partner 智能辅助区域 -->
        <div class="assist-section">
          <div class="assist-header">
            <span class="assist-icon">✨</span>
            <span>Partner 智能细化</span>
          </div>
          
          <div class="assist-input-row">
            <input
              v-model="assistDescription"
              placeholder="描述你的需求，例如：帮我调研一下最新的AI趋势..."
              :disabled="assistLoading"
            />
            <button
              type="button"
              class="btn-assist"
              :disabled="!canAssist || assistLoading"
              @click="requestAssist"
            >
              <span v-if="assistLoading">细化中...</span>
              <span v-else>🚀 AI 细化</span>
            </button>
          </div>
          
          <!-- 细化结果预览 -->
          <div v-if="assistResult" class="assist-preview">
            <div class="preview-header">
              <span>📋 细化方案</span>
              <button type="button" class="btn-apply" @click="applyAssistResult">
                应用方案
              </button>
            </div>
            
            <div class="preview-content">
              <div class="preview-item">
                <label>优化标题</label>
                <p>{{ assistResult.refined_title }}</p>
              </div>
              
              <div class="preview-item">
                <label>详细描述</label>
                <p>{{ assistResult.refined_description }}</p>
              </div>
              
              <div class="preview-item">
                <label>执行步骤</label>
                <ol>
                  <li v-for="(step, idx) in assistResult.execution_steps" :key="idx">
                    {{ step }}
                  </li>
                </ol>
              </div>
              
              <div class="preview-row">
                <div class="preview-item">
                  <label>预估成本</label>
                  <p class="cost-value">
                    {{ assistResult.estimated_cost }} OC币
                    <span class="cost-hint">({{ assistResult.cost_reasoning }})</span>
                  </p>
                </div>
                
                <div class="preview-item" v-if="assistResult.suggested_employee_id && !form.employee_id">
                  <label>推荐员工</label>
                  <p class="employee-suggestion">
                    {{ assistResult.suggested_employee_name }}
                    <span class="employee-reason">{{ assistResult.employee_reasoning }}</span>
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div class="form-group">
          <label>任务描述</label>
          <textarea
            v-model="form.description"
            rows="4"
            placeholder="描述任务内容..."
          ></textarea>
        </div>
        
        <div class="form-row">
          <div class="form-group">
            <label>预估成本 (OC币)</label>
            <input
              v-model.number="form.estimated_cost"
              type="number"
              min="0"
              step="0.1"
              placeholder="0"
            />
          </div>
        </div>
        
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" @click="$emit('close')">
            取消
          </button>
          <button
            type="submit"
            class="btn btn-primary"
            :disabled="submitting || !form.title || !form.employee_id"
          >
            <span v-if="submitting" class="spinner-sm"></span>
            {{ submitting ? '创建中...' : '创建任务' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useEmployeeStore } from '@/stores/employees'
import { usePartnerStore } from '@/stores/partner'

const props = defineProps({
  submitting: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'submit'])

const employeeStore = useEmployeeStore()
const partnerStore = usePartnerStore()

const employees = computed(() => employeeStore.employees)

const form = ref({
  title: '',
  description: '',
  employee_id: '',
  estimated_cost: 100
})

// Partner 辅助相关
const assistDescription = ref('')
const assistLoading = ref(false)
const assistResult = ref(null)
const showAssistPanel = ref(false)

const canAssist = computed(() => {
  return form.value.title.trim() && assistDescription.value.trim()
})

// 请求 Partner 辅助
async function requestAssist() {
  if (!canAssist.value) return
  
  assistLoading.value = true
  assistResult.value = null
  
  try {
    const result = await partnerStore.assistCreateTask({
      title: form.value.title,
      description: assistDescription.value,
      employee_id: form.value.employee_id || undefined
    })
    
    assistResult.value = result
    showAssistPanel.value = true
  } catch (err) {
    alert('AI 细化失败: ' + (err.message || '未知错误'))
  } finally {
    assistLoading.value = false
  }
}

// 应用细化结果
function applyAssistResult() {
  if (!assistResult.value) return
  
  // 应用优化后的标题
  if (assistResult.value.refined_title) {
    form.value.title = assistResult.value.refined_title
  }
  
  // 应用详细描述
  if (assistResult.value.refined_description) {
    form.value.description = assistResult.value.refined_description
  }
  
  // 应用成本建议
  if (assistResult.value.estimated_cost) {
    form.value.estimated_cost = assistResult.value.estimated_cost
  }
  
  // 应用推荐的员工（如果当前未选择）
  if (assistResult.value.suggested_employee_id && !form.value.employee_id) {
    form.value.employee_id = assistResult.value.suggested_employee_id
  }
  
  alert('已应用细化方案！标题、描述和成本已更新。')
}

function handleOverlayClick() {
  if (!props.submitting && !assistLoading.value) {
    emit('close')
  }
}

function handleSubmit() {
  emit('submit', { ...form.value })
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
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
  transition: max-width 0.3s;
}

.modal-content.assist-mode {
  max-width: 650px;
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

.btn-close {
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
  border-radius: 6px;
}

.btn-close:hover {
  background: var(--bg-secondary, #f5f5f5);
}

form {
  padding: 24px;
}

.form-row {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
}

.form-row .form-group {
  flex: 1;
  margin-bottom: 0;
}

.form-row .form-group-large {
  flex: 2;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #333);
}

.form-group input,
.form-group textarea,
.form-group select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-color, #ddd);
  border-radius: 6px;
  font-size: 14px;
  background: var(--bg-primary, #fff);
  color: var(--text-primary, #333);
  box-sizing: border-box;
}

.form-group input:focus,
.form-group textarea:focus,
.form-group select:focus {
  outline: none;
  border-color: var(--color-primary, #1976d2);
}

.form-group textarea {
  resize: vertical;
  min-height: 80px;
}

/* Partner 辅助区域 */
.assist-section {
  margin-bottom: 20px;
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
  font-size: 14px;
  font-weight: 500;
  color: #4f46e5;
}

.assist-icon {
  font-size: 18px;
}

.assist-input-row {
  display: flex;
  gap: 8px;
}

.assist-input-row input {
  flex: 1;
  padding: 10px 12px;
  border: 1px solid var(--border-color, #ddd);
  border-radius: 6px;
  font-size: 14px;
}

.assist-input-row input:focus {
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
.assist-preview {
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
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-color, #e0e0e0);
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

.preview-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.preview-item label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary, #666);
  margin-bottom: 4px;
}

.preview-item p {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-primary, #333);
}

.preview-item ol {
  margin: 0;
  padding-left: 20px;
}

.preview-item li {
  font-size: 13px;
  color: var(--text-primary, #333);
  margin-bottom: 4px;
}

.preview-row {
  display: flex;
  gap: 16px;
}

.preview-row .preview-item {
  flex: 1;
}

.cost-value {
  color: var(--color-success, #4caf50) !important;
  font-weight: 500;
}

.cost-hint {
  font-size: 12px;
  color: var(--text-secondary, #999);
  margin-left: 8px;
}

.employee-suggestion {
  color: var(--color-primary, #1976d2) !important;
  font-weight: 500;
}

.employee-reason {
  font-size: 12px;
  color: var(--text-secondary, #666);
  margin-left: 8px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color, #e0e0e0);
  margin-top: 8px;
}

.btn {
  padding: 10px 20px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--color-primary, #1976d2);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-dark, #1565c0);
}

.btn-secondary {
  background: var(--bg-secondary, #f5f5f5);
  color: var(--text-primary, #333);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-tertiary, #e0e0e0);
}

.spinner-sm {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-right-color: white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
