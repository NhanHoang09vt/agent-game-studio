"""
Security, Permission & Audit Management for AI Game Development Studio.
Enforces Role-Based Access Control (RBAC), prevents unauthorized file writes/deletions,
safeguards secrets (.env), provides file-locking for parallel agent runs,
and maintains audit trails with checkpoint/rollback.
"""

import asyncio
import os
import json
import time
import shutil
from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field


class PermissionType:
    READ_PROJECT = "read_project"
    WRITE_PROJECT = "write_project"
    EDIT_SOURCE_CODE = "edit_source_code"
    RUN_TESTS = "run_tests"
    EXECUTE_BUILD = "execute_build"
    MANAGE_ASSETS = "manage_assets"
    MANAGE_DATABASE = "manage_database"
    ACCESS_EXTERNAL_API = "access_external_api"
    APPROVE_CHANGES = "approve_changes"
    RELEASE_PROJECT = "release_project"


class SecurityAuditLog(BaseModel):
    timestamp: float = Field(default_factory=time.time)
    agent_id: str
    action: str
    target_path: Optional[str] = None
    allowed: bool = True
    reason: Optional[str] = None


class FileLockManager:
    """Async mutex lock to prevent concurrent agents from colliding on the same files"""

    def __init__(self):
        self._locks: Dict[str, asyncio.Lock] = {}
        self._master_lock = asyncio.Lock()

    async def acquire_lock(self, file_path: str) -> None:
        normalized = os.path.abspath(file_path).lower()
        async with self._master_lock:
            if normalized not in self._locks:
                self._locks[normalized] = asyncio.Lock()
            lock = self._locks[normalized]
        await lock.acquire()

    async def release_lock(self, file_path: str) -> None:
        normalized = os.path.abspath(file_path).lower()
        async with self._master_lock:
            lock = self._locks.get(normalized)
        if lock and lock.locked():
            lock.release()


class PermissionManager:
    """RBAC and boundary enforcement for agents"""

    DENIED_SECRET_PATTERNS = [".env", "id_rsa", "credentials", "secrets.yaml", "token"]
    PROTECTED_BINARY_EXTENSIONS = [".uasset", ".umap", ".unity", ".prefab"]

    def __init__(self, require_approval_for_writes: bool = True):
        self.require_approval_for_writes = require_approval_for_writes
        self._agent_permissions: Dict[str, Set[str]] = {}
        self._audit_logs: List[SecurityAuditLog] = []

    def set_agent_permissions(self, agent_id: str, permissions: List[str]) -> None:
        self._agent_permissions[agent_id] = set(permissions)

    def can_read_file(self, agent_id: str, file_path: str) -> tuple[bool, str]:
        normalized = file_path.lower()
        for secret in self.DENIED_SECRET_PATTERNS:
            if secret in normalized:
                self._log_audit(agent_id, "read_secret", file_path, False, "Access to secret files is strictly denied.")
                return False, f"Access denied: {file_path} contains sensitive secrets."
        self._log_audit(agent_id, "read", file_path, True)
        return True, "Allowed"

    def can_write_file(self, agent_id: str, file_path: str, is_new_file: bool = False) -> tuple[bool, str]:
        normalized = file_path.lower()
        # Guard secrets
        for secret in self.DENIED_SECRET_PATTERNS:
            if secret in normalized:
                self._log_audit(agent_id, "write_secret", file_path, False, "Writing secrets is forbidden.")
                return False, f"Access denied: cannot write to secret file {file_path}."

        # Guard protected binaries
        for ext in self.PROTECTED_BINARY_EXTENSIONS:
            if normalized.endswith(ext):
                self._log_audit(agent_id, "write_binary", file_path, False, "Binary engine assets cannot be edited directly.")
                return False, f"Access denied: binary asset {file_path} must be edited through engine tools."

        # Check agent RBAC
        perms = self._agent_permissions.get(agent_id, set())
        if "write_project" not in perms and "edit_source_code" not in perms:
            self._log_audit(agent_id, "write_unauthorized", file_path, False, "Missing write_project permission.")
            return False, f"Agent '{agent_id}' lacks write permission."

        self._log_audit(agent_id, "write", file_path, True)
        return True, "Allowed"

    def _log_audit(self, agent_id: str, action: str, target: Optional[str], allowed: bool, reason: Optional[str] = None):
        self._audit_logs.append(
            SecurityAuditLog(
                agent_id=agent_id,
                action=action,
                target_path=target,
                allowed=allowed,
                reason=reason,
            )
        )

    def get_audit_trail(self, limit: int = 100) -> List[SecurityAuditLog]:
        return self._audit_logs[-limit:]


class RollbackCheckpointManager:
    """Creates file snapshots before multi-agent operations and enables one-click rollback"""

    def __init__(self, checkpoints_dir: str = "./data/checkpoints"):
        self.checkpoints_dir = checkpoints_dir
        os.makedirs(self.checkpoints_dir, exist_ok=True)

    def create_checkpoint(self, checkpoint_id: str, target_dir: str) -> str:
        dest = os.path.join(self.checkpoints_dir, checkpoint_id)
        if os.path.exists(dest):
            shutil.rmtree(dest)
        if os.path.exists(target_dir):
            shutil.copytree(target_dir, dest, ignore=shutil.ignore_patterns(".git", "__pycache__", "node_modules"))
        return dest

    def rollback_to_checkpoint(self, checkpoint_id: str, target_dir: str) -> bool:
        src = os.path.join(self.checkpoints_dir, checkpoint_id)
        if not os.path.exists(src):
            return False
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        shutil.copytree(src, target_dir)
        return True
