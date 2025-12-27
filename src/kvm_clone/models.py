"""
Data models for KVM cloning operations.

This module defines the data structures used throughout the KVM cloning system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from datetime import datetime
from enum import Enum

from .constants import DEFAULT_PARALLEL_TRANSFERS


class VMState(Enum):
    """Virtual machine states."""

    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"
    SUSPENDED = "suspended"
    UNKNOWN = "unknown"


class OperationType(Enum):
    """Operation types."""

    CLONE = "clone"
    SYNC = "sync"
    LIST = "list"


class OperationStatusEnum(Enum):
    """Operation status values."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DiskInfo:
    """Disk information."""

    path: str
    size: int  # bytes
    format: str
    target: str
    backing_file: str | None = None


@dataclass
class NetworkInfo:
    """Network interface information."""

    interface: str
    mac_address: str
    network: str
    ip_address: str | None = None
    bridge: str | None = None


@dataclass
class VMInfo:
    """Virtual machine information."""

    name: str
    uuid: str
    state: VMState
    memory: int  # MB
    vcpus: int
    disks: list[DiskInfo]
    networks: list[NetworkInfo]
    host: str
    created: datetime
    last_modified: datetime
    config_path: str | None = None


@dataclass
class CloneOptions:
    """Options for cloning operations."""

    new_name: str | None = None
    force: bool = False
    dry_run: bool = False
    parallel: int = DEFAULT_PARALLEL_TRANSFERS
    compress: bool = False
    verify: bool = True
    preserve_mac: bool = False
    network_config: dict[str, Any] | None = None


@dataclass
class SyncOptions:
    """Options for sync operations."""

    target_name: str | None = None
    checkpoint: bool = False
    delta_only: bool = True
    bandwidth_limit: str | None = None
    allow_disk_mismatch: bool = False  # Allow sync despite disk count mismatch
    parallel: int = DEFAULT_PARALLEL_TRANSFERS  # Number of parallel disk transfers


@dataclass
class ProgressInfo:
    """Progress information for operations."""

    operation_id: str
    operation_type: OperationType
    progress_percent: float
    bytes_transferred: int
    total_bytes: int
    speed: float  # bytes/sec
    eta: int | None  # seconds
    status: OperationStatusEnum
    message: str | None = None
    current_file: str | None = None


@dataclass
class ValidationResult:
    """Result of prerequisite validation."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class CloneResult:
    """Result of clone operation."""

    operation_id: str
    success: bool
    vm_name: str
    new_vm_name: str
    source_host: str
    dest_host: str
    duration: float  # seconds
    bytes_transferred: int
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    validation: ValidationResult | None = None


@dataclass
class SyncResult:
    """Result of sync operation."""

    operation_id: str
    success: bool
    vm_name: str
    source_host: str
    dest_host: str
    duration: float  # seconds
    bytes_transferred: int
    blocks_synchronized: int
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class DeltaInfo:
    """Information about differences between VMs."""

    total_size: int
    changed_size: int
    changed_blocks: int
    files_changed: list[str]
    estimated_transfer_time: float


@dataclass
class OperationStatus:
    """Status of an operation."""

    operation_id: str
    operation_type: OperationType
    status: OperationStatusEnum
    progress: ProgressInfo | None = None
    result: CloneResult | SyncResult | None = None
    created: datetime = field(default_factory=datetime.now)
    started: datetime | None = None
    completed: datetime | None = None
    error: str | None = None


@dataclass
class SSHConnectionInfo:
    """SSH connection information."""

    host: str
    port: int = 22
    username: str | None = None
    key_path: str | None = None
    timeout: int = 30


@dataclass
class TransferStats:
    """Transfer statistics."""

    bytes_transferred: int = 0
    files_transferred: int = 0
    start_time: datetime | None = None
    end_time: datetime | None = None
    average_speed: float = 0.0  # bytes/sec
    peak_speed: float = 0.0  # bytes/sec


@dataclass
class ResourceInfo:
    """Host resource information."""

    total_memory: int  # MB
    available_memory: int  # MB
    total_disk: int  # bytes
    available_disk: int  # bytes
    cpu_count: int
    cpu_usage: float  # percentage
