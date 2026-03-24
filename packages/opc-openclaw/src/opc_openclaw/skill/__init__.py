"""
opc-openclaw: Skill包

Skill 定义和管理

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

from .definition import (
    SKILL_DEFINITION,
    SKILL_METADATA,
    get_skill_definition,
    get_skill_yaml,
)

__all__ = [
    "SKILL_DEFINITION",
    "SKILL_METADATA",
    "get_skill_definition",
    "get_skill_yaml",
]
