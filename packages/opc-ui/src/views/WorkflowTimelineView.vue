<template>
  <div class="workflow-timeline">
    <div class="page-header">
      <div class="header-left">
        <el-button @click="$router.back()">
          <el-icon><ArrowLeft /></el-icon>
          {{ $t('common.back') }}
        </el-button>
        <h1>{{ $t('timeline.title') }}</h1>
      </div>
      <div class="header-actions">
        <el-button @click="refresh">
          <el-icon><Refresh /></el-icon>
          {{ $t('common.refresh') }}
        </el-button>
      </div>
    </div>

    <!-- 摘要卡片 -->
    <div v-if="summary" class="summary-cards">
      <el-row :gutter="16">
        <el-col :span="6">
          <el-card>
            <div class="stat-item">
              <div class="stat-value" :class="getStatusClass">{{ getStatusText }}</div>
              <div class="stat-label">{{ $t('timeline.status') }}</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card>
            <div class="stat-item">
              <div class="stat-value">{{ formatDuration(summary.total_duration_minutes) }}</div>
              <div class="stat-label">{{ $t('timeline.totalDuration') }}</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card>
            <div class="stat-item">
              <div class="stat-value">{{ summary.completed_tasks }}/{{ summary.total_tasks }}</div>
              <div class="stat-label">{{ $t('timeline.progress') }}</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card>
            <div class="stat-item">
              <div class="stat-value" :class="{ 'text-warning': summary.rework_count > 0 }">
                {{ summary.rework_count }}
              </div>
              <div class="stat-label">{{ $t('timeline.reworks') }}</div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 时间线 -->
    <el-card class="timeline-card">
      <template #header>
        <span>{{ $t('timeline.events') }}</span>
      </template>
      
      <div v-if="loading" class="loading-state">
        <el-skeleton :rows="8" animated />
      </div>
      
      <el-timeline v-else-if="events.length > 0">
        <el-timeline-item
          v-for="event in events"
          :key="event.timestamp"
          :type="getEventType(event.event_type)"
          :icon="getEventIcon(event.event_type)"
          :timestamp="formatTime(event.timestamp)"
          placement="top"
        >
          <div class="timeline-event">
            <div class="event-header">
              <span class="event-title">{{ event.title }}</span>
              <el-tag v-if="event.step_index !== null" size="small" type="info">
                Step {{ event.step_index + 1 }}
              </el-tag>
            </div>
            
            <p class="event-description">{{ event.description }}</p>
            
            <div class="event-meta">
              <span class="actor">
                <el-icon><User /></el-icon>
                {{ event.actor }}
              </span>
              <span v-if="event.metadata?.tokens_used" class="tokens">
                <el-icon><Coin /></el-icon>
                {{ event.metadata.tokens_used }} tokens
              </span>
              <span v-if="event.metadata?.duration_minutes" class="duration">
                <el-icon><Timer /></el-icon>
                {{ event.metadata.duration_minutes }} min
              </span>
            </div>
          </div>
        </el-timeline-item>
      </el-timeline>
      
      <el-empty v-else :description="$t('timeline.noEvents')" />
    </el-card>

    <!-- 步骤耗时详情 -->
    <el-card v-if="summary?.step_durations?.length > 0" class="step-durations">
      <template #header>
        <span>{{ $t('timeline.stepDurations') }}</span>
      </template>
      
      <el-table :data="summary.step_durations">
        <el-table-column prop="step_index" :label="$t('timeline.step')" width="80">
          <template #default="{ row }">
            Step {{ row.step_index + 1 }}
          </template>
        </el-table-column>
        <el-table-column prop="title" :label="$t('timeline.stepTitle')" />
        <el-table-column prop="duration_minutes" :label="$t('timeline.duration')" width="120">
          <template #default="{ row }">
            {{ formatDuration(row.duration_minutes) }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('timeline.progress')" width="200">
          <template #default="{ row }">
            <el-progress
              :percentage="getStepProgress(row.duration_minutes)"
              :color="getProgressColor"
              :stroke-width="8"
            />
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft,
  Refresh,
  User,
  Coin,
  Timer,
  CircleCheck,
  CircleClose,
  Warning,
  InfoFilled,
  VideoPlay,
  VideoPause,
} from '@element-plus/icons-vue'
import { useWorkflowStore } from '@/stores/workflows'

const route = useRoute()
const workflowStore = useWorkflowStore()
const workflowId = route.params.id

// 状态
const loading = ref(false)
const events = ref([])
const summary = ref(null)

// 计算属性
const getStatusClass = computed(() => {
  if (!summary.value) return ''
  if (summary.value.completion_rate === 100) return 'text-success'
  if (summary.value.rework_count > 0) return 'text-warning'
  return 'text-info'
})

const getStatusText = computed(() => {
  if (!summary.value) return '-'
  if (summary.value.completion_rate === 100) return '已完成'
  if (summary.value.rework_count > 0) return '有返工'
  return '进行中'
})

// 方法
const loadTimeline = async () => {
  loading.value = true
  try {
    const [timelineRes, summaryRes] = await Promise.all([
      workflowStore.getTimeline(workflowId),
      workflowStore.getTimelineSummary(workflowId),
    ])
    events.value = timelineRes.data || []
    summary.value = summaryRes.data
  } catch (error) {
    ElMessage.error('加载时间线失败')
  } finally {
    loading.value = false
  }
}

const refresh = () => {
  loadTimeline()
}

const formatTime = (timestamp) => {
  if (!timestamp) return '-'
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const formatDuration = (minutes) => {
  if (!minutes || minutes <= 0) return '-'
  if (minutes < 60) return `${Math.round(minutes)}分钟`
  const hours = Math.floor(minutes / 60)
  const mins = Math.round(minutes % 60)
  if (hours < 24) return `${hours}小时${mins > 0 ? mins + '分钟' : ''}`
  const days = Math.floor(hours / 24)
  const remainingHours = hours % 24
  return `${days}天${remainingHours > 0 ? remainingHours + '小时' : ''}`
}

const getEventType = (type) => {
  const typeMap = {
    'workflow_created': 'primary',
    'task_assigned': 'info',
    'task_started': 'warning',
    'task_completed': 'success',
    'task_failed': 'danger',
    'rework_requested': 'warning',
    'rework_completed': 'success',
    'workflow_completed': 'success',
  }
  return typeMap[type] || 'info'
}

const getEventIcon = (type) => {
  const iconMap = {
    'workflow_created': InfoFilled,
    'task_assigned': User,
    'task_started': VideoPlay,
    'task_completed': CircleCheck,
    'task_failed': CircleClose,
    'rework_requested': Warning,
    'rework_completed': CircleCheck,
    'workflow_completed': CircleCheck,
  }
  return iconMap[type] || InfoFilled
}

const getStepProgress = (duration) => {
  if (!summary.value || !summary.value.total_duration_minutes) return 0
  return Math.round((duration / summary.value.total_duration_minutes) * 100)
}

const getProgressColor = (percentage) => {
  if (percentage < 30) return '#67c23a'
  if (percentage < 60) return '#e6a23c'
  return '#f56c6c'
}

onMounted(() => {
  loadTimeline()
})
</script>

<style scoped>
.workflow-timeline {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-left h1 {
  margin: 0;
  font-size: 20px;
}

.summary-cards {
  margin-bottom: 24px;
}

.stat-item {
  text-align: center;
  padding: 12px;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 8px;
}

.stat-label {
  color: #909399;
  font-size: 14px;
}

.text-success {
  color: #67c23a;
}

.text-warning {
  color: #e6a23c;
}

.text-info {
  color: #409eff;
}

.text-danger {
  color: #f56c6c;
}

.timeline-card {
  margin-bottom: 24px;
}

.timeline-event {
  padding: 8px 0;
}

.event-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.event-title {
  font-weight: 500;
  font-size: 15px;
}

.event-description {
  color: #606266;
  margin: 0 0 8px 0;
  font-size: 14px;
}

.event-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #909399;
}

.event-meta span {
  display: flex;
  align-items: center;
  gap: 4px;
}

.loading-state {
  padding: 40px;
}

.step-durations {
  margin-top: 24px;
}
</style>
