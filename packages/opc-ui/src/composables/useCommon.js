import { ref, computed } from 'vue'

export function useLoading() {
  const loading = ref(false)
  
  const startLoading = () => {
    loading.value = true
  }
  
  const stopLoading = () => {
    loading.value = false
  }
  
  return {
    loading: computed(() => loading.value),
    startLoading,
    stopLoading,
  }
}

export function useModal() {
  const isOpen = ref(false)
  
  const open = () => {
    isOpen.value = true
  }
  
  const close = () => {
    isOpen.value = false
  }
  
  const toggle = () => {
    isOpen.value = !isOpen.value
  }
  
  return {
    isOpen: computed(() => isOpen.value),
    open,
    close,
    toggle,
  }
}

export function usePagination(initialPage = 1, initialLimit = 20) {
  const page = ref(initialPage)
  const limit = ref(initialLimit)
  const total = ref(0)
  
  const offset = computed(() => (page.value - 1) * limit.value)
  const totalPages = computed(() => Math.ceil(total.value / limit.value))
  
  const setPage = (p) => {
    page.value = p
  }
  
  const setTotal = (t) => {
    total.value = t
  }
  
  const reset = () => {
    page.value = initialPage
    total.value = 0
  }
  
  return {
    page: computed(() => page.value),
    limit: computed(() => limit.value),
    offset,
    total: computed(() => total.value),
    totalPages,
    setPage,
    setTotal,
    reset,
  }
}
