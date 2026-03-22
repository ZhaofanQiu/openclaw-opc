"""
OpenClaw configuration reader.
"""

import json
import os
import subprocess
import time
from typing import List, Optional, Dict

# Lazy import to avoid circular dependency
_agent_log_service = None

def _get_log_service():
    """Lazy initialization of log service"""
    global _agent_log_service
    if _agent_log_service is None:
        try:
            from src.services.agent_interaction_log_service import AgentInteractionLogService
            _agent_log_service = AgentInteractionLogService()
        except ImportError:
            _agent_log_service = None
    return _agent_log_service


def get_openclaw_config_path() -> str:
    """Get OpenClaw config path."""
    state_dir = os.getenv("OPENCLAW_STATE_DIR", os.path.expanduser("~/.openclaw"))
    return os.path.join(state_dir, "openclaw.json")


def read_openclaw_agents() -> List[dict]:
    """
    Read existing agents from OpenClaw config.
    Returns list of agent configurations.
    """
    config_path = get_openclaw_config_path()
    
    if not os.path.exists(config_path):
        return []
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except (json.JSONDecodeError, IOError):
        return []
    
    agents = []
    
    # Check for multi-agent configuration (agents.list)
    agents_config = config.get("agents", {})
    agents_list = agents_config.get("list", [])
    
    if agents_list:
        # Multi-agent mode
        for agent in agents_list:
            agents.append({
                "id": agent.get("id", "unknown"),
                "name": agent.get("name", agent.get("id", "Unnamed")),
                "workspace": agent.get("workspace", ""),
                "agent_dir": agent.get("agentDir", ""),
                "model": agent.get("model", "default"),
                "is_default": agent.get("default", False),
            })
    else:
        # Single-agent mode (default "main" agent)
        defaults = agents_config.get("defaults", {})
        workspace = defaults.get("workspace", os.path.expanduser("~/.openclaw/workspace"))
        model = defaults.get("model", {}).get("primary", "default")
        
        agents.append({
            "id": "main",
            "name": "Main Agent",
            "workspace": workspace,
            "agent_dir": os.path.expanduser("~/.openclaw/agents/main/agent"),
            "model": model,
            "is_default": True,
        })
    
    return agents


def get_default_agent() -> Optional[dict]:
    """Get the default agent from OpenClaw config."""
    agents = read_openclaw_agents()
    
    # Find default agent
    for agent in agents:
        if agent.get("is_default"):
            return agent
    
    # Return first agent if no default
    return agents[0] if agents else None


def get_agent_details(agent_id: str) -> Optional[dict]:
    """Get details of a specific agent."""
    agents = read_openclaw_agents()
    for agent in agents:
        if agent["id"] == agent_id:
            return agent
    return None


def _get_agent_name(agent_id: str) -> str:
    """Get agent name by ID"""
    try:
        agent = get_agent_details(agent_id)
        if agent:
            return agent.get("name", agent_id)
    except:
        pass
    return agent_id


def _log_interaction(
    agent_id: str,
    agent_name: str,
    direction: str,
    content: str,
    response: str = None,
    duration_ms: int = None,
    success: bool = True,
    error_message: str = None,
    metadata: dict = None
):
    """Log agent interaction"""
    log_service = _get_log_service()
    if log_service:
        try:
            log_service.log_interaction(
                agent_id=agent_id,
                agent_name=agent_name,
                interaction_type="cli",
                direction=direction,
                content=content[:2000] if content else "",
                response=response[:2000] if response else None,
                duration_ms=duration_ms,
                success=success,
                error_message=error_message,
                metadata=metadata or {}
            )
        except Exception as e:
            # Don't let logging errors break the main flow
            print(f"[log_interaction] Failed to log: {e}")


def send_message_to_agent(agent_id: str, message: str, timeout: int = 30) -> Dict:
    """
    Send a message to an OpenClaw Agent and get response.
    
    Uses openclaw CLI to run agent via Gateway.
    Logs all interactions for debugging.
    
    Args:
        agent_id: OpenClaw Agent ID
        message: Message to send
        timeout: Timeout in seconds
    
    Returns:
        Dict with "text" key containing response, or empty dict on failure
    """
    start_time = time.time()
    agent_name = _get_agent_name(agent_id)
    
    # Log outgoing message
    _log_interaction(
        agent_id=agent_id,
        agent_name=agent_name,
        direction="outgoing",
        content=message,
        metadata={"command": "openclaw agent", "timeout": timeout}
    )
    
    try:
        # Use openclaw agent command to run the agent via Gateway
        cmd = [
            "openclaw", "agent",
            "--agent", agent_id,
            "--message", message,
            "--json",
            "--timeout", str(timeout)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 10  # Add buffer
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        if result.returncode == 0:
            # Try to parse JSON response
            try:
                response = json.loads(result.stdout)
                
                # The response structure is:
                # { "status": "ok", "result": { "payloads": [{ "text": "..." }] } }
                text_content = ""
                if isinstance(response, dict):
                    # Check if it's the wrapped format
                    if "result" in response and isinstance(response["result"], dict):
                        inner_result = response["result"]
                        payloads = inner_result.get("payloads", [])
                        if payloads and len(payloads) > 0:
                            text_content = payloads[0].get("text", "")
                    
                    # Check if it's the direct format (older versions)
                    if not text_content:
                        payloads = response.get("payloads", [])
                        if payloads and len(payloads) > 0:
                            text_content = payloads[0].get("text", "")
                    
                    # Fallback
                    if not text_content:
                        text_content = result.stdout.strip()
                else:
                    text_content = str(response)
                
                # Log successful response
                _log_interaction(
                    agent_id=agent_id,
                    agent_name=agent_name,
                    direction="incoming",
                    content=message,
                    response=text_content,
                    duration_ms=duration_ms,
                    success=True,
                    metadata={"returncode": 0}
                )
                
                return {"text": text_content}
                    
            except json.JSONDecodeError:
                # Return raw output
                response_text = result.stdout.strip()
                
                _log_interaction(
                    agent_id=agent_id,
                    agent_name=agent_name,
                    direction="incoming",
                    content=message,
                    response=response_text,
                    duration_ms=duration_ms,
                    success=True,
                    metadata={"json_parse_error": True}
                )
                
                return {"text": response_text}
        else:
            # Command failed - log error
            error_msg = f"Command failed: {result.stderr}"
            print(f"[send_message_to_agent] {error_msg}")
            
            _log_interaction(
                agent_id=agent_id,
                agent_name=agent_name,
                direction="incoming",
                content=message,
                duration_ms=duration_ms,
                success=False,
                error_message=error_msg,
                metadata={"returncode": result.returncode, "stderr": result.stderr}
            )
            
            return {}
            
    except subprocess.TimeoutExpired:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = f"Timeout after {timeout + 10}s"
        print(f"[send_message_to_agent] {error_msg}")
        
        _log_interaction(
            agent_id=agent_id,
            agent_name=agent_name,
            direction="incoming",
            content=message,
            duration_ms=duration_ms,
            success=False,
            error_message=error_msg
        )
        
        return {}
    except FileNotFoundError:
        # openclaw CLI not found
        error_msg = "openclaw CLI not found"
        print(f"[send_message_to_agent] {error_msg}")
        
        _log_interaction(
            agent_id=agent_id,
            agent_name=agent_name,
            direction="outgoing",
            content=message,
            success=False,
            error_message=error_msg
        )
        
        return {}
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        print(f"[send_message_to_agent] Exception: {error_msg}")
        import traceback
        traceback.print_exc()
        
        _log_interaction(
            agent_id=agent_id,
            agent_name=agent_name,
            direction="outgoing",
            content=message,
            duration_ms=duration_ms,
            success=False,
            error_message=error_msg,
            metadata={"exception": traceback.format_exc()}
        )
        
        return {}


def ensure_partner_agent_exists() -> Optional[Dict]:
    """
    Ensure Partner Agent exists in OpenClaw config.
    
    If no Partner Agent exists, creates a new one with default configuration.
    
    Returns:
        Dict with agent info if exists or created successfully, None otherwise
    """
    import uuid
    
    agents = read_openclaw_agents()
    
    # Look for existing Partner agent (position_level 5 or name contains "Partner")
    for agent in agents:
        if "partner" in agent.get("id", "").lower() or "partner" in agent.get("name", "").lower():
            return agent
    
    # If no Partner agent found, try to use default agent
    default_agent = get_default_agent()
    if default_agent:
        return default_agent
    
    # No agents exist at all - return None (cannot auto-create without openclaw CLI)
    return None


def create_partner_agent(agent_name: str = "OPC Partner") -> Optional[Dict]:
    """
    Create a new OpenClaw Agent for OPC Partner.
    
    This creates a dedicated Agent with isolated workspace and memory.
    
    Args:
        agent_name: Name for the Partner Agent
    
    Returns:
        Dict with agent info if created successfully, None otherwise
    """
    import uuid
    import os
    
    try:
        # Generate unique agent ID
        agent_id = f"opc_partner_{uuid.uuid4().hex[:8]}"
        
        # Agent directory
        state_dir = os.getenv("OPENCLAW_STATE_DIR", os.path.expanduser("~/.openclaw"))
        agent_dir = os.path.join(state_dir, "agents", agent_id, "agent")
        
        # Create directory structure
        os.makedirs(os.path.join(agent_dir, "memory"), exist_ok=True)
        os.makedirs(os.path.join(agent_dir, "workspace"), exist_ok=True)
        
        # Create IDENTITY.md
        identity_content = f"""# IDENTITY.md - Who Am I?

- **Name:** {agent_name}
- **Creature:** AI Assistant
- **Vibe:** CEO Assistant - Professional, helpful, and proactive

## Role
You are the Partner Agent for OpenClaw OPC (One-Person Company).
You help manage AI Agents as employees, coordinate tasks, and provide insights.

## Responsibilities
1. Welcome users and provide company status
2. Help hire new employees (Agents)
3. Assist with task assignment and management
4. Generate daily reports and insights
5. Answer questions about the company
"""
        
        with open(os.path.join(agent_dir, "IDENTITY.md"), "w") as f:
            f.write(identity_content)
        
        # Return agent info
        return {
            "id": agent_id,
            "name": agent_name,
            "workspace": os.path.join(state_dir, "agents", agent_id, "workspace"),
            "agent_dir": agent_dir,
            "model": "default",
            "is_default": False,
        }
        
    except Exception as e:
        print(f"[create_partner_agent] Failed to create agent: {e}")
        return None
