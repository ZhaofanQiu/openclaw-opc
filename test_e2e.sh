#!/bin/bash
# 端到端测试脚本 - Phase 4 异步任务分配 (简化版)

API_URL="http://localhost:8080/api/v1"

echo "=== Phase 4 端到端测试 ==="
echo ""

# 获取已有员工
EMP_ID=$(curl -s $API_URL/employees | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['employees'][0]['id'] if d['employees'] else '')")
echo "员工 ID: $EMP_ID"

# 清理旧任务
echo "清理旧任务..."
curl -s $API_URL/tasks | python3 -c "
import sys, json
data = json.load(sys.stdin)
for task in data.get('tasks', []):
    print(task['id'])
" | while read task_id; do
  curl -s -X DELETE $API_URL/tasks/$task_id > /dev/null
done

# 创建任务（预分配给该员工）
echo ""
echo "创建任务（预分配）..."
TASK_RESULT=$(curl -s -X POST $API_URL/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "端到端测试任务",
    "description": "测试异步任务分配流程",
    "employee_id": "'$EMP_ID'",
    "estimated_cost": 100
  }')
echo "Task: $TASK_RESULT"

TASK_ID=$(echo $TASK_RESULT | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "任务 ID: $TASK_ID"
echo ""

# 1. 验证任务已预分配
echo "1. 任务初始状态:"
curl -s $API_URL/tasks/$TASK_ID | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"  assigned_to: {d.get('assigned_to')}, status: {d.get('status')}\")"
echo ""

# 2. 分配任务（异步）
echo "2. 分配任务（异步）..."
ASSIGN_START=$(date +%s)
ASSIGN_RESULT=$(curl -s -X POST $API_URL/tasks/$TASK_ID/assign \
  -H "Content-Type: application/json" \
  -d '{"employee_id": "'$EMP_ID'"}')
ASSIGN_END=$(date +%s)
ASSIGN_TIME=$((ASSIGN_END - ASSIGN_START))
echo "分配耗时: ${ASSIGN_TIME}秒"
echo "分配响应:"
echo $ASSIGN_RESULT | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"  status: {d.get('task',{}).get('status', 'unknown')}\")"
echo ""

# 3. 立即检查任务状态（应该是 assigned）
echo "3. 立即检查状态（应为 assigned）:"
curl -s $API_URL/tasks/$TASK_ID | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"  Status: {d.get('status')}, Started: {d.get('started_at')}\")"
echo ""

# 4. 轮询检查状态（模拟前端轮询）
echo "4. 轮询状态变化（5秒间隔，最多6次）..."
for i in {1..6}; do
  STATUS=$(curl -s $API_URL/tasks/$TASK_ID | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status', 'unknown'))")
  echo "  轮询 $i: status = $STATUS"
  
  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    echo ""
    echo "✅ 任务完成! 最终状态: $STATUS"
    echo ""
    echo "任务详情:"
    curl -s $API_URL/tasks/$TASK_ID | python3 -m json.tool
    exit 0
  fi
  
  sleep 5
done

echo ""
echo "⏱ 轮询结束"
echo "（由于 Agent 未真实配置，任务将停留在 assigned/in_progress 或转为 failed）"
