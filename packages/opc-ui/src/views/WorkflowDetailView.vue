<template>
  <div class="view">
    <!-- 加载中 -->
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>

    <!-- 错误 -->
    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button class="btn btn-secondary" @click="fetchData">重试</button>
    </div>

    <!-- 内容 -->
    <template v-else-if="workflow">
      <!-- 页面头部 -->
      <div class="page-header">
        <button class="btn btn-text" @click="$router.back()">
          ← 返回
        </button>
        <div class="header-content">
          <h1>{{ workflow.name }}</h1>
          <span :class="['badge', getStatusClass(workflow.status)]">
            {{ getStatusLabel(workflow.status) }}
          </span>
        </div>
      </div>

      <!-- 进度概览 -->
      <div class="progress-overview">
        <div class="progress-bar-large">
          <div
            class="progress-fill"
            :style="{ width: `${workflow.progress_percent || 0}%` }"
          ></div>
        </div>
        <div class="progress-stats">
          <span>{{ workflow.completed_steps || 0 }} / {{ workflow.total_steps }} 步骤完成</span>
          <span>{{ workflow.progress_percent || 0 }}%</span>
        </div>
      </div>

      <!-- 步骤时间线 -->
      <div class="steps-timeline">
        <h3>执行步骤</h3>

        <div
          v-for="(task, index) in workflow.tasks"
          :key="task.id"
          class="timeline-item"
          :class="getTaskStatusClass(task)"
        >
          <div class="timeline-marker">
            <span v-if="task.status === 'completed'">✓</span>
            <span v-else-if="task.status === 'in_progress' || task.status === 'assigned'">●</span>
            <span v-else-if="task.status === 'failed'">✕</span>
            <span v-else>{{ index + 1 }}</span>
          </div>

          <div class="timeline-content">
            <div class="task-header">
              <h4>{{ task.title }}</h4>
              <span :class="['badge', getTaskBadgeClass(task)]">
                {{ getTaskStatusLabel(task) }}
              </span>
            </div>

            <p class="task-description">{{ task.description }}</p>

            <div class="task-meta">
              <span class="meta-item">
                👤 {{ getEmployeeName(task.assigned_to) }}
              </span>
              <span v-if="task.actual_cost > 0" class="meta-item">
                💰 {{ task.actual_cost.toFixed(2) }} OC币
              </span>
              <span v-if="task.rework_count > 0" class="meta-item rework-count">
                🔄 返工 {{ task.rework_count }} 次
              </span>
            </div>

            <!-- 操作按钮 -->
            <div class="task-actions">
              <button class="btn btn-sm" @click="viewTask(task.id)">
                查看详情
              </button>

              <button
                v-if="canRequestRework(task, index)"
                class="btn btn-sm btn-warning"
                @click="openReworkModal(task, index)"
              >
                请求返工
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- 返工模态框 -->
    <div v-if="showReworkModal" class="modal-overlay" @click.self="closeReworkModal">
      <div class="modal">
        <div class="modal-header">
          <h3>请求返工</h3>
          <button class="btn btn-text" @click="closeReworkModal">×</button>
        </div>

        <div class="modal-body">
          <p class="hint">
            从步骤 {{ currentStepIndex + 1 }} 返工到步骤 {{ reworkForm.to_step + 1 }}
          </p>

          <div class="form-group">
            <label>返工原因 *</label>
            <textarea
              v-model="reworkForm.reason"
              placeholder="为什么需要返工？"
              rows="3"
            ></textarea>
          </div>

          <div class="form-group">
            <label>返工指令 *</label>
            <textarea
              v-model="reworkForm.instructions"
              placeholder="具体需要修改什么？"
              rows="3"
            ></textarea>
          </div>

          <div class="form-group">
            <label>目标步骤</label>
            <select v-model.number="reworkForm.to_step">
              <option
                v-for="i in currentStepIndex"
                :key="i - 1"
                :value="i - 1"
              >
                步骤 {{ i }}: {{ getStepTitle(i - 1) }}
              </option>
            </select>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn btn-secondary" @click="closeReworkModal">取消</button>
          <button
            class="btn btn-warning"
            :disabled="!canSubmitRework"
            @click="submitRework"
          >
            提交返工请求
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useWorkflowStore } from '@/stores/workflows'
import { useEmployeeStore } from '@/stores/employees'

const route = useRoute()
const router = useRouter()
const workflowStore = useWorkflowStore()
const employeeStore = useEmployeeStore()
const { currentWorkflow: workflow, loading, error } = storeToRefs(workflowStore)
const { employees } = storeToRefs(employeeStore)

const showReworkModal = ref(false)
const currentStepIndex = ref(0)
const reworkForm = ref({
  reason: '',
  instructions: '',
  to_step: 0,
})

const canSubmitRework = computed(() => {
  return reworkForm.value.reason.trim() && reworkForm.value.instructions.trim()
})

function fetchData() {
  const id = route.params.id
  if (id) {
    workflowStore.fetchWorkflow(id)
  }
}

function getStatusClass(status) {
  const map = {
    running: 'badge-warning',
    completed: 'badge-success',
    failed: 'badge-danger',
  }
  return map[status] || 'badge-info'
}

function getStatusLabel(status) {
  const map = {
    running: '进行中',
    completed: '已完成',
    failed: '失败',
  }
  return map[status] || status
}

function getTaskStatusClass(task) {
  const map = {
    completed: 'completed',
    in_progress: 'active',
    assigned: 'active',
    failed: 'failed',
  }
  return map[task.status] || ''
}

function getTaskBadgeClass(task) {
  const map = {
    completed: 'badge-success',
    in_progress: 'badge-warning',
    assigned: 'badge-warning',
    failed: 'badge-danger',
    pending: 'badge-info',
  }
  return map[task.status] || 'badge-info'
}

function getTaskStatusLabel(task) {
  const map = {
    completed: '已完成',
    in_progress: '进行中',
    assigned: '已分配',
    failed: '失败',
    pending: '等待中',
  }
  return map[task.status] || task.status
}

function getEmployeeName(employeeId) {
  const emp = employees.value.find((e) => e.id === employeeId)
  return emp?.name || employeeId
}

function getStepTitle(stepIndex) {
  if (!workflow.value?.tasks) return ''
  const task = workflow.value.tasks.find((t) => t.step_index === stepIndex)
  return task?.title || `步骤 ${stepIndex + 1}`
}

function canRequestRework(task, index) {
  // 只能返工已完成的步骤，且不是第一步
  return (
    task.status === 'completed' &&
    index > 0 &&
    workflow.value?.status === 'running'
  )
}

function viewTask(taskId) {
  router.push(`/tasks/${taskId}`)
}

function openReworkModal(task, index) {
  currentStepIndex.value = index
  reworkForm.value.to_step = 0 // 默认返工到第一步
  reworkForm.value.reason = ''
  reworkForm.value.instructions = ''
  showReworkModal.value = true
}

function closeReworkModal() {
  showReworkModal.value = false
}

async function submitRework() {
  try {
    const fromTask = workflow.value.tasks[currentStepIndex.value]
    const toTask = workflow.value.tasks[reworkForm.value.to_step]

    await workflowStore.requestRework(workflow.value.workflow_id, {
      from_task_id: fromTask.id,
      to_task_id: toTask.id,
      reason: reworkForm.value.reason,
      instructions: reworkForm.value.instructions,
    })

    alert('返工请求已提交')
    closeReworkModal()
    fetchData()
  } catch (err) {
    alert('提交返工请求失败: ' + err.message)
  }
}

onMounted(() => {
  fetchData()
  employeeStore.fetchEmployees()
})
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.header-content {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.header-content h1 {
  margin: 0;
}

.progress-overview {
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
}

.progress-bar-large {
  height: 12px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  overflow: hidden;
  margin-bottom: var(--spacing-sm);
}

.progress-bar-large .progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary), var(--primary-light));
  border-radius: var(--radius-md);
  transition: width 0.3s ease;
}

.progress-stats {
  display: flex;
  justify-content: space-between;
  color: var(--text-muted);
  font-size: 0.875rem;
}

.steps-timeline {
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
}

.steps-timeline h3 {
  margin-top: 0;
  margin-bottom: var(--spacing-lg);
}

.timeline-item {
  display: flex;
  gap: var(--spacing-md);
  padding: var(--spacing-md) 0;
  border-left: 2px solid var(--border-color);
  margin-left: 15px;
  padding-left: var(--spacing-lg);
  position: relative;
}

.timeline-item:last-child {
  border-left-color: transparent;
}

.timeline-marker {
  position: absolute;
  left: -11px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--bg-tertiary);
  border: 2px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.timeline-item.completed .timeline-marker {
  background: var(--success);
  border-color: var(--success);
  color: white;
}

.timeline-item.active .timeline-marker {
  background: var(--primary);
  border-color: var(--primary);
  color: white;
}

.timeline-item.failed .timeline-marker {
  background: var(--danger);
  border-color: var(--danger);
  color: white;
}

.timeline-content {
  flex: 1;
  padding-bottom: var(--spacing-md);
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-sm);
}

.task-header h4 {
  margin: 0;
  font-size: 1rem;
}

.task-description {
  color: var(--text-muted);
  font-size: 0.875rem;
  margin-bottom: var(--spacing-sm);
}

.task-meta {
  display: flex;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-sm);
  font-size: 0.875rem;
  color: var(--text-muted);
}

.rework-count {
  color: var(--warning);
}

.task-actions {
  display: flex;
  gap: var(--spacing-sm);
}

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

.modal {
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md);
  border-bottom: 1px solid var(--border-color);
}

.modal-header h3 {
  margin: 0;
}

.modal-body {
  padding: var(--spacing-md);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  border-top: 1px solid var(--border-color);
}

.form-group {
  margin-bottom: var(--spacing-md);
}

.form-group label {
  display: block;
  margin-bottom: var(--spacing-xs);
  font-weight: 500;
}

.form-group textarea,
.form-group select {
  width: 100%;
  padding: var(--spacing-sm);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-primary);
  color: var(--text-primary);
}

.form-group textarea {
  resize: vertical;
  font-family: inherit;
}

.error-state {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--danger);
}
</style>
