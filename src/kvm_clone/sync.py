"""
VM synchronization operations.

This module handles VM synchronization (incremental updates) between hosts.
"""

import shlex
import uuid
from typing import Optional, Callable, Dict
from datetime import datetime

from .models import (
    SyncOptions,
    SyncResult,
    ProgressInfo,
    DeltaInfo,
    OperationType,
    OperationStatusEnum,
)
from .exceptions import VMNotFoundError, TransferError, ValidationError
from .transport import SSHTransport
from .libvirt_wrapper import LibvirtWrapper
from .security import SecurityValidator, CommandBuilder
from .logging import logger
from .constants import DEFAULT_BLOCK_SIZE, DEFAULT_NETWORK_SPEED_BYTES


class VMSynchronizer:
    """Handles VM synchronization operations."""

    def __init__(self, transport: SSHTransport, libvirt_wrapper: LibvirtWrapper):
        """Initialize VM synchronizer."""
        self.transport = transport
        self.libvirt = libvirt_wrapper

    async def sync(
        self,
        source_host: str,
        dest_host: str,
        vm_name: str,
        sync_options: SyncOptions,
        progress_callback: Optional[Callable[[ProgressInfo], None]] = None,
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

        logger.info(
            f"Starting sync operation {operation_id}: {vm_name} from {source_host} to {dest_host}",
            operation_id=operation_id,
            vm_name=vm_name,
            source_host=source_host,
            dest_host=dest_host,
        )

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
            _delta_info = None
            if sync_options.delta_only:
                _delta_info = await self.calculate_delta(
                    source_host, dest_host, vm_name, target_vm_name
                )

            # Create checkpoint if requested
            if sync_options.checkpoint:
                await self._create_checkpoint(dest_host, target_vm_name)

            # Validate disk counts BEFORE starting sync
            if len(source_vm_info.disks) != len(dest_vm_info.disks):
                if not sync_options.allow_disk_mismatch:
                    raise ValidationError(
                        f"Disk count mismatch: source has {len(source_vm_info.disks)} disks, "
                        f"destination has {len(dest_vm_info.disks)} disks. "
                        f"Use --allow-disk-mismatch to force sync (may lose data)."
                    )
                else:
                    logger.warning(
                        "Disk count mismatch - synchronizing subset only. Data loss may occur.",
                        source_disks=len(source_vm_info.disks),
                        dest_disks=len(dest_vm_info.disks),
                        operation_id=operation_id,
                    )

            # Perform synchronization
            # Calculate total bytes for progress tracking
            total_bytes = sum(disk.size for disk in source_vm_info.disks)
            transferred_bytes = 0
            blocks_synchronized = 0

            for i, source_disk in enumerate(source_vm_info.disks):
                if i < len(dest_vm_info.disks):
                    dest_disk = dest_vm_info.disks[i]

                    # Calculate progress percentage for this disk
                    disk_progress = (transferred_bytes / total_bytes * 100) if total_bytes > 0 else 0.0

                    if progress_callback:
                        progress_callback(
                            ProgressInfo(
                                operation_id=operation_id,
                                operation_type=OperationType.SYNC,
                                progress_percent=disk_progress,
                                bytes_transferred=transferred_bytes,
                                total_bytes=total_bytes,
                                speed=0.0,
                                eta=None,
                                status=OperationStatusEnum.RUNNING,
                                message=f"Synchronizing disk {i + 1}/{len(source_vm_info.disks)} ({source_disk.target})",
                                current_file=source_disk.path,
                            )
                        )

                    # Sync disk
                    sync_stats = await self._sync_disk(
                        source_host,
                        dest_host,
                        source_disk.path,
                        dest_disk.path,
                        sync_options,
                        progress_callback,
                        operation_id,
                    )

                    transferred_bytes += sync_stats["bytes_transferred"]
                    blocks_synchronized += sync_stats["blocks_synchronized"]

            duration = (datetime.now() - start_time).total_seconds()

            logger.info(
                f"Sync operation {operation_id} completed successfully",
                operation_id=operation_id,
                duration=duration,
            )

            warnings = []
            if len(source_vm_info.disks) != len(dest_vm_info.disks):
                warnings.append("Disk count mismatch - synchronized subset only.")

            return SyncResult(
                operation_id=operation_id,
                success=True,
                vm_name=vm_name,
                source_host=source_host,
                dest_host=dest_host,
                duration=duration,
                bytes_transferred=transferred_bytes,
                blocks_synchronized=blocks_synchronized,
                warnings=warnings,
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(
                f"Sync operation {operation_id} failed: {e}",
                operation_id=operation_id,
                exc_info=True,
            )

            return SyncResult(
                operation_id=operation_id,
                success=False,
                vm_name=vm_name,
                source_host=source_host,
                dest_host=dest_host,
                duration=duration,
                bytes_transferred=0,
                blocks_synchronized=0,
                error=str(e),
            )

    async def calculate_delta(
        self,
        source_host: str,
        dest_host: str,
        source_vm_name: str,
        dest_vm_name: Optional[str] = None,
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
                source_vm_info = await self.libvirt.get_vm_info(
                    source_conn, source_vm_name
                )

            async with self.transport.connect(dest_host) as dest_conn:
                dest_vm_info = await self.libvirt.get_vm_info(dest_conn, dest_vm_name)

            # Calculate differences using rsync --dry-run
            total_size = sum(disk.size for disk in source_vm_info.disks)
            changed_size = 0
            changed_blocks = 0
            files_changed = []

            for i, source_disk in enumerate(source_vm_info.disks):
                if i < len(dest_vm_info.disks):
                    dest_disk = dest_vm_info.disks[i]

                    # Use rsync --dry-run to calculate actual delta
                    try:
                        # Build rsync --dry-run --stats command
                        rsync_cmd = CommandBuilder.build_rsync_command(
                            source_path=source_disk.path,
                            dest_path=dest_disk.path,
                            dest_host=dest_host,
                            additional_options=["--dry-run", "--stats"],
                        )

                        async with self.transport.connect(source_host) as conn:
                            stdout, stderr, exit_code = await conn.execute_command(rsync_cmd)

                        # Parse rsync stats output
                        stats = self._parse_rsync_stats(stdout)
                        disk_changed_size = stats.get("transferred_size", source_disk.size)
                        changed_size += disk_changed_size
                        changed_blocks += disk_changed_size // DEFAULT_BLOCK_SIZE

                        if disk_changed_size > 0:
                            files_changed.append(source_disk.path)

                        logger.debug(
                            f"Delta calculation for {source_disk.path}: {disk_changed_size} bytes",
                            source_disk=source_disk.path,
                            changed_bytes=disk_changed_size,
                        )

                    except Exception as e:
                        # Fallback: assume full disk needs transfer
                        logger.warning(
                            f"rsync --dry-run failed for {source_disk.path}, assuming full transfer: {e}",
                            source_disk=source_disk.path,
                        )
                        changed_size += source_disk.size
                        changed_blocks += source_disk.size // DEFAULT_BLOCK_SIZE
                        files_changed.append(source_disk.path)

            # Estimate transfer time based on changed size and typical network speed
            estimated_speed = DEFAULT_NETWORK_SPEED_BYTES
            estimated_transfer_time = (
                changed_size / estimated_speed if changed_size > 0 else 0
            )

            return DeltaInfo(
                total_size=total_size,
                changed_size=changed_size,
                changed_blocks=changed_blocks,
                files_changed=files_changed,
                estimated_transfer_time=estimated_transfer_time,
            )

        except (VMNotFoundError, TransferError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Failed to calculate delta: {e}", exc_info=True)
            raise TransferError(str(e), source_host, dest_host) from e

    def _parse_rsync_stats(self, rsync_output: str) -> Dict[str, int]:
        """Parse rsync --stats output to extract transfer information.

        Args:
            rsync_output: Output from rsync --stats command

        Returns:
            Dict with 'total_size' and 'transferred_size' keys
        """
        stats = {
            "total_size": 0,
            "transferred_size": 0,
        }

        for line in rsync_output.split('\n'):
            line = line.strip()

            # Match: "Total file size: 1,234,567 bytes"
            if line.startswith("Total file size:"):
                size_str = line.split(":")[1].strip().split()[0].replace(",", "")
                try:
                    stats["total_size"] = int(size_str)
                except ValueError:
                    pass

            # Match: "Total transferred file size: 123,456 bytes"
            elif line.startswith("Total transferred file size:"):
                size_str = line.split(":")[1].strip().split()[0].replace(",", "")
                try:
                    stats["transferred_size"] = int(size_str)
                except ValueError:
                    pass

        return stats

    async def _create_checkpoint(self, host: str, vm_name: str) -> None:
        """Create a checkpoint/snapshot before synchronization."""
        try:
            # Validate inputs
            host = SecurityValidator.validate_hostname(host)
            vm_name = SecurityValidator.validate_vm_name(vm_name)

            async with self.transport.connect(host) as conn:
                # Create a snapshot using secure virsh command
                snapshot_name = (
                    f"{vm_name}_sync_checkpoint_{int(datetime.now().timestamp())}"
                )
                snapshot_name = SecurityValidator.validate_snapshot_name(snapshot_name)

                command = CommandBuilder.build_virsh_command(
                    "snapshot-create-as", vm_name, snapshot_name, "Pre-sync checkpoint"
                )

                stdout, stderr, exit_code = await conn.execute_command(command)

                if exit_code != 0:
                    logger.warning(
                        f"Failed to create checkpoint: {stderr}",
                        host=host,
                        vm_name=vm_name,
                    )
                else:
                    logger.info(
                        f"Created checkpoint {snapshot_name} for {vm_name}",
                        host=host,
                        vm_name=vm_name,
                    )

        except ValidationError as e:
            logger.warning(
                f"Checkpoint creation failed due to validation error: {e}",
                host=host,
                vm_name=vm_name,
            )
        except Exception as e:
            logger.warning(
                f"Checkpoint creation failed: {e}",
                host=host,
                vm_name=vm_name,
                exc_info=True,
            )

    async def _sync_disk(
        self,
        source_host: str,
        dest_host: str,
        source_path: str,
        dest_path: str,
        sync_options: SyncOptions,
        progress_callback: Optional[Callable[[ProgressInfo], None]],
        operation_id: str,
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
            # Validate inputs
            source_host = SecurityValidator.validate_hostname(source_host)
            dest_host = SecurityValidator.validate_hostname(dest_host)

            # Build secure rsync command
            additional_options: list[str] = []

            # Add bandwidth limit if specified
            if sync_options.bandwidth_limit:
                # Bandwidth limit validation is done in CommandBuilder.build_rsync_command
                pass

            if source_host == dest_host:
                # Local sync
                command = CommandBuilder.build_rsync_command(
                    source_path=source_path,
                    dest_path=dest_path,
                    bandwidth_limit=sync_options.bandwidth_limit,
                    additional_options=additional_options,
                )

                async with self.transport.connect(source_host) as conn:
                    stdout, stderr, exit_code = await conn.execute_command(command)
            else:
                # Remote sync
                command = CommandBuilder.build_rsync_command(
                    source_path=source_path,
                    dest_path=dest_path,
                    dest_host=dest_host,
                    bandwidth_limit=sync_options.bandwidth_limit,
                    additional_options=additional_options,
                )

                async with self.transport.connect(source_host) as conn:
                    stdout, stderr, exit_code = await conn.execute_command(command)

            if exit_code != 0:
                raise TransferError(f"Rsync failed: {stderr}", source_host, dest_host)

            # Parse rsync output for actual transfer statistics
            stats = self._parse_rsync_transfer_stats(stdout)

            return {
                "bytes_transferred": stats.get("bytes_transferred", 0),
                "blocks_synchronized": stats.get("blocks_synchronized", 0),
            }

        except (ValidationError, TransferError):
            raise
        except Exception as e:
            raise TransferError(str(e), source_host, dest_host) from e

    def _parse_rsync_transfer_stats(self, rsync_output: str) -> Dict[str, int]:
        """Parse rsync verbose output for transfer statistics.

        Args:
            rsync_output: Output from rsync command with --verbose or --stats

        Returns:
            Dict with 'bytes_transferred' and 'blocks_synchronized' keys
        """
        stats = {
            "bytes_transferred": 0,
            "blocks_synchronized": 0,
        }

        for line in rsync_output.split('\n'):
            line = line.strip()

            # Match: "sent X bytes  received Y bytes"
            if "sent " in line and " bytes" in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "sent" and i + 1 < len(parts):
                        sent_str = parts[i + 1].replace(",", "")
                        try:
                            stats["bytes_transferred"] = int(sent_str)
                        except ValueError:
                            pass
                        break

            # Alternative: look for "Total transferred file size: X bytes"
            if "Total transferred file size:" in line:
                size_str = line.split(":")[1].strip().split()[0].replace(",", "")
                try:
                    stats["bytes_transferred"] = int(size_str)
                except (ValueError, IndexError):
                    pass

        # Calculate blocks synchronized from bytes
        if stats["bytes_transferred"] > 0:
            stats["blocks_synchronized"] = stats["bytes_transferred"] // DEFAULT_BLOCK_SIZE

        return stats
