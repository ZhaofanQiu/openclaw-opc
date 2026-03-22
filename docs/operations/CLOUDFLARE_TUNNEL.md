# Cloudflare Quick Tunnel 测试方案

> ⚠️ **警告：此方案尚未经验证，仅供测试使用**

---

## 概述

Cloudflare Quick Tunnel 是一种无需账号、无需配置的临时隧道方案，适合快速测试外网访问功能。

---

## ⚠️ 重要警告

**此方案存在以下已知问题：**

1. **连接不稳定** - Quick Tunnel 是临时性的，可能随时断开
2. **530 错误** - 可能遇到 Cloudflare 530 错误导致无法访问
3. **仅限测试** - 不建议用于生产环境或长期运行
4. **无持久域名** - 每次启动 URL 都会变化

---

## 快速开始

### 前提条件

- Docker 已安装
- OpenClaw OPC 本地可正常访问

### 启动 Quick Tunnel

```bash
# 确保 OpenClaw OPC 已在本地运行
# 然后启动 Quick Tunnel
docker run --rm -it cloudflare/cloudflared:latest tunnel --url http://host.docker.internal:3000
```

输出示例：
```
Your quick Tunnel URL: https://random-string.trycloudflare.com
```

### 访问 Dashboard

1. 复制输出的 URL（如 `https://random-string.trycloudflare.com`）
2. 在浏览器中打开
3. 使用 API Key 登录（需提前创建）

---

## 已知问题与解决

### 连接不稳定

**现象**：隧道突然断开，无法访问

**解决**：重新运行 Quick Tunnel 命令获取新 URL

### 530 错误

**现象**：浏览器显示 "Error 530"

**可能原因**：
- Cloudflare 边缘节点问题
- Quick Tunnel 服务临时不可用
- 本地服务未启动或端口错误

**解决**：
1. 检查本地服务是否正常运行
2. 重新启动 Quick Tunnel
3. 等待几分钟后重试

### CORS 错误

**现象**：API 请求失败，浏览器控制台显示 CORS 错误

**解决**：设置环境变量允许 Quick Tunnel 域名

```bash
# 在启动 OPC 前设置
export CORS_ORIGINS="https://*.trycloudflare.com"
```

---

## 生产环境建议

如需稳定的公网访问，建议：

1. **使用正式 Cloudflare Tunnel**（需 Cloudflare 账号和域名）
2. **使用传统方案**（公网 IP + DDNS + 反向代理）
3. **使用云服务部署**（VPS、云服务器等）

---

## 参考

- [Cloudflare Tunnel 文档](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
