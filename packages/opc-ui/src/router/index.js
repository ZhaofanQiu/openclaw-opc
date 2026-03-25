import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    name: 'dashboard',
    component: () => import('@/views/DashboardView.vue'),
  },
  {
    path: '/employees',
    name: 'employees',
    component: () => import('@/views/EmployeesView.vue'),
  },
  {
    path: '/employees/:id',
    name: 'employee-detail',
    component: () => import('@/views/EmployeeDetailView.vue'),
  },
  {
    path: '/tasks',
    name: 'tasks',
    component: () => import('@/views/TasksView.vue'),
  },
  {
    path: '/tasks/:id',
    name: 'task-detail',
    component: () => import('@/views/TaskDetailView.vue'),
  },
  {
    path: '/workflows',
    name: 'workflows',
    component: () => import('@/views/WorkflowsView.vue'),
  },
  {
    path: '/workflows/create',
    name: 'workflow-create',
    component: () => import('@/views/WorkflowCreateView.vue'),
  },
  {
    path: '/workflows/:id',
    name: 'workflow-detail',
    component: () => import('@/views/WorkflowDetailView.vue'),
  },
  // v0.4.2-P2 新增
  {
    path: '/workflow-templates',
    name: 'workflow-templates',
    component: () => import('@/views/TemplateMarketView.vue'),
  },
  {
    path: '/workflows/:id/timeline',
    name: 'workflow-timeline',
    component: () => import('@/views/WorkflowTimelineView.vue'),
  },
  {
    path: '/workflow-analytics',
    name: 'workflow-analytics',
    component: () => import('@/views/WorkflowAnalyticsView.vue'),
  },
  {
    path: '/budget',
    name: 'budget',
    component: () => import('@/views/BudgetView.vue'),
  },
  {
    path: '/reports',
    name: 'reports',
    component: () => import('@/views/ReportsView.vue'),
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/SettingsView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  
  if (!to.meta.public && !authStore.isAuthenticated) {
    next('/login')
  } else {
    next()
  }
})

export default router
