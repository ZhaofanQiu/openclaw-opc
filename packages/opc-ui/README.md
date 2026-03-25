# opc-ui

**OpenClaw OPC v0.4.1 - Vue3 Frontend**

基于 Vue 3 + Vite + Pinia + Vue I18n 的前端应用。

## 技术栈

- **Vue 3** - 渐进式框架
- **Vite** - 构建工具
- **Vue Router 4** - 路由
- **Pinia** - 状态管理
- **Vue I18n 9** - 国际化
- **Chart.js** - 图表

## 安装

```bash
cd packages/opc-ui
npm install
```

## 开发

```bash
npm run dev
```

开发服务器运行在 `http://localhost:3000`

API 请求自动代理到 `http://localhost:8000`

## 构建

```bash
npm run build
```

构建产物在 `dist/` 目录

## 项目结构

```
src/
├── components/          # 组件
│   └── layout/         # 布局组件
├── views/              # 页面视图
├── stores/             # Pinia stores
├── router/             # 路由配置
├── locales/            # i18n 语言包
├── composables/        # 组合式函数
├── utils/              # 工具函数
├── styles/             # 样式
├── App.vue             # 根组件
└── main.js             # 入口
```

## 路由

| 路径 | 页面 | 说明 |
|------|------|------|
| `/login` | 登录 | API Key 登录 |
| `/` | Dashboard | 数据概览 |
| `/employees` | 员工列表 | 员工管理 |
| `/employees/:id` | 员工详情 | |
| `/tasks` | 任务列表 | 任务管理 |
| `/tasks/:id` | 任务详情 | |
| `/budget` | 预算管理 | |
| `/reports` | 报表 | 绩效统计 |
| `/settings` | 设置 | 语言/API |

## 状态管理

### Stores

- `auth.js` - 认证状态 (API Key)
- `employees.js` - 员工数据
- `tasks.js` - 任务数据
- `budget.js` - 预算数据
- `reports.js` - 报表数据

## API 配置

前端通过代理访问后端 API：

```javascript
// vite.config.js
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  },
}
```

## 国际化

支持语言:
- 简体中文 (`zh-CN`)
- English (`en-US`)

切换语言自动保存到 `localStorage`

## 样式

- CSS Variables 主题色
- 响应式布局
- 暗黑主题（默认）
