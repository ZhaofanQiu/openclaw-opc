"""
opc-openclaw: Response Parser

解析 Agent 回复中的结构化报告数据

作者: OpenClaw OPC Team
版本: 0.4.1
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .definition import REPORT_START_MARKER, REPORT_END_MARKER, REPORT_FIELDS, VALID_STATUSES


@dataclass
class ParsedReport:
    """解析后的任务报告"""
    task_id: str
    status: str  # completed, failed, needs_revision
    tokens_used: int
    summary: str
    result_files: List[str]
    raw_content: str  # 原始报告文本
    is_valid: bool  # 是否解析成功
    errors: List[str]  # 解析错误信息


class ResponseParser:
    """
    Agent 响应解析器
    
    从 Agent 回复中提取结构化报告数据
    具有充分的容错和错误检测机制
    """
    
    @classmethod
    def parse(cls, response_text: str) -> ParsedReport:
        """
        解析 Agent 响应
        
        Args:
            response_text: Agent 的完整回复文本
            
        Returns:
            ParsedReport: 解析结果（即使失败也返回，is_valid=False）
        """
        if not response_text:
            return cls._create_empty_report("Empty response")
        
        # 提取报告部分
        report_section, errors = cls._extract_report_section(response_text)
        
        if not report_section:
            return cls._create_empty_report(
                "Report section not found",
                raw_content="",
                errors=errors
            )
        
        # 解析报告字段
        data, parse_errors = cls._parse_report_fields(report_section)
        errors.extend(parse_errors)
        
        # 验证字段
        validation_errors = cls._validate_report(data)
        errors.extend(validation_errors)
        
        # 解析结果文件（逗号分隔或列表格式）
        result_files = cls._parse_result_files(data.get("result_files", ""))
        
        return ParsedReport(
            task_id=data.get("task_id", ""),
            status=data.get("status", "").lower().strip(),
            tokens_used=cls._parse_tokens(data.get("tokens_used", "0")),
            summary=data.get("summary", "").strip(),
            result_files=result_files,
            raw_content=report_section,
            is_valid=len(errors) == 0 and bool(data.get("task_id")),
            errors=errors
        )
    
    @classmethod
    def _extract_report_section(cls, text: str) -> Tuple[str, List[str]]:
        """
        提取报告部分（容错版本）
        
        支持多种格式变体：
        - 标准格式: ---OPC-REPORT--- ... ---END-REPORT---
        - 只有开始标记
        - 只有结束标记
        - 大小写不敏感
        """
        errors = []
        report_section = ""
        
        # 查找开始标记（不区分大小写）
        start_idx = -1
        for marker in [REPORT_START_MARKER, REPORT_START_MARKER.lower(), REPORT_START_MARKER.upper()]:
            start_idx = text.find(marker)
            if start_idx != -1:
                start_idx += len(marker)
                break
        
        if start_idx == -1:
            errors.append("Start marker '---OPC-REPORT---' not found")
            return "", errors
        
        # 查找结束标记
        end_idx = len(text)
        for marker in [REPORT_END_MARKER, REPORT_END_MARKER.lower(), REPORT_END_MARKER.upper()]:
            idx = text.find(marker, start_idx)
            if idx != -1:
                end_idx = idx
                break
        else:
            errors.append("End marker '---END-REPORT---' not found, using text until end")
        
        report_section = text[start_idx:end_idx].strip()
        
        if not report_section:
            errors.append("Report section is empty")
        
        return report_section, errors
    
    @classmethod
    def _parse_report_fields(cls, report_section: str) -> Tuple[Dict[str, str], List[str]]:
        """
        解析报告字段（容错版本）
        
        支持格式：
        - key: value
        - key:value
        - key = value
        """
        data = {}
        errors = []
        
        lines = report_section.split('\n')
        current_key = None
        current_value = []
        
        for line in lines:
            line = line.rstrip()
            if not line:
                continue
            
            # 尝试匹配 key: value 格式
            # 支持 task_id: xxx 或 task_id : xxx 或 task_id=xxx
            match = re.match(r'^(\w+)\s*[:=]\s*(.*)$', line)
            
            if match:
                # 保存之前的字段
                if current_key:
                    data[current_key] = '\n'.join(current_value).strip()
                
                current_key = match.group(1).lower().strip()
                current_value = [match.group(2)]
                
                # 检查是否是已知字段
                if current_key not in REPORT_FIELDS:
                    errors.append(f"Unknown field: {current_key}")
            elif current_key:
                # 继续当前字段的值（多行）
                current_value.append(line)
        
        # 保存最后一个字段
        if current_key:
            data[current_key] = '\n'.join(current_value).strip()
        
        return data, errors
    
    @classmethod
    def _validate_report(cls, data: Dict[str, str]) -> List[str]:
        """
        验证报告数据
        
        Returns:
            错误列表（空列表表示验证通过）
        """
        errors = []
        
        # 检查必填字段
        if not data.get("task_id"):
            errors.append("Missing required field: task_id")
        
        if not data.get("status"):
            errors.append("Missing required field: status")
        elif data.get("status", "").lower().strip() not in VALID_STATUSES:
            errors.append(f"Invalid status: {data.get('status')}, expected: {VALID_STATUSES}")
        
        # 检查 tokens_used 是否为数字
        tokens_str = data.get("tokens_used", "")
        if tokens_str:
            try:
                int(tokens_str)
            except ValueError:
                errors.append(f"Invalid tokens_used: {tokens_str}, expected number")
        
        return errors
    
    @classmethod
    def _parse_tokens(cls, value: str) -> int:
        """解析 token 数（容错）"""
        if not value:
            return 0
        try:
            # 提取数字部分
            match = re.search(r'\d+', str(value))
            if match:
                return int(match.group())
        except (ValueError, TypeError):
            pass
        return 0
    
    @classmethod
    def _parse_result_files(cls, value: str) -> List[str]:
        """
        解析结果文件列表（容错）
        
        支持格式：
        - /path/file1.md, /path/file2.md
        - /path/file1.md /path/file2.md
        - - /path/file1.md\n- /path/file2.md
        """
        if not value or value.strip() in ["", "none", "null", "-", "n/a"]:
            return []
        
        files = []
        
        # 尝试按逗号或空格分割
        for separator in [',', '\n', '  ']:
            if separator in value:
                parts = value.split(separator)
                for part in parts:
                    part = part.strip()
                    # 移除列表标记（- 或 *）
                    part = re.sub(r'^[-*]\s*', '', part)
                    if part and part not in ['', '-']:
                        files.append(part)
                return files
        
        # 单个文件
        value = re.sub(r'^[-*]\s*', '', value.strip())
        if value:
            files.append(value)
        
        return files
    
    @classmethod
    def _create_empty_report(cls, error_msg: str, raw_content: str = "", errors: List[str] = None) -> ParsedReport:
        """创建空的解析报告"""
        if errors is None:
            errors = []
        if error_msg:
            errors.append(error_msg)
        
        return ParsedReport(
            task_id="",
            status="",
            tokens_used=0,
            summary="",
            result_files=[],
            raw_content=raw_content,
            is_valid=False,
            errors=errors
        )
    
    @classmethod
    def extract_human_readable(cls, response_text: str) -> str:
        """
        提取人类可读部分（去除结构化数据）
        
        Returns:
            去除报告标记后的文本
        """
        if not response_text:
            return ""
        
        # 查找开始标记
        start_idx = -1
        for marker in [REPORT_START_MARKER, REPORT_START_MARKER.lower(), REPORT_START_MARKER.upper()]:
            start_idx = response_text.find(marker)
            if start_idx != -1:
                break
        
        if start_idx == -1:
            return response_text.strip()
        
        # 返回标记之前的文本
        return response_text[:start_idx].strip()


__all__ = [
    "ResponseParser",
    "ParsedReport",
    "REPORT_START_MARKER",
    "REPORT_END_MARKER",
    "VALID_STATUSES",
]