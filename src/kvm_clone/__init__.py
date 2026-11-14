"""KVM Clone - A utility for cloning KVM virtual machines over SSH."""

from __future__ import annotations

__version__ = "0.1.0"
__author__ = "tomaz"
__description__ = "KVM cloning utility"

# Import main classes for easy access
from .client import KVMCloneClient
from .exceptions import (
    ConfigurationError,
    ConnectionError,
    KVMCloneError,
    TransferError,
    ValidationError,
    VMExistsError,
    VMNotFoundError,
)
from .models import (
    CloneOptions,
    CloneResult,
    OperationStatus,
    ProgressInfo,
    SyncOptions,
    SyncResult,
    VMInfo,
)
from .progress import create_disk_progress_info, create_progress_info
from .security import CommandBuilder, SecurityValidator, SSHSecurity

__all__ = [
    "CloneOptions",
    "CloneResult",
    "CommandBuilder",
    "ConfigurationError",
    "ConnectionError",
    "KVMCloneClient",
    "KVMCloneError",
    "OperationStatus",
    "ProgressInfo",
    "SSHSecurity",
    "SecurityValidator",
    "SyncOptions",
    "SyncResult",
    "TransferError",
    "VMExistsError",
    "VMInfo",
    "VMNotFoundError",
    "ValidationError",
    "__author__",
    "__description__",
    "__version__",
    "create_disk_progress_info",
    "create_progress_info",
]
