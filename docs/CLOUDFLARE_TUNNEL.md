# Cloudflare Tunnel 部署指南

> 无需公网 IP，安全访问 OpenClaw OPC Dashboard

---

## 目录

- [什么是 Cloudflare Tunnel](#什么是-cloudflare-tunnel)
- [为什么选择 Cloudflare Tunnel](#为什么选择-cloudflare-tunnel)
- [前置要求](#前置要求)
- [快速开始](#快速开始)
- [详细部署步骤](#详细部署步骤)
- [域名配置](#域名配置)
- [生产环境部署](#生产环境部署)
- [故障排查](#故障排查)
- [安全建议](#安全建议)

---

## 什么是 Cloudflare Tunnel

[Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) 是 Cloudflare 提供的一项免费服务，它允许你将本地服务安全地暴露到互联网，而无需：

- ❌ 公网 IP 地址
- ❌ 配置路由器端口转发
- ❌ 购买 SSL 证书
- ❌ 配置防火墙规则

Cloudflare Tunnel 通过在本地运行一个轻量级客户端（`cloudflared`），建立一条加密的出站连接到 Cloudflare 的边缘网络。这样，流量总是从内向外流动，**外部无法直接访问你的服务器**，大大提高了安全性。

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   用户浏览器  │ ◄─────► │ Cloudflare   │ ◄─────► │ cloudflared │
│  (全球任何地方)│   HTTPS │ 边缘网络      │  加密隧道 │  (你的服务器)  │
└─────────────┘         └──────────────┘         └──────┬──────┘
                                                        │
                                                        ▼
                                                ┌─────────────┐
                                                │  OPC Backend │
                                                │   :8080      │
                                                └─────────────┘
```

---

## 为什么选择 Cloudflare Tunnel

| 特性 | 传统方案 (DDNS+端口转发) | Cloudflare Tunnel |
|------|-------------------------|-------------------|
| **公网 IP** | 必需 | ❌ 不需要 |
| **端口转发** | 需要配置路由器 | ❌ 不需要 |
| **SSL 证书** | 手动申请/续期 | ✅ 自动 HTTPS |
| **DDoS 防护** | ❌ 无 | ✅ Cloudflare 防护 |
| **访问控制** | ❌ 需要自己实现 | ✅ 内置身份验证 |
| **部署难度** | 复杂 | ✅ 简单 |
| **成本** | 域名 + DDNS 服务 | ✅ **免费** |

### 适合场景

- 🏠 家庭服务器 / NAS
- 🧪 开发测试环境
- 🚀 小型生产部署
- 📱 需要移动办公访问内部系统

---

## 前置要求

1. **Cloudflare 账号** - 免费注册：https://dash.cloudflare.com/sign-up
2. **域名**（可选）- 可以使用免费域名或购买自己的域名
3. **Docker 和 Docker Compose** - 已安装在你的服务器上
4. **OpenClaw OPC 已部署** - 本地可以正常访问

---

## 快速开始

如果你已经熟悉 Cloudflare，可以通过以下命令快速设置：

```bash
# 1. 登录 Cloudflare
docker run --rm -it cloudflare/cloudflared:latest tunnel login

# 2. 创建隧道
docker run --rm -it cloudflare/cloudflared:latest tunnel create opc-dashboard

# 3. 获取隧道凭证（复制输出中的 Tunnel ID）
docker run --rm -it cloudflare/cloudflared:latest tunnel list

# 4. 配置 DNS 路由（替换 your-domain.com 和 tunnel-id）
docker run --rm -it cloudflare/cloudflared:latest tunnel route dns <tunnel-id> opc.your-domain.com

# 5. 运行隧道
docker run --rm -it \
  -e TUNNEL_TOKEN=<你的令牌> \
  cloudflare/cloudflared:latest tunnel run
```

---

## 详细部署步骤

### 步骤 1：安装 cloudflared

我们使用 Docker 运行 cloudflared，无需在宿主机安装：

```bash
# 拉取最新镜像
docker pull cloudflare/cloudflared:latest
```

### 步骤 2：登录 Cloudflare

```bash
docker run --rm -it cloudflare/cloudflared:latest tunnel login
```

运行后会显示一个 URL，在浏览器中打开并授权：

```
Please open the following URL and log in with your Cloudflare account:

https://dash.cloudflare.com/argotunnel?callback=https%3A%2F%2Flocalhost%3A...

Leave cloudflared running to download the cert automatically.
```

授权成功后，证书会下载到 `~/.cloudflared/cert.pem`。

### 步骤 3：创建隧道

```bash
docker run --rm -it \
  -v ~/.cloudflared:/etc/cloudflared \
  cloudflare/cloudflared:latest tunnel create opc-dashboard
```

输出示例：
```
Tunnel credentials written to /etc/cloudflared/<tunnel-id>.json. cloudflared chose this file based on where your origin certificate was found. Keep this file secret. To revoke these credentials, delete the tunnel.

Created tunnel opc-dashboard with id <tunnel-id>
```

### 步骤 4：配置隧道

创建配置文件 `~/.cloudflared/config.yml`：

```yaml
tunnel: <your-tunnel-id>
credentials-file: /etc/cloudflared/<your-tunnel-id>.json

ingress:
  # Dashboard 前端
  - hostname: opc.your-domain.com
    service: http://frontend:80
    originRequest:
      noTLSVerify: true
  
  # API 后端
  - hostname: opc-api.your-domain.com
    service: http://backend:8080
    originRequest:
      noTLSVerify: true
  
  # 拒绝其他所有请求
  - service: http_status:404
```

### 步骤 5：配置 DNS 路由

```bash
# 将域名指向隧道
docker run --rm -it \
  -v ~/.cloudflared:/etc/cloudflared \
  cloudflare/cloudflared:latest tunnel route dns <tunnel-id> opc.your-domain.com

docker run --rm -it \
  -v ~/.cloudflared:/etc/cloudflared \
  cloudflare/cloudflared:latest tunnel route dns <tunnel-id> opc-api.your-domain.com
```

### 步骤 6：获取隧道令牌

```bash
# 查看隧道令牌（复制输出）
cat ~/.cloudflared/<tunnel-id>.json
```

或者使用命令获取：
```bash
docker run --rm -it \
  -v ~/.cloudflared:/etc/cloudflared \
  cloudflare/cloudflared:latest tunnel token <tunnel-id>
```

### 步骤 7：配置 OpenClaw OPC

1. 复制环境变量文件：
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，启用 API Key 认证并添加隧道令牌：

```bash
# ============================================
# API Key Authentication (Required for external access)
# ============================================
API_KEY_AUTH_ENABLED=true
API_KEY_SECRET=your-secure-secret-key-here  # 用于签名 API Keys

# ============================================
# Cloudflare Tunnel Configuration
# ============================================
CLOUDFLARE_TUNNEL_TOKEN=eyJhIjoi...

# ============================================
# Security Configuration
# ============================================
# 生产环境只允许 Cloudflare 域名访问
CORS_ORIGINS=https://opc.your-domain.com,https://opc-api.your-domain.com
```

### 步骤 8：启动生产环境

```bash
# 使用生产环境配置启动
docker-compose -f docker-compose.prod.yml up -d
```

### 步骤 9：验证部署

1. 访问 Dashboard：`https://opc.your-domain.com`
2. 使用 API Key 登录
3. 检查所有功能正常工作

---

## 域名配置

### 选项 A：使用自有域名

如果你已经有域名：

1. 将域名 NS 记录指向 Cloudflare（在域名注册商处设置）
2. 在 Cloudflare Dashboard 中添加站点
3. 按照上述步骤配置隧道 DNS

### 选项 B：使用免费 workers.dev 域名

Cloudflare 为每个账户提供一个免费的 `*.workers.dev` 子域名：

```bash
# 创建隧道时，路由到 workers.dev
docker run --rm -it \
  -v ~/.cloudflared:/etc/cloudflared \
  cloudflare/cloudflared:latest tunnel route dns <tunnel-id> opc-dashboard.<your-account>.workers.dev
```

> **注意**：workers.dev 域名在国内访问可能较慢，建议使用自有域名或配合 Cloudflare 中国网络优化。

---

## 生产环境部署

我们提供了 `docker-compose.prod.yml` 用于生产环境部署：

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: opc-backend
    expose:
      - "8080"  # 仅暴露给内部网络
    volumes:
      - ./data:/app/data
    environment:
      - DATABASE_URL=${DATABASE_URL:-sqlite:///data/opc.db}
      - LOG_LEVEL=INFO
      - CORS_ORIGINS=${CORS_ORIGINS:-*}
      - TOKEN_RATE=${TOKEN_RATE:-100}
      - BUDGET_WARNING_THRESHOLD=${BUDGET_WARNING_THRESHOLD:-80}
      - BUDGET_FUSE_THRESHOLD=${BUDGET_FUSE_THRESHOLD:-100}
      - TASK_TIMEOUT_MINUTES=${TASK_TIMEOUT_MINUTES:-30}
      - HEARTBEAT_INTERVAL=${HEARTBEAT_INTERVAL:-30}
      - HEARTBEAT_TIMEOUT=${HEARTBEAT_TIMEOUT:-60}
      - AUTO_ASSIGN_STRATEGY=${AUTO_ASSIGN_STRATEGY:-budget}
      # 启用 API Key 认证
      - API_KEY_AUTH_ENABLED=true
      - API_KEY_SECRET=${API_KEY_SECRET}
    restart: unless-stopped
    networks:
      - opc-network

  frontend:
    image: nginx:alpine
    container_name: opc-frontend
    expose:
      - "80"  # 仅暴露给内部网络
    volumes:
      - ./web:/usr/share/nginx/html:ro
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - backend
    restart: unless-stopped
    networks:
      - opc-network

  # Cloudflare Tunnel
  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: opc-tunnel
    command: tunnel run
    environment:
      - TUNNEL_TOKEN=${CLOUDFLARE_TUNNEL_TOKEN}
    restart: unless-stopped
    networks:
      - opc-network
    depends_on:
      - backend
      - frontend

networks:
  opc-network:
    name: opc-network
```

### 部署步骤

```bash
# 1. 确保 .env 文件已配置
cat .env | grep -E "(API_KEY|CLOUDFLARE)"

# 2. 启动生产环境
docker-compose -f docker-compose.prod.yml up -d

# 3. 查看日志
docker-compose -f docker-compose.prod.yml logs -f cloudflared

# 4. 验证隧道状态
docker-compose -f docker-compose.prod.yml ps
```

---

## 故障排查

### 隧道无法连接

**症状**：访问域名显示 "Error 1033" 或超时

**排查步骤**：

```bash
# 1. 检查 cloudflared 容器状态
docker-compose -f docker-compose.prod.yml ps cloudflared

# 2. 查看详细日志
docker-compose -f docker-compose.prod.yml logs -f cloudflared

# 3. 验证令牌是否正确
docker run --rm -it \
  -e TUNNEL_TOKEN=$CLOUDFLARE_TUNNEL_TOKEN \
  cloudflare/cloudflared:latest tunnel info

# 4. 测试本地服务是否可访问
curl http://localhost:8080/health
curl http://localhost:3000
```

### API Key 认证失败

**症状**：登录页面提示 "Invalid API Key"

**排查步骤**：

```bash
# 1. 检查 API Key 认证是否启用
docker-compose -f docker-compose.prod.yml exec backend env | grep API_KEY

# 2. 查看后端日志
docker-compose -f docker-compose.prod.yml logs -f backend

# 3. 手动创建 API Key
docker-compose -f docker-compose.prod.yml exec backend \
  python3 -c "from src.services.api_key_service import APIKeyService; print(APIKeyService.create_key('admin', ['read','write','admin'], None))"
```

### SSL/TLS 错误

**症状**：浏览器显示 "Your connection is not private"

**解决**：Cloudflare Tunnel 自动提供 SSL 证书，如果出现问题：

1. 检查 Cloudflare Dashboard 中 SSL/TLS 设置
2. 确保加密模式为 "Full (strict)" 或 "Full"
3. 清除浏览器缓存后重试

### 性能问题

**症状**：访问速度慢

**优化建议**：

```yaml
# 在 docker-compose.prod.yml 中添加资源限制
services:
  cloudflared:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M
        reservations:
          cpus: '0.25'
          memory: 128M
```

### 隧道断开重连

**症状**：日志显示频繁断开连接

**排查**：

```bash
# 检查网络稳定性
ping 1.1.1.1

# 查看 cloudflared 版本
docker run --rm cloudflare/cloudflared:latest version

# 尝试指定 Cloudflare 边缘节点
# 在 .env 中添加：
CLOUDFLARE_TUNNEL_EDGE_IP_VERSION=auto
```

---

## 安全建议

### 1. 启用 API Key 认证（必须）

```bash
# .env
API_KEY_AUTH_ENABLED=true
API_KEY_SECRET=$(openssl rand -hex 32)  # 生成随机密钥
```

### 2. 限制 CORS 来源

```bash
# .env - 只允许 Cloudflare 域名
CORS_ORIGINS=https://opc.your-domain.com
```

### 3. 使用 Cloudflare Access（可选）

在 Cloudflare Dashboard 中配置 Zero Trust Access，添加额外的身份验证层：

1. 登录 https://one.dash.cloudflare.com/
2. 导航到 Access → Applications
3. 添加你的域名
4. 配置身份提供商（Google、GitHub、OTP 等）

### 4. 定期轮换隧道令牌

```bash
# 1. 创建新隧道
docker run --rm -it cloudflare/cloudflared:latest tunnel create opc-dashboard-new

# 2. 更新 .env 中的令牌
# 3. 重启服务
docker-compose -f docker-compose.prod.yml up -d

# 4. 删除旧隧道
docker run --rm -it cloudflare/cloudflared:latest tunnel delete opc-dashboard
```

### 5. 监控和日志

```bash
# 启用 cloudflared 指标端点
docker-compose -f docker-compose.prod.yml exec cloudflared \
  cloudflared tunnel --metrics localhost:45678 info

# 查看实时指标
curl localhost:45678/metrics
```

---

## 参考文档

- [Cloudflare Tunnel 官方文档](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
- [cloudflared Docker 镜像](https://hub.docker.com/r/cloudflare/cloudflared)
- [Cloudflare Zero Trust](https://developers.cloudflare.com/cloudflare-one/)

---

## 获取帮助

如果遇到问题：

1. 查看 [故障排查](#故障排查) 章节
2. 检查 Cloudflare 状态页面：https://www.cloudflarestatus.com/
3. 提交 Issue：https://github.com/ZhaofanQiu/openclaw-opc/issues

---

**祝你部署顺利！** 🚀
