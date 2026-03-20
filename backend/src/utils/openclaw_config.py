"""
OpenClaw configuration reader.
"""

import json
import os
from typing import List, Optional


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
