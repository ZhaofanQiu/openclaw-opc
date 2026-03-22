#!/bin/bash
# OpenClaw OPC API 使用示例脚本
# 演示完整的API调用流程

# 配置
BASE_URL="http://localhost:8000"
API_KEY="${OPC_API_KEY:-your-api-key}"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=================================="
echo "OpenClaw OPC API 示例脚本"
echo "=================================="
echo ""

# 检查依赖
if ! command -v curl &> /dev/null; then
    echo -e "${RED}错误: 需要安装 curl${NC}"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}警告: 建议安装 jq 以格式化 JSON 输出${NC}"
    JQ="cat"
else
    JQ="jq"
fi

# 辅助函数
api_call() {
    local method=$1
    local endpoint=$2
    local data=$3
    
    echo -e "${YELLOW}$method $endpoint${NC}"
    
    if [ -n "$data" ]; then
        curl -s -X "$method" \
            "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -H "X-API-Key: $API_KEY" \
            -d "$data" | $JQ
    else
        curl -s -X "$method" \
            "$BASE_URL$endpoint" \
            -H "X-API-Key: $API_KEY" | $JQ
    fi
    
    echo ""
}

# 1. 检查服务健康
echo "1. 检查服务健康状态..."
api_call "GET" "/health"
sleep 1

# 2. 设置Partner
echo "2. 设置 Partner..."
PARTNER_RESPONSE=$(api_call "POST" "/api/agents/partner/setup-auto" '{
    "monthly_budget": 10000
}')

# 提取 Partner ID (如果没有jq，需要手动设置)
if command -v jq &> /dev/null; then
    PARTNER_ID=$(echo "$PARTNER_RESPONSE" | jq -r '.partner.id // empty')
else
    echo -e "${YELLOW}请手动设置 PARTNER_ID 变量${NC}"
    PARTNER_ID=""
fi

if [ -z "$PARTNER_ID" ]; then
    echo -e "${YELLOW}使用默认 Partner ID: partner_001${NC}"
    PARTNER_ID="partner_001"
fi

echo "Partner ID: $PARTNER_ID"
sleep 1

# 3. 雇佣员工
echo "3. 雇佣员工..."
EMPLOYEE_RESPONSE=$(api_call "POST" "/api/agents/partner/hire?partner_id=$PARTNER_ID" '{
    "name": "开发助手",
    "emoji": "👨‍💻",
    "monthly_budget": 3000,
    "position_title": "全栈开发"
}')

if command -v jq &> /dev/null; then
    EMPLOYEE_ID=$(echo "$EMPLOYEE_RESPONSE" | jq -r '.employee.id // empty')
else
    echo -e "${YELLOW}请手动设置 EMPLOYEE_ID 变量${NC}"
    EMPLOYEE_ID=""
fi

if [ -z "$EMPLOYEE_ID" ]; then
    echo -e "${YELLOW}使用默认 Employee ID: employee_001${NC}"
    EMPLOYEE_ID="employee_001"
fi

echo "Employee ID: $EMPLOYEE_ID"
sleep 1

# 4. 列出所有员工
echo "4. 列出所有员工..."
api_call "GET" "/api/agents"
sleep 1

# 5. 获取可用Agent列表
echo "5. 获取可绑定的 OpenClaw Agent..."
api_call "GET" "/api/agents/binding/available"
sleep 1

# 6. 创建任务
echo "6. 创建任务..."
TASK_RESPONSE=$(api_call "POST" "/api/tasks" "{
    \"title\": \"开发用户登录功能\",
    \"description\": \"实现基于JWT的用户认证系统\",
    \"agent_id\": \"$EMPLOYEE_ID\",
    \"estimated_cost\": 500
}")

if command -v jq &> /dev/null; then
    TASK_ID=$(echo "$TASK_RESPONSE" | jq -r '.task.id // empty')
else
    TASK_ID=""
fi

if [ -z "$TASK_ID" ]; then
    echo -e "${YELLOW}使用默认 Task ID: task_001${NC}"
    TASK_ID="task_001"
fi

echo "Task ID: $TASK_ID"
sleep 1

# 7. 列出任务
echo "7. 列出任务..."
api_call "GET" "/api/tasks"
sleep 1

# 8. 获取预算汇总
echo "8. 获取预算汇总..."
api_call "GET" "/api/budget/summary"
sleep 1

# 9. 创建工作流
echo "9. 创建工作流..."
WORKFLOW_RESPONSE=$(api_call "POST" "/api/workflows?created_by=$PARTNER_ID" '{
    "title": "Web应用开发项目",
    "description": "开发一个完整的Web应用，包含前端和后端",
    "total_budget": 5000,
    "rework_budget_ratio": 0.2
}')

if command -v jq &> /dev/null; then
    WORKFLOW_ID=$(echo "$WORKFLOW_RESPONSE" | jq -r '.workflow.id // empty')
else
    WORKFLOW_ID=""
fi

if [ -z "$WORKFLOW_ID" ]; then
    echo -e "${YELLOW}使用默认 Workflow ID: workflow_001${NC}"
    WORKFLOW_ID="workflow_001"
fi

echo "Workflow ID: $WORKFLOW_ID"
sleep 1

# 10. 列出工作流
echo "10. 列出工作流..."
api_call "GET" "/api/workflows"
sleep 1

# 11. 获取成长路径
echo "11. 获取员工成长路径..."
api_call "GET" "/api/agent-skill-paths/agent/$EMPLOYEE_ID"
sleep 1

# 12. Partner 唤醒
echo "12. 唤醒 Partner..."
api_call "POST" "/api/agents/partner/wake?partner_id=$PARTNER_ID"
sleep 1

# 13. 获取公司状态
echo "13. 获取公司状态..."
api_call "GET" "/api/agents/partner/summary?partner_id=$PARTNER_ID"
sleep 1

echo ""
echo "=================================="
echo -e "${GREEN}示例脚本执行完成!${NC}"
echo "=================================="
echo ""
echo "关键 ID (请保存):"
echo "  Partner ID:   $PARTNER_ID"
echo "  Employee ID:  $EMPLOYEE_ID"
echo "  Task ID:      $TASK_ID"
echo "  Workflow ID:  $WORKFLOW_ID"
echo ""
echo "后续操作示例:"
echo "  # 启动工作流"
echo "  curl -X POST \"$BASE_URL/api/workflows/$WORKFLOW_ID/start\" -H \"X-API-Key: $API_KEY\""
echo ""
echo "  # 完成任务"
echo "  curl -X POST \"$BASE_URL/api/tasks/$TASK_ID/complete\" -H \"X-API-Key: $API_KEY\""
echo ""
