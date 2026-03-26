<template>
  <div class="view">
    <div class="page-header">
      <h1>{{ $t('nav.settings') }}</h1>
    </div>
    
    <div class="settings-section">
      <h2>语言设置</h2>
      
      <div class="setting-item">
        <label>选择语言</label>
        <select v-model="locale" class="form-input" @change="changeLocale">
          <option value="zh-CN">简体中文</option>
          <option value="en-US">English</option>
        </select>
      </div>
    </div>
    
    
    <div class="settings-section">
      <h2>API 设置</h2>
      
      <div class="setting-item">
        <label>API Key</label>
        <input
          v-model="apiKeyInput"
          type="password"
          class="form-input"
          placeholder="输入 API Key"
        />
        <button class="btn btn-primary mt-sm" @click="saveApiKey">
          {{ $t('common.save') }}
        </button>
      </div>
    </div>
    
    
    <div class="settings-section">
      <h2>关于</h2>
      
      <div class="about-info">
        <p><strong>OpenClaw OPC</strong></p>
        <p>版本: v0.4.3</p>
        <p>一人公司管理系统</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'

const { locale } = useI18n()
const authStore = useAuthStore()

const apiKeyInput = ref(authStore.apiKey)

function changeLocale() {
  localStorage.setItem('locale', locale.value)
}

function saveApiKey() {
  if (apiKeyInput.value.trim()) {
    authStore.setApiKey(apiKeyInput.value.trim())
    alert('API Key saved')
  }
}
</script>

<style scoped>
.page-header {
  margin-bottom: 24px;
}

.settings-section {
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  padding: 24px;
  margin-bottom: 24px;
  border: 1px solid var(--border-color);
}

.settings-section h2 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-color);
}

.setting-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.setting-item label {
  font-size: 14px;
  color: var(--text-secondary);
}

.about-info p {
  margin-bottom: 8px;
  color: var(--text-secondary);
}

.about-info strong {
  color: var(--text-primary);
  font-size: 16px;
}
</style>
