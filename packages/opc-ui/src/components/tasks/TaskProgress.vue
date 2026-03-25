<template>
  <div class="task-progress">
    <div class="progress-bar">
      <div class="progress-fill indeterminate"></div>
    </div>    
    <span v-if="showTime" class="elapsed-time">
      {{ elapsedTime }}
    </span>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  task: {
    type: Object,
    required: true
  },
  showTime: {
    type: Boolean,
    default: true
  }
})

const now = ref(Date.now())
let intervalId = null

// 计算已执行时间
const elapsedTime = computed(() => {
  if (!props.task?.started_at) return '00:00'
  
  const start = new Date(props.task.started_at).getTime()
  const elapsed = Math.floor((now.value - start) / 1000)
  
  const minutes = Math.floor(elapsed / 60)
  const seconds = elapsed % 60
  
  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
})

onMounted(() => {
  // 每秒更新时间
  intervalId = setInterval(() => {
    now.value = Date.now()
  }, 1000)
})

onUnmounted(() => {
  if (intervalId) {
    clearInterval(intervalId)
  }
})
</script>

<style scoped>
.task-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 100px;
}

.progress-bar {
  flex: 1;
  height: 4px;
  background: var(--bg-tertiary, #e0e0e0);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--color-primary, #1976d2);
  border-radius: 2px;
  transition: width 0.3s ease;
}

/* 不确定进度动画 */
.indeterminate {
  width: 50%;
  animation: indeterminate 1.5s infinite ease-in-out;
}

@keyframes indeterminate {
  0% {
    transform: translateX(-100%);
  }
  50% {
    transform: translateX(100%);
  }
  100% {
    transform: translateX(-100%);
  }
}

.elapsed-time {
  font-size: 11px;
  color: var(--text-secondary, #666);
  font-variant-numeric: tabular-nums;
  min-width: 40px;
}
</style>
