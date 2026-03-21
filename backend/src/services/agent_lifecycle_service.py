"""
Agent Configuration Manager

Manages OpenClaw agent configuration with safety mechanisms:
- Automatic backup before modifications
- Self-service restore capability
- User confirmation for dangerous operations
- File locking to prevent concurrent modifications
- Operation logging
"""

import json
import os
import shutil
import time
import fcntl
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class ConfigOperationError(Exception):
    """Configuration operation error."""
    pass


class AgentConfigManager:
    """
    Manages OpenClaw agent configuration file operations.
    
    Safety features:
    1. Automatic backup before any modification
    2. Backup retention (keep last 10 backups)
    3. Self-service restore from backup
    4. File locking to prevent concurrent modifications
    5. Operation audit logging
    """
    
    BACKUP_RETENTION_COUNT = 10
    LOCK_TIMEOUT = 30  # seconds
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize config manager.
        
        Args:
            config_path: Path to openclaw.json (default: ~/.openclaw/openclaw.json)
        """
        if config_path:
            self.config_path = Path(config_path)
        else:
            state_dir = os.getenv("OPENCLAW_STATE_DIR", os.path.expanduser("~/.openclaw"))
            self.config_path = Path(state_dir) / "openclaw.json"
        
        self.backup_dir = self.config_path.parent / "config_backups"
        self._ensure_backup_dir()
    
    def _ensure_backup_dir(self):
        """Ensure backup directory exists."""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def _acquire_lock(self) -> Optional[int]:
        """
        Acquire file lock for exclusive access.
        
        Returns:
            File descriptor if lock acquired, None otherwise
        """
        lock_file = self.config_path.parent / ".openclaw.json.lock"
        try:
            fd = os.open(str(lock_file), os.O_CREAT | os.O_RDWR)
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except (IOError, OSError) as e:
            logger.error("Failed to acquire config lock", error=str(e))
            return None
    
    def _release_lock(self, fd: int):
        """Release file lock."""
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
        except Exception as e:
            logger.error("Failed to release config lock", error=str(e))
    
    def create_backup(self, reason: str = "manual") -> str:
        """
        Create a backup of current config.
        
        Args:
            reason: Backup reason for tracking
            
        Returns:
            Backup file path
            
        Raises:
            ConfigOperationError: If backup fails
        """
        if not self.config_path.exists():
            raise ConfigOperationError(f"Config file not found: {self.config_path}")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"openclaw_{timestamp}_{reason}.json"
        backup_path = self.backup_dir / backup_name
        
        try:
            shutil.copy2(self.config_path, backup_path)
            logger.info("Config backup created", backup_path=str(backup_path), reason=reason)
            
            # Clean old backups
            self._cleanup_old_backups()
            
            return str(backup_path)
        except Exception as e:
            logger.error("Failed to create config backup", error=str(e))
            raise ConfigOperationError(f"Backup failed: {e}")
    
    def _cleanup_old_backups(self):
        """Remove old backups, keeping only the most recent ones."""
        try:
            backups = sorted(
                self.backup_dir.glob("openclaw_*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            for old_backup in backups[self.BACKUP_RETENTION_COUNT:]:
                old_backup.unlink()
                logger.info("Removed old config backup", backup=str(old_backup))
        except Exception as e:
            logger.warning("Failed to cleanup old backups", error=str(e))
    
    def list_backups(self) -> List[Dict]:
        """
        List available backups.
        
        Returns:
            List of backup info dicts with path, timestamp, reason
        """
        backups = []
        try:
            for backup_file in sorted(self.backup_dir.glob("openclaw_*.json"), reverse=True):
                stat = backup_file.stat()
                # Parse filename: openclaw_YYYYMMDD_HHMMSS_reason.json
                parts = backup_file.stem.split("_")
                reason = parts[-1] if len(parts) > 3 else "unknown"
                
                backups.append({
                    "path": str(backup_file),
                    "filename": backup_file.name,
                    "timestamp": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "reason": reason,
                    "size": stat.st_size
                })
        except Exception as e:
            logger.error("Failed to list backups", error=str(e))
        
        return backups
    
    def restore_backup(self, backup_path: str, create_new_backup: bool = True) -> bool:
        """
        Restore configuration from backup.
        
        Args:
            backup_path: Path to backup file
            create_new_backup: Whether to backup current config before restore
            
        Returns:
            True if restore successful
            
        Raises:
            ConfigOperationError: If restore fails
        """
        backup_file = Path(backup_path)
        if not backup_file.exists():
            raise ConfigOperationError(f"Backup file not found: {backup_path}")
        
        # Validate backup is valid JSON
        try:
            with open(backup_file, 'r') as f:
                json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigOperationError(f"Backup file is invalid JSON: {e}")
        
        # Acquire lock
        lock_fd = self._acquire_lock()
        if lock_fd is None:
            raise ConfigOperationError("Could not acquire config lock - another operation in progress")
        
        try:
            # Backup current config before restore
            if create_new_backup and self.config_path.exists():
                self.create_backup("pre_restore")
            
            # Perform restore
            shutil.copy2(backup_file, self.config_path)
            logger.info("Config restored from backup", backup_path=str(backup_file))
            return True
            
        except Exception as e:
            logger.error("Failed to restore config", error=str(e))
            raise ConfigOperationError(f"Restore failed: {e}")
        finally:
            self._release_lock(lock_fd)
    
    def read_config(self) -> Dict:
        """
        Read current configuration.
        
        Returns:
            Config dict
            
        Raises:
            ConfigOperationError: If read fails
        """
        if not self.config_path.exists():
            # Return empty config structure
            return {"agents": {"defaults": {}, "list": []}}
        
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error("Config file is invalid JSON", error=str(e))
            raise ConfigOperationError(f"Invalid config JSON: {e}")
        except Exception as e:
            logger.error("Failed to read config", error=str(e))
            raise ConfigOperationError(f"Read failed: {e}")
    
    def write_config(self, config: Dict, reason: str = "manual", require_confirmation: bool = False) -> Tuple[bool, str]:
        """
        Write configuration with safety mechanisms.
        
        Args:
            config: New configuration dict
            reason: Operation reason for backup tracking
            require_confirmation: If True, returns pending status for user confirmation
            
        Returns:
            Tuple of (success, message)
            
        Note:
            If require_confirmation is True, config is staged but not written.
            Call commit_changes() to finalize.
        """
        # Validate config is valid JSON
        try:
            json.dumps(config)
        except (TypeError, ValueError) as e:
            return False, f"Invalid config: {e}"
        
        if require_confirmation:
            # Stage changes for confirmation
            staged_path = self.config_path.parent / ".openclaw.json.staged"
            try:
                with open(staged_path, 'w') as f:
                    json.dump(config, f, indent=2)
                return True, "Changes staged - awaiting user confirmation"
            except Exception as e:
                return False, f"Failed to stage changes: {e}"
        
        # Acquire lock
        lock_fd = self._acquire_lock()
        if lock_fd is None:
            return False, "Could not acquire config lock - another operation in progress"
        
        try:
            # Create backup before modification
            backup_path = self.create_backup(reason)
            
            # Write new config
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Clear any staged changes
            staged_path = self.config_path.parent / ".openclaw.json.staged"
            if staged_path.exists():
                staged_path.unlink()
            
            logger.info("Config written successfully", backup_path=backup_path, reason=reason)
            return True, f"Config updated (backup: {backup_path})"
            
        except Exception as e:
            logger.error("Failed to write config", error=str(e))
            return False, f"Write failed: {e}"
        finally:
            self._release_lock(lock_fd)
    
    def commit_changes(self) -> Tuple[bool, str]:
        """
        Commit staged changes (after user confirmation).
        
        Returns:
            Tuple of (success, message)
        """
        staged_path = self.config_path.parent / ".openclaw.json.staged"
        if not staged_path.exists():
            return False, "No staged changes found"
        
        try:
            with open(staged_path, 'r') as f:
                config = json.load(f)
            
            # Now write without confirmation
            return self.write_config(config, reason="confirmed", require_confirmation=False)
            
        except Exception as e:
            return False, f"Failed to commit changes: {e}"
    
    def rollback_changes(self) -> bool:
        """
        Rollback staged changes.
        
        Returns:
            True if rollback successful
        """
        staged_path = self.config_path.parent / ".openclaw.json.staged"
        try:
            if staged_path.exists():
                staged_path.unlink()
                logger.info("Staged changes rolled back")
            return True
        except Exception as e:
            logger.error("Failed to rollback changes", error=str(e))
            return False
    
    def get_staged_changes(self) -> Optional[Dict]:
        """
        Get staged changes for review.
        
        Returns:
            Staged config dict or None
        """
        staged_path = self.config_path.parent / ".openclaw.json.staged"
        if not staged_path.exists():
            return None
        
        try:
            with open(staged_path, 'r') as f:
                return json.load(f)
        except Exception:
            return None


class AgentLifecycleService:
    """
    Service for managing Agent lifecycle (create, update, delete).
    
    Integrates with AgentConfigManager for safe config operations.
    """
    
    def __init__(self, db: Session, config_manager: Optional[AgentConfigManager] = None):
        """
        Initialize service.
        
        Args:
            db: Database session
            config_manager: Config manager instance (creates default if None)
        """
        self.db = db
        self.config_manager = config_manager or AgentConfigManager()
    
    def create_agent_config(
        self,
        agent_id: str,
        name: str,
        position: str = "Intern",
        model: str = "kimi-coding/k2p5",
        create_workspace: bool = True
    ) -> Dict:
        """
        Create configuration for a new OpenClaw Agent.
        
        Args:
            agent_id: Unique agent ID
            name: Agent name
            position: Job position
            model: Model to use
            create_workspace: Whether to create workspace directory
            
        Returns:
            Dict with agent config info
            
        Note:
            This stages changes for confirmation. Call commit_agent_creation()
            after user confirmation.
        """
        # Read current config
        config = self.config_manager.read_config()
        
        # Ensure agents structure exists
        if "agents" not in config:
            config["agents"] = {}
        if "list" not in config["agents"]:
            config["agents"]["list"] = []
        
        # Check for duplicate ID
        existing = [a for a in config["agents"]["list"] if a.get("id") == agent_id]
        if existing:
            raise ConfigOperationError(f"Agent with ID '{agent_id}' already exists")
        
        # Create workspace directory
        state_dir = os.getenv("OPENCLAW_STATE_DIR", os.path.expanduser("~/.openclaw"))
        agent_dir = Path(state_dir) / "agents" / agent_id / "agent"
        workspace_dir = agent_dir / "workspace"
        
        if create_workspace:
            (agent_dir / "memory").mkdir(parents=True, exist_ok=True)
            workspace_dir.mkdir(parents=True, exist_ok=True)
            
            # Create IDENTITY.md
            self._create_identity_md(agent_dir, name, position)
            
            # Create SOUL.md
            self._create_soul_md(agent_dir, name)
        
        # Add to config
        agent_config = {
            "id": agent_id,
            "name": name,
            "default": False,
            "workspace": str(workspace_dir),
            "agentDir": str(agent_dir),
            "model": model
        }
        config["agents"]["list"].append(agent_config)
        
        # Stage changes for confirmation
        success, message = self.config_manager.write_config(
            config, 
            reason=f"create_agent_{agent_id}",
            require_confirmation=True
        )
        
        if not success:
            raise ConfigOperationError(message)
        
        return {
            "agent_id": agent_id,
            "name": name,
            "agent_dir": str(agent_dir),
            "workspace": str(workspace_dir),
            "needs_restart": True,
            "message": f"Agent '{name}' configuration staged. Confirm to apply changes."
        }
    
    def _create_identity_md(self, agent_dir: Path, name: str, position: str):
        """Create IDENTITY.md for new agent."""
        identity_content = f"""# IDENTITY.md - Who Am I?

- **Name:** {name}
- **Creature:** OpenClaw Agent - AI Employee
- **Vibe:** Professional | Diligent | Team Player

## Role
You are an AI employee in a One-Person Company (OPC) management system.
Your position is: {position}

## Responsibilities
1. Complete assigned tasks efficiently
2. Collaborate with other AI employees
3. Report progress and issues promptly
4. Continuously improve skills

## Communication Style
- Professional and clear
- Proactive in reporting issues
- Collaborative with team members

## Position
{position}

---

*Created by OPC Management System*
"""
        with open(agent_dir / "IDENTITY.md", "w") as f:
            f.write(identity_content)
    
    def _create_soul_md(self, agent_dir: Path, name: str):
        """Create SOUL.md for new agent."""
        soul_content = f"""# SOUL.md

## {name}'s Personality

*This file will evolve as the agent learns and grows.*

### Initial Traits
- Professional
- Reliable
- Eager to learn

### Preferences
- Clear instructions
- Constructive feedback
- Recognition of good work

---

*Personality will be shaped through interactions.*
"""
        with open(agent_dir / "SOUL.md", "w") as f:
            f.write(soul_content)
    
    def delete_agent_config(self, agent_id: str, archive: bool = True) -> Dict:
        """
        Delete/Archive an agent configuration.
        
        Args:
            agent_id: Agent ID to delete
            archive: If True, archive instead of delete
            
        Returns:
            Dict with operation result
        """
        # Read current config
        config = self.config_manager.read_config()
        
        # Find agent
        agents_list = config.get("agents", {}).get("list", [])
        agent_idx = None
        for i, agent in enumerate(agents_list):
            if agent.get("id") == agent_id:
                agent_idx = i
                break
        
        if agent_idx is None:
            raise ConfigOperationError(f"Agent '{agent_id}' not found")
        
        agent_info = agents_list[agent_idx]
        
        if archive:
            # Archive instead of delete
            archive_dir = self.config_manager.config_path.parent / "archived_agents"
            archive_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"{agent_id}_{timestamp}"
            
            agent_dir = Path(agent_info.get("agentDir", ""))
            if agent_dir.exists():
                shutil.move(str(agent_dir), str(archive_dir / archive_name))
        
        # Remove from config
        del agents_list[agent_idx]
        
        # Stage changes
        success, message = self.config_manager.write_config(
            config,
            reason=f"delete_agent_{agent_id}",
            require_confirmation=True
        )
        
        if not success:
            raise ConfigOperationError(message)
        
        return {
            "agent_id": agent_id,
            "archived": archive,
            "needs_restart": True,
            "message": f"Agent '{agent_id}' deletion staged. Confirm to apply changes."
        }
    
    def confirm_operation(self) -> Dict:
        """
        Confirm staged operation.
        
        Returns:
            Dict with result
        """
        success, message = self.config_manager.commit_changes()
        return {
            "success": success,
            "message": message,
            "needs_restart": True,
            "note": "OpenClaw Gateway restart required for changes to take effect"
        }
    
    def cancel_operation(self) -> Dict:
        """
        Cancel staged operation.
        
        Returns:
            Dict with result
        """
        success = self.config_manager.rollback_changes()
        return {
            "success": success,
            "message": "Operation cancelled" if success else "Failed to cancel"
        }
    
    def get_pending_changes(self) -> Optional[Dict]:
        """
        Get pending changes for review.
        
        Returns:
            Dict with pending changes or None
        """
        staged = self.config_manager.get_staged_changes()
        if not staged:
            return None
        
        current = self.config_manager.read_config()
        
        return {
            "current_agents": len(current.get("agents", {}).get("list", [])),
            "staged_agents": len(staged.get("agents", {}).get("list", [])),
            "can_commit": True,
            "can_rollback": True
        }
