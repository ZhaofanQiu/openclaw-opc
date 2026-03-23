"""
Configuration API routes - OpenClaw Agent management only (v2.0 simplified).
"""

import json
import os
import shutil
import signal
import subprocess
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class CreateAgentRequest(BaseModel):
    """Create new OpenClaw Agent request."""
    id: str = Field(..., pattern=r"^[a-z0-9_]+$", description="Agent ID (lowercase letters, numbers, underscores)")
    name: str = Field(..., min_length=1, max_length=50, description="Agent display name")
    model: str = Field(default="kimi-coding/k2p5", description="Default model for the agent")


def get_openclaw_config_path():
    """Get OpenClaw configuration directory."""
    # Try common paths
    paths = [
        "/root/.openclaw",
        os.path.expanduser("~/.openclaw"),
    ]
    for path in paths:
        if os.path.exists(path):
            return path
    return None


def get_openclaw_config():
    """Read openclaw.json configuration."""
    config_path = get_openclaw_config_path()
    if not config_path:
        return None
    
    config_file = os.path.join(config_path, "openclaw.json")
    if not os.path.exists(config_file):
        return None
    
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except Exception:
        return None


def save_openclaw_config(config):
    """Save openclaw.json configuration."""
    config_path = get_openclaw_config_path()
    if not config_path:
        raise Exception("OpenClaw configuration directory not found")
    
    config_file = os.path.join(config_path, "openclaw.json")
    
    # Backup original
    backup_file = config_file + ".backup"
    if os.path.exists(config_file):
        shutil.copy2(config_file, backup_file)
    
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        # Restore backup on failure
        if os.path.exists(backup_file):
            shutil.copy2(backup_file, config_file)
        raise Exception(f"Failed to save config: {str(e)}")


@router.get("/openclaw-agents")
async def get_openclaw_agents():
    """
    Get list of available OpenClaw Agents from configuration.
    
    Reads from openclaw.json agents.list
    """
    config = get_openclaw_config()
    if not config:
        return {"agents": [], "models": []}
    
    agents = config.get("agents", {})
    agent_list = agents.get("list", [])
    
    # Format agent list
    result_agents = []
    for agent in agent_list:
        result_agents.append({
            "id": agent.get("id"),
            "name": agent.get("name", agent.get("id")),
            "default": agent.get("default", False),
            "workspace": agent.get("workspace", ""),
            "agentDir": agent.get("agentDir", "")
        })
    
    # Get available models from defaults
    defaults = agents.get("defaults", {})
    models_config = defaults.get("models", {})
    models = []
    for model_id, model_info in models_config.items():
        models.append({
            "id": model_id,
            "name": model_info.get("alias", model_id),
            "primary": defaults.get("model", {}).get("primary") == model_id
        })
    
    # If no models in config, add default
    if not models:
        models = [{"id": "kimi-coding/k2p5", "name": "Kimi K2.5", "primary": True}]
    
    return {"agents": result_agents, "models": models}


@router.post("/agents")
async def create_openclaw_agent(request: CreateAgentRequest):
    """
    Create a new OpenClaw Agent by modifying openclaw.json.
    
    Adds agent to agents.list and creates agent directory.
    Returns restart_required flag to indicate gateway restart needed.
    """
    config = get_openclaw_config()
    if not config:
        raise HTTPException(status_code=500, detail="OpenClaw configuration not found")
    
    agents_config = config.get("agents", {})
    agent_list = agents_config.get("list", [])
    
    # Check if agent already exists
    for agent in agent_list:
        if agent.get("id") == request.id:
            raise HTTPException(status_code=400, detail=f"Agent '{request.id}' already exists")
    
    # Get config path for creating directories
    config_path = get_openclaw_config_path()
    agents_dir = os.path.join(config_path, "agents")
    agent_dir = os.path.join(agents_dir, request.id)
    
    try:
        # Create agent directory structure
        os.makedirs(agent_dir, exist_ok=True)
        os.makedirs(os.path.join(agent_dir, "sessions"), exist_ok=True)
        
        # Create AGENTS.md
        agents_md_path = os.path.join(agent_dir, "AGENTS.md")
        with open(agents_md_path, 'w') as f:
            f.write(f"# {request.name}\n\n")
            f.write(f"Created by OPC at {os.popen('date -Iseconds').read().strip()}\n\n")
            f.write("## About\n\n")
            f.write(f"This is an AI agent named {request.name}.\n\n")
        
        # Create workspace directory
        workspace_dir = os.path.join(config_path, f"workspace-{request.id}")
        os.makedirs(workspace_dir, exist_ok=True)
        
        # Create agent config in openclaw.json
        new_agent = {
            "id": request.id,
            "name": request.name,
            "default": False,
            "workspace": workspace_dir,
            "agentDir": agent_dir
        }
        
        # Add model configuration if provided
        if request.model:
            defaults = agents_config.get("defaults", {})
            if "models" not in defaults:
                defaults["models"] = {}
            if request.model not in defaults["models"]:
                # Add model alias
                model_alias = request.model.split('/')[-1].upper()
                defaults["models"][request.model] = {
                    "alias": model_alias
                }
            agents_config["defaults"] = defaults
        
        # Add agent to list
        agent_list.append(new_agent)
        agents_config["list"] = agent_list
        config["agents"] = agents_config
        
        # Save configuration
        save_openclaw_config(config)
        
        return {
            "success": True,
            "message": f"Agent '{request.id}' created successfully. Gateway restart required to activate.",
            "restart_required": True,
            "agent": {
                "id": request.id,
                "name": request.name,
                "model": request.model,
                "path": agent_dir
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        # Clean up on failure
        if os.path.exists(agent_dir):
            shutil.rmtree(agent_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {str(e)}")


@router.post("/gateway/restart")
async def restart_gateway():
    """
    Restart OpenClaw Gateway.
    
    Sends SIGUSR1 signal to trigger graceful restart.
    Requires user confirmation before calling this endpoint.
    """
    config_path = get_openclaw_config_path()
    if not config_path:
        raise HTTPException(status_code=500, detail="OpenClaw configuration not found")
    
    # Find gateway process
    try:
        # Try to find openclaw gateway process
        result = subprocess.run(
            ["pgrep", "-f", "openclaw.*gateway"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0 or not result.stdout.strip():
            # Try alternative method
            result = subprocess.run(
                ["pgrep", "-f", "node.*openclaw"],
                capture_output=True,
                text=True
            )
        
        if result.returncode != 0 or not result.stdout.strip():
            raise HTTPException(
                status_code=500, 
                detail="Gateway process not found. Is OpenClaw running?"
            )
        
        pid = int(result.stdout.strip().split('\n')[0])
        
        # Send SIGUSR1 for graceful restart
        os.kill(pid, signal.SIGUSR1)
        
        return {
            "success": True,
            "message": "Gateway restart signal sent",
            "pid": pid,
            "note": "Gateway is restarting. This may take 10-30 seconds."
        }
        
    except ProcessLookupError:
        raise HTTPException(status_code=500, detail="Gateway process not found")
    except PermissionError:
        raise HTTPException(status_code=500, detail="Permission denied. Cannot restart gateway.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to restart gateway: {str(e)}")


@router.get("/gateway/status")
async def get_gateway_status():
    """Check if OpenClaw Gateway is running."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "openclaw.*gateway"],
            capture_output=True,
            text=True
        )
        
        is_running = result.returncode == 0 and result.stdout.strip()
        
        # Get health endpoint if running
        health_status = "unknown"
        if is_running:
            try:
                import urllib.request
                req = urllib.request.Request(
                    "http://localhost:18789/health",
                    method="GET",
                    timeout=5
                )
                with urllib.request.urlopen(req) as response:
                    health_status = "healthy" if response.status == 200 else "unhealthy"
            except:
                health_status = "not responding"
        
        return {
            "running": is_running,
            "health": health_status,
            "config_path": get_openclaw_config_path()
        }
        
    except Exception as e:
        return {
            "running": False,
            "health": "error",
            "error": str(e)
        }
