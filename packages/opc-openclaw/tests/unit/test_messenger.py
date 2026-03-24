"""
opc-openclaw: CLIMessenger 单元测试 (v0.4.1)
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from opc_openclaw.interaction import CLIMessenger, MessageResponse, MessageType


class TestCLIMessenger:
    """CLIMessenger 测试"""

    @pytest.fixture
    def messenger(self):
        """创建 messenger"""
        return CLIMessenger(openclaw_bin="/usr/bin/openclaw")

    @pytest.fixture
    def mock_cli_response(self):
        """Mock OpenClaw CLI 响应格式"""
        return {
            "runId": "test-run-id",
            "status": "ok",
            "summary": "completed",
            "result": {
                "payloads": [
                    {"text": "Hello from agent", "mediaUrl": None}
                ],
                "meta": {
                    "durationMs": 2000,
                    "agentMeta": {
                        "sessionId": "test-session-id",
                        "sessionKey": "agent:opc-test:main",
                        "provider": "kimi-coding",
                        "model": "k2p5",
                        "usage": {
                            "input": 100,
                            "output": 50,
                            "cacheRead": 12800,
                            "total": 12950
                        }
                    }
                }
            }
        }

    @pytest.mark.asyncio
    async def test_send_success(self, messenger, mock_cli_response):
        """测试成功发送消息"""
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(
            return_value=(json.dumps(mock_cli_response).encode(), b"")
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            response = await messenger.send(
                agent_id="opc-test-worker",
                message="Hello",
                timeout=300,
            )

        assert response.success is True
        assert response.content == "Hello from agent"
        assert response.session_key == "agent:opc-test:main"
        assert response.tokens_input == 100
        assert response.tokens_output == 50

    @pytest.mark.asyncio
    async def test_send_cli_error(self, messenger):
        """测试 CLI 错误"""
        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"", b"Agent not found"))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            response = await messenger.send(
                agent_id="opc-test-worker",
                message="Hello",
            )

        assert response.success is False
        assert "Agent not found" in response.error

    @pytest.mark.asyncio
    async def test_send_cli_not_found(self, messenger):
        """测试 CLI 不存在"""
        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError("openclaw not found"),
        ):
            response = await messenger.send(
                agent_id="opc-test-worker",
                message="Hello",
            )

        assert response.success is False
        assert "not found" in response.error

    @pytest.mark.asyncio
    async def test_send_timeout(self, messenger):
        """测试超时"""
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_proc.kill = MagicMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError()):
                response = await messenger.send(
                    agent_id="opc-test-worker",
                    message="Hello",
                    timeout=1,
                )

        assert response.success is False
        assert "Timeout" in response.error

    def test_parse_response_with_payloads(self, messenger, mock_cli_response):
        """测试解析包含 payloads 的响应"""
        stdout = json.dumps(mock_cli_response)
        response = messenger._parse_response(stdout)

        assert response.success is True
        assert response.content == "Hello from agent"
        assert response.session_key == "agent:opc-test:main"
        assert response.tokens_input == 100
        assert response.tokens_output == 50

    def test_parse_response_with_multiple_payloads(self, messenger):
        """测试解析包含多个 payloads 的响应"""
        stdout = json.dumps({
            "status": "ok",
            "result": {
                "payloads": [
                    {"text": "First part", "mediaUrl": None},
                    {"text": "Second part", "mediaUrl": None}
                ],
                "meta": {
                    "agentMeta": {
                        "sessionId": "sess-123",
                        "usage": {"input": 200, "output": 100}
                    }
                }
            }
        })
        response = messenger._parse_response(stdout)

        assert response.content == "First part\nSecond part"
        assert response.tokens_input == 200
        assert response.tokens_output == 100

    def test_parse_response_error_status(self, messenger):
        """测试解析错误状态响应"""
        stdout = json.dumps({
            "status": "error",
            "error": "Something went wrong"
        })
        response = messenger._parse_response(stdout)

        assert response.success is False

    def test_parse_response_plain_text(self, messenger):
        """测试解析纯文本响应"""
        stdout = "Plain text response"
        response = messenger._parse_response(stdout)

        assert response.success is True
        assert response.content == "Plain text response"

    def test_parse_response_empty(self, messenger):
        """测试解析空响应"""
        response = messenger._parse_response("")

        assert response.success is True
        assert response.content == ""

    def test_parse_response_with_warnings(self, messenger, mock_cli_response):
        """测试解析包含 Config warnings 的输出"""
        # 模拟 CLI 输出包含警告信息
        stdout = "Config warnings:\n- some warning\n" + json.dumps(mock_cli_response)
        response = messenger._parse_response(stdout)

        assert response.success is True
        assert response.content == "Hello from agent"

    @pytest.mark.asyncio
    async def test_send_with_message_type(self, messenger, mock_cli_response):
        """测试使用不同消息类型"""
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(
            return_value=(json.dumps(mock_cli_response).encode(), b"")
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
            await messenger.send(
                agent_id="opc-test-worker",
                message="Hello",
                message_type=MessageType.WAKEUP,
            )

        # 验证命令构建正确
        call_args = mock_exec.call_args
        assert call_args[0][0] == "/usr/bin/openclaw"
        assert "agent" in call_args[0]
        assert "--agent" in call_args[0]
        assert "opc-test-worker" in call_args[0]

    @pytest.mark.asyncio
    async def test_default_timeout(self, messenger, mock_cli_response):
        """测试默认超时时间"""
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(
            return_value=(json.dumps(mock_cli_response).encode(), b"")
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            with patch("asyncio.wait_for") as mock_wait:
                await messenger.send(
                    agent_id="opc-test-worker",
                    message="Hello",
                )

                # 验证超时时间是 900 秒（15分钟）+ 10 秒缓冲
                call_kwargs = mock_wait.call_args[1]
                assert call_kwargs["timeout"] == 910


class TestMessageResponse:
    """MessageResponse 测试"""

    def test_total_tokens(self):
        """测试总 token 计算"""
        response = MessageResponse(
            success=True,
            content="Test",
            tokens_input=100,
            tokens_output=50,
        )
        assert response.total_tokens == 150

    def test_default_values(self):
        """测试默认值"""
        response = MessageResponse(success=True)
        assert response.content == ""
        assert response.session_key is None
        assert response.tokens_input == 0
        assert response.tokens_output == 0
        assert response.error is None
