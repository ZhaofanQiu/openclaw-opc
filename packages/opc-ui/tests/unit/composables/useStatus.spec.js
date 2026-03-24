import { describe, it, expect, vi } from 'vitest'
import { ref } from 'vue'
import { useStatusBadge } from '@/composables/useStatus'

// Mock vue-i18n
vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key) => {
      const translations = {
        'employees.statusTypes.idle': '空闲',
        'employees.statusTypes.working': '工作中',
        'employees.statusTypes.offline': '离线',
        'tasks.status.pending': '待分配',
        'tasks.status.completed': '已完成',
      }
      return translations[key] || key
    }
  })
}))

describe('useStatusBadge composable', () => {
  it('should return correct badge class for idle status', () => {
    const status = ref('idle')
    const { badgeClass } = useStatusBadge(status)
    
    expect(badgeClass.value).toBe('badge-success')
  })

  it('should return correct badge class for working status', () => {
    const status = ref('working')
    const { badgeClass } = useStatusBadge(status)
    
    expect(badgeClass.value).toBe('badge-warning')
  })

  it('should return correct badge class for offline status', () => {
    const status = ref('offline')
    const { badgeClass } = useStatusBadge(status)
    
    expect(badgeClass.value).toBe('badge-danger')
  })

  it('should return correct badge class for pending status', () => {
    const status = ref('pending')
    const { badgeClass } = useStatusBadge(status)
    
    expect(badgeClass.value).toBe('badge-info')
  })

  it('should return correct badge class for completed status', () => {
    const status = ref('completed')
    const { badgeClass } = useStatusBadge(status)
    
    expect(badgeClass.value).toBe('badge-success')
  })

  it('should return correct badge class for failed status', () => {
    const status = ref('failed')
    const { badgeClass } = useStatusBadge(status)
    
    expect(badgeClass.value).toBe('badge-danger')
  })

  it('should return default badge class for unknown status', () => {
    const status = ref('unknown')
    const { badgeClass } = useStatusBadge(status)
    
    expect(badgeClass.value).toBe('badge-info')
  })

  it('should return translated status text', () => {
    const status = ref('idle')
    const { statusText } = useStatusBadge(status)
    
    expect(statusText.value).toBe('空闲')
  })

  it('should react to status changes', () => {
    const status = ref('idle')
    const { badgeClass, statusText } = useStatusBadge(status)
    
    expect(badgeClass.value).toBe('badge-success')
    expect(statusText.value).toBe('空闲')
    
    status.value = 'working'
    
    expect(badgeClass.value).toBe('badge-warning')
    expect(statusText.value).toBe('工作中')
  })
})
