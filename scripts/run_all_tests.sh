#!/bin/bash
#
# OpenClaw OPC v0.4.1 统一测试脚本
# 运行所有模块的测试
#

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  OpenClaw OPC v0.4.1 模块测试套件   ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 统计变量
TOTAL_PASSED=0
TOTAL_FAILED=0

# 测试函数
run_test() {
    local module=$1
    local command=$2
    local dir=$3
    
    echo -e "${YELLOW}▶ 测试模块: $module${NC}"
    echo "--------------------------------------------"
    
    cd "$dir"
    
    if eval "$command"; then
        echo -e "${GREEN}✓ $module 测试通过${NC}"
        ((TOTAL_PASSED++))
        return 0
    else
        echo -e "${RED}✗ $module 测试失败${NC}"
        ((TOTAL_FAILED++))
        return 1
    fi
}

# 获取项目根目录
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}项目目录: $PROJECT_ROOT${NC}"
echo ""

# ============================================
# 1. 测试 opc-database
# ============================================
echo -e "${BLUE}[1/4] 测试 opc-database${NC}"
if [ -d "$PROJECT_ROOT/packages/opc-database" ]; then
    run_test "opc-database" \
        "pip install -e '.[dev]' -q && pytest tests/ -v --tb=short" \
        "$PROJECT_ROOT/packages/opc-database" || true
else
    echo -e "${YELLOW}⚠ opc-database 目录不存在，跳过${NC}"
fi
echo ""

# ============================================
# 2. 测试 opc-openclaw
# ============================================
echo -e "${BLUE}[2/4] 测试 opc-openclaw${NC}"
if [ -d "$PROJECT_ROOT/packages/opc-openclaw" ]; then
    # opc-openclaw 依赖 opc-database，先安装
    pip install -e "$PROJECT_ROOT/packages/opc-database" -q 2>/dev/null || true
    run_test "opc-openclaw" \
        "pip install -e '.[dev]' -q && pytest tests/ -v --tb=short" \
        "$PROJECT_ROOT/packages/opc-openclaw" || true
else
    echo -e "${YELLOW}⚠ opc-openclaw 目录不存在，跳过${NC}"
fi
echo ""

# ============================================
# 3. 测试 opc-core
# ============================================
echo -e "${BLUE}[3/4] 测试 opc-core${NC}"
if [ -d "$PROJECT_ROOT/packages/opc-core" ]; then
    # opc-core 依赖 opc-database 和 opc-openclaw，先安装
    pip install -e "$PROJECT_ROOT/packages/opc-database" -q 2>/dev/null || true
    pip install -e "$PROJECT_ROOT/packages/opc-openclaw" -q 2>/dev/null || true
    run_test "opc-core" \
        "pip install -e '.[dev]' -q && pytest tests/ -v --tb=short" \
        "$PROJECT_ROOT/packages/opc-core" || true
else
    echo -e "${YELLOW}⚠ opc-core 目录不存在，跳过${NC}"
fi
echo ""

# ============================================
# 4. 测试 opc-ui
# ============================================
echo -e "${BLUE}[4/4] 测试 opc-ui${NC}"
if [ -d "$PROJECT_ROOT/packages/opc-ui" ]; then
    run_test "opc-ui" \
        "npm install && npm run test" \
        "$PROJECT_ROOT/packages/opc-ui" || true
else
    echo -e "${YELLOW}⚠ opc-ui 目录不存在，跳过${NC}"
fi
echo ""

# ============================================
# 总结
# ============================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}           测试总结                    ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "通过: ${GREEN}$TOTAL_PASSED${NC}"
echo -e "失败: ${RED}$TOTAL_FAILED${NC}"
echo ""

if [ $TOTAL_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 所有测试通过！${NC}"
    exit 0
else
    echo -e "${RED}⚠ 有测试失败，请查看详细日志${NC}"
    exit 1
fi
