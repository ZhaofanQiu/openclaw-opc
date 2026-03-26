<template>
  <div class="modal-overlay" @click.self="close">
    <div class="modal-content">
      <div class="modal-header">
        <h3>雇佣新员工</h3>
        <button class="close-btn" @click="close">×</button>
      </div>
      
      <div class="modal-body">
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
            <label>月预算 (tokens) *</label>
            <input 
              v-model.number="form.monthly_budget" 
              type="number" 
              min="100"
              required
              placeholder="例如：10000"
            />
            <p class="hint">建议预算：1000-50000 tokens</p>
          </div>
          
          <div class="form-group">
            <label>头像 Emoji</label>
            <div class="emoji-picker">
              <button 
                v-for="emoji in commonEmojis" 
                :key="emoji"
                type="button"
                :class="['emoji-btn', { active: form.emoji === emoji }]"
                @click="form.emoji = emoji"
              >
                {{ emoji }}
              </button>
              <input 
                v-model="form.emoji" 
                maxlength="2"
                class="emoji-input"
                placeholder="👤"
              />
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

const emit = defineEmits(['close', 'created'])

const employeeStore = useEmployeeStore()

const commonEmojis = ['👤', '👨‍💻', '👩‍💻', '🧑‍💼', '👨‍💼', '👩‍💼', '🤖', '👾', '🦄', '🦁', '🦊', '🐼']

const form = ref({
  name: '',
  position_level: 1,
  monthly_budget: 10000,
  emoji: '👤'
})

const submitting = ref(false)

const isValid = computed(() => {
  return form.value.name.trim() && 
         form.value.position_level >= 1 && 
         form.value.position_level <= 5 && 
         form.value.monthly_budget >= 100
})

async function handleSubmit() {
  if (!isValid.value) return
  
  submitting.value = true
  try {
    await employeeStore.createEmployee(form.value)
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

.emoji-picker {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.emoji-btn {
  width: 40px;
  height: 40px;
  font-size: 20px;
  border: 2px solid var(--border-color, #ddd);
  border-radius: 8px;
  background: var(--bg-primary, #fff);
  cursor: pointer;
  transition: all 0.2s;
}

.emoji-btn:hover {
  border-color: var(--color-primary, #1976d2);
  background: var(--bg-secondary, #f5f5f5);
}

.emoji-btn.active {
  border-color: var(--color-primary, #1976d2);
  background: var(--color-primary-bg, #e3f2fd);
}

.emoji-input {
  width: 60px !important;
  text-align: center;
  font-size: 20px !important;
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
