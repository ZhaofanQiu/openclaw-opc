# OpenClaw OPC Cpolar 远程测试配置指南

**文档版本**: v1.0  
**更新时间**: 2026-03-22  
**适用版本**: v0.3.0-beta+

---

## 前置条件

1. OPC Backend 已在本地运行 (localhost:8080)
2. 拥有 Cpolar 账号和 Authtoken
3. 服务器能够访问外网

---

## 快速配置步骤

### Step 1: 确认 OPC 服务运行

```bash
# 检查服务状态
curl http://localhost:8080/health

# 预期输出
{"status":"healthy","database":{"type":"sqlite","connected":true},"version":"0.2.0-alpha"}
```

**关键**: 必须先启动 OPC，再启动 cpolar！

### Step 2: 清理旧进程

```bash
# 停止所有 cpolar 进程
pkill -9 cpolar

# 确认清理
ps aux | grep cpolar | grep -v grep  # 应无输出
```

### Step 3: 启动 cpolar 隧道

```bash
# 使用前台模式启动（推荐，便于观察）
cpolar http 8080 --authtoken ZjQxNjlkN2MtODM0Yy00Yzc0LWI4NDktNjJmYmNiZjRkNDcw

# 或使用后台模式
nohup cpolar http 8080 --authtoken ZjQxNjlkN2MtODM0Yy00Yzc0LWI4NDktNjJmYmNiZjRkNDcw > /tmp/cpolar.log 2>&1 &
```

### Step 4: 获取公网 URL

启动后等待 5-10 秒，通过以下方式获取 URL：

```bash
# 方法 1: 通过 Web 界面 API
curl -s http://127.0.0.1:4040/http/in | grep -oE "https://[a-z0-9_-]+\.cpolar[^\"]*"

# 方法 2: 查看日志（后台模式）
grep -E "https://.*cpolar" /tmp/cpolar.log

# 方法 3: 直接访问 Web UI
curl -s http://127.0.0.1:4040/http/in | grep "PublicUrl"
```

### Step 5: 验证连接

```bash
# 测试公网访问
curl https://YOUR_URL.r19.cpolar.top/health

# 预期输出与本地相同
{"status":"healthy","database":{...}}
```

---

## 关键要点总结

### 1. 启动顺序至关重要

```
✅ 正确: 先 OPC → 后 cpolar
❌ 错误: 先 cpolar → 后 OPC (隧道会显示 unavailable)
```

如果顺序错了，必须重启 cpolar：
```bash
pkill cpolar
# 确认 OPC 运行中
cpolar http 8080 --authtoken YOUR_TOKEN
```

### 2. 使用中国区域服务器

如果连接不稳定，指定中国区域：
```bash
cpolar http 8080 --authtoken TOKEN --region cn
```

### 3. Token 有效性检查

Token 失效时会显示：`Failed to authenticate to switch server`

解决：
- 登录 https://dashboard.cpolar.com
- 获取新的 Authtoken

### 4. 端口占用检查

```bash
# 检查 4040 端口（cpolar Web UI）
netstat -tlnp | grep 4040

# 检查 8080 端口（OPC Backend）
netstat -tlnp | grep 8080
```

### 5. 网络连接确认

```bash
# 确认 cpolar 已连接到服务器
netstat -tnp | grep cpolar

# 预期看到 ESTABLISHED 连接到 cpolar 服务器
tcp ESTABLISHED ... 47.243.175.14:4443
```

---

## 常见问题

### Q1: cpolar 进程在运行但无法获取 URL

**原因**: 隧道尚未完全建立

**解决**: 
- 等待 10-15 秒
- 检查网络连接：`netstat -tnp | grep cpolar`
- 确认看到 ESTABLISHED 状态

### Q2: 显示 "Tunnel unavailable"

**原因**: OPC 服务未运行或端口不匹配

**解决**:
```bash
# 1. 确认 OPC 运行
curl http://localhost:8080/health

# 2. 确认端口匹配（cpolar 配置的是 8080）
netstat -tlnp | grep 8080

# 3. 重启 cpolar
pkill cpolar
cpolar http 8080 --authtoken TOKEN
```

### Q3: Token 认证失败

**错误**: `Failed to authenticate to switch server: user authToken auth failed`

**解决**:
- 在 https://dashboard.cpolar.com 获取新 token
- 确认 token 复制完整（无多余空格）

---

## 一键启动脚本

```bash
#!/bin/bash
# save as: start_test_env.sh

OPC_DIR="/root/.openclaw/workspace/openclaw-opc/backend"
CPOLAR_TOKEN="ZjQxNjlkN2MtODM0Yy00Yzc0LWI4NDktNjJmYmNiZjRkNDcw"

echo "=== 启动 OPC Backend ==="
cd "$OPC_DIR" || exit 1
source venv/bin/activate

# 检查是否已在运行
if curl -s http://localhost:8080/health > /dev/null; then
    echo "OPC 已在运行"
else
    nohup python -m uvicorn src.main:app --host 0.0.0.0 --port 8080 > /tmp/opc_backend.log 2>&1 &
    echo "OPC 启动中..."
    sleep 5
fi

# 确认 OPC 运行
curl -s http://localhost:8080/health || { echo "OPC 启动失败"; exit 1; }
echo "OPC 运行正常"

echo ""
echo "=== 启动 Cpolar 隧道 ==="
pkill -9 cpolar 2>/dev/null
sleep 1

nohup cpolar http 8080 --authtoken "$CPOLAR_TOKEN" > /tmp/cpolar.log 2>&1 &
echo "Cpolar 启动中..."
sleep 8

# 获取 URL
URL=$(curl -s http://127.0.0.1:4040/http/in 2>/dev/null | grep -oE "https://[a-z0-9_-]+\.cpolar[^\"]*" | head -1)

if [ -n "$URL" ]; then
    echo ""
    echo "✅ 测试环境已就绪！"
    echo "Dashboard: $URL/dashboard/"
    echo "Health: $URL/health"
else
    echo "⚠️  未能获取 URL，请检查 cpolar 状态"
fi
```

---

## 安全提醒

⚠️ **Cpolar 仅用于临时测试，测试完成后必须关闭！**

```bash
# 关闭隧道
pkill cpolar

# 确认关闭
ps aux | grep cpolar | grep -v grep  # 应无输出
```

---

## 历史记录

| 时间 | 事件 |
|------|------|
| 2026-03-22 | 首次成功配置 cpolar 隧道 |
| 2026-03-22 | URL: https://5fe0b0f7.r19.cpolar.top |
| 2026-03-22 | 完成第三轮实际使用场景测试 |
