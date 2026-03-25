<template>
  <div class="modal-overlay" @click.self="close">
    <div class="modal-content">
      <div class="modal-header">
        <h3>分配任务</h3>
        <button class="close-btn" @click="close">×</button>
      </div>
      
      <div v-if="!assigning" class="modal-body">
        <div class="form-group">
          <label>选择员工</label>
          <select v-model="selectedEmployee" required :disabled="loadingEmployees">
            <option value="" disabled>请选择员工</option>
            <option 
              v-for="emp in availableEmployees" 
              :key="emp.id" 
              :value="emp.id"
              :disabled="!emp.openclaw_agent_id"
            >
              {{ emp.name }} ({{ emp.position_title }})
              <span v-if="!emp.openclaw_agent_id" class="no-agent-tag">未绑定 Agent</span>
              <span v-else class="agent-bound-tag">已绑定</span>
            </option>
          </select>
          <p v-if="loadingEmployees" class="hint">加载员工列表中...</p>
          <p v-else-if="availableEmployees.length === 0" class="hint error">
            没有可用的员工，请先雇佣员工并绑定 Agent
          </p>
        </div>
        
        <div class="task-preview">
          <label>任务</label>
          <p class="task-title">{{ task?.title }}</p>
          <p class="task-desc">{{ task?.description || '无描述' }}</p>
        </div>
      </div>
      
      <div v-else class="modal-body assigning">
        <div class="assigning-state">
          <div class="spinner"></div>
          <p class="main-text">任务分配中...</p>
          <p class="sub-text">正在发送给 Agent，请稍候</p>
        </div>
      </div>
      
      <div class="modal-footer">
        <button 
          type="button" 
          class="btn btn-secondary" 
          @click="close"
          :disabled="assigning"
        >
          {{ assigning ? '请稍候...' : '取消' }}
        </button>
        <button 
          v-if="!assigning"
          type="button" 
          class="btn btn-primary" 
          :disabled="!selectedEmployee || assigning"
          @click="handleAssign"
        >
          确认分配
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useEmployeeStore } from '@/stores/employees'
import { useTaskStore } from '@/stores/tasks'

const props = defineProps({
  task: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['close', 'assigned'])

const employeeStore = useEmployeeStore()
const taskStore = useTaskStore()

const selectedEmployee = ref('')
const assigning = ref(false)
const loadingEmployees = ref(false)

const availableEmployees = computed(() => employeeStore.employees)

onMounted(async () => {
  loadingEmployees.value = true
  try {
    await employeeStore.fetchEmployees()
  } finally {
    loadingEmployees.value = false
  }
})

async function handleAssign() {
  if (!selectedEmployee.value) return
  
  assigning.value = true
  try {
    await taskStore.assignTask(props.task.id, selectedEmployee.value)
    emit('assigned', props.task)
    close()
  } catch (err) {
    console.error('Assign failed:', err)
    alert('分配失败: ' + err.message)
  } finally {
    assigning.value = false
  }
}

function close() {
  if (!assigning.value) {
    emit('close')
  }
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
}

.modal-body.assigning {
  padding: 40px 20px;
  text-align: center;
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

.form-group select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-color, #ddd);
  border-radius: 6px;
  font-size: 14px;
  background: var(--bg-primary, #fff);
}

.form-group select:focus {
  outline: none;
  border-color: var(--color-primary, #1976d2);
}

.hint {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-secondary, #666);
}

.hint.error {
  color: var(--color-danger, #d32f2f);
}

.no-agent-tag {
  margin-left: 8px;
  padding: 2px 6px;
  background: var(--color-danger-bg, #ffebee);
  color: var(--color-danger, #d32f2f);
  font-size: 11px;
  border-radius: 4px;
}

.agent-bound-tag {
  margin-left: 8px;
  padding: 2px 6px;
  background: var(--color-success-bg, #e8f5e9);
  color: var(--color-success, #388e3c);
  font-size: 11px;
  border-radius: 4px;
}

.task-preview {
  padding: 12px;
  background: var(--bg-secondary, #f5f5f5);
  border-radius: 6px;
}

.task-preview label {
  font-size: 12px;
  color: var(--text-secondary, #666);
  margin-bottom: 4px;
  display: block;
}

.task-title {
  font-weight: 500;
  margin: 0 0 4px 0;
}

.task-desc {
  font-size: 13px;
  color: var(--text-secondary, #666);
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.assigning-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-color, #e0e0e0);
  border-top-color: var(--color-primary, #1976d2);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.main-text {
  font-size: 16px;
  font-weight: 500;
  margin: 0;
}

.sub-text {
  font-size: 14px;
  color: var(--text-secondary, #666);
  margin: 0;
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
