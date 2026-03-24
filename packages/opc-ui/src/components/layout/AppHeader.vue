<template>
  <header class="header">
    <div class="header-left">
      <div class="logo">
        <span class="logo-icon">🦾</span>
        <span class="logo-text">{{ $t('app.title') }}</span>
      </div>
    </div>
    
    <div class="header-right">
      <div class="api-key-input">
        <input
          v-model="apiKeyInput"
          type="password"
          :placeholder="$t('login.apiKeyPlaceholder')"
          class="form-input"
          @keyup.enter="saveApiKey"
        />
        <button class="btn btn-sm btn-primary" @click="saveApiKey">
          {{ $t('common.save') }}
        </button>
      </div>
      
      <button class="btn btn-sm btn-secondary" @click="toggleLocale">
        {{ currentLocale === 'zh-CN' ? 'EN' : '中' }}
      </button>
    </div>
  </header>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'

const { locale } = useI18n()
const authStore = useAuthStore()

const apiKeyInput = ref(authStore.apiKey)
const currentLocale = computed(() => locale.value)

function saveApiKey() {
  if (apiKeyInput.value.trim()) {
    authStore.setApiKey(apiKeyInput.value.trim())
    alert('API Key saved')
  }
}

function toggleLocale() {
  const newLocale = locale.value === 'zh-CN' ? 'en-US' : 'zh-CN'
  locale.value = newLocale
  localStorage.setItem('locale', newLocale)
}
</script>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  font-size: 24px;
}

.logo-text {
  font-size: 20px;
  font-weight: 600;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-secondary) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.api-key-input {
  display: flex;
  gap: 8px;
}

.api-key-input input {
  width: 200px;
}
</style>
