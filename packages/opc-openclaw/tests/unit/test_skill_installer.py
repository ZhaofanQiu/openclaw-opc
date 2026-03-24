"""
opc-openclaw: SkillInstaller 单元测试 (v0.4.1)
"""

from pathlib import Path

import pytest

from opc_openclaw.skill import SkillInstaller


class TestSkillInstaller:
    """SkillInstaller 测试"""

    @pytest.fixture
    def installer(self, temp_skill_dir):
        """创建测试用的 installer"""
        return SkillInstaller(skill_dir=temp_skill_dir)

    def test_init_default_path(self):
        """测试默认路径"""
        installer = SkillInstaller()
        assert installer.skill_dir == Path.home() / ".openclaw" / "skills" / "opc-bridge"

    def test_init_custom_path(self, temp_skill_dir):
        """测试自定义路径"""
        installer = SkillInstaller(skill_dir=temp_skill_dir)
        assert installer.skill_dir == temp_skill_dir

    def test_is_installed_false(self, installer):
        """测试未安装状态"""
        assert installer.is_installed() is False

    def test_is_installed_true(self, installer):
        """测试已安装状态"""
        # 创建 SKILL.md 文件
        installer.skill_dir.mkdir(parents=True, exist_ok=True)
        (installer.skill_dir / "SKILL.md").write_text("test")
        assert installer.is_installed() is True

    def test_install_creates_directory(self, installer):
        """测试安装创建目录"""
        success, msg = installer.install()

        assert success is True
        assert installer.skill_dir.exists()

    def test_install_creates_skill_md(self, installer):
        """测试安装创建 SKILL.md"""
        installer.install()

        skill_md = installer.skill_dir / "SKILL.md"
        assert skill_md.exists()
        content = skill_md.read_text()
        assert "opc-bridge" in content
        assert "0.4.1" in content
        assert "OPC-REPORT" in content

    def test_uninstall_success(self, installer):
        """测试成功卸载"""
        # 先安装
        installer.install()
        assert installer.is_installed()

        # 再卸载
        success, msg = installer.uninstall()
        assert success is True
        assert installer.is_installed() is False

    def test_uninstall_not_installed(self, installer):
        """测试卸载未安装的 skill"""
        success, msg = installer.uninstall()
        assert success is True  # 视为成功
        assert "is not installed" in msg

    def test_reinstall(self, installer):
        """测试重新安装"""
        # 先安装
        installer.install()
        old_content = (installer.skill_dir / "SKILL.md").read_text()

        # 修改内容模拟旧版本
        (installer.skill_dir / "SKILL.md").write_text("OLD VERSION")

        # 重新安装
        installer.reinstall()

        # 验证更新为新内容
        new_content = (installer.skill_dir / "SKILL.md").read_text()
        assert new_content == old_content
        assert "OLD VERSION" not in new_content

    def test_get_version(self, installer):
        """测试获取版本"""
        # 未安装时
        assert installer.get_version() == ""

        # 安装后
        installer.install()
        assert installer.get_version() == "0.4.1"


class TestSkillContent:
    """Skill 内容测试"""

    @pytest.fixture
    def installed_installer(self, temp_skill_dir):
        """已安装的 installer"""
        installer = SkillInstaller(skill_dir=temp_skill_dir)
        installer.install()
        return installer

    def test_skill_md_contains_report_format(self, installed_installer):
        """测试 SKILL.md 包含报告格式说明"""
        skill_md = installed_installer.skill_dir / "SKILL.md"
        content = skill_md.read_text()

        assert "---OPC-REPORT---" in content
        assert "---END-REPORT---" in content
        assert "task_id:" in content
        assert "status:" in content
        assert "completed|failed|needs_revision" in content
        assert "tokens_used:" in content

    def test_skill_md_contains_budget_info(self, installed_installer):
        """测试 SKILL.md 包含预算信息说明"""
        skill_md = installed_installer.skill_dir / "SKILL.md"
        content = skill_md.read_text()

        assert "预算信息" in content
        assert "本月预算" in content
        assert "已使用" in content
        assert "剩余" in content

    def test_skill_md_contains_example(self, installed_installer):
        """测试 SKILL.md 包含示例"""
        skill_md = installed_installer.skill_dir / "SKILL.md"
        content = skill_md.read_text()

        assert "示例：" in content
        assert "task-001" in content
        assert "summary:" in content
