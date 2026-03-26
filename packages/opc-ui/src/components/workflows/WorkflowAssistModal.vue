<template>
  <div class="modal-overlay" @click.self="close">
    <div class="modal-content">
      <div class="modal-header">
        <h3>🪄 一句话创建工作流</h3>
        <button class="close-btn" @click="close">×</button>
      </div>
      
      <div class="modal-body">
        <!-- 自然语言输入 -->
        <div v-if="!previewResult" class="input-section">
          <label>描述你想要的工作流</label>
          <textarea
            v-model="description"
            placeholder="例如：帮我做一个内容创作流程，从选题到发布，包括调研、写作、配图、审核四个步骤..."
            :disabled="loading"
            rows="4"
          />
          
          <div class="examples">
            <p>💡 示例：</p>
            <div class="example-list">
              <button 
                v-for="ex in examples" 
                :key="ex"
                type="button"
                class="example-btn"
                @click="description = ex"
                :disabled="loading"
              >
                {{ ex }}
              </button>
            </div>
          </div>
          
          <button
            type="button"
            class="btn-generate"
            :disabled="!description.trim() || loading"
            @click="generateWorkflow"
          >
            <span v-if="loading">✨ Partner 正在设计...</span>
            <span v-else>🚀 生成工作流</span>
          </button>
        </div>
        
        <!-- 预览结果 -->
        <div v-else class="preview-section">
          <div class="preview-header">
            <div class="workflow-title">
              <h4>{{ previewResult.name }}</h4>
              <p>{{ previewResult.description }}</p>
            </div>            
            <div class="total-cost">
              <label>预估总成本</label>
              <span class="cost-value">{{ previewResult.total_estimated_cost }} OC币</span>
            </div>
          </div>
          
          <div class="steps-list">
            <div
              v-for="(step, index) in previewResult.steps"
              :key="index"
              class="step-item"
            >
              <div class="step-number">{{ index + 1 }}</div>
              
              <div class="step-content">
                <div class="step-header">
                  <span class="step-title">{{ step.title }}</span>
                  <span class="step-cost">{{ step.estimated_cost }} OC币</span>
                </div>                
                <p class="step-desc">{{ step.description }}</p>                
                <div class="step-assignment">
                  <span class="assignment-label">👤 分配员工：</span>
                  <span class="assignment-name">{{ step.employee_name }}</span>
                </div>
              </div>
            </div>
          </div>
          
          <div class="reasoning-box">
            <label>🧠 设计思路</label>
            <p>{{ previewResult.workflow_reasoning }}</p>
          </div>
        </div>
      </div>
      
      <div class="modal-footer">
        <button 
          v-if="previewResult"
          type="button" 
          class="btn btn-secondary" 
          @click="previewResult = null; description = ''"
        >
          重新设计
        </button>
        
        <button type="button" class="btn btn-secondary" @click="close">
          取消
        </button>
        
        <button 
          v-if="previewResult"
          type="button" 
          class="btn btn-primary" 
          :disabled="creating"
          @click="createWorkflow"
        >
          {{ creating ? '创建中...' : '确认创建工作流' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { usePartnerStore } from '@/stores/partner'
import { useWorkflowStore } from '@/stores/workflows'

const emit = defineEmits(['close', 'created'])

const partnerStore = usePartnerStore()
const workflowStore = useWorkflowStore()

const description = ref('')
const loading = ref(false)
const creating = ref(false)
const previewResult = ref(null)

const examples = [
  '帮我做一个内容创作流程，从选题到发布',
  '设计一个代码审查流程，包括自测、互审、合并',
  '创建一个市场调研流程，从需求分析到报告输出',
  '帮我设计一个产品发布流程，包括测试、文档、上线'
]

async function generateWorkflow() {
  if (!description.value.trim()) return
  
  loading.value = true
  previewResult.value = null
  
  try {
    const result = await partnerStore.assistCreateWorkflow({
      description: description.value
    })
    
    previewResult.value = result
  } catch (err) {
    alert('生成失败: ' + (err.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

async function createWorkflow() {
  if (!previewResult.value) return
  
  creating.value = true
  
  try {
    // 转换步骤格式
    const steps = previewResult.value.steps.map((step, index) => ({
      title: step.title,
      description: step.description,
      assigned_to: step.assigned_to,
      estimated_cost: step.estimated_cost,
      dependencies: index > 0 ? [index - 1] : []
    }))
    
    const workflowData = {
      name: previewResult.value.name,
      description: previewResult.value.description,
      steps: steps,
      total_estimated_cost: previewResult.value.total_estimated_cost
    }
    
    const created = await workflowStore.createWorkflow(workflowData)
    emit('created', created)
    close()
  } catch (err) {
    alert('创建失败: ' + (err.message || '未知错误'))
    creating.value = false
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
  max-width: 600px;
  max-height: 90vh;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
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

/* 输入区域 */
.input-section label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 12px;
  color: var(--text-primary, #333);
}

.input-section textarea {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid var(--border-color, #ddd);
  border-radius: 8px;
  font-size: 14px;
  resize: vertical;
  box-sizing: border-box;
  background: var(--bg-primary, #fff);
}

.input-section textarea:focus {
  outline: none;
  border-color: var(--color-primary, #1976d2);
}

.examples {
  margin-top: 16px;
}

.examples p {
  margin: 0 0 8px 0;
  font-size: 12px;
  color: var(--text-secondary, #666);
}

.example-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.example-btn {
  padding: 6px 12px;
  background: var(--bg-secondary, #f5f5f5);
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 16px;
  font-size: 12px;
  color: var(--text-secondary, #666);
  cursor: pointer;
  transition: all 0.2s;
}

.example-btn:hover {
  background: var(--color-primary-bg, #e3f2fd);
  border-color: var(--color-primary, #1976d2);
  color: var(--color-primary, #1976d2);
}

.btn-generate {
  width: 100%;
  margin-top: 20px;
  padding: 14px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-generate:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-generate:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 预览区域 */
.preview-section {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 2px solid var(--border-color, #e0e0e0);
}

.workflow-title h4 {
  margin: 0 0 4px 0;
  font-size: 18px;
  font-weight: 600;
}

.workflow-title p {
  margin: 0;
  font-size: 14px;
  color: var(--text-secondary, #666);
}

.total-cost {
  text-align: right;
}

.total-cost label {
  display: block;
  font-size: 12px;
  color: var(--text-secondary, #666);
  margin-bottom: 4px;
}

.cost-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-primary, #1976d2);
}

.steps-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.step-item {
  display: flex;
  gap: 12px;
  padding: 16px;
  background: var(--bg-secondary, #f8f9fa);
  border-radius: 8px;
  border: 1px solid var(--border-color, #e0e0e0);
}

.step-number {
  width: 28px;
  height: 28px;
  background: var(--color-primary, #1976d2);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.step-content {
  flex: 1;
}

.step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.step-title {
  font-weight: 500;
  font-size: 14px;
}

.step-cost {
  font-size: 12px;
  color: var(--color-success, #4caf50);
  font-weight: 500;
}

.step-desc {
  margin: 0 0 8px 0;
  font-size: 13px;
  color: var(--text-secondary, #666);
  line-height: 1.5;
}

.step-assignment {
  font-size: 12px;
}

.assignment-label {
  color: var(--text-secondary, #999);
}

.assignment-name {
  color: var(--text-primary, #333);
  font-weight: 500;
}

.reasoning-box {
  margin-top: 20px;
  padding: 16px;
  background: #f0f7ff;
  border-radius: 8px;
  border-left: 4px solid var(--color-primary, #1976d2);
}

.reasoning-box label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: var(--color-primary, #1976d2);
  margin-bottom: 8px;
}

.reasoning-box p {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-secondary, #666);
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
