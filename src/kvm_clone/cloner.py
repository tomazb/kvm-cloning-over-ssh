"""
VM cloning operations.

This module handles the actual VM cloning process including disk image transfer
and VM definition creation.
"""

import asyncio
import logging
import uuid
from typing import Optional, Callable
from datetime import datetime
from pathlib import Path

from .models import CloneOptions, CloneResult, ProgressInfo, ValidationResult, OperationType, OperationStatus
from .exceptions import VMNotFoundError, VMExistsError, TransferError, ValidationError
from .transport import SSHTransport
from .libvirt_wrapper import LibvirtWrapper


class VMCloner:
    """Handles VM cloning operations."""
    
    def __init__(self, transport: SSHTransport, libvirt_wrapper: LibvirtWrapper):
        """Initialize VM cloner."""
        self.transport = transport
        self.libvirt = libvirt_wrapper
        self.logger = logging.getLogger(__name__)
    
    async def clone(
        self,
        source_host: str,
        dest_host: str,
        vm_name: str,
        clone_options: CloneOptions,
        progress_callback: Optional[Callable[[ProgressInfo], None]] = None
    ) -> CloneResult:
        """
        Clone a virtual machine from source to destination host.
        
        Args:
            source_host: Source host (hostname or IP)
            dest_host: Destination host (hostname or IP)
            vm_name: Name of VM to clone
            clone_options: Cloning options
            progress_callback: Callback for progress updates
            
        Returns:
            CloneResult: Result of the clone operation
        """
        operation_id = str(uuid.uuid4())
        start_time = datetime.now()
        new_vm_name = clone_options.new_name or f"{vm_name}_clone"
        
        self.logger.info(f"Starting clone operation {operation_id}: {vm_name} from {source_host} to {dest_host}")
        
        try:
            # Validate prerequisites
            validation = await self.validate_prerequisites(source_host, dest_host, vm_name, clone_options)
            if not validation.valid:
                return CloneResult(
                    operation_id=operation_id,
                    success=False,
                    vm_name=vm_name,
                    new_vm_name=new_vm_name,
                    source_host=source_host,
                    dest_host=dest_host,
                    duration=0.0,
                    bytes_transferred=0,
                    error=f"Validation failed: {'; '.join(validation.errors)}",
                    validation=validation
                )
            
            if clone_options.dry_run:
                self.logger.info(f"Dry run completed for {operation_id}")
                return CloneResult(
                    operation_id=operation_id,
                    success=True,
                    vm_name=vm_name,
                    new_vm_name=new_vm_name,
                    source_host=source_host,
                    dest_host=dest_host,
                    duration=0.0,
                    bytes_transferred=0,
                    validation=validation
                )
            
            # Get VM information from source
            async with self.transport.connect(source_host) as source_conn:
                vm_info = await self.libvirt.get_vm_info(source_conn, vm_name)
                
                # Clone VM definition
                new_xml = await self.libvirt.clone_vm_definition(
                    source_conn, vm_name, new_vm_name, clone_options.preserve_mac
                )
                
                # Transfer disk images
                total_bytes = 0
                transferred_bytes = 0
                
                for disk in vm_info.disks:
                    if progress_callback:
                        progress_callback(ProgressInfo(
                            operation_id=operation_id,
                            operation_type=OperationType.CLONE,
                            progress_percent=0.0,
                            bytes_transferred=transferred_bytes,
                            total_bytes=total_bytes,
                            speed=0.0,
                            eta=None,
                            status=OperationStatus.RUNNING,
                            message=f"Transferring disk {disk.target}",
                            current_file=disk.path
                        ))
                    
                    # Transfer disk image
                    dest_path = await self._transfer_disk_image(
                        source_host, dest_host, disk.path, new_vm_name, 
                        progress_callback, operation_id
                    )
                    
                    # Update XML with new disk path
                    new_xml = new_xml.replace(disk.path, dest_path)
                    transferred_bytes += disk.size
                
                # Create VM on destination
                async with self.transport.connect(dest_host) as dest_conn:
                    await self.libvirt.create_vm_from_xml(dest_conn, new_xml)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            self.logger.info(f"Clone operation {operation_id} completed successfully")
            
            return CloneResult(
                operation_id=operation_id,
                success=True,
                vm_name=vm_name,
                new_vm_name=new_vm_name,
                source_host=source_host,
                dest_host=dest_host,
                duration=duration,
                bytes_transferred=transferred_bytes,
                validation=validation,
                warnings=validation.warnings
            )
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"Clone operation {operation_id} failed: {e}")
            
            return CloneResult(
                operation_id=operation_id,
                success=False,
                vm_name=vm_name,
                new_vm_name=new_vm_name,
                source_host=source_host,
                dest_host=dest_host,
                duration=duration,
                bytes_transferred=0,
                error=str(e)
            )
    
    async def validate_prerequisites(
        self,
        source_host: str,
        dest_host: str,
        vm_name: str,
        clone_options: CloneOptions
    ) -> ValidationResult:
        """
        Validate prerequisites for cloning operation.
        
        Args:
            source_host: Source host
            dest_host: Destination host
            vm_name: VM name to clone
            clone_options: Clone options
            
        Returns:
            ValidationResult: Validation results
        """
        errors = []
        warnings = []
        
        try:
            # Check source VM exists
            async with self.transport.connect(source_host) as source_conn:
                if not await self.libvirt.vm_exists(source_conn, vm_name):
                    errors.append(f"VM '{vm_name}' not found on source host {source_host}")
                else:
                    # Get VM info for further validation
                    vm_info = await self.libvirt.get_vm_info(source_conn, vm_name)
                    
                    # Check if VM is running
                    if vm_info.state.value == "running":
                        warnings.append(f"VM '{vm_name}' is currently running. Consider stopping it before cloning.")
            
            # Check destination
            new_vm_name = clone_options.new_name or f"{vm_name}_clone"
            async with self.transport.connect(dest_host) as dest_conn:
                if await self.libvirt.vm_exists(dest_conn, new_vm_name):
                    if not clone_options.force:
                        errors.append(f"VM '{new_vm_name}' already exists on destination host {dest_host}")
                    else:
                        warnings.append(f"VM '{new_vm_name}' will be overwritten on destination host")
                
                # Check destination resources
                try:
                    resources = await self.libvirt.get_host_resources(dest_conn)
                    # Add resource validation logic here
                except Exception as e:
                    warnings.append(f"Could not check destination resources: {e}")
            
        except Exception as e:
            errors.append(f"Validation error: {e}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    async def _transfer_disk_image(
        self,
        source_host: str,
        dest_host: str,
        source_path: str,
        new_vm_name: str,
        progress_callback: Optional[Callable[[ProgressInfo], None]],
        operation_id: str
    ) -> str:
        """
        Transfer a disk image from source to destination.
        
        Args:
            source_host: Source host
            dest_host: Destination host
            source_path: Source disk image path
            new_vm_name: New VM name for destination path
            progress_callback: Progress callback
            operation_id: Operation ID for progress tracking
            
        Returns:
            str: Destination path of transferred disk
        """
        try:
            # Generate destination path
            source_file = Path(source_path)
            dest_path = f"/var/lib/libvirt/images/{new_vm_name}_{source_file.name}"
            
            # For now, use a simple rsync-based transfer
            # In a production implementation, this would use more sophisticated methods
            async with self.transport.connect(source_host) as source_conn:
                # Create a compressed copy command
                if dest_host == source_host:
                    # Local copy
                    command = f"cp {source_path} {dest_path}"
                else:
                    # Remote copy via rsync
                    command = f"rsync -avz --progress {source_path} {dest_host}:{dest_path}"
                
                stdout, stderr, exit_code = await source_conn.execute_command(command)
                
                if exit_code != 0:
                    raise TransferError(f"Transfer failed: {stderr}", source_host, dest_host)
            
            return dest_path
            
        except Exception as e:
            raise TransferError(str(e), source_host, dest_host)