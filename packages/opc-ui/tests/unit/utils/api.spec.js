import { describe, it, expect, vi } from 'vitest'
import { formatCurrency, formatDate, statusMap } from '@/utils/api'

describe('API Utils', () => {
  describe('formatCurrency', () => {
    it('should format number as currency', () => {
      expect(formatCurrency(100)).toBe('¥100.00')
      expect(formatCurrency(100.5)).toBe('¥100.50')
      expect(formatCurrency(1000.99)).toBe('¥1000.99')
    })

    it('should handle zero', () => {
      expect(formatCurrency(0)).toBe('¥0.00')
    })

    it('should return dash for undefined/null', () => {
      expect(formatCurrency(undefined)).toBe('-')
      expect(formatCurrency(null)).toBe('-')
    })

    it('should handle string numbers', () => {
      expect(formatCurrency('100.5')).toBe('¥100.50')
    })
  })

  describe('formatDate', () => {
    it('should format ISO date string', () => {
      const result = formatDate('2024-03-24T10:30:00Z')
      expect(result).toContain('2024')
      expect(result).toContain('03')
      expect(result).toContain('24')
    })

    it('should return dash for empty string', () => {
      expect(formatDate('')).toBe('-')
    })

    it('should return dash for null/undefined', () => {
      expect(formatDate(null)).toBe('-')
      expect(formatDate(undefined)).toBe('-')
    })
  })

  describe('statusMap', () => {
    it('should have correct employee status mappings', () => {
      expect(statusMap.idle).toEqual({ label: '空闲', class: 'badge-success' })
      expect(statusMap.working).toEqual({ label: '工作中', class: 'badge-warning' })
      expect(statusMap.offline).toEqual({ label: '离线', class: 'badge-danger' })
    })

    it('should have correct task status mappings', () => {
      expect(statusMap.pending).toEqual({ label: '待分配', class: 'badge-info' })
      expect(statusMap.assigned).toEqual({ label: '已分配', class: 'badge-warning' })
      expect(statusMap.in_progress).toEqual({ label: '进行中', class: 'badge-warning' })
      expect(statusMap.completed).toEqual({ label: '已完成', class: 'badge-success' })
      expect(statusMap.failed).toEqual({ label: '失败', class: 'badge-danger' })
    })
  })
})
