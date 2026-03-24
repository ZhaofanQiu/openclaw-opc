import { config } from '@vue/test-utils'
import { createPinia } from 'pinia'

// 全局配置
config.global.plugins = [createPinia()]

// 模拟全局组件
config.global.stubs = {
  'router-link': {
    template: '<a><slot /></a>',
  },
  'router-view': {
    template: '<div><slot /></div>',
  },
}

// 模拟全局属性
config.global.mocks = {
  $t: (key) => key,
  $i18n: {
    locale: 'zh-CN',
  },
}
