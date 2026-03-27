<template>
  <div class="modal-overlay" @click.self="handleOverlayClick">
    <div class="modal-content" :class="{ 'assist-mode': showAssistPanel }" @click.stop>
      <div class="modal-header">
        <h3>创建工作流</h3>
        <button class="btn-close" @click="$emit('close')">×</button>
      </div>

      <form @submit.prevent="handleSubmit">
        <!-- 工作流基本信息 -->
        <div class="form-row">
          <div class="form-group form-group-large">
            <label>工作流名称 *</label>
            <input
              v-model="form.name"
              type="text"
              placeholder="例如：内容创作工作流"
              required
            />
          </div>
        </div>

        <div class="form-group">
          <label>工作流描述</label>
          <textarea
            v-model="form.description"
            rows="2"
            placeholder="描述这个工作流的目标和用途..."
          />
        </div>

        <!-- Partner 智能辅助区域 (v0.4.6) -->
        <div class="assist-section">
          <div class="assist-header">
            <span class="assist-icon">✨</span>
            <span>Partner 智能规划</span>
          </div>

          <div class="assist-input-row">
            <input
              v-model="assistDescription"
              placeholder="描述你的工作流需求，例如：帮我设计一个从选题到发布的文章创作流程..."
              :disabled="assistLoading"
            />
            <button
              type="button"
              class="btn-assist"
              :disabled="!canAssist || assistLoading"
              @click="requestAssist"
            >
              <span v-if="assistLoading">规划中...</span>
              <span v-else>🚀 AI 规划</span>
            </button>
          </div>

          <!-- 规划结果预览 -->
          <div v-if="assistResult" class="assist-preview">
            <div class="preview-header">
              <span>📋 工作流方案</span>
              <div class="preview-actions">
                <button type="button" class="btn-apply" @click="applyAssistResult">
                  应用方案
                </button>
                <button type="button" class="btn-clear" @click="clearAssistResult">
                  清除
                </button>
              </div>
            </div>

            <div class="preview-content">
              <div class="preview-item">
                <label>工作流名称</label>
                <p>{{ assistResult.name }}</p>
              </div>

              <div class="preview-item">
                <label>工作流描述</label>
                <p>{{ assistResult.description }}</p>
              </div>

              <div class="preview-item">
                <label>规划思路</label>
                <p class="reasoning-text">{{ assistResult.workflow_reasoning }}</p>
              </div>

              <div class="preview-item">
                <label>执行步骤 ({{ assistResult.steps.length }}步)</label>
                <div class="steps-preview-list">
                  <div
                    v-for="(step, idx) in assistResult.steps"
                    :key="idx"
                    class="step-preview-item"
                  >
                    <div class="step-preview-header">
                      <span class="step-number">{{ idx + 1 }}</span>
                      <span class="step-title">{{ step.title }}</span>
                      <span class="step-employee">👤 {{ step.employee_name }}</span>
                      <span class="step-cost">💰 {{ step.estimated_cost }} OC币</span>
                    </div>
                    <div class="step-preview-desc">{{ step.description }}</div>
                    <div v-if="step.manual_content" class="step-preview-manual">
                      <span class="manual-badge">📚 含执行手册</span>
                    </div>
                  </div>
                </div>
              </div>

              <div class="preview-item">
                <label>总预估成本</label>
                <p class="cost-value">
                  {{ assistResult.total_estimated_cost }} OC币
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- 步骤列表 (手动模式) -->
        <div class="steps-section">
          <div class="section-header">
            <label>执行步骤 *</label>
            <span class="step-count">{{ form.steps.length }} 个步骤</span>
          </div>

          <div class="steps-list">
            <div
              v-for="(step, index) in form.steps"
              :key="index"
              class="step-card"
            >
              <div class="step-header">
                <span class="step-badge">步骤 {{ index + 1 }}</span>
                <button
                  v-if="form.steps.length > 2"
                  type="button"
                  class="btn-remove-step"
                  @click="removeStep(index)"
                  title="删除此步骤"
                >
                  ×
                </button>
              </div>

              <div class="form-row">
                <div class="form-group form-group-large">
                  <label>步骤标题 *</label>
                  <input
                    v-model="step.title"
                    type="text"
                    placeholder="例如：调研选题"
                    required
                  />
                </div>

                <div class="form-group">
                  <label>分配给 *</label>
                  <select v-model="step.employee_id" required>
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

                <div class="form-group form-group-small">
                  <label>预估成本</label>
                  <input
                    v-model.number="step.estimated_cost"
                    type="number"
                    min="0"
                    step="0.01"
                    placeholder="0.00"
                  />
                </div>
              </div>

              <div class="form-group">
                <label>步骤描述</label>
                <textarea
                  v-model="step.description"
                  rows="2"
                  placeholder="描述此步骤需要完成的工作..."
                />
              </div>

              <!-- v0.4.6: 步骤手册扩展 -->
              <div class="step-manual-section">
                <div class="manual-toggle" @click="toggleManual(index)">
                  <span class="toggle-icon">{{ step.showManual ? '▼' : '▶' }}</span>
                  <span>执行手册 (可选)</span>
                  <span v-if="hasManualContent(step)" class="manual-indicator">●</span>
                </div>

                <div v-if="step.showManual" class="manual-fields">
                  <div class="form-group">
                    <label>执行手册内容</label>
                    <textarea
                      v-model="step.manual_content"
                      rows="3"
                      placeholder="详细的执行指南，包括注意事项、参考资源等..."
                    />
                  </div>

                  <div class="form-row">
                    <div class="form-group">
                      <label>输入要求</label>
                      <input
                        v-model="step.input_requirements"
                        type="text"
                        placeholder="前置步骤需要提供什么..."
                      />
                    </div>

                    <div class="form-group">
                      <label>输出交付物</label>
                      <input
                        v-model="step.output_deliverables"
                        type="text"
                        placeholder="此步骤需要产出什么..."
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <button
            v-if="form.steps.length < 10"
            type="button"
            class="btn-add-step"
            @click="addStep"
          >
            <span>+</span> 添加步骤
          </button>
        </div>

        <!-- 提交按钮 -->
        <div class="form-actions">
          <div class="cost-summary" v-if="totalCost > 0">
            <span>总预估成本:</span>
            <span class="cost-value">{{ totalCost.toFixed(2) }} OC币</span>
          </div>
          <div class="action-buttons">
            <button type="button" class="btn btn-secondary" @click="$emit('close')">
              取消
            </button>
            <button
              type="submit"
              class="btn btn-primary"
              :disabled="!canSubmit || isSubmitting"
            >
              <span v-if="isSubmitting">创建中...</span>
              <span v-else>创建工作流</span>
            </button>
          </div>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useEmployeeStore } from '@/stores/employees'
import { useWorkflowStore } from '@/stores/workflows'
import { usePartnerStore } from '@/stores/partner'

const emit = defineEmits(['close', 'created'])

// Stores
const employeeStore = useEmployeeStore()
const workflowStore = useWorkflowStore()
const partnerStore = usePartnerStore()

// State
const employees = ref([])
const loading = ref(false)
const isSubmitting = ref(false)
const showAssistPanel = ref(false)

// AI 辅助相关
const assistDescription = ref('')
const assistLoading = ref(false)
const assistResult = ref(null)
const assistError = ref(null)

// 表单数据
const form = ref({
  name: '',
  description: '',
  steps: [
    createEmptyStep(),
    createEmptyStep()
  ]
})

// 计算属性
const canAssist = computed(() => {
  return assistDescription.value.trim().length > 5
})

const canSubmit = computed(() => {
  if (!form.value.name.trim()) return false
  if (form.value.steps.length < 2) return false
  return form.value.steps.every(step =>
    step.title.trim() && step.employee_id
  )
})

const totalCost = computed(() => {
  return form.value.steps.reduce((sum, step) => {
    return sum + (parseFloat(step.estimated_cost) || 0)
  }, 0)
})

// 方法
function createEmptyStep() {
  return {
    title: '',
    description: '',
    employee_id: '',
    estimated_cost: 0,
    // v0.4.6: 步骤手册字段
    manual_content: '',
    input_requirements: '',
    output_deliverables: '',
    showManual: false
  }
}

function addStep() {
  if (form.value.steps.length < 10) {
    form.value.steps.push(createEmptyStep())
  }
}

function removeStep(index) {
  if (form.value.steps.length > 2) {
    form.value.steps.splice(index, 1)
  }
}

function toggleManual(index) {
  form.value.steps[index].showManual = !form.value.steps[index].showManual
}

function hasManualContent(step) {
  return step.manual_content || step.input_requirements || step.output_deliverables
}

async function requestAssist() {
  if (!canAssist.value) return

  assistLoading.value = true
  assistError.value = null
  assistResult.value = null

  try {
    const result = await partnerStore.assistCreateWorkflow({
      description: assistDescription.value
    })

    assistResult.value = result
    showAssistPanel.value = true
  } catch (err) {
    assistError.value = err.message || 'AI 规划失败，请重试'
    console.error('Assist workflow error:', err)
  } finally {
    assistLoading.value = false
  }
}

function applyAssistResult() {
  if (!assistResult.value) return

  // 应用基本信息
  form.value.name = assistResult.value.name
  form.value.description = assistResult.value.description

  // 应用步骤
  form.value.steps = assistResult.value.steps.map(step => ({
    title: step.title,
    description: step.description,
    employee_id: step.assigned_to,
    estimated_cost: step.estimated_cost,
    // v0.4.6: 应用步骤手册字段
    manual_content: step.manual_content || '',
    input_requirements: step.input_requirements || '',
    output_deliverables: step.output_deliverables || '',
    showManual: !!(step.manual_content || step.input_requirements || step.output_deliverables)
  }))

  // 清除辅助结果
  clearAssistResult()
}

function clearAssistResult() {
  assistResult.value = null
  assistDescription.value = ''
  showAssistPanel.value = false
}

async function handleSubmit() {
  if (!canSubmit.value) return

  isSubmitting.value = true

  try {
    // 构建提交数据
    const data = {
      name: form.value.name,
      description: form.value.description,
      steps: form.value.steps.map(step => ({
        employee_id: step.employee_id,
        title: step.title,
        description: step.description,
        estimated_cost: parseFloat(step.estimated_cost) || 0,
        // v0.4.6: 提交步骤手册字段
        manual_content: step.manual_content,
        input_requirements: step.input_requirements,
        output_deliverables: step.output_deliverables
      }))
    }

    const result = await workflowStore.createWorkflow(data)

    emit('created', result)
    emit('close')
  } catch (err) {
    console.error('Create workflow error:', err)
    alert('创建工作流失败: ' + (err.message || '请重试'))
  } finally {
    isSubmitting.value = false
  }
}

function handleOverlayClick() {
  if (!isSubmitting.value) {
    emit('close')
  }
}

// 初始化
onMounted(async () => {
  loading.value = true
  try {
    await employeeStore.fetchEmployees()
    employees.value = employeeStore.employees.filter(e => e.openclaw_agent_id)
  } catch (err) {
    console.error('Failed to load employees:', err)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
/* 基础样式 - 继承自 TaskCreateModal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background: var(--bg-card);
  border-radius: 16px;
  width: 100%;
  max-width: 700px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.modal-content.assist-mode {
  max-width: 800px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
}

.modal-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.btn-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: var(--text-secondary);
  transition: color 0.2s;
}

.btn-close:hover {
  color: var(--text-primary);
}

form {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}

.form-row .form-group-large {
  grid-column: 1 / -1;
}

.form-row .form-group-small {
  max-width: 120px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  font-size: 14px;
  background: var(--bg-input);
  color: var(--text-primary);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.form-group textarea {
  resize: vertical;
  min-height: 60px;
}

/* 辅助区域样式 */
.assist-section {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.05), rgba(168, 85, 247, 0.05));
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 24px;
}

.assist-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-weight: 500;
  color: var(--primary);
}

.assist-icon {
  font-size: 18px;
}

.assist-input-row {
  display: flex;
  gap: 12px;
}

.assist-input-row input {
  flex: 1;
  padding: 10px 12px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  font-size: 14px;
}

.btn-assist {
  padding: 10px 20px;
  background: linear-gradient(135deg, var(--primary), #a855f7);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  white-space: nowrap;
}

.btn-assist:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.btn-assist:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 预览区域 */
.assist-preview {
  margin-top: 16px;
  background: var(--bg-card);
  border-radius: 10px;
  border: 1px solid var(--border-color);
  overflow: hidden;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--bg-hover);
  border-bottom: 1px solid var(--border-color);
}

.preview-header span {
  font-weight: 500;
}

.preview-actions {
  display: flex;
  gap: 8px;
}

.btn-apply {
  padding: 6px 14px;
  background: var(--success);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
}

.btn-clear {
  padding: 6px 14px;
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
}

.preview-content {
  padding: 16px;
}

.preview-item {
  margin-bottom: 16px;
}

.preview-item:last-child {
  margin-bottom: 0;
}

.preview-item label {
  font-size: 12px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
  display: block;
}

.preview-item p {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
}

.reasoning-text {
  color: var(--text-secondary);
  font-style: italic;
}

.cost-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--warning);
}

/* 步骤预览列表 */
.steps-preview-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.step-preview-item {
  background: var(--bg-input);
  border-radius: 8px;
  padding: 12px;
}

.step-preview-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.step-number {
  width: 24px;
  height: 24px;
  background: var(--primary);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
}

.step-title {
  font-weight: 500;
  flex: 1;
}

.step-employee {
  font-size: 13px;
  color: var(--text-secondary);
}

.step-cost {
  font-size: 13px;
  color: var(--warning);
  font-weight: 500;
}

.step-preview-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.step-preview-manual {
  display: flex;
  gap: 8px;
}

.manual-badge {
  font-size: 11px;
  padding: 2px 8px;
  background: rgba(99, 102, 241, 0.1);
  color: var(--primary);
  border-radius: 4px;
}

/* 步骤列表样式 */
.steps-section {
  margin-bottom: 24px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-header label {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
}

.step-count {
  font-size: 13px;
  color: var(--text-secondary);
  background: var(--bg-hover);
  padding: 4px 10px;
  border-radius: 12px;
}

.steps-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.step-card {
  background: var(--bg-hover);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 16px;
}

.step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.step-badge {
  font-size: 12px;
  font-weight: 600;
  color: var(--primary);
  background: rgba(99, 102, 241, 0.1);
  padding: 4px 10px;
  border-radius: 12px;
}

.btn-remove-step {
  background: none;
  border: none;
  font-size: 20px;
  color: var(--danger);
  cursor: pointer;
  padding: 0;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: background 0.2s;
}

.btn-remove-step:hover {
  background: rgba(239, 68, 68, 0.1);
}

.btn-add-step {
  width: 100%;
  padding: 12px;
  background: transparent;
  border: 2px dashed var(--border-color);
  border-radius: 10px;
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.2s;
  margin-top: 16px;
}

.btn-add-step:hover {
  border-color: var(--primary);
  color: var(--primary);
  background: rgba(99, 102, 241, 0.05);
}

/* 步骤手册折叠区域 */
.step-manual-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed var(--border-color);
}

.manual-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-secondary);
  user-select: none;
}

.manual-toggle:hover {
  color: var(--primary);
}

.toggle-icon {
  font-size: 10px;
  transition: transform 0.2s;
}

.manual-indicator {
  width: 8px;
  height: 8px;
  background: var(--success);
  border-radius: 50%;
}

.manual-fields {
  margin-top: 12px;
  padding-top: 12px;
  animation: slideDown 0.2s ease-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 底部操作 */
.form-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
  margin-top: 8px;
}

.cost-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.cost-summary .cost-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--warning);
}

.action-buttons {
  display: flex;
  gap: 12px;
}

.btn {
  padding: 10px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: var(--primary);
  color: white;
  border: none;
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-dark);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

/* 响应式 */
@media (max-width: 640px) {
  .modal-content {
    max-width: 100%;
    max-height: 100%;
    border-radius: 0;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .assist-input-row {
    flex-direction: column;
  }

  .step-preview-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .form-actions {
    flex-direction: column;
    gap: 16px;
  }

  .action-buttons {
    width: 100%;
  }

  .btn {
    flex: 1;
  }
}
</style>
