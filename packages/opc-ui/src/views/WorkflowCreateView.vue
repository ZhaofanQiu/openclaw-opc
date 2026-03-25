<template>
  <div class="view">
    <!-- 页面头部 -->
    <div class="page-header">
      <button class="btn btn-text" @click="$router.back()">
        ← 返回
      </button>
      <h1>创建工作流</h1>
    </div>

    <!-- 创建表单 -->
    <div class="create-form">
      <!-- 基本信息 -->
      <section class="form-section">
        <h3>基本信息</h3>

        <div class="form-group">
          <label>工作流名称 *</label>
          <input
            v-model="form.name"
            type="text"
            placeholder="例如：研究报告生成"
            class="form-input"
          />
        </div>

        <div class="form-group">
          <label>描述</label>
          <textarea
            v-model="form.description"
            placeholder="描述这个工作流的目的..."
            class="form-textarea"
            rows="3"
          ></textarea>
        </div>
      </section>

      <!-- 步骤配置 -->
      <section class="form-section">
        <div class="section-header">
          <h3>步骤配置</h3>
          <span class="hint">至少 2 个步骤</span>
        </div>

        <div class="steps-list">
          <div
            v-for="(step, index) in form.steps"
            :key="index"
            class="step-card"
          >
            <div class="step-header">
              <span class="step-number">步骤 {{ index + 1 }}</span>
              <button
                v-if="form.steps.length > 2"
                class="btn btn-sm btn-danger"
                @click="removeStep(index)"
              >
                删除
              </button>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>执行员工 *</label>
                <select v-model="step.employee_id" class="form-select">
                  <option value="">选择员工...</option>
                  <option
                    v-for="emp in employees"
                    :key="emp.id"
                    :value="emp.id"
                  >
                    {{ emp.name }} ({{ emp.position || '员工' }})
                  </option>
                </select>
              </div>

              <div class="form-group">
                <label>预估成本 (OC币)</label>
                <input
                  v-model.number="step.estimated_cost"
                  type="number"
                  min="0"
                  class="form-input"
                />
              </div>
            </div>

            <div class="form-group">
              <label>步骤标题 *</label>
              <input
                v-model="step.title"
                type="text"
                placeholder="例如：研究主题"
                class="form-input"
              />
            </div>

            <div class="form-group">
              <label>任务描述 *</label>
              <textarea
                v-model="step.description"
                placeholder="描述这个步骤需要完成的任务..."
                class="form-textarea"
                rows="3"
              ></textarea>
            </div>
          </div>
        </div>

        <button class="btn btn-secondary" @click="addStep">
          + 添加步骤
        </button>
      </section>

      <!-- 高级设置 -->
      <section class="form-section">
        <h3>高级设置</h3>

        <div class="form-row">
          <div class="form-group">
            <label>每步最大返工次数</label>
            <input
              v-model.number="form.max_rework_per_step"
              type="number"
              min="0"
              max="5"
              class="form-input"
            />
            <span class="hint">0-5，建议 2</span>
          </div>
        </div>

        <div class="form-group">
          <label>初始输入数据 (JSON)</label>
          <textarea
            v-model="initialInputJson"
            placeholder='{"topic": "AI医疗", "keywords": ["诊断", "治疗"]}'
            class="form-textarea"
            rows="4"
          ></textarea>
          <span class="hint">可选：传递给第一个步骤的初始数据</span>
        </div>
      </section>

      <!-- 提交按钮 -->
      <div class="form-actions">
        <button
          class="btn btn-primary btn-lg"
          :disabled="!isValid || creating"
          @click="createWorkflow"
        >
          <span v-if="creating" class="spinner-sm"></span>
          {{ creating ? '创建中...' : '创建工作流' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useWorkflowStore } from '@/stores/workflows'
import { useEmployeeStore } from '@/stores/employees'

const router = useRouter()
const workflowStore = useWorkflowStore()
const employeeStore = useEmployeeStore()
const { employees } = storeToRefs(employeeStore)

const creating = ref(false)
const initialInputJson = ref('{}')

const form = ref({
  name: '',
  description: '',
  steps: [
    {
      employee_id: '',
      title: '',
      description: '',
      estimated_cost: 100,
    },
    {
      employee_id: '',
      title: '',
      description: '',
      estimated_cost: 100,
    },
  ],
  max_rework_per_step: 2,
})

const isValid = computed(() => {
  if (!form.value.name.trim()) return false
  if (form.value.steps.length < 2) return false

  return form.value.steps.every(
    (step) =>
      step.employee_id &&
      step.title.trim() &&
      step.description.trim()
  )
})

function addStep() {
  form.value.steps.push({
    employee_id: '',
    title: '',
    description: '',
    estimated_cost: 100,
  })
}

function removeStep(index) {
  if (form.value.steps.length > 2) {
    form.value.steps.splice(index, 1)
  }
}

async function createWorkflow() {
  if (!isValid.value) return

  creating.value = true
  try {
    // 解析初始输入
    let initialInput = {}
    try {
      initialInput = JSON.parse(initialInputJson.value || '{}')
    } catch {
      alert('初始输入数据 JSON 格式错误')
      creating.value = false
      return
    }

    const data = {
      ...form.value,
      initial_input: initialInput,
    }

    const result = await workflowStore.createWorkflow(data)
    alert(`工作流创建成功！ID: ${result.workflow_id}`)
    router.push(`/workflows/${result.workflow_id}`)
  } catch (err) {
    alert('创建工作流失败: ' + err.message)
  } finally {
    creating.value = false
  }
}

onMounted(() => {
  employeeStore.fetchEmployees()
})
</script>

<style scoped>
.create-form {
  max-width: 800px;
}

.form-section {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
  margin-bottom: var(--space-lg);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-md);
}

.section-header h3 {
  margin: 0;
}

.form-group {
  margin-bottom: var(--space-md);
}

.form-group label {
  display: block;
  margin-bottom: var(--space-xs);
  font-weight: 500;
}

.form-input,
.form-textarea,
.form-select {
  width: 100%;
  padding: var(--space-sm);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 1rem;
}

.form-textarea {
  resize: vertical;
  font-family: inherit;
}

.form-row {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: var(--space-md);
}

.steps-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  margin-bottom: var(--space-md);
}

.step-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: var(--space-md);
}

.step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-sm);
}

.step-number {
  font-weight: 600;
  color: var(--primary);
}

.hint {
  font-size: 0.875rem;
  color: var(--text-muted);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-md);
  padding-top: var(--space-lg);
  border-top: 1px solid var(--border-color);
}

.btn-lg {
  padding: var(--space-sm) var(--space-lg);
  font-size: 1rem;
}
</style>
