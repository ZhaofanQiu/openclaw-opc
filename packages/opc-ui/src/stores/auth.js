import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', () => {
  // State
  const apiKey = ref(localStorage.getItem('opc_api_key') || '')
  const isAuthenticated = computed(() => !!apiKey.value)

  // Actions
  function setApiKey(key) {
    apiKey.value = key
    localStorage.setItem('opc_api_key', key)
  }

  function clearApiKey() {
    apiKey.value = ''
    localStorage.removeItem('opc_api_key')
  }

  function logout() {
    clearApiKey()
  }

  return {
    apiKey,
    isAuthenticated,
    setApiKey,
    clearApiKey,
    logout,
  }
})
