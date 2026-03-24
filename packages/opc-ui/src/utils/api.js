import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

// 创建 axios 实例
const apiClient = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器 - 添加 API Key
apiClient.interceptors.request.use((config) => {
  const authStore = useAuthStore()
  if (authStore.apiKey) {
    config.headers.Authorization = `Bearer ${authStore.apiKey}`
  }
  return config
})

// 响应拦截器 - 错误处理
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.detail || error.message
    return Promise.reject(new Error(message))
  }
)

// API 方法
export const api = {
  get: (url, config) => apiClient.get(url, config),
  post: (url, data, config) => apiClient.post(url, data, config),
  put: (url, data, config) => apiClient.put(url, data, config),
  delete: (url, config) => apiClient.delete(url, config),
}

// 状态映射
export const statusMap = {
  // 员工状态
  idle: { label: '空闲', class: 'badge-success' },
  working: { label: '工作中', class: 'badge-warning' },
  offline: { label: '离线', class: 'badge-danger' },
  
  // 任务状态
  pending: { label: '待分配', class: 'badge-info' },
  assigned: { label: '已分配', class: 'badge-warning' },
  in_progress: { label: '进行中', class: 'badge-warning' },
  completed: { label: '已完成', class: 'badge-success' },
  failed: { label: '失败', class: 'badge-danger' },
}

// 格式化货币
export function formatCurrency(value) {
  if (value === undefined || value === null) return '-'
  return `¥${Number(value).toFixed(2)}`
}

// 格式化日期
export function formatDate(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
