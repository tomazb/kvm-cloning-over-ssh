"""KVM Clone - A utility for cloning KVM virtual machines over SSH."""

__version__ = "0.1.0"
__author__ = "tomaz"
__description__ = "KVM cloning utility"

# Import main classes for easy access
from .client import KVMCloneClient
from .models import (
    CloneOptions,
    SyncOptions,
    CloneResult,
    SyncResult,
    VMInfo,
    ProgressInfo,
    OperationStatus,
)
from .exceptions import (
    KVMCloneError,
    ConfigurationError,
    ConnectionError,
    VMNotFoundError,
    VMExistsError,
    TransferError,
    ValidationError,
)
from .security import SecurityValidator, CommandBuilder, SSHSecurity

__all__ = [
    "__version__",
    "__author__",
    "__description__",
    "KVMCloneClient",
    "CloneOptions",
    "SyncOptions",
    "CloneResult",
    "SyncResult",
    "VMInfo",
    "ProgressInfo",
    "OperationStatus",
    "KVMCloneError",
    "ConfigurationError",
    "ConnectionError",
    "VMNotFoundError",
    "VMExistsError",
    "TransferError",
    "ValidationError",
    "SecurityValidator",
    "CommandBuilder",
    "SSHSecurity",
]
