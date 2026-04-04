"""
opc-openclaw: Response Parser (Compatibility Wrapper)

解析 Agent 回复中的结构化报告数据。

注意：本模块从 v0.4.6 起不再维护独立的解析逻辑，
所有解析功能委托给 opc_openclaw.interaction.response_parser，
本文件仅保留向后兼容的导出和类方法签名。

作者: OpenClaw OPC Team
版本: 0.4.6
"""

from ..interaction.response_parser import (
    ParsedReport,
    ResponseParser as _InnerResponseParser,
    parse_response,
)
from .definition import REPORT_END_MARKER, REPORT_START_MARKER, VALID_STATUSES


class ResponseParser:
    """
    Agent 响应解析器（向后兼容包装）

    从 Agent 回复中提取结构化报告数据。
    内部委托给 opc_openclaw.interaction.response_parser.ResponseParser。
    """

    @classmethod
    def parse(cls, response_text: str) -> "ParsedReport":
        """
        解析 Agent 响应

        Args:
            response_text: Agent 的完整回复文本

        Returns:
            ParsedReport: 解析结果（即使失败也返回，is_valid=False）
        """
        parser = _InnerResponseParser()
        return parser.parse(response_text)

    @classmethod
    def extract_human_readable(cls, response_text: str) -> str:
        """
        提取人类可读部分（去除结构化数据）

        Returns:
            去除报告标记后的文本
        """
        return _InnerResponseParser._extract_human_readable(response_text)


__all__ = [
    "ResponseParser",
    "ParsedReport",
    "REPORT_START_MARKER",
    "REPORT_END_MARKER",
    "VALID_STATUSES",
    "parse_response",
]
