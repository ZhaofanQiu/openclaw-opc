"""
opc-openclaw: 测试配置

Pytest 配置和共享 fixtures
"""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_config_dir():
    """创建临时配置目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / ".openclaw"
        config_dir.mkdir(parents=True, exist_ok=True)
        yield config_dir


@pytest.fixture
def sample_config():
    """示例 OpenClaw 配置"""
    return {
        "agents": {
            "opc-worker-1": {
                "name": "Worker One",
                "model": "kimi-coding/k2p5",
                "description": "Test worker",
            },
            "opc-worker-2": {
                "name": "Worker Two",
                "model": "kimi-coding/k2p5",
            },
            "main": {  # 应该被过滤
                "name": "Main",
                "model": "kimi-coding/k2p5",
            },
            "default": {  # 应该被过滤
                "name": "Default",
                "model": "kimi-coding/k2p5",
            },
            "other_agent": {  # 不以 opc- 开头，应该被过滤
                "name": "Other",
                "model": "kimi-coding/k2p5",
            },
        }
    }


@pytest.fixture
def mock_openclaw_bin():
    """Mock OpenClaw CLI 路径"""
    return "/usr/local/bin/openclaw"


@pytest.fixture
def temp_skill_dir():
    """创建临时 Skill 目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = Path(tmpdir) / "skills" / "opc-bridge"
        yield skill_dir