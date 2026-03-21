# Cloudflare Tunnel 部署指南

> ⚠️ **注意：本文档尚未经验证，仅供测试参考**
> 
> Quick Tunnel 方案存在连接不稳定问题，可能遇到 530 错误。
> 生产环境建议使用带有公网 IP 的服务器或购买独立域名配置正式 Tunnel。

---

## 快速开始（Quick Tunnel）

Cloudflare Quick Tunnel 是一种无需账号、无需域名的临时公网访问方案。

### 安装 cloudflared

```bash
# Linux (amd64)
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
dpkg -x cloudflared.deb /tmp/
cp /tmp/usr/bin/cloudflared /usr/local/bin/
chmod +x /usr/local/bin/cloudflared

# 验证安装
cloudflared version
```

### 启动 Quick Tunnel

```bash
# 确保 OPC 后端服务在 8080 端口运行
curl http://localhost:8080/health

# 启动临时公网隧道
cloudflared tunnel --url http://localhost:8080
```

输出示例：
```
INF |  https://xxxxx.trycloudflare.com  |
```

### 访问 Dashboard

```
https://xxxxx.trycloudflare.com/dashboard
```

使用 API Key 登录（通过后端创建）。

---

## ⚠️ 已知问题

| 问题 | 说明 |
|------|------|
| **连接不稳定** | Quick Tunnel 没有可用性保证，可能频繁断开 |
| **530 错误** | 隧道连接中断时会返回 530 错误 |
| **1 小时限制** | 临时隧道大约 1 小时后自动关闭 |
| **无自定义域名** | 无法使用自己的域名 |

---

## 生产环境建议

### 方案 1：购买域名 + 正式 Tunnel（推荐）

1. 购买域名（阿里云/腾讯云 .top/.xyz 首年 1-10 元）
2. 注册 Cloudflare 账号，添加域名
3. 创建正式 Tunnel 并配置 Public Hostname
4. 参考 Cloudflare 官方文档：https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/

### 方案 2：有公网 IP 的服务器

直接部署 OPC，配置防火墙开放端口，使用 Let's Encrypt SSL。

### 方案 3：其他内网穿透工具

- **ngrok**: 需要注册，免费版有速率限制
- **frp**: 需要自建服务端或有公网 IP 的服务器
- **花生壳/神卓互联**: 国内商业服务

---

## 安全提醒

⚠️ **启用 API Key 认证**

无论使用哪种公网访问方案，都必须启用 API Key 认证：

```bash
# .env
API_KEY_AUTH_ENABLED=true
API_KEY_SECRET=your-secure-secret-key
```

创建 API Key 后，Dashboard 和 Reports 页面需要登录才能访问。

---

## 参考文档

- [Cloudflare Tunnel 官方文档](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
- [cloudflared GitHub](https://github.com/cloudflare/cloudflared)
