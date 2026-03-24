// 测试工具函数

/**
 * 创建 Mock 员工数据
 */
export function createMockEmployee(overrides = {}) {
  return {
    id: 'emp_test123',
    name: '测试员工',
    emoji: '🤖',
    position_level: 2,
    monthly_budget: 1000,
    used_budget: 200,
    remaining_budget: 800,
    budget_percentage: 20,
    status: 'idle',
    completed_tasks: 5,
    openclaw_agent_id: 'agent_test',
    ...overrides,
  }
}

/**
 * 创建 Mock 任务数据
 */
export function createMockTask(overrides = {}) {
  return {
    id: 'task_test456',
    title: '测试任务',
    description: '这是一个测试任务',
    priority: 'normal',
    status: 'pending',
    estimated_cost: 500,
    actual_cost: 0,
    assigned_to: null,
    created_at: '2024-03-24T10:00:00',
    ...overrides,
  }
}

/**
 * 创建 Mock API 响应
 */
export function createMockResponse(data = {}, status = 200) {
  return {
    status,
    data,
  }
}

/**
 * 等待指定时间
 */
export function wait(ms = 0) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/**
 * 模拟 API 错误
 */
export function createMockError(message = 'Request failed', status = 500) {
  const error = new Error(message)
  error.response = {
    status,
    data: { detail: message },
  }
  return error
}
