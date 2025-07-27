"""
Main client class for KVM cloning operations.

This module implements the primary interface for KVM virtual machine cloning
and synchronization operations over SSH connections.
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List, Callable, Union
from pathlib import Path

from .models import (
    CloneOptions, SyncOptions, CloneResult, SyncResult, 
    OperationStatus, VMInfo, ProgressInfo
)
from .exceptions import ConfigurationError, ConnectionError
from .cloner import VMCloner
from .sync import VMSynchronizer
from .transport import SSHTransport
from .libvirt_wrapper import LibvirtWrapper


class KVMCloneClient:
    """
    Main client for KVM cloning operations.
    
    Args:
        config (Optional[Dict[str, Any]]): Configuration dictionary
        ssh_key_path (Optional[str]): Path to SSH private key
        timeout (int): Default operation timeout in seconds
        
    Attributes:
        config (Dict[str, Any]): Current configuration
        timeout (int): Operation timeout
        
    Raises:
        ConfigurationError: If configuration is invalid
        ConnectionError: If unable to establish connections
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        ssh_key_path: Optional[str] = None,
        timeout: int = 3600
    ) -> None:
        """Initialize the KVM clone client."""
        self.config = config or self._load_default_config()
        self.timeout = timeout
        self.ssh_key_path = ssh_key_path or self.config.get('ssh_key_path', '~/.ssh/id_rsa')
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.transport = SSHTransport(
            key_path=self.ssh_key_path,
            timeout=timeout
        )
        self.libvirt = LibvirtWrapper()
        self.cloner = VMCloner(self.transport, self.libvirt)
        self.synchronizer = VMSynchronizer(self.transport, self.libvirt)
        
        # Operation tracking
        self._operations: Dict[str, OperationStatus] = {}
        
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration."""
        return {
            'ssh_key_path': '~/.ssh/id_rsa',
            'ssh_port': 22,
            'parallel_transfers': 4,
            'verify_transfers': True,
            'compress_transfers': False,
            'timeout': 3600
        }
    
    async def clone_vm(
        self,
        source_host: str,
        dest_host: str,
        vm_name: str,
        *,
        new_name: Optional[str] = None,
        force: bool = False,
        dry_run: bool = False,
        parallel: int = 4,
        compress: bool = False,
        verify: bool = True,
        preserve_mac: bool = False,
        network_config: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[ProgressInfo], None]] = None
    ) -> CloneResult:
        """
        Clone a virtual machine from source to destination host.
        
        Args:
            source_host: Source host (hostname or IP)
            dest_host: Destination host (hostname or IP)
            vm_name: Name of VM to clone
            new_name: Name for cloned VM (default: {vm_name}_clone)
            force: Overwrite existing VM
            dry_run: Show what would be done without executing
            parallel: Number of parallel transfers
            compress: Enable compression during transfer
            verify: Verify integrity after transfer
            preserve_mac: Preserve MAC addresses
            network_config: Custom network configuration
            progress_callback: Callback for progress updates
            
        Returns:
            CloneResult: Result of the clone operation
        """
        clone_options = CloneOptions(
            new_name=new_name,
            force=force,
            dry_run=dry_run,
            parallel=parallel,
            compress=compress,
            verify=verify,
            preserve_mac=preserve_mac,
            network_config=network_config
        )
        
        return await self.cloner.clone(
            source_host=source_host,
            dest_host=dest_host,
            vm_name=vm_name,
            clone_options=clone_options,
            progress_callback=progress_callback
        )
    
    async def sync_vm(
        self,
        source_host: str,
        dest_host: str,
        vm_name: str,
        *,
        target_name: Optional[str] = None,
        checkpoint: bool = False,
        delta_only: bool = True,
        bandwidth_limit: Optional[str] = None,
        progress_callback: Optional[Callable[[ProgressInfo], None]] = None
    ) -> SyncResult:
        """
        Synchronize an existing VM between hosts (incremental transfer).
        
        Args:
            source_host: Source host (hostname or IP)
            dest_host: Destination host (hostname or IP)
            vm_name: Name of VM to synchronize
            target_name: Target VM name on destination
            checkpoint: Create checkpoint before sync
            delta_only: Transfer only changed blocks
            bandwidth_limit: Bandwidth limit (e.g., '100M', '1G')
            progress_callback: Callback for progress updates
            
        Returns:
            SyncResult: Result of the sync operation
        """
        sync_options = SyncOptions(
            target_name=target_name,
            checkpoint=checkpoint,
            delta_only=delta_only,
            bandwidth_limit=bandwidth_limit
        )
        
        return await self.synchronizer.sync(
            source_host=source_host,
            dest_host=dest_host,
            vm_name=vm_name,
            sync_options=sync_options,
            progress_callback=progress_callback
        )
    
    async def list_vms(
        self,
        hosts: List[str],
        *,
        status_filter: Optional[str] = None
    ) -> Dict[str, List[VMInfo]]:
        """
        List virtual machines on specified hosts.
        
        Args:
            hosts: List of hosts to query
            status_filter: Filter by status ('all', 'running', 'stopped', 'paused')
            
        Returns:
            Dict mapping host names to lists of VM information
        """
        results = {}
        
        for host in hosts:
            try:
                async with self.transport.connect(host) as conn:
                    vms = await self.libvirt.list_vms(conn, status_filter)
                    results[host] = vms
            except Exception as e:
                self.logger.error(f"Failed to list VMs on {host}: {e}")
                results[host] = []
                
        return results
    
    def get_operation_status(
        self,
        operation_id: str
    ) -> Optional[OperationStatus]:
        """
        Get status of a specific operation.
        
        Args:
            operation_id: Specific operation ID to check
            
        Returns:
            OperationStatus or None if not found
        """
        return self._operations.get(operation_id)
    
    def cancel_operation(
        self,
        operation_id: str
    ) -> bool:
        """
        Cancel a running operation.
        
        Args:
            operation_id: Operation ID to cancel
            
        Returns:
            True if operation was cancelled, False otherwise
        """
        operation = self._operations.get(operation_id)
        if operation and operation.status == 'running':
            operation.status = 'cancelled'
            return True
        return False
    
    def cleanup_failed_operations(self) -> List[str]:
        """
        Clean up failed operations and return their IDs.
        
        Returns:
            List of cleaned up operation IDs
        """
        failed_ops = [
            op_id for op_id, op in self._operations.items()
            if op.status == 'failed'
        ]
        
        for op_id in failed_ops:
            del self._operations[op_id]
            
        return failed_ops
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.transport.close_all()