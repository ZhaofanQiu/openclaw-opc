"""
任务响应解析器
解析员工任务完成反馈
"""

import re
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TaskResult:
    """任务结果数据结构"""
    status: str  # completed/failed/partial
    result_summary: str
    output_path: Optional[str]
    token_used: int
    error_reason: Optional[str]
    raw_response: str
    is_valid_format: bool


class TaskResponseParser:
    """
    解析员工任务完成反馈
    
    期望的回复格式:
    ```
    STATUS: completed/failed
    RESULT: [结果摘要或失败原因]
    OUTPUT_PATH: [输出文件路径或数据库记录ID]
    TOKEN_USED: [实际消耗token数]
    ```
    """
    
    # 正则表达式模式
    STATUS_PATTERN = re.compile(r'STATUS:\s*(completed|failed|partial)', re.IGNORECASE)
    RESULT_PATTERN = re.compile(r'RESULT:\s*(.+?)(?=\n[A-Z_]+:|$)', re.DOTALL | re.IGNORECASE)
    OUTPUT_PATH_PATTERN = re.compile(r'OUTPUT_PATH:\s*(\S+)', re.IGNORECASE)
    TOKEN_USED_PATTERN = re.compile(r'TOKEN_USED:\s*(\d+)', re.IGNORECASE)
    ERROR_REASON_PATTERN = re.compile(r'(?:ERROR|FAILED|失败原因)[:：]\s*(.+?)(?=\n[A-Z_]+:|$)', re.DOTALL | re.IGNORECASE)
    
    def parse_response(self, response_text: str) -> TaskResult:
        """
        解析员工回复
        
        Args:
            response_text: 员工的回复文本
        
        Returns:
            TaskResult 对象
        """
        if not response_text:
            return TaskResult(
                status="unknown",
                result_summary="空回复",
                output_path=None,
                token_used=0,
                error_reason="No response content",
                raw_response="",
                is_valid_format=False
            )
        
        # 提取 STATUS
        status_match = self.STATUS_PATTERN.search(response_text)
        status = status_match.group(1).lower() if status_match else "unknown"
        
        # 提取 RESULT
        result_match = self.RESULT_PATTERN.search(response_text)
        result_summary = result_match.group(1).strip() if result_match else ""
        
        # 如果没有 RESULT 字段，尝试提取第一段文字
        if not result_summary:
            lines = response_text.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('STATUS:') and not line.startswith('OUTPUT_PATH:') and not line.startswith('TOKEN_USED:'):
                    result_summary = line
                    break
        
        # 提取 OUTPUT_PATH
        output_match = self.OUTPUT_PATH_PATTERN.search(response_text)
        output_path = output_match.group(1) if output_match else None
        
        # 提取 TOKEN_USED
        token_match = self.TOKEN_USED_PATTERN.search(response_text)
        token_used = int(token_match.group(1)) if token_match else 0
        
        # 提取失败原因 (如果状态是 failed)
        error_reason = None
        if status == "failed":
            error_match = self.ERROR_REASON_PATTERN.search(response_text)
            if error_match:
                error_reason = error_match.group(1).strip()
            elif not result_summary:
                error_reason = "任务失败，未提供具体原因"
            else:
                error_reason = result_summary
        
        # 判断格式是否有效
        is_valid_format = bool(status_match and result_summary)
        
        return TaskResult(
            status=status,
            result_summary=result_summary,
            output_path=output_path,
            token_used=token_used,
            error_reason=error_reason,
            raw_response=response_text,
            is_valid_format=is_valid_format
        )
    
    def parse_with_fuzzy_matching(self, response_text: str) -> TaskResult:
        """
        使用模糊匹配解析员工回复
        
        对于不严格遵循格式的回复，尝试智能提取信息
        """
        result = self.parse_response(response_text)
        
        # 如果格式无效，尝试模糊匹配
        if not result.is_valid_format:
            # 检查是否包含完成关键词
            completion_keywords = ['完成', 'done', 'finished', 'completed', '成功']
            failure_keywords = ['失败', 'fail', 'error', 'unable', 'cannot', '无法']
            
            text_lower = response_text.lower()
            
            # 判断状态
            if any(kw in text_lower for kw in completion_keywords):
                result.status = "completed"
            elif any(kw in text_lower for kw in failure_keywords):
                result.status = "failed"
            
            # 提取结果摘要（取前200字符）
            if not result.result_summary:
                result.result_summary = response_text[:200].strip()
            
            # 尝试提取文件路径
            if not result.output_path:
                path_patterns = [
                    r'(?:保存到|输出到|路径|path)[：:]\s*(\S+)',
                    r'(?:文件|file)[：:]\s*(\S+)',
                    r'`([^`]+\.(?:md|json|csv|txt|py|js))`',
                ]
                for pattern in path_patterns:
                    match = re.search(pattern, response_text, re.IGNORECASE)
                    if match:
                        result.output_path = match.group(1)
                        break
        
        return result
    
    def validate_result(self, result: TaskResult) -> Tuple[bool, str]:
        """
        验证任务结果是否有效
        
        Returns:
            (是否有效, 错误信息)
        """
        if result.status not in ["completed", "failed", "partial"]:
            return False, f"无效的状态: {result.status}"
        
        if not result.result_summary:
            return False, "缺少结果摘要"
        
        if result.status == "completed" and not result.output_path:
            return False, "完成的任务需要提供 OUTPUT_PATH"
        
        if result.token_used < 0:
            return False, "TOKEN_USED 不能为负数"
        
        return True, "有效"
    
    def format_success_response(
        self,
        result_summary: str,
        output_path: str,
        token_used: int = 0
    ) -> str:
        """生成标准的成功反馈格式"""
        return f"""STATUS: completed
RESULT: {result_summary}
OUTPUT_PATH: {output_path}
TOKEN_USED: {token_used}"""
    
    def format_failure_response(
        self,
        error_reason: str,
        token_used: int = 0
    ) -> str:
        """生成标准的失败反馈格式"""
        return f"""STATUS: failed
RESULT: 任务执行失败
ERROR: {error_reason}
TOKEN_USED: {token_used}"""


# ============ 任务结果处理器 ============

class TaskResultHandler:
    """
    处理任务结果，更新任务状态
    """
    
    def __init__(self, db_session):
        self.db = db_session
        self.parser = TaskResponseParser()
    
    def process_agent_response(
        self,
        task_id: str,
        agent_response: str,
        message_id: Optional[str] = None
    ) -> Dict:
        """
        处理 Agent 的任务完成回复
        
        Args:
            task_id: 任务ID
            agent_response: Agent 的回复文本
            message_id: 关联的消息ID
        
        Returns:
            处理结果
        """
        # 解析回复
        result = self.parser.parse_with_fuzzy_matching(agent_response)
        
        # 验证结果
        is_valid, error_msg = self.parser.validate_result(result)
        
        # 更新任务状态
        from models import Task, TaskStatus
        
        task = self.db.query(Task).filter(Task.id == task_id).first()
        
        if not task:
            return {
                "success": False,
                "error": f"Task {task_id} not found",
                "parsed_result": result.__dict__
            }
        
        # 根据解析结果更新任务
        if result.status == "completed":
            task.status = TaskStatus.COMPLETED.value
            task.execution_status = "completed"
            task.result_summary = result.result_summary
            if result.output_path:
                task.result_summary += f"\n输出路径: {result.output_path}"
            if result.token_used > 0:
                task.actual_tokens_output = result.token_used
            task.completed_at = datetime.utcnow()
            self.db.commit()
            
        elif result.status == "failed":
            task.status = TaskStatus.FAILED.value
            task.execution_status = "failed"
            task.result_summary = result.error_reason or result.result_summary
            if result.token_used > 0:
                task.actual_tokens_output = result.token_used
            self.db.commit()
            
        else:
            # 部分完成或其他状态
            task.execution_status = result.status
            task.result_summary = result.result_summary
            if result.output_path:
                if task.result_summary:
                    task.result_summary += f"\n输出路径: {result.output_path}"
                else:
                    task.result_summary = f"输出路径: {result.output_path}"
            self.db.commit()
        
        return {
            "success": True,
            "task_id": task_id,
            "status": result.status,
            "is_valid_format": result.is_valid_format,
            "validation_error": error_msg if not is_valid else None,
            "parsed_result": {
                "status": result.status,
                "result_summary": result.result_summary,
                "output_path": result.output_path,
                "token_used": result.token_used,
                "error_reason": result.error_reason,
            }
        }
