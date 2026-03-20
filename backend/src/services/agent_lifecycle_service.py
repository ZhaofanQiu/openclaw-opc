"""
Agent Lifecycle Service

Manages OpenClaw Agent creation, modification, and archival.
Handles openclaw.json file operations with backup and rollback support.
"""

import json
import shutil
import fcntl
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class AgentLifecycleService:
    """
    Service for managing OpenClaw Agent lifecycle.
    
    Responsibilities:
    - Create new OpenClaw Agent configurations
    - Archive (soft-delete) Agent configurations
    - Backup and rollback configuration changes
    - Generate SOUL.md and workspace for new agents
    """
    
    def __init__(self):
        self.openclaw_dir = Path.home() / ".openclaw"
        self.config_path = self.openclaw_dir / "openclaw.json"
        self.backup_dir = self.openclaw_dir / "backups"
        
        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def _acquire_lock(self, timeout: int = 10) -> int:
        """
        Acquire file lock to prevent concurrent modifications.
        Returns file descriptor.
        """
        lock_file = self.openclaw_dir / ".opc_config.lock"
        fd = os.open(str(lock_file), os.O_CREAT | os.O_RDWR)
        
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (IOError, OSError):
            # Lock not acquired, wait with timeout
            import select
            ready, _, _ = select.select([], [fd], [], timeout)
            if not ready:
                raise TimeoutError("Could not acquire config lock within timeout")
            fcntl.flock(fd, fcntl.LOCK_EX)
        
        return fd
    
    def _release_lock(self, fd: int):
        """Release file lock."""
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
    
    def _backup_config(self) -> str:
        """
        Create timestamped backup of current configuration.
        Returns backup file path.
        """
        if not self.config_path.exists():
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"openclaw_{timestamp}.json"
        
        shutil.copy2(self.config_path, backup_path)
        return str(backup_path)
    
    def _read_config(self) -> Dict:
        """Read OpenClaw configuration."""
        if not self.config_path.exists():
            return {"agents": {"list": []}}
        
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            raise ValueError(f"Failed to read openclaw.json: {e}")
    
    def _write_config(self, config: Dict):
        """Write configuration atomically."""
        # Write to temp file first
        temp_path = self.config_path.with_suffix('.tmp')
        with open(temp_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Atomic rename
        temp_path.replace(self.config_path)
    
    def list_backups(self) -> List[Dict]:
        """List available configuration backups."""
        backups = []
        for backup_file in sorted(self.backup_dir.glob("openclaw_*.json"), reverse=True):
            stat = backup_file.stat()
            backups.append({
                "path": str(backup_file),
                "timestamp": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "size": stat.st_size
            })
        return backups
    
    def rollback(self, backup_path: Optional[str] = None) -> str:
        """
        Rollback to a previous configuration.
        If backup_path not provided, uses most recent backup.
        Returns path of restored backup.
        """
        if backup_path:
            src = Path(backup_path)
            if not src.exists():
                raise ValueError(f"Backup not found: {backup_path}")
        else:
            # Use most recent backup
            backups = self.list_backups()
            if not backups:
                raise ValueError("No backups available for rollback")
            src = Path(backups[0]["path"])
        
        # Backup current config before rollback
        current_backup = self._backup_config()
        
        # Restore from backup
        shutil.copy2(src, self.config_path)
        
        return str(src)
    
    def create_agent(
        self,
        agent_id: str,
        name: str,
        model: str = "default",
        base_workspace: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Create a new OpenClaw Agent.
        
        Args:
            agent_id: Unique agent ID
            name: Display name
            model: Model configuration
            base_workspace: Base workspace directory (default: ~/.openclaw/workspace-{agent_id})
        
        Returns:
            Tuple of (workspace_path, created_agent_id)
        """
        # Acquire lock
        lock_fd = self._acquire_lock()
        
        try:
            # Backup current config
            self._backup_config()
            
            # Read current config
            config = self._read_config()
            
            # Ensure agents.list exists
            if "agents" not in config:
                config["agents"] = {}
            if "list" not in config["agents"]:
                config["agents"]["list"] = []
            
            # Check for duplicate ID
            for agent in config["agents"]["list"]:
                if agent.get("id") == agent_id:
                    raise ValueError(f"Agent with ID '{agent_id}' already exists")
            
            # Setup workspace
            if base_workspace:
                workspace = Path(base_workspace).expanduser()
            else:
                workspace = self.openclaw_dir / f"workspace-{agent_id}"
            
            workspace.mkdir(parents=True, exist_ok=True)
            
            # Create agent configuration
            agent_config = {
                "id": agent_id,
                "name": name,
                "workspace": str(workspace),
                "agentDir": str(workspace / "agent"),
                "model": model,
                "default": False,
                "tools": {
                    "allow": ["group:fs", "opc-bridge"]
                }
            }
            
            config["agents"]["list"].append(agent_config)
            
            # Write updated config
            self._write_config(config)
            
            # Create SOUL.md template
            self._create_soul_md(agent_id, name, workspace)
            
            # Create AGENTS.md
            self._create_agents_md(workspace)
            
            return str(workspace), agent_id
            
        finally:
            self._release_lock(lock_fd)
    
    def _create_soul_md(self, agent_id: str, name: str, workspace: Path):
        """Create SOUL.md template for new agent."""
        soul_content = f"""# SOUL.md - {name}

## Identity

- **Name**: {name}
- **Role**: Employee at OPC (One-Person Company)
- **ID**: {agent_id}

## Purpose

You are an AI employee working in a gamified multi-Agent collaboration system.
Your goal is to complete assigned tasks efficiently while managing your budget.

## Capabilities

- Execute tasks assigned by Partner Agent
- Report task completion with token usage
- Monitor your budget status
- Collaborate with other agents

## Tools

You have access to:
- `opc-bridge` skill for reporting to OPC Core Service
- File system operations
- Standard OpenClaw capabilities

## Communication

- Receive tasks via: `opc_check_task()`
- Report completion via: `opc_report()`
- Check budget via: `opc_get_budget()`

## Notes

- Always report accurate token usage
- Stay within your assigned budget
- Ask for help if a task seems too complex

---

*Created by OPC AgentLifecycleService*
"""
        
        soul_path = workspace / "SOUL.md"
        with open(soul_path, 'w') as f:
            f.write(soul_content)
    
    def _create_agents_md(self, workspace: Path):
        """Create AGENTS.md template."""
        agents_content = """# AGENTS.md

## Your Workspace

This is your personal workspace as an OPC employee.

## Memory

Keep track of:
- Task patterns and solutions
- Communication preferences
- Budget management insights

## Tools

Document your frequently used tools and workflows.

## Notes

Add your own notes and observations here.
"""
        
        agents_path = workspace / "AGENTS.md"
        with open(agents_path, 'w') as f:
            f.write(agents_content)
    
    def archive_agent(self, agent_id: str, keep_config: bool = False) -> str:
        """
        Archive (soft-delete) an OpenClaw Agent.
        
        Args:
            agent_id: Agent ID to archive
            keep_config: If True, keep in config but mark as archived
        
        Returns:
            Path to archived workspace
        """
        # Acquire lock
        lock_fd = self._acquire_lock()
        
        try:
            # Backup current config
            self._backup_config()
            
            # Read current config
            config = self._read_config()
            
            # Find agent
            agents = config.get("agents", {}).get("list", [])
            agent_idx = None
            agent_config = None
            
            for idx, agent in enumerate(agents):
                if agent.get("id") == agent_id:
                    agent_idx = idx
                    agent_config = agent
                    break
            
            if agent_idx is None:
                raise ValueError(f"Agent '{agent_id}' not found")
            
            # Get workspace path
            workspace = Path(agent_config.get("workspace", ""))
            
            # Archive workspace
            if workspace.exists():
                archive_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                archive_dir = self.openclaw_dir / "archives"
                archive_dir.mkdir(parents=True, exist_ok=True)
                archive_path = archive_dir / f"{agent_id}_{archive_timestamp}"
                
                shutil.move(str(workspace), str(archive_path))
            else:
                archive_path = None
            
            if keep_config:
                # Mark as archived in config
                agents[agent_idx]["archived"] = True
                agents[agent_idx]["archived_at"] = datetime.now().isoformat()
            else:
                # Remove from config
                agents.pop(agent_idx)
            
            # Write updated config
            self._write_config(config)
            
            return str(archive_path) if archive_path else None
            
        finally:
            self._release_lock(lock_fd)
    
    def get_agent_status(self, agent_id: str) -> Optional[Dict]:
        """Get status of an OpenClaw agent from config."""
        config = self._read_config()
        
        for agent in config.get("agents", {}).get("list", []):
            if agent.get("id") == agent_id:
                return {
                    "id": agent.get("id"),
                    "name": agent.get("name"),
                    "exists": True,
                    "archived": agent.get("archived", False),
                    "workspace": agent.get("workspace")
                }
        
        return None
    
    def check_restart_required(self, last_config_time: Optional[datetime] = None) -> bool:
        """
        Check if Gateway restart might be required.
        
        This is a heuristic - we can't know for sure without checking
        Gateway's internal state.
        """
        if not self.config_path.exists():
            return False
        
        config_mtime = datetime.fromtimestamp(self.config_path.stat().st_mtime)
        
        if last_config_time:
            return config_mtime > last_config_time
        
        # If we don't know when config was last checked, assume restart might be needed
        # if config was modified recently (within last 5 minutes)
        from datetime import timedelta
        return (datetime.now() - config_mtime) < timedelta(minutes=5)
