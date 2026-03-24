<template>
  <div class="app">
    <AppHeader />
    <div class="app-body">
      <AppSidebar v-if="!isLoginPage" />
      <main class="app-main" :class="{ 'full-width': isLoginPage }">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from './components/layout/AppHeader.vue'
import AppSidebar from './components/layout/AppSidebar.vue'

const route = useRoute()
const isLoginPage = computed(() => route.name === 'login')
</script>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-body {
  display: flex;
  flex: 1;
}

.app-main {
  flex: 1;
  padding: 24px;
  background: var(--bg-secondary);
  overflow: auto;
}

.app-main.full-width {
  padding: 0;
}
</style>
