<template>
  <div class="modal-overlay" @click.self="handleOverlayClick">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h3>创建新任务</h3>
        <button class="btn-close" @click="$emit('close')">×</button>
      </div>
      
      <form @submit.prevent="handleSubmit">
        <div class="form-group">
          <label>任务标题 *</label>
          <input
            v-model="form.title"
            type="text"
            placeholder="输入任务标题"
            required
          />
        </div>
        
        <div class="form-group">
          <label>任务描述</label>
          <textarea
            v-model="form.description"
            rows="4"
            placeholder="描述任务内容..."
          ></textarea>
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

const props = defineProps({
  submitting: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'submit'])

const employeeStore = useEmployeeStore()
const employees = computed(() => employeeStore.employees)

const form = ref({
  title: '',
  description: '',
  employee_id: '',
  estimated_cost: 100
})

function handleOverlayClick() {
  // 只在非提交状态下允许点击外部关闭
  if (!props.submitting) {
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
