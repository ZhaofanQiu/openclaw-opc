#!/bin/bash
# 完整的端到端测试 - 使用真实 Agent

API_URL="http://localhost:8080/api/v1"

echo "=== 完整端到端测试 (使用真实 Agent) ==="
echo ""

# 使用已存在的 Agent
AGENT_ID="opc-test-worker"
echo "使用 Agent: $AGENT_ID"

# 1. 创建员工（绑定到真实 Agent）
echo ""
echo "1. 创建员工（绑定到 Agent: $AGENT_ID）..."
EMP_RESULT=$(curl -s -X POST $API_URL/employees \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试员工",
    "emoji": "🤖",
    "position_title": "测试工程师",
    "monthly_budget": 1000,
    "openclaw_agent_id": "'$AGENT_ID'"
  }')
echo "Employee: $EMP_RESULT"
EMP_ID=$(echo $EMP_RESULT | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "员工 ID: $EMP_ID"

# 2. 创建任务（预分配给该员工）
echo ""
echo "2. 创建任务..."
TASK_RESULT=$(curl -s -X POST $API_URL/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "写一首关于AI助手的小诗",
    "description": "请写一首简短的关于AI助手的小诗，4-6行即可",
    "employee_id": "'$EMP_ID'",
    "estimated_cost": 50
  }')
echo "Task: $TASK_RESULT"
TASK_ID=$(echo $TASK_RESULT | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "任务 ID: $TASK_ID"

# 3. 查看初始状态
echo ""
echo "3. 初始状态:"
curl -s $API_URL/tasks/$TASK_ID | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"  status: {d.get('status')}, assigned_to: {d.get('assigned_to')}\")"

# 4. 分配任务（异步）
echo ""
echo "4. 分配任务（异步）..."
START_TIME=$(date +%s)
ASSIGN_RESULT=$(curl -s -X POST $API_URL/tasks/$TASK_ID/assign \
  -H "Content-Type: application/json" \
  -d '{"employee_id": "'$EMP_ID'"}')
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
echo "  分配耗时: ${DURATION}秒 (应 < 1秒)"
echo "  响应状态: $(echo $ASSIGN_RESULT | python3 -c "import sys,json; print(json.load(sys.stdin)['task']['status'])")"

# 5. 轮询等待任务完成
echo ""
echo "5. 轮询等待任务完成（最长60秒）..."
for i in {1..12}; do
  TASK_DATA=$(curl -s $API_URL/tasks/$TASK_ID)
  STATUS=$(echo $TASK_DATA | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
  echo "  [$i] $(date '+%H:%M:%S') status: $STATUS"
  
  if [ "$STATUS" = "completed" ]; then
    echo ""
    echo "✅ 任务成功完成!"
    echo ""
    echo "任务结果:"
    echo $TASK_DATA | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"  结果: {d.get('result', 'N/A')}\")"
    echo ""
    echo "完整任务详情:"
    echo $TASK_DATA | python3 -m json.tool
    exit 0
  fi
  
  if [ "$STATUS" = "failed" ]; then
    echo ""
    echo "❌ 任务失败"
    echo ""
    echo "失败原因:"
    echo $TASK_DATA | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"  {d.get('result', 'Unknown error')}\")"
    exit 1
  fi
  
  sleep 5
done

echo ""
echo "⏱ 超时 - 任务仍在执行中"
exit 1
