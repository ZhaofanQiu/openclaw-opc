"""
opc-openclaw: Skill定义单元测试

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

from opc_openclaw.skill import (
    get_skill_definition,
    get_skill_yaml,
    SKILL_METADATA,
    SKILL_DEFINITION,
)


class TestSkillDefinition:
    """Skill 定义测试"""
    
    def test_get_skill_definition(self):
        """测试获取 Skill 定义"""
        definition = get_skill_definition()
        
        assert "opc-bridge" in definition
        assert "opc_get_current_task" in definition
        assert "opc_report_task_result" in definition
        assert "opc_read_manual" in definition
        assert "opc_get_budget" in definition
    
    def test_get_skill_yaml(self):
        """测试获取 Skill YAML"""
        yaml = get_skill_yaml()
        
        assert "name: opc-bridge" in yaml
        assert "version: 2.0.0" in yaml
        assert "permissions:" in yaml
    
    def test_skill_metadata(self):
        """测试 Skill 元数据"""
        assert SKILL_METADATA["name"] == "opc-bridge"
        assert SKILL_METADATA["version"] == "2.0.0"
        assert "opc_get_current_task" in SKILL_METADATA["capabilities"]
        assert "opc_report_task_result" in SKILL_METADATA["capabilities"]
