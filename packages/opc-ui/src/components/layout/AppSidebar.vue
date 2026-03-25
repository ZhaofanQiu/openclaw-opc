<template>
  <aside class="sidebar">
    <nav class="nav">
      <router-link
        v-for="item in navItems"
        :key="item.name"
        :to="item.path"
        class="nav-item"
        :class="{ active: $route.path.startsWith(item.path) && item.path !== '/' }"
      >
        <span class="nav-icon">{{ item.icon }}</span>
        <span class="nav-text">{{ $t(item.labelKey) }}</span>
      </router-link>
    </nav>
  </aside>
</template>

<script setup>
const navItems = [
  { name: 'dashboard', path: '/', icon: '📊', labelKey: 'nav.dashboard' },
  { name: 'employees', path: '/employees', icon: '👥', labelKey: 'nav.employees' },
  { name: 'tasks', path: '/tasks', icon: '📋', labelKey: 'nav.tasks' },
  { name: 'workflows', path: '/workflows', icon: '🔄', labelKey: 'nav.workflows' },
  // v0.4.2-P2 新增
  { name: 'templates', path: '/workflow-templates', icon: '📑', labelKey: 'nav.templates' },
  { name: 'analytics', path: '/workflow-analytics', icon: '📉', labelKey: 'nav.analytics' },
  { name: 'budget', path: '/budget', icon: '💰', labelKey: 'nav.budget' },
  { name: 'reports', path: '/reports', icon: '📈', labelKey: 'nav.reports' },
  { name: 'settings', path: '/settings', icon: '⚙️', labelKey: 'nav.settings' },
]
</script>

<style scoped>
.sidebar {
  width: 200px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  padding: 16px 0;
}

.nav {
  display: flex;
  flex-direction: column;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  color: var(--text-secondary);
  text-decoration: none;
  transition: all 0.2s;
  border-left: 3px solid transparent;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary);
}

.nav-item.active {
  background: rgba(102, 126, 234, 0.1);
  color: var(--color-primary);
  border-left-color: var(--color-primary);
}

.nav-icon {
  font-size: 18px;
}

.nav-text {
  font-size: 14px;
}
</style>
