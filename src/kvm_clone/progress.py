"""
Progress tracking utilities for KVM cloning operations.

This module provides helper functions for creating ProgressInfo objects,
eliminating code duplication between cloner and sync operations.
"""

from __future__ import annotations

from .models import ProgressInfo, OperationType, OperationStatusEnum


def create_progress_info(
    operation_id: str,
    operation_type: OperationType,
    progress_percent: float,
    bytes_transferred: int,
    total_bytes: int,
    current_file: str | None = None,
    message: str | None = None,
    speed: float = 0.0,
    status: OperationStatusEnum = OperationStatusEnum.RUNNING,
) -> ProgressInfo:
    """
    Create a ProgressInfo object with common defaults.

    Args:
        operation_id: Operation identifier
        operation_type: Type of operation
        progress_percent: Progress percentage (0-100)
        bytes_transferred: Number of bytes transferred
        total_bytes: Total bytes to transfer
        current_file: Current file being processed
        message: Progress message
        speed: Transfer speed in bytes/sec
        status: Operation status

    Returns:
        ProgressInfo: Progress information object
    """
    return ProgressInfo(
        operation_id=operation_id,
        operation_type=operation_type,
        progress_percent=progress_percent,
        bytes_transferred=bytes_transferred,
        total_bytes=total_bytes,
        speed=speed,
        eta=None,  # Could be calculated later
        status=status,
        message=message,
        current_file=current_file,
    )


def create_disk_progress_info(
    operation_id: str,
    operation_type: OperationType,
    disk_index: int,
    total_disks: int,
    bytes_transferred: int,
    total_bytes: int,
    disk_path: str,
    speed: float = 0.0,
) -> ProgressInfo:
    """
    Create ProgressInfo for disk transfer operation.

    Args:
        operation_id: Operation identifier
        operation_type: Type of operation (CLONE or SYNC)
        disk_index: Index of current disk (0-based)
        total_disks: Total number of disks
        bytes_transferred: Bytes transferred so far
        total_bytes: Total bytes to transfer
        disk_path: Path to disk being transferred
        speed: Current transfer speed

    Returns:
        ProgressInfo: Progress information
    """
    # Calculate progress percentage based on disk index
    progress_percent = (disk_index / total_disks * 100) if total_disks > 0 else 0.0

    if operation_type == OperationType.CLONE:
        message = f"Transferring disk {disk_index + 1}/{total_disks}"
    else:
        message = f"Synchronizing disk {disk_index + 1}/{total_disks}"

    return create_progress_info(
        operation_id=operation_id,
        operation_type=operation_type,
        progress_percent=progress_percent,
        bytes_transferred=bytes_transferred,
        total_bytes=total_bytes,
        current_file=disk_path,
        message=message,
        speed=speed,
    )
