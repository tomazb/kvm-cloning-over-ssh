"""
VM cloning operations.

This module handles the actual VM cloning process including disk image transfer
and VM definition creation.
"""

import uuid
from typing import Optional, Callable
from datetime import datetime
from pathlib import Path

from .logging import logger
from .models import (
    CloneOptions,
    CloneResult,
    ProgressInfo,
    ValidationResult,
    OperationType,
    OperationStatusEnum,
)
from .exceptions import VMNotFoundError, TransferError, ValidationError, LibvirtError
from .transport import SSHTransport
from .libvirt_wrapper import LibvirtWrapper
from .security import SecurityValidator, CommandBuilder
from .transaction import CloneTransaction


class VMCloner:
    """Handles VM cloning operations."""

    def __init__(self, transport: SSHTransport, libvirt_wrapper: LibvirtWrapper):
        """Initialize VM cloner."""
        self.transport = transport
        self.libvirt = libvirt_wrapper

    async def clone(
        self,
        source_host: str,
        dest_host: str,
        vm_name: str,
        clone_options: CloneOptions,
        progress_callback: Optional[Callable[[ProgressInfo], None]] = None,
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

        logger.info(
            f"Starting clone operation {operation_id}: {vm_name} from {source_host} to {dest_host}",
            operation_id=operation_id,
            vm_name=vm_name,
            source_host=source_host,
            dest_host=dest_host,
        )

        try:
            # Validate prerequisites
            validation = await self.validate_prerequisites(
                source_host, dest_host, vm_name, clone_options
            )
            if not validation.valid:
                error_msg = f"Validation failed: {'; '.join(validation.errors)}"
                logger.error(
                    error_msg,
                    operation_id=operation_id,
                    validation_errors=validation.errors,
                )
                return CloneResult(
                    operation_id=operation_id,
                    success=False,
                    vm_name=vm_name,
                    new_vm_name=new_vm_name,
                    source_host=source_host,
                    dest_host=dest_host,
                    duration=0.0,
                    bytes_transferred=0,
                    error=error_msg,
                    validation=validation,
                )

            if clone_options.dry_run:
                logger.info(
                    f"Dry run completed for {operation_id}", operation_id=operation_id
                )
                return CloneResult(
                    operation_id=operation_id,
                    success=True,
                    vm_name=vm_name,
                    new_vm_name=new_vm_name,
                    source_host=source_host,
                    dest_host=dest_host,
                    duration=0.0,
                    bytes_transferred=0,
                    validation=validation,
                )

            # Handle idempotent mode - cleanup existing VM before cloning
            if clone_options.idempotent or clone_options.force:
                async with self.transport.connect(dest_host) as dest_conn:
                    if await self.libvirt.vm_exists(dest_conn, new_vm_name):
                        if clone_options.idempotent:
                            logger.info(
                                f"Idempotent mode: Cleaning up existing VM '{new_vm_name}' on {dest_host}",
                                operation_id=operation_id,
                                vm_name=new_vm_name,
                                dest_host=dest_host,
                            )
                        else:
                            logger.info(
                                f"Force mode: Cleaning up existing VM '{new_vm_name}' on {dest_host}",
                                operation_id=operation_id,
                                vm_name=new_vm_name,
                                dest_host=dest_host,
                            )

                        try:
                            await self.libvirt.cleanup_vm(dest_conn, new_vm_name)
                            logger.info(
                                f"Successfully cleaned up existing VM '{new_vm_name}'",
                                operation_id=operation_id,
                            )
                        except Exception as e:
                            logger.error(
                                f"Failed to cleanup existing VM '{new_vm_name}': {e}",
                                operation_id=operation_id,
                                exc_info=True,
                            )
                            raise

            # Use transaction for atomic operations
            async with CloneTransaction(operation_id, self.transport) as txn:
                # Get VM information from source
                async with self.transport.connect(source_host) as source_conn:
                    try:
                        vm_info = await self.libvirt.get_vm_info(source_conn, vm_name)
                    except LibvirtError as e:
                        raise VMNotFoundError(vm_name, source_host) from e

                    # Clone VM definition
                    new_xml = await self.libvirt.clone_vm_definition(
                        source_conn, vm_name, new_vm_name, clone_options.preserve_mac
                    )

                    # Transfer disk images and collect path mappings
                    total_bytes = 0
                    transferred_bytes = 0
                    disk_path_mappings = {}  # old_path -> new_path mapping

                    # Create staging directory on destination
                    async with self.transport.connect(dest_host) as dest_conn:
                        staging_dir = txn.staging_dir
                        mkdir_cmd = CommandBuilder.mkdir(staging_dir)
                        await dest_conn.execute_command(mkdir_cmd)
                        txn.register_directory(staging_dir, dest_host)

                    for disk in vm_info.disks:
                        if progress_callback:
                            progress_callback(
                                ProgressInfo(
                                    operation_id=operation_id,
                                    operation_type=OperationType.CLONE,
                                    progress_percent=0.0,
                                    bytes_transferred=transferred_bytes,
                                    total_bytes=total_bytes,
                                    speed=0.0,
                                    eta=None,
                                    status=OperationStatusEnum.RUNNING,
                                    message=f"Transferring disk {disk.target}",
                                    current_file=disk.path,
                                )
                            )

                        # Transfer to staging directory
                        import os

                        disk_filename = os.path.basename(disk.path)
                        staging_path = txn.get_staging_path(disk_filename)

                        # Transfer disk image to staging
                        await self._transfer_disk_image_to_path(
                            source_host,
                            dest_host,
                            disk.path,
                            staging_path,
                            progress_callback,
                            operation_id,
                        )

                        # Final destination path
                        dest_path = f"/var/lib/libvirt/images/{new_vm_name}_{disk_filename}"

                        # Register as temporary disk (will be moved on commit)
                        txn.register_disk(
                            staging_path, dest_host, is_temporary=True, final_path=dest_path
                        )

                        # Store mapping for XML update
                        disk_path_mappings[disk.path] = dest_path
                        transferred_bytes += disk.size

                    # Update XML with new disk paths using ElementTree
                    import xml.etree.ElementTree as ET

                    root = ET.fromstring(new_xml)
                    for disk_elem in root.findall(".//disk[@type='file']"):
                        source_elem = disk_elem.find("source")
                        if source_elem is not None:
                            old_path = source_elem.get("file", "")
                            if old_path in disk_path_mappings:
                                source_elem.set("file", disk_path_mappings[old_path])

                    new_xml = ET.tostring(root, encoding="unicode")

                    # Create VM on destination
                    async with self.transport.connect(dest_host) as dest_conn:
                        await self.libvirt.create_vm_from_xml(dest_conn, new_xml)

                    # Register VM for cleanup on failure
                    txn.register_vm(new_vm_name, dest_host)

                # Commit transaction (move files to final location)
                await txn.commit()

                logger.info(
                    f"Transaction {operation_id} committed - clone successful",
                    operation_id=operation_id,
                )

            duration = (datetime.now() - start_time).total_seconds()

            logger.info(
                f"Clone operation {operation_id} completed successfully",
                operation_id=operation_id,
                duration=duration,
            )

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
                warnings=validation.warnings,
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(
                f"Clone operation {operation_id} failed: {e}",
                operation_id=operation_id,
                exc_info=True,
            )

            return CloneResult(
                operation_id=operation_id,
                success=False,
                vm_name=vm_name,
                new_vm_name=new_vm_name,
                source_host=source_host,
                dest_host=dest_host,
                duration=duration,
                bytes_transferred=0,
                error=str(e),
            )

    async def validate_prerequisites(
        self,
        source_host: str,
        dest_host: str,
        vm_name: str,
        clone_options: CloneOptions,
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
        vm_info = None  # Store VM info for resource validation

        try:
            # Verify source VM exists
            async with self.transport.connect(source_host) as source_conn:
                if not await self.libvirt.vm_exists(source_conn, vm_name):
                    errors.append(
                        f"VM '{vm_name}' not found on source host {source_host}"
                    )
                else:
                    # Get VM info for further validation
                    vm_info = await self.libvirt.get_vm_info(source_conn, vm_name)

                    # Check if VM is running
                    if vm_info.state.value == "running":
                        warnings.append(
                            f"VM '{vm_name}' is currently running. Consider stopping it before cloning."
                        )

            # Check destination
            new_vm_name = clone_options.new_name or f"{vm_name}_clone"
            async with self.transport.connect(dest_host) as dest_conn:
                if await self.libvirt.vm_exists(dest_conn, new_vm_name):
                    if clone_options.idempotent:
                        warnings.append(
                            f"VM '{new_vm_name}' already exists on destination host {dest_host} "
                            "(will be automatically cleaned up in idempotent mode)"
                        )
                    elif clone_options.force:
                        warnings.append(
                            f"VM '{new_vm_name}' will be overwritten on destination host"
                        )
                    else:
                        errors.append(
                            f"VM '{new_vm_name}' already exists on destination host {dest_host}"
                        )

                # Check destination resources
                try:
                    resources = await self.libvirt.get_host_resources(dest_conn)

                    # Validate disk space if we have VM info
                    if vm_info:
                        # Calculate total disk space required
                        total_disk_size = sum(disk.size for disk in vm_info.disks)

                        # Add 15% margin for safety (overhead, snapshots, etc.)
                        required_space = int(total_disk_size * 1.15)

                        if resources.available_disk > 0:  # Only check if we got disk info
                            if resources.available_disk < required_space:
                                errors.append(
                                    f"Insufficient disk space on {dest_host}. "
                                    f"Required: {required_space / 1e9:.2f} GB "
                                    f"(including 15% safety margin), "
                                    f"Available: {resources.available_disk / 1e9:.2f} GB"
                                )
                            elif resources.available_disk < required_space * 1.2:
                                # Warn if less than 20% extra space
                                warnings.append(
                                    f"Low disk space on {dest_host}. "
                                    f"Required: {required_space / 1e9:.2f} GB, "
                                    f"Available: {resources.available_disk / 1e9:.2f} GB. "
                                    f"Consider freeing up space for safety."
                                )
                        else:
                            warnings.append(
                                f"Could not determine available disk space on {dest_host}. "
                                f"VM requires approximately {total_disk_size / 1e9:.2f} GB."
                            )

                        # Validate memory
                        if resources.available_memory > 0:
                            # Memory requirement in MB
                            if resources.available_memory < vm_info.memory:
                                warnings.append(
                                    f"Low memory on {dest_host}. "
                                    f"VM requires {vm_info.memory} MB, "
                                    f"available: {resources.available_memory} MB"
                                )

                        # Validate CPU
                        if resources.cpu_count > 0:
                            if resources.cpu_count < vm_info.vcpus:
                                warnings.append(
                                    f"VM requires {vm_info.vcpus} vCPUs, "
                                    f"but destination has only {resources.cpu_count} CPUs"
                                )

                except Exception as e:
                    warnings.append(f"Could not check destination resources: {e}")

        except Exception as e:
            errors.append(f"Validation error: {e}")

        return ValidationResult(
            valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    async def _transfer_disk_image(
        self,
        source_host: str,
        dest_host: str,
        source_path: str,
        new_vm_name: str,
        progress_callback: Optional[Callable[[ProgressInfo], None]],
        operation_id: str,
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
            # Validate inputs
            source_host = SecurityValidator.validate_hostname(source_host)
            dest_host = SecurityValidator.validate_hostname(dest_host)
            new_vm_name = SecurityValidator.validate_vm_name(new_vm_name)

            # Generate destination path with path traversal protection
            source_file = Path(source_path)
            base_dir = "/var/lib/libvirt/images"
            dest_filename = f"{new_vm_name}_{source_file.name}"
            dest_path = SecurityValidator.sanitize_path(dest_filename, base_dir)

            # Build secure command
            async with self.transport.connect(source_host) as source_conn:
                if dest_host == source_host:
                    # Local copy using secure command building
                    command = CommandBuilder.build_safe_command(
                        "cp {source} {dest}", source=source_path, dest=dest_path
                    )
                else:
                    # Remote copy using secure rsync command
                    command = CommandBuilder.build_rsync_command(
                        source_path=source_path,
                        dest_path=dest_path,
                        dest_host=dest_host,
                    )

                stdout, stderr, exit_code = await source_conn.execute_command(command)

                if exit_code != 0:
                    raise TransferError(
                        f"Transfer failed: {stderr}", source_host, dest_host
                    )

            return dest_path

        except ValidationError as e:
            raise TransferError(f"Validation error: {e}", source_host, dest_host)
        except Exception as e:
            raise TransferError(str(e), source_host, dest_host)

    async def _transfer_disk_image_to_path(
        self,
        source_host: str,
        dest_host: str,
        source_path: str,
        dest_path: str,
        progress_callback: Optional[Callable[[ProgressInfo], None]],
        operation_id: str,
    ) -> None:
        """
        Transfer a disk image to a specific destination path.

        Args:
            source_host: Source host
            dest_host: Destination host
            source_path: Source disk image path
            dest_path: Destination disk image path
            progress_callback: Progress callback
            operation_id: Operation ID for progress tracking
        """
        try:
            # Validate inputs
            source_host = SecurityValidator.validate_hostname(source_host)
            dest_host = SecurityValidator.validate_hostname(dest_host)
            SecurityValidator.validate_path(source_path)
            SecurityValidator.validate_path(dest_path)

            # Build secure command
            async with self.transport.connect(source_host) as source_conn:
                if dest_host == source_host:
                    # Local copy using secure command building
                    command = CommandBuilder.build_safe_command(
                        "cp {source} {dest}", source=source_path, dest=dest_path
                    )
                else:
                    # Remote copy using secure rsync command
                    command = CommandBuilder.build_rsync_command(
                        source_path=source_path,
                        dest_path=dest_path,
                        dest_host=dest_host,
                    )

                stdout, stderr, exit_code = await source_conn.execute_command(command)

                if exit_code != 0:
                    raise TransferError(
                        f"Transfer failed: {stderr}", source_host, dest_host
                    )

        except ValidationError as e:
            raise TransferError(f"Validation error: {e}", source_host, dest_host)
        except Exception as e:
            raise TransferError(str(e), source_host, dest_host)
