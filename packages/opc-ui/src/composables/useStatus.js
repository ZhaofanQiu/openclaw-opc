import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

export function useStatusBadge(status) {
  const { t } = useI18n()
  
  const badgeClass = computed(() => {
    const map = {
      idle: 'badge-success',
      working: 'badge-warning',
      offline: 'badge-danger',
      pending: 'badge-info',
      assigned: 'badge-warning',
      in_progress: 'badge-warning',
      completed: 'badge-success',
      failed: 'badge-danger',
    }
    return map[status.value] || 'badge-info'
  })
  
  const statusText = computed(() => {
    return t(`employees.statusTypes.${status.value}`) || 
           t(`tasks.status.${status.value}`) || 
           status.value
  })
  
  return {
    badgeClass,
    statusText,
  }
}
