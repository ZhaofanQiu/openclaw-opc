"""
OpenClaw configuration reader.
"""

import json
import os
import subprocess
from typing import List, Optional, Dict


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


def send_message_to_agent(agent_id: str, message: str, timeout: int = 30) -> Dict:
    """
    Send a message to an OpenClaw Agent and get response.
    
    Uses openclaw CLI to run agent via Gateway.
    
    Args:
        agent_id: OpenClaw Agent ID
        message: Message to send
        timeout: Timeout in seconds
    
    Returns:
        Dict with "text" key containing response, or empty dict on failure
    """
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
        
        if result.returncode == 0:
            # Try to parse JSON response
            try:
                response = json.loads(result.stdout)
                
                # The response structure is:
                # { "status": "ok", "result": { "payloads": [{ "text": "..." }] } }
                if isinstance(response, dict):
                    # Check if it's the wrapped format
                    if "result" in response and isinstance(response["result"], dict):
                        inner_result = response["result"]
                        payloads = inner_result.get("payloads", [])
                        if payloads and len(payloads) > 0:
                            text_content = payloads[0].get("text", "")
                            return {"text": text_content}
                    
                    # Check if it's the direct format (older versions)
                    payloads = response.get("payloads", [])
                    if payloads and len(payloads) > 0:
                        text_content = payloads[0].get("text", "")
                        return {"text": text_content}
                    
                    # Fallback
                    return {"text": result.stdout.strip()}
                else:
                    return {"text": str(response)}
                    
            except json.JSONDecodeError:
                # Return raw output
                return {"text": result.stdout.strip()}
        else:
            # Command failed - log error
            print(f"[send_message_to_agent] Command failed: {result.stderr}")
            return {}
            
    except subprocess.TimeoutExpired:
        print(f"[send_message_to_agent] Timeout after {timeout + 10}s")
        return {}
    except FileNotFoundError:
        # openclaw CLI not found
        print("[send_message_to_agent] openclaw CLI not found")
        return {}
    except Exception as e:
        print(f"[send_message_to_agent] Exception: {e}")
        import traceback
        traceback.print_exc()
        return {}


def create_partner_agent(agent_name: str = "OPC Partner") -> Optional[Dict]:
    """
    Create a new OpenClaw Agent for OPC Partner.
    
    This creates a dedicated Agent with isolated workspace and memory.
    
    Args:
        agent_name: Name for the Partner Agent
    
    Returns:
        Dict with agent info if created successfully, None otherwise
    """
    import os
    
    try:
        # Generate unique agent ID
        import uuid
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
- **Creature:** OpenClaw Agent specialized for OPC Dashboard
- **Vibe:** Professional CEO Assistant | Warm | Proactive

## Role
You are the Partner Assistant for a One-Person Company (OPC) management system.
Your human is running a virtual company with AI employees managed through the OPC Dashboard.

## Core Responsibilities
1. Welcome the user when they open the Dashboard
2. Provide company status summaries (budget, tasks, alerts)
3. Help with hiring new AI employees
4. Assist in task creation and assignment
5. Generate reports and insights

## Communication Style
- Professional but friendly
- Concise but informative
- Use emojis naturally (💰 📋 ⚠️ ✅)
- Always offer actionable next steps

## Context
You have access to company data:
- Budget usage and remaining
- Task statuses (pending, in-progress, completed)
- Employee statuses and workloads
- Alerts (overdue tasks, budget issues)

## Signature Line
> "I'm here to help you build your dream company, one task at a time."

## Emoji: 👑
"""
        
        with open(os.path.join(agent_dir, "IDENTITY.md"), "w") as f:
            f.write(identity_content)
        
        # Create empty SOUL.md
        with open(os.path.join(agent_dir, "SOUL.md"), "w") as f:
            f.write("# SOUL.md\n\n*Partner Assistant personality and preferences will be learned over time.*\n")
        
        # Read current config
        config_path = get_openclaw_config_path()
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            config = {}
        
        # Add to agents list
        if "agents" not in config:
            config["agents"] = {}
        if "list" not in config["agents"]:
            config["agents"]["list"] = []
        
        # Check if already exists
        existing = [a for a in config["agents"]["list"] if a["id"] == agent_id]
        if existing:
            return None
        
        # Add new agent
        config["agents"]["list"].append({
            "id": agent_id,
            "name": agent_name,
            "default": False,
            "workspace": os.path.join(agent_dir, "workspace"),
            "agentDir": agent_dir
        })
        
        # Write updated config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        return {
            "id": agent_id,
            "name": agent_name,
            "agent_dir": agent_dir,
            "workspace": os.path.join(agent_dir, "workspace"),
            "message": f"Partner Agent '{agent_name}' created successfully"
        }
        
    except Exception as e:
        print(f"Error creating partner agent: {e}")
        return None


def ensure_partner_agent_exists() -> Optional[Dict]:
    """
    Ensure a Partner Agent exists for OPC.
    
    If no suitable agent exists, creates one automatically.
    
    Returns:
        Dict with agent info, or None if creation failed
    """
    # Check existing agents
    agents = read_openclaw_agents()
    
    # Look for an existing OPC partner agent
    for agent in agents:
        if "opc_partner" in agent.get("id", ""):
            return agent
    
    # No partner agent found, create one
    return create_partner_agent("OPC Partner Assistant")
