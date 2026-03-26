<template>
  <div class="modal-overlay" @click.self="close">
    <div class="modal-content" :class="{ 'assist-mode': showAssistPanel }">
      <div class="modal-header">
        <h3>雇佣新员工</h3>
        <button class="close-btn" @click="close">×</button>
      </div>
      
      <div class="modal-body">
        <!-- 基础表单 -->
        <form @submit.prevent="handleSubmit">
          <div class="form-group">
            <label>姓名 *</label>
            <input 
              v-model="form.name" 
              required 
              maxlength="50"
              placeholder="请输入员工姓名"
            />
          </div>
          
          <div class="form-group">
            <label>职位 *</label>
            <select v-model.number="form.position_level" required>
              <option :value="1">实习生</option>
              <option :value="2">专员</option>
              <option :value="3">资深</option>
              <option :value="4">专家</option>
              <option :value="5">合伙人</option>
            </select>
          </div>
          
          <div class="form-group">
            <label>月预算 (OC币) *</label>
            <input 
              v-model.number="form.monthly_budget" 
              type="number" 
              min="100"
              required
              placeholder="例如：1500"
            />
            <p class="hint">建议预算：500-8000 OC币 (1 OC币 ≈ 1000 tokens)</p>
          </div>
          
          <div class="form-group">
            <label>工种 *</label>
            <select v-model="form.job_type" required>
              <option value="researcher">研究员</option>
              <option value="analyst">分析师</option>
              <option value="reviewer">审查员</option>
              <option value="developer">开发工程师</option>
              <option value="designer">设计师</option>
              <option value="writer">内容创作</option>
              <option value="general">通用型</option>
            </select>
            <p class="hint">工种决定员工的专长领域和默认技能</p>
          </div>
          
          <!-- AI 辅助设计区域 -->
          <div class="assist-section">
            <div class="assist-header">
              <span class="assist-icon">✨</span>
              <span>Partner 智能设计</span>
            </div>
            
            <div class="assist-input">
              <input
                v-model="assistIntent"
                placeholder="描述你对这位员工的期望，例如：帮我设计一个擅长数据分析的员工..."
                :disabled="assistLoading"
              />
              <button
                type="button"
                class="btn-assist"
                :disabled="!canAssist || assistLoading"
                @click="requestAssist"
              >
                {{ assistLoading ? '设计中...' : 'AI 设计' }}
              </button>
            </div>
            
            <!-- 设计方案预览 -->
            <div v-if="assistResult" class="assist-preview">
              <div class="preview-header">
                <span>📋 设计方案</span>
                <button type="button" class="btn-apply" @click="applyAssistResult">
                  应用此方案
                </button>
              </div>
              
              <div class="preview-content">
                <div class="preview-item">
                  <label>背景故事</label>
                  <p>{{ assistResult.background }}</p>
                </div>
                
                <div class="preview-item">
                  <label>性格特点</label>
                  <p>{{ assistResult.personality }}</p>
                </div>
                
                <div class="preview-item">
                  <label>行事风格</label>
                  <p>{{ assistResult.working_style }}</p>
                </div>
                
                <div class="preview-item">
                  <label>技能专长</label>
                  <div class="skills-list">
                    <span 
                      v-for="skill in assistResult.skills" 
                      :key="skill"
                      class="skill-tag"
                    >
                      {{ skill }}
                    </span>
                  </div>
                </div>
                
                <div class="preview-item">
                  <label>推荐预算</label>
                  <p class="budget-suggestion">
                    {{ assistResult.suggested_budget }} OC币
                    <span class="budget-hint">(约 {{ (assistResult.suggested_budget * 1000).toLocaleString() }} tokens)</span>
                  </p>
                </div>
              </div>
            </div>
          </div>
        </form>
      </div>
      
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" @click="close">
          取消
        </button>
        <button 
          type="button" 
          class="btn btn-primary" 
          :disabled="!isValid || submitting"
          @click="handleSubmit"
        >
          {{ submitting ? '创建中...' : '确认雇佣' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useEmployeeStore } from '@/stores/employees'
import { usePartnerStore } from '@/stores/partner'

const emit = defineEmits(['close', 'created'])

const employeeStore = useEmployeeStore()
const partnerStore = usePartnerStore()

const form = ref({
  name: '',
  position_level: 1,
  job_type: 'general',
  monthly_budget: 1500
})

const submitting = ref(false)
const assistLoading = ref(false)
const assistIntent = ref('')
const assistResult = ref(null)
const showAssistPanel = ref(false)

const isValid = computed(() => {
  return form.value.name.trim() && 
         form.value.position_level >= 1 && 
         form.value.position_level <= 5 && 
         form.value.monthly_budget >= 100
})

const canAssist = computed(() => {
  return form.value.name.trim() && 
         form.value.job_type && 
         assistIntent.value.trim()
})

// 请求 Partner 辅助设计
async function requestAssist() {
  if (!canAssist.value) return
  
  assistLoading.value = true
  assistResult.value = null
  
  try {
    const result = await partnerStore.assistCreateEmployee({
      name: form.value.name,
      job_type: form.value.job_type,
      user_intent: assistIntent.value
    })
    
    assistResult.value = result
    showAssistPanel.value = true
  } catch (err) {
    alert('AI 设计失败: ' + (err.message || '未知错误'))
  } finally {
    assistLoading.value = false
  }
}

// 应用设计方案
function applyAssistResult() {
  if (!assistResult.value) return
  
  // 应用预算建议
  if (assistResult.value.suggested_budget) {
    form.value.monthly_budget = Math.round(assistResult.value.suggested_budget)
  }
  
  // 这里可以存储设计方案，用于后续创建员工手册
  // 实际项目中，这些设计数据可以在创建员工后用于生成手册
  
  alert('已应用设计方案！建议的预算和技能已更新。创建员工后，可在员工详情页查看完整设计。')
  
  // 保持结果显示，但标记为已应用
}

async function handleSubmit() {
  if (!isValid.value) return
  
  submitting.value = true
  try {
    // 如果有设计方案，可以一起提交用于生成手册
    const employeeData = {
      ...form.value,
      design_data: assistResult.value // 可选：传递给后端用于初始化手册
    }
    
    await employeeStore.createEmployee(employeeData)
    emit('created')
    close()
  } catch (err) {
    alert('创建失败: ' + err.message)
  } finally {
    submitting.value = false
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
  border-radius: 8px;
  width: 90%;
  max-width: 480px;
  max-height: 90vh;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  transition: max-width 0.3s;
}

.modal-content.assist-mode {
  max-width: 600px;
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

.form-group input, .form-group select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-color, #ddd);
  border-radius: 6px;
  font-size: 14px;
  background: var(--bg-primary, #fff);
  color: var(--text-primary, #333);
  box-sizing: border-box;
}

.form-group input::placeholder {
  color: var(--text-secondary, #999);
}

.form-group select {
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23666' d='M6 8L1 3h10z'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  padding-right: 32px;
}

.form-group input:focus {
  outline: none;
  border-color: var(--color-primary, #1976d2);
}

.hint {
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-secondary, #666);
}

/* 辅助设计区域 */
.assist-section {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px dashed var(--border-color, #e0e0e0);
}

.assist-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-primary, #1976d2);
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
  background: var(--bg-primary, #fff);
}

.assist-input input:focus {
  outline: none;
  border-color: var(--color-primary, #1976d2);
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

/* 设计方案预览 */
.assist-preview {
  margin-top: 16px;
  padding: 16px;
  background: var(--bg-secondary, #f8f9fa);
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

.skills-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.skill-tag {
  padding: 4px 10px;
  background: var(--color-primary-bg, #e3f2fd);
  color: var(--color-primary, #1976d2);
  border-radius: 12px;
  font-size: 12px;
}

.budget-suggestion {
  color: var(--color-success, #4caf50) !important;
  font-weight: 500;
}

.budget-hint {
  font-size: 12px;
  color: var(--text-secondary, #999);
  margin-left: 8px;
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
