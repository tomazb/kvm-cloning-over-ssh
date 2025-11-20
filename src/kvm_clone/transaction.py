"""
Transaction management for atomic clone operations.

This module provides a transactional framework to ensure clone operations
are atomic - either fully succeed or fully rollback with no partial state.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Callable, Awaitable

from .logging import logger
from .transport import SSHConnection


class ResourceType(Enum):
    """Types of resources that can be created during cloning."""

    DISK_FILE = "disk_file"
    TEMP_DISK_FILE = "temp_disk_file"
    VM_DEFINITION = "vm_definition"
    NETWORK_INTERFACE = "network_interface"
    DIRECTORY = "directory"


@dataclass
class TransactionResource:
    """A resource created during a transaction."""

    resource_type: ResourceType
    resource_id: str  # Path, VM name, etc.
    host: str  # Which host the resource is on
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    cleanup_func: Optional[Callable[[SSHConnection], Awaitable[None]]] = field(
        default=None, repr=False, compare=False
    )


@dataclass
class TransactionLog:
    """Log of a transaction for debugging and recovery."""

    transaction_id: str
    operation_type: str
    started_at: str
    completed_at: Optional[str] = None
    status: str = "pending"  # pending, committed, rolled_back, failed
    resources: List[TransactionResource] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        # Remove cleanup_func as it can't be serialized and normalize enums
        for resource in result.get("resources", []):
            resource.pop("cleanup_func", None)
            # Convert ResourceType enum to string value
            rt = resource.get("resource_type")
            if isinstance(rt, Enum):
                resource["resource_type"] = rt.value
        return result

    def save_to_file(self, path: str) -> None:
        """Save transaction log to file."""
        try:
            with open(path, "w") as f:
                json.dump(self.to_dict(), f, indent=2)
            logger.debug(f"Transaction log saved to {path}")
        except Exception as e:
            logger.warning(f"Failed to save transaction log: {e}")


class CloneTransaction:
    """
    Manages a transactional clone operation.

    Tracks all resources created during cloning and provides rollback
    capability if the operation fails.

    Usage:
        async with CloneTransaction(operation_id, transport) as txn:
            # Create resources and register them
            txn.register_disk("/var/lib/libvirt/images/disk1.qcow2", dest_host)
            txn.register_vm("vm_name", dest_host)

            # If any exception occurs, automatic rollback happens
            # If successful, resources are committed
    """

    def __init__(
        self,
        operation_id: str,
        transport: Any,  # SSHTransport
        staging_dir: Optional[str] = None,
    ):
        """
        Initialize transaction.

        Args:
            operation_id: Unique operation identifier
            transport: SSH transport for executing cleanup commands
            staging_dir: Optional staging directory for temporary files
        """
        self.operation_id = operation_id
        self.transport = transport
        self.resources: List[TransactionResource] = []
        self.committed = False
        self.rolled_back = False

        # Staging directory for temporary files
        self.staging_dir = staging_dir or f"/tmp/kvm-clone-{operation_id}"

        # Transaction log
        self.log = TransactionLog(
            transaction_id=operation_id,
            operation_type="clone",
            started_at=datetime.now().isoformat(),
        )

        logger.info(
            f"Transaction {operation_id} started",
            transaction_id=operation_id,
            staging_dir=self.staging_dir,
        )

    async def __aenter__(self) -> CloneTransaction:
        """Enter transaction context."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit transaction context with automatic rollback on failure."""
        if exc_type is not None:
            # Exception occurred, rollback
            self.log.status = "failed"
            self.log.error = str(exc_val)
            logger.error(
                f"Transaction {self.operation_id} failed, rolling back",
                transaction_id=self.operation_id,
                error=str(exc_val),
            )
            await self.rollback()
        elif not self.committed:
            # No exception but not committed - should not happen
            logger.warning(
                f"Transaction {self.operation_id} exited without commit or error",
                transaction_id=self.operation_id,
            )
            await self.rollback()

        # Save transaction log
        self.log.completed_at = datetime.now().isoformat()
        log_path = f"/tmp/kvm-clone-txn-{self.operation_id}.json"
        self.log.save_to_file(log_path)

    def register_resource(
        self,
        resource_type: ResourceType,
        resource_id: str,
        host: str,
        metadata: Optional[Dict[str, Any]] = None,
        cleanup_func: Optional[Callable[[SSHConnection], Awaitable[None]]] = None,
    ) -> None:
        """
        Register a resource created during the transaction.

        Args:
            resource_type: Type of resource
            resource_id: Unique identifier (path, name, etc.)
            host: Host where resource exists
            metadata: Optional metadata
            cleanup_func: Optional custom cleanup function
        """
        resource = TransactionResource(
            resource_type=resource_type,
            resource_id=resource_id,
            host=host,
            metadata=metadata or {},
            cleanup_func=cleanup_func,
        )
        self.resources.append(resource)
        self.log.resources.append(resource)

        logger.debug(
            f"Registered resource: {resource_type.value} - {resource_id} on {host}",
            transaction_id=self.operation_id,
            resource_type=resource_type.value,
            resource_id=resource_id,
        )

    def register_disk(
        self,
        path: str,
        host: str,
        is_temporary: bool = False,
        final_path: Optional[str] = None,
    ) -> None:
        """Register a disk file."""
        resource_type = (
            ResourceType.TEMP_DISK_FILE if is_temporary else ResourceType.DISK_FILE
        )
        metadata = {"final_path": final_path} if final_path else {}
        self.register_resource(resource_type, path, host, metadata)

    def register_vm(self, vm_name: str, host: str) -> None:
        """Register a VM definition."""
        self.register_resource(ResourceType.VM_DEFINITION, vm_name, host)

    def register_directory(self, path: str, host: str) -> None:
        """Register a directory."""
        self.register_resource(ResourceType.DIRECTORY, path, host)

    async def commit(self) -> None:
        """
        Commit the transaction.

        Moves temporary files to final locations and marks transaction as committed.
        """
        if self.committed:
            logger.warning(
                f"Transaction {self.operation_id} already committed",
                transaction_id=self.operation_id,
            )
            return

        logger.info(
            f"Committing transaction {self.operation_id}",
            transaction_id=self.operation_id,
        )

        try:
            # Move temporary files to final locations
            for resource in self.resources:
                if resource.resource_type == ResourceType.TEMP_DISK_FILE:
                    final_path = resource.metadata.get("final_path")
                    if final_path:
                        await self._move_file(
                            resource.resource_id, final_path, resource.host
                        )
                        logger.debug(
                            f"Moved {resource.resource_id} to {final_path}",
                            transaction_id=self.operation_id,
                        )

            self.committed = True
            self.log.status = "committed"
            logger.info(
                f"Transaction {self.operation_id} committed successfully",
                transaction_id=self.operation_id,
            )

        except Exception as e:
            logger.error(
                f"Failed to commit transaction {self.operation_id}: {e}",
                transaction_id=self.operation_id,
                exc_info=True,
            )
            # Try to rollback if commit fails
            await self.rollback()
            raise

    async def rollback(self) -> None:
        """
        Rollback the transaction.

        Deletes all created resources in reverse order.
        """
        if self.rolled_back:
            logger.warning(
                f"Transaction {self.operation_id} already rolled back",
                transaction_id=self.operation_id,
            )
            return

        logger.info(
            f"Rolling back transaction {self.operation_id}",
            transaction_id=self.operation_id,
            resource_count=len(self.resources),
        )

        # Rollback in reverse order
        for resource in reversed(self.resources):
            try:
                await self._cleanup_resource(resource)
                logger.debug(
                    f"Cleaned up resource: {resource.resource_type.value} - {resource.resource_id}",
                    transaction_id=self.operation_id,
                )
            except Exception as e:
                # Log but continue cleanup
                logger.warning(
                    f"Failed to cleanup resource {resource.resource_id}: {e}",
                    transaction_id=self.operation_id,
                    resource_id=resource.resource_id,
                )

        # Clean up staging directory
        try:
            await self._cleanup_staging_dir()
        except Exception as e:
            logger.warning(f"Failed to cleanup staging directory: {e}")

        self.rolled_back = True
        self.log.status = "rolled_back"
        logger.info(
            f"Transaction {self.operation_id} rolled back",
            transaction_id=self.operation_id,
        )

    async def _cleanup_resource(self, resource: TransactionResource) -> None:
        """Clean up a single resource."""
        # Use custom cleanup function if provided
        if resource.cleanup_func:
            async with self.transport.connect(resource.host) as conn:
                await resource.cleanup_func(conn)
            return

        # Default cleanup based on resource type
        async with self.transport.connect(resource.host) as conn:
            if resource.resource_type in (
                ResourceType.DISK_FILE,
                ResourceType.TEMP_DISK_FILE,
            ):
                # Delete disk file
                await self._delete_file(resource.resource_id, resource.host)

            elif resource.resource_type == ResourceType.VM_DEFINITION:
                # Undefine VM
                await self._undefine_vm(resource.resource_id, resource.host)

            elif resource.resource_type == ResourceType.DIRECTORY:
                # Remove directory
                await self._delete_directory(resource.resource_id, resource.host)

    async def _delete_file(self, path: str, host: str) -> None:
        """Delete a file on remote host."""
        from .security import CommandBuilder

        async with self.transport.connect(host) as conn:
            cmd = CommandBuilder.rm_file(path)
            await conn.execute_command(cmd)
            logger.debug(f"Deleted file {path} on {host}")

    async def _delete_directory(self, path: str, host: str) -> None:
        """Delete a directory on remote host."""
        from .security import CommandBuilder

        async with self.transport.connect(host) as conn:
            cmd = CommandBuilder.rm_directory(path)
            await conn.execute_command(cmd)
            logger.debug(f"Deleted directory {path} on {host}")

    async def _undefine_vm(self, vm_name: str, host: str) -> None:
        """Undefine a VM on remote host."""
        from .security import CommandBuilder

        async with self.transport.connect(host) as conn:
            # Try to stop VM first if running
            try:
                cmd = CommandBuilder.virsh_destroy(vm_name)
                await conn.execute_command(cmd)
            except Exception:
                pass  # VM might not be running

            # Undefine VM (without removing storage, we handle that separately)
            cmd = CommandBuilder.virsh_undefine(vm_name)
            await conn.execute_command(cmd)
            logger.debug(f"Undefined VM {vm_name} on {host}")

    async def _move_file(self, src: str, dst: str, host: str) -> None:
        """Move a file on remote host."""
        from .security import CommandBuilder

        async with self.transport.connect(host) as conn:
            cmd = CommandBuilder.move_file(src, dst)
            await conn.execute_command(cmd)

    async def _cleanup_staging_dir(self) -> None:
        """Clean up staging directory."""
        # Staging dir contains resources we already tracked, so just remove it
        # We only do this if rollback is complete
        pass  # Resources are already cleaned up individually

    def get_staging_path(self, filename: str) -> str:
        """Get a path in the staging directory."""
        return os.path.join(self.staging_dir, filename)
