#!/bin/bash
# OPC Bridge Skill 一键安装脚本
# Usage: curl -sSL <url> | bash

set -e

SKILL_NAME="opc-bridge-v2"
SKILL_DIR="$HOME/.openclaw/skills/$SKILL_NAME"
REPO_URL="https://github.com/your-org/openclaw-opc"

echo "╔════════════════════════════════════════════════════════╗"
echo "║     OPC Bridge Skill Installer                        ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# 检查 OpenClaw 是否安装
if ! command -v openclaw &> /dev/null; then
    echo "❌ OpenClaw is not installed"
    echo "   Please install OpenClaw first: https://docs.openclaw.ai"
    exit 1
fi
echo "✅ OpenClaw found"

# 创建 skills 目录
mkdir -p "$HOME/.openclaw/skills"

# 检查是否已安装
if [ -d "$SKILL_DIR" ]; then
    echo "⚠️  Skill already exists at $SKILL_DIR"
    read -p "   Overwrite? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "   Installation cancelled"
        exit 0
    fi
    rm -rf "$SKILL_DIR"
fi

# 安装方式选择
echo ""
echo "Select installation method:"
echo "  1) From local repository (if developing OPC)"
echo "  2) From GitHub (production)"
echo "  3) Manual copy"
read -p "Choice (1-3): " choice

case $choice in
    1)
        # 本地安装
        OPC_DIR="${OPC_DIR:-$HOME/.openclaw/workspace/openclaw-opc}"
        if [ -d "$OPC_DIR/skills/$SKILL_NAME" ]; then
            cp -r "$OPC_DIR/skills/$SKILL_NAME" "$SKILL_DIR"
            echo "✅ Installed from $OPC_DIR"
        else
            echo "❌ OPC directory not found at $OPC_DIR"
            echo "   Set OPC_DIR environment variable or choose another method"
            exit 1
        fi
        ;;
    2)
        # 从 GitHub 安装
        TEMP_DIR=$(mktemp -d)
        echo "📥 Downloading from GitHub..."
        curl -sL "$REPO_URL/archive/refs/heads/main.tar.gz" | tar -xz -C "$TEMP_DIR"
        cp -r "$TEMP_DIR/openclaw-opc-main/skills/$SKILL_NAME" "$SKILL_DIR"
        rm -rf "$TEMP_DIR"
        echo "✅ Installed from GitHub"
        ;;
    3)
        echo ""
        echo "Manual installation steps:"
        echo "  1. Copy the skill folder to: $SKILL_DIR"
        echo "  2. Make scripts executable: chmod +x $SKILL_DIR/scripts/*.py"
        echo "  3. Test: python3 $SKILL_DIR/scripts/opc-get-budget.py"
        exit 0
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

# 设置权限
chmod +x "$SKILL_DIR/scripts/"*.py

# 测试安装
echo ""
echo "Testing installation..."
export OPC_CORE_URL="${OPC_CORE_URL:-http://localhost:8080}"
export OPC_AGENT_ID="test"

if python3 "$SKILL_DIR/scripts/opc-get-budget.py" &> /dev/null; then
    echo "✅ Skill installed and functional"
elif python3 "$SKILL_DIR/scripts/opc-get-budget.py" 2>&1 | grep -q "Error"; then
    echo "⚠️  Skill installed but OPC service not running"
    echo "   Start OPC service to use the skill"
else
    echo "⚠️  Installation may have issues"
fi

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║     Installation Complete                             ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "Skill location: $SKILL_DIR"
echo ""
echo "Quick test:"
echo "  export OPC_CORE_URL=http://localhost:8080"
echo "  export OPC_AGENT_ID=your-agent-id"
echo "  python3 $SKILL_DIR/scripts/opc-get-budget.py"
echo ""
echo "Usage in agent:"
echo "  python3 {baseDir}/scripts/opc-report.py <task_id> <tokens> <summary>"
echo ""
