import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
}
Object.defineProperty(window, 'localStorage', { value: localStorageMock })

describe('Auth Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('should initialize with empty apiKey', () => {
    localStorageMock.getItem.mockReturnValue(null)
    const store = useAuthStore()
    
    expect(store.apiKey).toBe('')
    expect(store.isAuthenticated).toBe(false)
  })

  it('should initialize with stored apiKey', () => {
    localStorageMock.getItem.mockReturnValue('test_api_key')
    const store = useAuthStore()
    
    expect(store.apiKey).toBe('test_api_key')
    expect(store.isAuthenticated).toBe(true)
  })

  it('should set apiKey and save to localStorage', () => {
    const store = useAuthStore()
    
    store.setApiKey('new_api_key')
    
    expect(store.apiKey).toBe('new_api_key')
    expect(store.isAuthenticated).toBe(true)
    expect(localStorageMock.setItem).toHaveBeenCalledWith('opc_api_key', 'new_api_key')
  })

  it('should clear apiKey and remove from localStorage', () => {
    const store = useAuthStore()
    store.setApiKey('test_key')
    
    store.clearApiKey()
    
    expect(store.apiKey).toBe('')
    expect(store.isAuthenticated).toBe(false)
    expect(localStorageMock.removeItem).toHaveBeenCalledWith('opc_api_key')
  })

  it('should logout and clear apiKey', () => {
    const store = useAuthStore()
    store.setApiKey('test_key')
    
    store.logout()
    
    expect(store.apiKey).toBe('')
    expect(store.isAuthenticated).toBe(false)
  })
})
