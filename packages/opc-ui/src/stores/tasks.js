import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { api } from '@/utils/api'

export const useTaskStore = defineStore('tasks', () => {
  // State
  const tasks = ref([])
  const currentTask = ref(null)
  const loading = ref(false)
  const error = ref(null)
  
  // Phase 4: 轮询状态管理
  const pollingTasks = ref(new Map()) // taskId -> { intervalId, startTime }
  const notifications = ref([])

  // Getters
  const taskCount = computed(() => tasks.value.length)
  const pendingCount = computed(() =>
    tasks.value.filter(t => t.status === 'pending').length
  )
  const inProgressCount = computed(() =>
    tasks.value.filter(t => ['assigned', 'in_progress'].includes(t.status)).length
  )
  const completedCount = computed(() =>
    tasks.value.filter(t => t.status === 'completed').length
  )
  
  // 正在执行中的任务列表
  const runningTasks = computed(() =>
    tasks.value.filter(t => ['assigned', 'in_progress'].includes(t.status))
  )

  // Actions
  async function fetchTasks(params = {}) {
    loading.value = true
    error.value = null
    try {
      const query = new URLSearchParams(params).toString()
      const url = query ? `/tasks?${query}` : '/tasks'
      const response = await api.get(url)
      tasks.value = response.tasks || []
      return tasks.value
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchTask(id) {
    loading.value = true
    error.value = null
    try {
      const response = await api.get(`/tasks/${id}`)
      currentTask.value = response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createTask(data) {
    loading.value = true
    try {
      const response = await api.post('/tasks', data)
      await fetchTasks()
      return response
    } finally {
      loading.value = false
    }
  }

  async function updateTask(id, data) {
    loading.value = true
    try {
      const response = await api.put(`/tasks/${id}`, data)
      await fetchTasks()
      return response
    } finally {
      loading.value = false
    }
  }

  async function deleteTask(id) {
    loading.value = true
    try {
      await api.delete(`/tasks/${id}`)
      await fetchTasks()
    } finally {
      loading.value = false
    }
  }

  // ============================================================
  // Phase 4: 异步分配任务 + 轮询
  // ============================================================
  
  async function assignTask(taskId, employeeId) {
    loading.value = true
    error.value = null
    try {
      // 发送分配请求，立即返回
      const response = await api.post(`/tasks/${taskId}/assign`, {
        employee_id: employeeId
      })
      
      // 更新本地任务列表
      await fetchTasks()
      
      // 开始轮询任务状态
      startPolling(taskId)
      
      // 显示任务已分配的通知
      showToast('任务已分配，正在后台执行...', 'info')
      
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 开始轮询任务状态
   */
  function startPolling(taskId, intervalMs = 5000) {
    // 避免重复轮询
    if (pollingTasks.value.has(taskId)) {
      return
    }
    
    const startTime = Date.now()
    
    // 立即执行一次
    pollOnce(taskId)
    
    // 设置轮询间隔
    const intervalId = setInterval(() => {
      pollOnce(taskId)
    }, intervalMs)
    
    pollingTasks.value.set(taskId, {
      intervalId,
      startTime,
      lastPoll: Date.now()
    })
    
    console.log(`[Polling] Started for task ${taskId}`)
  }

  /**
   * 单次轮询
   */
  async function pollOnce(taskId) {
    try {
      const task = await fetchTask(taskId)
      
      // 更新任务列表中的对应任务
      const index = tasks.value.findIndex(t => t.id === taskId)
      if (index !== -1) {
        tasks.value[index] = task
      }
      
      // 检查是否完成
      const finalStatuses = ['completed', 'failed', 'needs_review']
      if (finalStatuses.includes(task.status)) {
        stopPolling(taskId)
        showTaskCompleteNotification(task)
      }
      
      // 更新轮询记录
      const record = pollingTasks.value.get(taskId)
      if (record) {
        record.lastPoll = Date.now()
      }
      
    } catch (err) {
      console.error(`[Polling] Error polling task ${taskId}:`, err)
    }
  }

  /**
   * 停止轮询
   */
  function stopPolling(taskId) {
    const record = pollingTasks.value.get(taskId)
    if (record) {
      clearInterval(record.intervalId)
      pollingTasks.value.delete(taskId)
      console.log(`[Polling] Stopped for task ${taskId}`)
    }
  }

  /**
   * 停止所有轮询
   */
  function stopAllPolling() {
    pollingTasks.value.forEach((record, taskId) => {
      clearInterval(record.intervalId)
      console.log(`[Polling] Stopped for task ${taskId}`)
    })
    pollingTasks.value.clear()
  }

  /**
   * 恢复对执行中任务的轮询
   * 用于页面刷新后恢复状态
   */
  function resumePollingForRunningTasks() {
    runningTasks.value.forEach(task => {
      if (!pollingTasks.value.has(task.id)) {
        startPolling(task.id)
      }
    })
  }

  // ============================================================
  // 通知系统
  // ============================================================
  
  /**
   * 显示任务完成通知
   */
  function showTaskCompleteNotification(task) {
    const statusMap = {
      'completed': { type: 'success', message: `任务 "${task.title}" 已完成` },
      'failed': { type: 'error', message: `任务 "${task.title}" 执行失败` },
      'needs_review': { type: 'warning', message: `任务 "${task.title}" 需要人工检查` }
    }
    
    const info = statusMap[task.status]
    if (info) {
      showToast(info.message, info.type)
      
      // 浏览器通知
      if (Notification.permission === 'granted') {
        new Notification('OpenClaw OPC', {
          body: info.message,
          icon: '/favicon.ico'
        })
      }
    }
  }

  /**
   * 显示 Toast 通知
   */
  function showToast(message, type = 'info', duration = 5000) {
    const id = Date.now() + Math.random()
    notifications.value.push({ id, message, type, duration })
    
    setTimeout(() => {
      removeNotification(id)
    }, duration)
    
    return id
  }

  /**
   * 移除通知
   */
  function removeNotification(id) {
    const index = notifications.value.findIndex(n => n.id === id)
    if (index > -1) {
      notifications.value.splice(index, 1)
    }
  }

  /**
   * 请求浏览器通知权限
   */
  async function requestNotificationPermission() {
    if ('Notification' in window) {
      const permission = await Notification.requestPermission()
      return permission === 'granted'
    }
    return false
  }

  // ============================================================
  // 其他任务操作
  // ============================================================
  
  async function retryTask(taskId) {
    loading.value = true
    error.value = null
    try {
      const response = await api.post(`/tasks/${taskId}/retry`)
      await fetchTasks()
      
      // 重试后开始轮询
      startPolling(taskId)
      showToast('任务已重置，重新开始执行...', 'info')
      
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function cancelTask(taskId) {
    loading.value = true
    error.value = null
    try {
      const response = await api.post(`/tasks/${taskId}/cancel`)
      stopPolling(taskId)
      await fetchTasks()
      showToast('任务已取消', 'info')
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    // State
    tasks,
    currentTask,
    loading,
    error,
    pollingTasks,
    notifications,
    
    // Getters
    taskCount,
    pendingCount,
    inProgressCount,
    completedCount,
    runningTasks,
    
    // Actions
    fetchTasks,
    fetchTask,
    createTask,
    updateTask,
    deleteTask,
    assignTask,
    retryTask,
    cancelTask,
    
    // Polling
    startPolling,
    stopPolling,
    stopAllPolling,
    resumePollingForRunningTasks,
    
    // Notifications
    showToast,
    removeNotification,
    requestNotificationPermission,
  }
})
