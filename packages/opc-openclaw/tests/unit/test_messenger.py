"""
opc-openclaw: Messenger单元测试

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

import pytest

from opc_openclaw.interaction import Messenger, MessageResponse, MessageType


class TestMessenger:
    """Messenger 测试"""
    
    def test_message_response_properties(self):
        """测试 MessageResponse 属性"""
        response = MessageResponse(
            success=True,
            content="测试响应",
            session_key="sess_123",
            tokens_input=100,
            tokens_output=50
        )
        
        assert response.success is True
        assert response.content == "测试响应"
        assert response.session_key == "sess_123"
        assert response.total_tokens == 150  # 100 + 50
    
    def test_message_type_enum(self):
        """测试消息类型枚举"""
        assert MessageType.TASK.value == "task"
        assert MessageType.WAKEUP.value == "wakeup"
        assert MessageType.NOTIFICATION.value == "notification"


class TestMessageResponse:
    """MessageResponse 测试"""
    
    def test_error_response(self):
        """测试错误响应"""
        response = MessageResponse(
            success=False,
            error="连接失败"
        )
        
        assert response.success is False
        assert response.error == "连接失败"
        assert response.total_tokens == 0
    
    def test_empty_response(self):
        """测试空响应"""
        response = MessageResponse(success=True)
        
        assert response.success is True
        assert response.content == ""
        assert response.session_key is None
