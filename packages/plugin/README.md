# OPC OpenClaw Plugin

OpenClaw 插件，桥接 Agent 和管理系统。

## 安装

将此目录作为 Skill 安装到 OpenClaw:

```bash
# 复制到 OpenClaw skills 目录
cp -r packages/plugin ~/.openclaw/skills/opc-plugin
```

## 配置

在 `config.json` 中设置 Core Service 地址:

```json
{
  "opc_core_url": "http://localhost:8080"
}
```

## 功能

- 拦截 Agent 调用
- 注入公司上下文
- 上报 Token 消耗
- 接收管理指令
