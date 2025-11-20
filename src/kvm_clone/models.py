"""
Data models for KVM cloning operations.

This module defines the data structures used throughout the KVM cloning system.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum


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
    backing_file: Optional[str] = None


@dataclass
class NetworkInfo:
    """Network interface information."""

    interface: str
    mac_address: str
    network: str
    ip_address: Optional[str] = None
    bridge: Optional[str] = None


@dataclass
class VMInfo:
    """Virtual machine information."""

    name: str
    uuid: str
    state: VMState
    memory: int  # MB
    vcpus: int
    disks: List[DiskInfo]
    networks: List[NetworkInfo]
    host: str
    created: datetime
    last_modified: datetime
    config_path: Optional[str] = None


@dataclass
class CloneOptions:
    """Options for cloning operations."""

    new_name: Optional[str] = None
    force: bool = False
    dry_run: bool = False
    parallel: int = 4
    compress: bool = False
    verify: bool = True
    preserve_mac: bool = False
    network_config: Optional[Dict[str, Any]] = None
    bandwidth_limit: Optional[str] = None  # e.g., "100M", "1G"


@dataclass
class SyncOptions:
    """Options for sync operations."""

    target_name: Optional[str] = None
    checkpoint: bool = False
    delta_only: bool = True
    bandwidth_limit: Optional[str] = None


@dataclass
class ProgressInfo:
    """Progress information for operations."""

    operation_id: str
    operation_type: OperationType
    progress_percent: float
    bytes_transferred: int
    total_bytes: int
    speed: float  # bytes/sec
    eta: Optional[int]  # seconds
    status: OperationStatusEnum
    message: Optional[str] = None
    current_file: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of prerequisite validation."""

    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


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
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    validation: Optional[ValidationResult] = None


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
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


@dataclass
class DeltaInfo:
    """Information about differences between VMs."""

    total_size: int
    changed_size: int
    changed_blocks: int
    files_changed: List[str]
    estimated_transfer_time: float


@dataclass
class OperationStatus:
    """Status of an operation."""

    operation_id: str
    operation_type: OperationType
    status: OperationStatusEnum
    progress: Optional[ProgressInfo] = None
    result: Optional[Union[CloneResult, SyncResult]] = None
    created: datetime = field(default_factory=datetime.now)
    started: Optional[datetime] = None
    completed: Optional[datetime] = None
    error: Optional[str] = None


@dataclass
class SSHConnectionInfo:
    """SSH connection information."""

    host: str
    port: int = 22
    username: Optional[str] = None
    key_path: Optional[str] = None
    timeout: int = 30


@dataclass
class TransferStats:
    """Transfer statistics."""

    bytes_transferred: int = 0
    files_transferred: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
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
