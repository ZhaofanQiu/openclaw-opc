# Week 2 计划 - UI 与自动化

## 目标
添加基础 Web UI 和 Partner 自动协调功能

## Day 1-3: 简单 HTML UI

### 任务
- [ ] 创建静态 HTML 页面 (无框架，纯 HTML+CSS+JS)
- [ ] 员工列表页面
- [ ] 任务列表页面
- [ ] 预算仪表盘
- [ ] 实时状态显示

### 技术方案
- 纯 HTML/CSS/JS (无构建工具)
- 放置于 `web/` 目录
- 使用 Fetch API 调用后端
- 简单轮询更新 (每 5 秒)

## Day 4-5: Partner 自动任务分配

### 任务
- [ ] Partner 查询待分配任务
- [ ] Partner 根据员工技能/预算分配任务
- [ ] 自动分配策略 (最简单: 预算充足的员工)

## Day 6-7: Docker 打包

### 任务
- [ ] Dockerfile for Core Service
- [ ] docker-compose.yml (Core + Web)
- [ ] 一键启动脚本

## 里程碑
- [ ] 能在浏览器看到员工列表
- [ ] 能看到预算状态
- [ ] Partner 能自动分配任务
- [ ] Docker 一键启动

---
