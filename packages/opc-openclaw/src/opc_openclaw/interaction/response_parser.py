"""
opc-openclaw: 响应解析器

解析 Agent 的任务响应，提取结构化数据、返工标记等

作者: OpenClaw OPC Team
创建日期: 2026-03-25
版本: 0.4.6
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ParsedReport:
    """
    解析后的任务报告

    包含 Agent 回复中的所有结构化信息
    """

    # 基本信息
    is_valid: bool = False  # 是否为有效报告
    task_id: str = ""  # 任务ID
    status: str = ""  # 状态: completed/failed/needs_revision
    tokens_used: int = 0  # Token消耗
    summary: str = ""  # 执行摘要
    result_files: list[str] = field(default_factory=list)  # 结果文件列表
    errors: list[str] = field(default_factory=list)  # 解析错误
    human_readable: Optional[str] = None  # 人类可读内容（非结构化部分）

    # v0.4.2 新增：结构化输出
    structured_output: Optional[dict] = None  # 结构化数据

    # v0.4.2 新增：返工标记
    needs_rework: bool = False  # 是否需要返工
    rework_target_step: Optional[int] = None  # 返工目标步骤索引
    rework_reason: Optional[str] = None  # 返工原因
    rework_instructions: Optional[str] = None  # 返工指令

    @property
    def is_success(self) -> bool:
        """是否成功完成"""
        return self.is_valid and self.status == "completed"

    @property
    def is_failed(self) -> bool:
        """是否失败"""
        return self.status == "failed"

    @property
    def needs_revision(self) -> bool:
        """是否需要返工/修订"""
        return self.status == "needs_revision" or self.needs_rework

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "is_valid": self.is_valid,
            "task_id": self.task_id,
            "status": self.status,
            "tokens_used": self.tokens_used,
            "summary": self.summary,
            "result_files": self.result_files,
            "errors": self.errors,
            "human_readable": self.human_readable,
            "structured_output": self.structured_output,
            "needs_rework": self.needs_rework,
            "rework_target_step": self.rework_target_step,
            "rework_reason": self.rework_reason,
            "rework_instructions": self.rework_instructions,
        }


class ResponseParser:
    """
    响应解析器

    解析 Agent 的文本回复，提取 OPC-REPORT、OPC-OUTPUT、OPC-REWORK 等标记块
    """

    # 正则表达式模式
    REPORT_PATTERN = re.compile(
        r"---OPC-REPORT---\s*(.*?)\s*(?:---END-REPORT---|$)",
        re.DOTALL | re.IGNORECASE,
    )

    OUTPUT_PATTERN = re.compile(
        r"---OPC-OUTPUT---\s*(.*?)\s*(?:---END-OUTPUT---|$)",
        re.DOTALL | re.IGNORECASE,
    )

    REWORK_PATTERN = re.compile(
        r"---OPC-REWORK---\s*(.*?)\s*(?:---END-REWORK---|$)",
        re.DOTALL | re.IGNORECASE,
    )

    def parse(self, content: str, expected_task_id: Optional[str] = None) -> ParsedReport:
        """
        解析 Agent 响应内容

        Args:
            content: Agent 回复的原始文本
            expected_task_id: 期望的任务ID（用于验证）

        Returns:
            ParsedReport 解析结果
        """
        report = ParsedReport()

        # 提取人类可读内容
        report.human_readable = self._extract_human_readable(content)

        # 1. 解析 OPC-REPORT 块
        self._parse_report_block(content, report, expected_task_id)

        # 2. 解析 OPC-OUTPUT 块（结构化输出）
        self._parse_output_block(content, report)

        # 3. 解析 OPC-REWORK 块（返工标记）
        self._parse_rework_block(content, report)

        return report

    @classmethod
    def _extract_human_readable(cls, content: str) -> str:
        """提取人类可读部分（去除结构化数据）"""
        if not content:
            return ""
        # 查找 REPORT 开始标记
        for marker in ["---OPC-REPORT---", "---opc-report---"]:
            idx = content.find(marker)
            if idx != -1:
                return content[:idx].strip()
        return content.strip()

    def _parse_report_block(
        self, content: str, report: ParsedReport, expected_task_id: Optional[str] = None
    ) -> None:
        """解析 OPC-REPORT 块"""
        match = self.REPORT_PATTERN.search(content)
        if not match:
            report.errors.append("未找到 OPC-REPORT 块")
            return

        report.is_valid = True
        report_block = match.group(1).strip()

        # 解析键值对（支持多行和 '=' 分隔符）
        lines = report_block.split("\n")
        current_key = None
        current_value = []

        for line in lines:
            line = line.rstrip()
            if not line:
                continue

            # 支持 key: value 或 key = value
            line_match = re.match(r"^(\w+)\s*[:=]\s*(.*)$", line)
            if line_match:
                # 保存之前的字段
                if current_key:
                    self._set_report_field(report, current_key, "\n".join(current_value).strip(), expected_task_id)
                current_key = line_match.group(1).lower().strip()
                current_value = [line_match.group(2)]
            elif current_key:
                current_value.append(line)

        if current_key:
            self._set_report_field(report, current_key, "\n".join(current_value).strip(), expected_task_id)

    def _set_report_field(
        self,
        report: ParsedReport,
        key: str,
        value: str,
        expected_task_id: Optional[str] = None,
    ) -> None:
        """设置报告字段"""
        if key == "task_id":
            report.task_id = value
            if expected_task_id and value != expected_task_id:
                report.errors.append(f"任务ID不匹配: 期望 {expected_task_id}, 实际 {value}")
        elif key == "status":
            report.status = value.lower().strip()
        elif key == "tokens_used":
            report.tokens_used = self._parse_tokens(value)
        elif key == "summary":
            report.summary = value
        elif key == "result_files":
            report.result_files = self._parse_result_files(value)

    def _parse_output_block(self, content: str, report: ParsedReport) -> None:
        """解析 OPC-OUTPUT 块（结构化输出）"""
        match = self.OUTPUT_PATTERN.search(content)
        if not match:
            return

        output_block = match.group(1).strip()
        try:
            report.structured_output = json.loads(output_block)
        except json.JSONDecodeError as e:
            report.errors.append(f"OPC-OUTPUT JSON 解析失败: {e}")

    def _parse_rework_block(self, content: str, report: ParsedReport) -> None:
        """解析 OPC-REWORK 块（返工标记）"""
        match = self.REWORK_PATTERN.search(content)
        if not match:
            return

        report.needs_rework = True
        rework_block = match.group(1).strip()

        # 解析键值对
        for line in rework_block.split("\n"):
            line = line.strip()
            if not line or ":" not in line:
                continue

            key, _, value = line.partition(":")
            key = key.strip().lower()
            value = value.strip()

            if key == "target_step":
                try:
                    report.rework_target_step = int(value)
                except ValueError:
                    report.errors.append(f"无效的 target_step: {value}")
            elif key == "reason":
                report.rework_reason = value
            elif key == "instructions":
                report.rework_instructions = value

        # 如果有返工标记但没有 status，自动设置为 needs_revision
        if report.needs_rework and not report.status:
            report.status = "needs_revision"

    @classmethod
    def _parse_tokens(cls, value: str) -> int:
        """解析 token 数（容错）"""
        if not value:
            return 0
        try:
            match = re.search(r"\d+", str(value))
            if match:
                return int(match.group())
        except (ValueError, TypeError):
            pass
        return 0

    @classmethod
    def _parse_result_files(cls, value: str) -> list[str]:
        """
        解析结果文件列表（容错）
        """
        if not value or value.strip().lower() in ("", "none", "null", "-", "n/a"):
            return []

        files = []
        # 尝试按逗号或换行分割
        for separator in [",", "\n", "  "]:
            if separator in value:
                for part in value.split(separator):
                    part = part.strip()
                    part = re.sub(r"^[-*]\s*", "", part)
                    if part and part not in ("", "-"):
                        files.append(part)
                return files

        value = re.sub(r"^[-*]\s*", "", value.strip())
        if value:
            files.append(value)
        return files


# 便捷函数
def parse_response(content: str, expected_task_id: Optional[str] = None) -> ParsedReport:
    """
    便捷解析函数

    Args:
        content: Agent 回复内容
        expected_task_id: 期望的任务ID

    Returns:
        ParsedReport
    """
    parser = ResponseParser()
    return parser.parse(content, expected_task_id)


__all__ = ["ResponseParser", "ParsedReport", "parse_response"]
