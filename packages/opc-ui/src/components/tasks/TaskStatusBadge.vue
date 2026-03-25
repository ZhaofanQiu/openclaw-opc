<template>
  <span :class="['badge', statusClass, { 'pulse': isRunning }]">
    <span v-if="isRunning" class="spinner-xs"></span>
    {{ label }}
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: {
    type: String,
    required: true
  },
  size: {
    type: String,
    default: 'normal' // normal | large
  }
})

const isRunning = computed(() => 
  ['assigned', 'in_progress'].includes(props.status)
)

const statusClass = computed(() => {
  const baseClass = props.size === 'large' ? 'badge-lg' : ''
  const colorClass = {
    'pending': 'badge-info',
    'assigned': 'badge-warning',
    'in_progress': 'badge-warning',
    'completed': 'badge-success',
    'failed': 'badge-danger',
    'needs_review': 'badge-warning',
    'needs_revision': 'badge-warning'
  }[props.status] || 'badge-info'
  
  return [baseClass, colorClass].join(' ')
})

const label = computed(() => ({
  'pending': '待分配',
  'assigned': '准备中',
  'in_progress': '执行中',
  'completed': '已完成',
  'failed': '失败',
  'needs_review': '需检查',
  'needs_revision': '需返工'
}[props.status] || props.status))
</script>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.badge-lg {
  padding: 6px 12px;
  font-size: 14px;
}

.badge-info {
  background: var(--color-info-bg, #e3f2fd);
  color: var(--color-info, #1976d2);
}

.badge-warning {
  background: var(--color-warning-bg, #fff3e0);
  color: var(--color-warning, #f57c00);
}

.badge-success {
  background: var(--color-success-bg, #e8f5e9);
  color: var(--color-success, #388e3c);
}

.badge-danger {
  background: var(--color-danger-bg, #ffebee);
  color: var(--color-danger, #d32f2f);
}

/* 脉冲动画 */
.pulse {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

/* 小型旋转器 */
.spinner-xs {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
