import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useTaskStore } from '../tasks'
import { api } from '@/utils/api'

// Mock API
vi.mock('@/utils/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  }
}))

describe('Task Store - Phase 4 Polling', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useTaskStore()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.clearAllMocks()
  })

  describe('assignTask', () => {
    it('should assign task and start polling', async () => {
      // Mock API 响应
      api.post.mockResolvedValue({
        task: { id: 'task-1', status: 'assigned' }
      })
      api.get.mockResolvedValue({
        id: 'task-1',
        status: 'assigned',
        title: 'Test Task'
      })

      // 执行分配
      await store.assignTask('task-1', 'emp-1')

      // 验证 API 调用
      expect(api.post).toHaveBeenCalledWith('/tasks/task-1/assign', {
        employee_id: 'emp-1'
      })

      // 验证开始轮询
      expect(store.pollingTasks.has('task-1')).toBe(true)
    })

    it('should show toast notification on assign', async () => {
      api.post.mockResolvedValue({
        task: { id: 'task-1', status: 'assigned' }
      })

      await store.assignTask('task-1', 'emp-1')

      // 验证 Toast 通知
      expect(store.notifications.length).toBe(1)
      expect(store.notifications[0].message).toContain('任务已分配')
    })
  })

  describe('polling', () => {
    it('should poll task status periodically', async () => {
      // 模拟任务从 assigned 到 completed
      api.get
        .mockResolvedValueOnce({ id: 'task-1', status: 'assigned' })
        .mockResolvedValueOnce({ id: 'task-1', status: 'in_progress' })
        .mockResolvedValueOnce({ id: 'task-1', status: 'completed', result: 'Done' })

      // 开始轮询
      store.startPolling('task-1', 5000)

      // 初始状态
      expect(store.pollingTasks.has('task-1')).toBe(true)

      // 快进 5 秒 - 第一次轮询
      await vi.advanceTimersByTimeAsync(5000)
      expect(api.get).toHaveBeenCalledTimes(1)

      // 快进 5 秒 - 第二次轮询
      await vi.advanceTimersByTimeAsync(5000)
      expect(api.get).toHaveBeenCalledTimes(2)

      // 快进 5 秒 - 第三次轮询 (completed)
      await vi.advanceTimersByTimeAsync(5000)
      expect(api.get).toHaveBeenCalledTimes(3)

      // 任务完成后应停止轮询
      expect(store.pollingTasks.has('task-1')).toBe(false)
    })

    it('should stop polling when task is completed', async () => {
      api.get.mockResolvedValue({
        id: 'task-1',
        status: 'completed',
        result: 'Task completed successfully'
      })

      store.startPolling('task-1')
      
      // 等待第一次轮询完成
      await vi.advanceTimersByTimeAsync(5000)

      // 验证停止轮询
      expect(store.pollingTasks.has('task-1')).toBe(false)
    })

    it('should stop polling when task fails', async () => {
      api.get.mockResolvedValue({
        id: 'task-1',
        status: 'failed',
        result: 'Task failed'
      })

      store.startPolling('task-1')
      
      await vi.advanceTimersByTimeAsync(5000)

      expect(store.pollingTasks.has('task-1')).toBe(false)
    })

    it('should prevent duplicate polling for same task', () => {
      store.startPolling('task-1', 5000)
      store.startPolling('task-1', 5000)

      // 应该只启动一个轮询
      expect(store.pollingTasks.size).toBe(1)
    })
  })

  describe('stopPolling', () => {
    it('should stop polling for specific task', () => {
      store.startPolling('task-1', 5000)
      expect(store.pollingTasks.has('task-1')).toBe(true)

      store.stopPolling('task-1')
      expect(store.pollingTasks.has('task-1')).toBe(false)
    })

    it('should stop all polling', () => {
      store.startPolling('task-1', 5000)
      store.startPolling('task-2', 5000)
      expect(store.pollingTasks.size).toBe(2)

      store.stopAllPolling()
      expect(store.pollingTasks.size).toBe(0)
    })
  })

  describe('notifications', () => {
    it('should show notification when task completes', async () => {
      api.get.mockResolvedValue({
        id: 'task-1',
        status: 'completed',
        title: 'Test Task',
        result: 'Done'
      })

      store.startPolling('task-1')
      await vi.advanceTimersByTimeAsync(5000)

      // 验证通知
      const successToast = store.notifications.find(
        n => n.type === 'success' && n.message.includes('Test Task')
      )
      expect(successToast).toBeDefined()
    })

    it('should show notification when task fails', async () => {
      api.get.mockResolvedValue({
        id: 'task-1',
        status: 'failed',
        title: 'Test Task'
      })

      store.startPolling('task-1')
      await vi.advanceTimersByTimeAsync(5000)

      const errorToast = store.notifications.find(
        n => n.type === 'error'
      )
      expect(errorToast).toBeDefined()
    })

    it('should auto-remove notifications after duration', async () => {
      store.showToast('Test message', 'info', 1000)
      expect(store.notifications.length).toBe(1)

      await vi.advanceTimersByTimeAsync(1000)
      expect(store.notifications.length).toBe(0)
    })
  })

  describe('retryTask', () => {
    it('should reset task and start polling', async () => {
      api.post.mockResolvedValue({
        task: { id: 'task-1', status: 'pending' }
      })
      api.get.mockResolvedValue({
        id: 'task-1',
        status: 'pending',
        title: 'Test Task'
      })

      await store.retryTask('task-1')

      expect(api.post).toHaveBeenCalledWith('/tasks/task-1/retry')
      expect(store.pollingTasks.has('task-1')).toBe(true)
    })
  })
})
