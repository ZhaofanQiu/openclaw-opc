import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useEmployeeStore } from '@/stores/employees'

// Mock API
vi.mock('@/utils/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  }
}))

import { api } from '@/utils/api'

describe('Employee Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('should have initial state', () => {
    const store = useEmployeeStore()
    
    expect(store.employees).toEqual([])
    expect(store.currentEmployee).toBeNull()
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
  })

  it('should calculate employeeCount correctly', () => {
    const store = useEmployeeStore()
    store.employees = [{ id: 1 }, { id: 2 }, { id: 3 }]
    
    expect(store.employeeCount).toBe(3)
  })

  it('should calculate onlineCount correctly', () => {
    const store = useEmployeeStore()
    store.employees = [
      { id: 1, status: 'idle' },
      { id: 2, status: 'working' },
      { id: 3, status: 'idle' },
    ]
    
    expect(store.onlineCount).toBe(2)
  })

  it('should calculate workingCount correctly', () => {
    const store = useEmployeeStore()
    store.employees = [
      { id: 1, status: 'idle' },
      { id: 2, status: 'working' },
      { id: 3, status: 'working' },
    ]
    
    expect(store.workingCount).toBe(2)
  })

  it('should fetch employees successfully', async () => {
    const store = useEmployeeStore()
    const mockEmployees = [{ id: 1, name: '员工1' }, { id: 2, name: '员工2' }]
    api.get.mockResolvedValue({ employees: mockEmployees })
    
    await store.fetchEmployees()
    
    expect(api.get).toHaveBeenCalledWith('/employees')
    expect(store.employees).toEqual(mockEmployees)
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
  })

  it('should handle fetch employees error', async () => {
    const store = useEmployeeStore()
    api.get.mockRejectedValue(new Error('Network error'))
    
    await expect(store.fetchEmployees()).rejects.toThrow('Network error')
    
    expect(store.error).toBe('Network error')
    expect(store.loading).toBe(false)
  })

  it('should fetch single employee', async () => {
    const store = useEmployeeStore()
    const mockEmployee = { id: 'emp_123', name: '测试员工' }
    api.get.mockResolvedValue(mockEmployee)
    
    const result = await store.fetchEmployee('emp_123')
    
    expect(api.get).toHaveBeenCalledWith('/employees/emp_123')
    expect(store.currentEmployee).toEqual(mockEmployee)
    expect(result).toEqual(mockEmployee)
  })

  it('should create employee and refresh list', async () => {
    const store = useEmployeeStore()
    const newEmployee = { name: '新员工', emoji: '🤖' }
    api.post.mockResolvedValue({ id: 'emp_new', ...newEmployee })
    api.get.mockResolvedValue({ employees: [{ id: 'emp_new', ...newEmployee }] })
    
    const result = await store.createEmployee(newEmployee)
    
    expect(api.post).toHaveBeenCalledWith('/employees', newEmployee)
    expect(api.get).toHaveBeenCalledWith('/employees')
  })

  it('should update employee and refresh list', async () => {
    const store = useEmployeeStore()
    const updateData = { name: '更新后' }
    api.put.mockResolvedValue({ success: true })
    api.get.mockResolvedValue({ employees: [] })
    
    await store.updateEmployee('emp_123', updateData)
    
    expect(api.put).toHaveBeenCalledWith('/employees/emp_123', updateData)
  })

  it('should delete employee and refresh list', async () => {
    const store = useEmployeeStore()
    api.delete.mockResolvedValue({ success: true })
    api.get.mockResolvedValue({ employees: [] })
    
    await store.deleteEmployee('emp_123')
    
    expect(api.delete).toHaveBeenCalledWith('/employees/emp_123')
  })

  it('should bind agent and refresh list', async () => {
    const store = useEmployeeStore()
    api.post.mockResolvedValue({ success: true })
    api.get.mockResolvedValue({ employees: [] })
    
    await store.bindAgent('emp_123', 'agent_456')
    
    expect(api.post).toHaveBeenCalledWith('/employees/emp_123/bind', {
      openclaw_agent_id: 'agent_456'
    })
  })

  it('should unbind agent and refresh list', async () => {
    const store = useEmployeeStore()
    api.post.mockResolvedValue({ success: true })
    api.get.mockResolvedValue({ employees: [] })
    
    await store.unbindAgent('emp_123')
    
    expect(api.post).toHaveBeenCalledWith('/employees/emp_123/unbind')
  })
})
