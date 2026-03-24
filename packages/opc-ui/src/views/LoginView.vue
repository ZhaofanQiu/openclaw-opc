<template>
  <div class="view">
    <h1>{{ $t('login.title') }}</h1>
    
    <div class="login-form">
      <div class="form-group">
        <label class="form-label">{{ $t('login.apiKey') }}</label>
        <input
          v-model="apiKey"
          type="password"
          class="form-input"
          :placeholder="$t('login.apiKeyPlaceholder')"
          @keyup.enter="login"
        />
      </div>
      
      <button class="btn btn-primary btn-block" @click="login">
        {{ $t('common.confirm') }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const apiKey = ref('')

function login() {
  if (apiKey.value.trim()) {
    authStore.setApiKey(apiKey.value.trim())
    router.push('/')
  }
}
</script>

<style scoped>
.view {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 24px;
}

.login-form {
  width: 100%;
  max-width: 360px;
  margin-top: 32px;
}

.btn-block {
  width: 100%;
  margin-top: 24px;
}
</style>
