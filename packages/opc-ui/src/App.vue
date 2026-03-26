<template>
  <div class="app">
    <AppHeader />
    <div class="app-body">
      <AppSidebar v-if="!isLoginPage" />
      <main class="app-main" :class="{ 'full-width': isLoginPage }">
        <router-view />
      </main>
    </div>
    
    <!-- Partner Widget - 全局存在 -->
    <PartnerWidget 
      v-if="!isLoginPage" 
      @openCreateEmployee="showEmployeeModal = true"
      @openCreateWorkflow="showWorkflowModal = true"
    />
    
    <!-- 全局对话框 -->
    <EmployeeCreateModal
      v-if="showEmployeeModal"
      @close="showEmployeeModal = false"
      @created="onEmployeeCreated"
    />
    
    <WorkflowAssistModal
      v-if="showWorkflowModal"
      @close="showWorkflowModal = false"
      @created="onWorkflowCreated"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppHeader from './components/layout/AppHeader.vue'
import AppSidebar from './components/layout/AppSidebar.vue'
import PartnerWidget from './components/partner/PartnerWidget.vue'
import EmployeeCreateModal from './components/employees/EmployeeCreateModal.vue'
import WorkflowAssistModal from './components/workflows/WorkflowAssistModal.vue'

const route = useRoute()
const router = useRouter()
const isLoginPage = computed(() => route.name === 'login')

// 对话框状态
const showEmployeeModal = ref(false)
const showWorkflowModal = ref(false)

// 创建成功回调
const onEmployeeCreated = () => {
  // 刷新当前页面数据
  window.location.reload()
}

const onWorkflowCreated = (workflow) => {
  // 导航到新创建的工作流
  if (workflow && workflow.id) {
    router.push(`/workflows/${workflow.id}`)
  }
}
</script>

<style>
/* 全局视图样式 */
.view {
  padding: 24px;
  min-height: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
}
</style>

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
