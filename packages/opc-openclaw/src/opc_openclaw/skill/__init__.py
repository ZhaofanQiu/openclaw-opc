"""
opc-openclaw: Skill 包 (v0.4.1)

OPC Bridge Skill 定义、安装器和响应解析器
"""

from .definition import (
    SKILL_DEFINITION,
    SKILL_METADATA,
    get_skill_definition,
    get_skill_yaml,
)
from .installer import SkillInstaller
from .parser import (
    ResponseParser,
    ParsedReport,
    REPORT_START_MARKER,
    REPORT_END_MARKER,
    VALID_STATUSES,
)

__all__ = [
    # 定义
    "SKILL_DEFINITION",
    "SKILL_METADATA",
    "get_skill_definition",
    "get_skill_yaml",
    # 安装器
    "SkillInstaller",
    # 解析器
    "ResponseParser",
    "ParsedReport",
    "REPORT_START_MARKER",
    "REPORT_END_MARKER",
    "VALID_STATUSES",
]