"""
VM synchronization operations.

This module handles VM synchronization (incremental updates) between hosts.
"""

import asyncio
import logging
import uuid
from typing import Optional, Callable
from datetime import datetime

from .models import SyncOptions, SyncResult, ProgressInfo, DeltaInfo, OperationType, OperationStatus
from .exceptions import VMNotFoundError, TransferError
from .transport import SSHTransport
from .libvirt_wrapper import LibvirtWrapper


class VMSynchronizer:
    """Handles VM synchronization operations."""
    
    def __init__(self, transport: SSHTransport, libvirt_wrapper: LibvirtWrapper):
        """Initialize VM synchronizer."""
        self.transport = transport
        self.libvirt = libvirt_wrapper
        self.logger = logging.getLogger(__name__)
    
    async def sync(
        self,
        source_host: str,
        dest_host: str,
        vm_name: str,
        sync_options: SyncOptions,
        progress_callback: Optional[Callable[[ProgressInfo], None]] = None
    ) -> SyncResult:
        """
        Synchronize a virtual machine between hosts.
        
        Args:
            source_host: Source host (hostname or IP)
            dest_host: Destination host (hostname or IP)
            vm_name: Name of VM to synchronize
            sync_options: Synchronization options
            progress_callback: Callback for progress updates
            
        Returns:
            SyncResult: Result of the sync operation
        """
        operation_id = str(uuid.uuid4())
        start_time = datetime.now()
        target_vm_name = sync_options.target_name or vm_name
        
        self.logger.info(f"Starting sync operation {operation_id}: {vm_name} from {source_host} to {dest_host}")
        
        try:
            # Validate that both VMs exist
            async with self.transport.connect(source_host) as source_conn:
                if not await self.libvirt.vm_exists(source_conn, vm_name):
                    raise VMNotFoundError(vm_name, source_host)
                
                source_vm_info = await self.libvirt.get_vm_info(source_conn, vm_name)
            
            async with self.transport.connect(dest_host) as dest_conn:
                if not await self.libvirt.vm_exists(dest_conn, target_vm_name):
                    raise VMNotFoundError(target_vm_name, dest_host)
                
                dest_vm_info = await self.libvirt.get_vm_info(dest_conn, target_vm_name)
            
            # Calculate delta if requested
            delta_info = None
            if sync_options.delta_only:
                delta_info = await self.calculate_delta(source_host, dest_host, vm_name, target_vm_name)
            
            # Create checkpoint if requested
            if sync_options.checkpoint:
                await self._create_checkpoint(dest_host, target_vm_name)
            
            # Perform synchronization
            total_bytes = 0
            transferred_bytes = 0
            blocks_synchronized = 0
            
            for i, source_disk in enumerate(source_vm_info.disks):
                if i < len(dest_vm_info.disks):
                    dest_disk = dest_vm_info.disks[i]
                    
                    if progress_callback:
                        progress_callback(ProgressInfo(
                            operation_id=operation_id,
                            operation_type=OperationType.SYNC,
                            progress_percent=(i / len(source_vm_info.disks)) * 100,
                            bytes_transferred=transferred_bytes,
                            total_bytes=total_bytes,
                            speed=0.0,
                            eta=None,
                            status=OperationStatus.RUNNING,
                            message=f"Synchronizing disk {source_disk.target}",
                            current_file=source_disk.path
                        ))
                    
                    # Sync disk
                    sync_stats = await self._sync_disk(
                        source_host, dest_host, 
                        source_disk.path, dest_disk.path,
                        sync_options, progress_callback, operation_id
                    )
                    
                    transferred_bytes += sync_stats['bytes_transferred']
                    blocks_synchronized += sync_stats['blocks_synchronized']
            
            duration = (datetime.now() - start_time).total_seconds()
            
            self.logger.info(f"Sync operation {operation_id} completed successfully")
            
            return SyncResult(
                operation_id=operation_id,
                success=True,
                vm_name=vm_name,
                source_host=source_host,
                dest_host=dest_host,
                duration=duration,
                bytes_transferred=transferred_bytes,
                blocks_synchronized=blocks_synchronized
            )
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"Sync operation {operation_id} failed: {e}")
            
            return SyncResult(
                operation_id=operation_id,
                success=False,
                vm_name=vm_name,
                source_host=source_host,
                dest_host=dest_host,
                duration=duration,
                bytes_transferred=0,
                blocks_synchronized=0,
                error=str(e)
            )
    
    async def calculate_delta(
        self,
        source_host: str,
        dest_host: str,
        source_vm_name: str,
        dest_vm_name: Optional[str] = None
    ) -> DeltaInfo:
        """
        Calculate differences between source and destination VMs.
        
        Args:
            source_host: Source host
            dest_host: Destination host
            source_vm_name: Source VM name
            dest_vm_name: Destination VM name (defaults to source_vm_name)
            
        Returns:
            DeltaInfo: Information about differences
        """
        dest_vm_name = dest_vm_name or source_vm_name
        
        try:
            # Get VM information from both hosts
            async with self.transport.connect(source_host) as source_conn:
                source_vm_info = await self.libvirt.get_vm_info(source_conn, source_vm_name)
            
            async with self.transport.connect(dest_host) as dest_conn:
                dest_vm_info = await self.libvirt.get_vm_info(dest_conn, dest_vm_name)
            
            # Calculate differences (simplified implementation)
            total_size = sum(disk.size for disk in source_vm_info.disks)
            changed_size = 0
            changed_blocks = 0
            files_changed = []
            
            # In a real implementation, this would use tools like rsync --dry-run
            # or qemu-img compare to calculate actual differences
            for i, source_disk in enumerate(source_vm_info.disks):
                if i < len(dest_vm_info.disks):
                    dest_disk = dest_vm_info.disks[i]
                    
                    # Simplified: assume some percentage has changed
                    # Real implementation would compare checksums, modification times, etc.
                    estimated_change = source_disk.size * 0.1  # Assume 10% changed
                    changed_size += int(estimated_change)
                    changed_blocks += int(estimated_change / 4096)  # Assume 4KB blocks
                    files_changed.append(source_disk.path)
            
            # Estimate transfer time based on changed size and typical network speed
            estimated_speed = 100 * 1024 * 1024  # 100 MB/s
            estimated_transfer_time = changed_size / estimated_speed if changed_size > 0 else 0
            
            return DeltaInfo(
                total_size=total_size,
                changed_size=changed_size,
                changed_blocks=changed_blocks,
                files_changed=files_changed,
                estimated_transfer_time=estimated_transfer_time
            )
            
        except Exception as e:
            self.logger.error(f"Failed to calculate delta: {e}")
            raise TransferError(str(e), source_host, dest_host)
    
    async def _create_checkpoint(self, host: str, vm_name: str) -> None:
        """Create a checkpoint/snapshot before synchronization."""
        try:
            async with self.transport.connect(host) as conn:
                # Create a snapshot using virsh
                snapshot_name = f"{vm_name}_sync_checkpoint_{int(datetime.now().timestamp())}"
                command = f"virsh snapshot-create-as {vm_name} {snapshot_name} 'Pre-sync checkpoint'"
                
                stdout, stderr, exit_code = await conn.execute_command(command)
                
                if exit_code != 0:
                    self.logger.warning(f"Failed to create checkpoint: {stderr}")
                else:
                    self.logger.info(f"Created checkpoint {snapshot_name} for {vm_name}")
                    
        except Exception as e:
            self.logger.warning(f"Checkpoint creation failed: {e}")
    
    async def _sync_disk(
        self,
        source_host: str,
        dest_host: str,
        source_path: str,
        dest_path: str,
        sync_options: SyncOptions,
        progress_callback: Optional[Callable[[ProgressInfo], None]],
        operation_id: str
    ) -> dict:
        """
        Synchronize a single disk image.
        
        Args:
            source_host: Source host
            dest_host: Destination host
            source_path: Source disk path
            dest_path: Destination disk path
            sync_options: Sync options
            progress_callback: Progress callback
            operation_id: Operation ID
            
        Returns:
            dict: Sync statistics
        """
        try:
            # Build rsync command for incremental sync
            rsync_cmd = ["rsync", "-avz", "--progress"]
            
            # Add bandwidth limit if specified
            if sync_options.bandwidth_limit:
                rsync_cmd.extend(["--bwlimit", sync_options.bandwidth_limit])
            
            # Add source and destination
            if source_host == dest_host:
                # Local sync
                rsync_cmd.extend([source_path, dest_path])
                command = " ".join(rsync_cmd)
                
                async with self.transport.connect(source_host) as conn:
                    stdout, stderr, exit_code = await conn.execute_command(command)
            else:
                # Remote sync
                rsync_cmd.extend([source_path, f"{dest_host}:{dest_path}"])
                command = " ".join(rsync_cmd)
                
                async with self.transport.connect(source_host) as conn:
                    stdout, stderr, exit_code = await conn.execute_command(command)
            
            if exit_code != 0:
                raise TransferError(f"Rsync failed: {stderr}", source_host, dest_host)
            
            # Parse rsync output for statistics (simplified)
            bytes_transferred = 0
            blocks_synchronized = 0
            
            # In a real implementation, parse rsync output to get actual statistics
            # For now, return placeholder values
            return {
                'bytes_transferred': bytes_transferred,
                'blocks_synchronized': blocks_synchronized
            }
            
        except Exception as e:
            raise TransferError(str(e), source_host, dest_host)