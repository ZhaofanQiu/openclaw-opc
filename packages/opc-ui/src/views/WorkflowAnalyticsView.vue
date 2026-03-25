<template>
  <div class="workflow-analytics">
    <div class="page-header">
      <h1>{{ $t('analytics.title') }}</h1>
      <div class="header-actions">
        <el-radio-group v-model="timeRange" @change="loadData">
          <el-radio-button label="7">{{ $t('analytics.last7Days') }}</el-radio-button>
          <el-radio-button label="30">{{ $t('analytics.last30Days') }}</el-radio-button>
          <el-radio-button label="90">{{ $t('analytics.last90Days') }}</el-radio-button>
        </el-radio-group>
        <el-button @click="refresh">
          <el-icon><Refresh /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- 概览统计 -->
    <el-row :gutter="16" class="overview-section">
      <el-col :span="4">
        <el-card>
          <div class="overview-item">
            <div class="overview-value">{{ stats?.overview?.total_workflows || 0 }}</div>
            <div class="overview-label">{{ $t('analytics.totalWorkflows') }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card>
          <div class="overview-item">
            <div class="overview-value text-success">{{ stats?.overview?.completed || 0 }}</div>
            <div class="overview-label">{{ $t('analytics.completed') }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card>
          <div class="overview-item">
            <div class="overview-value text-danger">{{ stats?.overview?.failed || 0 }}</div>
            <div class="overview-label">{{ $t('analytics.failed') }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card>
          <div class="overview-item">
            <div class="overview-value">{{ stats?.overview?.completion_rate || 0 }}%</div>
            <div class="overview-label">{{ $t('analytics.completionRate') }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card>
          <div class="overview-item">
            <div class="overview-value text-warning">{{ stats?.rework?.total_reworks || 0 }}</div>
            <div class="overview-label">{{ $t('analytics.totalReworks') }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card>
          <div class="overview-item">
            <div class="overview-value">{{ formatDuration(stats?.duration?.avg_minutes) }}</div>
            <div class="overview-label">{{ $t('analytics.avgDuration') }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 趋势图表 -->
    <el-row :gutter="16" class="charts-section">
      <el-col :span="16">
        <el-card>
          <template #header>
            <span>{{ $t('analytics.dailyTrend') }}</span>
          </template>
          <div ref="trendChart" class="chart-container"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>{{ $t('analytics.statusDistribution') }}</span>
          </template>
          <div ref="statusChart" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 步骤分析 -->
    <el-card class="step-analysis">
      <template #header>
        <span>{{ $t('analytics.stepAnalysis') }}</span>
      </template>
      
      <el-table :data="stepStats" v-loading="loading">
        <el-table-column type="index" :label="$t('analytics.step')" width="80" />
        <el-table-column prop="title" :label="$t('analytics.stepTitle')" />
        <el-table-column prop="completed_count" :label="$t('analytics.completedCount')" width="100">
          <template #default="{ row }">
            <el-tag type="success">{{ row.completed_count }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="rework_count" :label="$t('analytics.reworkCount')" width="100">
          <template #default="{ row }">
            <el-tag :type="row.rework_count > 0 ? 'warning' : 'info'">{{ row.rework_count }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="rework_rate" :label="$t('analytics.reworkRate')" width="120">
          <template #default="{ row }">
            <el-progress
              :percentage="row.rework_rate"
              :color="row.rework_rate > 20 ? '#f56c6c' : row.rework_rate > 10 ? '#e6a23c' : '#67c23a'"
              :stroke-width="8"
            />
          </template>
        </el-table-column>
        <el-table-column prop="avg_duration_minutes" :label="$t('analytics.avgDuration')" width="120">
          <template #default="{ row }">
            {{ formatDuration(row.avg_duration_minutes) }}
          </template>
        </el-table-column>
        <el-table-column prop="min_duration_minutes" :label="$t('analytics.minDuration')" width="120">
          <template #default="{ row }">
            {{ formatDuration(row.min_duration_minutes) }}
          </template>
        </el-table-column>
        <el-table-column prop="max_duration_minutes" :label="$t('analytics.maxDuration')" width="120">
          <template #default="{ row }">
            {{ formatDuration(row.max_duration_minutes) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 员工排名 -->
    <el-card class="employee-ranking">
      <template #header>
        <span>{{ $t('analytics.employeeRanking') }}</span>
      </template>
      
      <el-row :gutter="16">
        <el-col
          v-for="(employee, index) in employeeRankings"
          :key="employee.employee_id"
          :span="8"
        >
          <el-card :class="['rank-card', `rank-${index + 1}`]">
            <div class="rank-header">
              <div class="rank-number">#{{ index + 1 }}</div>
              <div class="employee-info">
                <span class="emoji">{{ employee.employee_emoji || '🤖' }}</span>
                <span class="name">{{ employee.employee_name }}</span>
              </div>
              <div class="score">{{ employee.score }}</div>
            </div>
            
            <el-divider />
            
            <div class="rank-stats">
              <div class="stat">
                <div class="stat-value text-success">{{ employee.tasks_completed }}</div>
                <div class="stat-label">{{ $t('analytics.completed') }}</div>
              </div>
              <div class="stat">
                <div class="stat-value text-danger">{{ employee.tasks_failed }}</div>
                <div class="stat-label">{{ $t('analytics.failed') }}</div>
              </div>
              <div class="stat">
                <div class="stat-value text-warning">{{ employee.tasks_reworked }}</div>
                <div class="stat-label">{{ $t('analytics.reworked') }}</div>
              </div>
              <div class="stat">
                <div class="stat-value">{{ employee.completion_rate }}%</div>
                <div class="stat-label">{{ $t('analytics.completionRate') }}</div>
              </div>
              <div class="stat">
                <div class="stat-value">{{ formatDuration(employee.avg_task_duration_minutes) }}</div>
                <div class="stat-label">{{ $t('analytics.avgDuration') }}</div>
              </div>
              <div class="stat">
                <div class="stat-value">{{ formatTokens(employee.total_tokens_used) }}</div>
                <div class="stat-label">{{ $t('analytics.tokens') }}</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { useAnalyticsStore } from '@/stores/analytics'

const analyticsStore = useAnalyticsStore()

// 状态
const loading = ref(false)
const timeRange = ref('30')
const stats = ref(null)
const stepStats = ref([])
const employeeRankings = ref([])

const trendChart = ref(null)
const statusChart = ref(null)

let trendChartInstance = null
let statusChartInstance = null

// 方法
const loadData = async () => {
  loading.value = true
  try {
    const days = parseInt(timeRange.value)
    
    const [statsRes, stepRes, dailyRes, rankingRes] = await Promise.all([
      analyticsStore.getWorkflowStats(days),
      analyticsStore.getStepAnalysis(days),
      analyticsStore.getDailyTrend(days),
      analyticsStore.getEmployeeRankings(days),
    ])
    
    // 修复：直接使用返回的数据，不需要 .data
    stats.value = statsRes.data || {}
    stepStats.value = stepRes.data || []
    employeeRankings.value = rankingRes.data || []
    
    // 渲染图表
    await nextTick()
    renderTrendChart(dailyRes.data || [])
    renderStatusChart(statsRes.data?.overview)
  } catch (error) {
    console.error('加载分析数据失败:', error)
    ElMessage.error('加载数据失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

const refresh = () => {
  loadData()
}

const formatDuration = (minutes) => {
  if (!minutes || minutes <= 0) return '-'
  if (minutes < 60) return `${Math.round(minutes)}m`
  const hours = Math.floor(minutes / 60)
  const mins = Math.round(minutes % 60)
  if (hours < 24) return `${hours}h${mins > 0 ? mins + 'm' : ''}`
  const days = Math.floor(hours / 24)
  return `${days}d`
}

const formatTokens = (tokens) => {
  if (!tokens) return '0'
  if (tokens < 1000) return tokens.toString()
  if (tokens < 1000000) return (tokens / 1000).toFixed(1) + 'K'
  return (tokens / 1000000).toFixed(1) + 'M'
}

const renderTrendChart = (data) => {
  if (!trendChart.value) return
  
  if (trendChartInstance) {
    trendChartInstance.dispose()
  }
  
  trendChartInstance = echarts.init(trendChart.value)
  
  const dates = data.map(d => d.date.slice(5)) // MM-DD
  const created = data.map(d => d.created)
  const completed = data.map(d => d.completed)
  const failed = data.map(d => d.failed)
  
  const option = {
    tooltip: {
      trigger: 'axis',
    },
    legend: {
      data: ['创建', '完成', '失败'],
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates,
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
    },
    series: [
      {
        name: '创建',
        type: 'line',
        data: created,
        smooth: true,
        itemStyle: { color: '#409eff' },
        areaStyle: { opacity: 0.1 },
      },
      {
        name: '完成',
        type: 'line',
        data: completed,
        smooth: true,
        itemStyle: { color: '#67c23a' },
        areaStyle: { opacity: 0.1 },
      },
      {
        name: '失败',
        type: 'line',
        data: failed,
        smooth: true,
        itemStyle: { color: '#f56c6c' },
      },
    ],
  }
  
  trendChartInstance.setOption(option)
}

const renderStatusChart = (overview) => {
  if (!statusChart.value || !overview) return
  
  if (statusChartInstance) {
    statusChartInstance.dispose()
  }
  
  statusChartInstance = echarts.init(statusChart.value)
  
  const option = {
    tooltip: {
      trigger: 'item',
    },
    legend: {
      bottom: '5%',
    },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2,
        },
        label: {
          show: false,
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 16,
            fontWeight: 'bold',
          },
        },
        data: [
          { value: overview.completed || 0, name: '完成', itemStyle: { color: '#67c23a' } },
          { value: overview.failed || 0, name: '失败', itemStyle: { color: '#f56c6c' } },
          { value: overview.in_progress || 0, name: '进行中', itemStyle: { color: '#e6a23c' } },
        ],
      },
    ],
  }
  
  statusChartInstance.setOption(option)
}

// 监听窗口大小变化
const handleResize = () => {
  trendChartInstance?.resize()
  statusChartInstance?.resize()
}

onMounted(() => {
  loadData()
  window.addEventListener('resize', handleResize)
})
</script>

<style scoped>
.workflow-analytics {
  padding: 24px;
  min-height: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.overview-section {
  margin-bottom: 24px;
}

.overview-item {
  text-align: center;
  padding: 8px;
}

.overview-value {
  font-size: 28px;
  font-weight: 600;
  margin-bottom: 8px;
}

.overview-label {
  color: #909399;
  font-size: 13px;
}

.text-success {
  color: #67c23a;
}

.text-danger {
  color: #f56c6c;
}

.text-warning {
  color: #e6a23c;
}

.charts-section {
  margin-bottom: 24px;
}

.chart-container {
  height: 300px;
}

.step-analysis {
  margin-bottom: 24px;
}

.employee-ranking {
  margin-bottom: 24px;
}

.rank-card {
  margin-bottom: 16px;
}

.rank-1 {
  border: 2px solid #ffd700;
}

.rank-2 {
  border: 2px solid #c0c0c0;
}

.rank-3 {
  border: 2px solid #cd7f32;
}

.rank-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.rank-number {
  font-size: 24px;
  font-weight: bold;
  color: #409eff;
}

.employee-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.employee-info .emoji {
  font-size: 24px;
}

.employee-info .name {
  font-weight: 500;
}

.rank-header .score {
  font-size: 28px;
  font-weight: bold;
  color: #67c23a;
}

.rank-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  text-align: center;
}

.rank-stats .stat-value {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 4px;
}

.rank-stats .stat-label {
  color: #909399;
  font-size: 12px;
}
</style>
