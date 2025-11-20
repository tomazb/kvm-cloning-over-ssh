"""
Custom exceptions for KVM cloning operations.

This module defines all custom exceptions used throughout the KVM cloning system.
"""


class KVMCloneError(Exception):
    """Base exception for KVM clone operations."""

    def __init__(self, message: str, error_code: int = 1000) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


class ConfigurationError(KVMCloneError):
    """Configuration-related errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code=1001)


class ConnectionError(KVMCloneError):
    """Connection-related errors."""

    def __init__(self, message: str, host: str) -> None:
        super().__init__(f"Connection error to {host}: {message}", error_code=1002)
        self.host = host


class VMNotFoundError(KVMCloneError):
    """VM not found errors."""

    def __init__(self, vm_name: str, host: str) -> None:
        super().__init__(f"VM '{vm_name}' not found on host '{host}'", error_code=1003)
        self.vm_name = vm_name
        self.host = host


class VMExistsError(KVMCloneError):
    """VM already exists errors."""

    def __init__(self, vm_name: str, host: str) -> None:
        super().__init__(
            f"VM '{vm_name}' already exists on host '{host}'", error_code=1004
        )
        self.vm_name = vm_name
        self.host = host


class InsufficientResourcesError(KVMCloneError):
    """Insufficient resources errors."""

    def __init__(self, message: str, resource_type: str) -> None:
        super().__init__(f"Insufficient {resource_type}: {message}", error_code=1005)
        self.resource_type = resource_type


class TransferError(KVMCloneError):
    """Data transfer errors."""

    def __init__(self, message: str, source: str, destination: str) -> None:
        super().__init__(
            f"Transfer error from {source} to {destination}: {message}", error_code=1006
        )
        self.source = source
        self.destination = destination


class ValidationError(KVMCloneError):
    """Validation errors."""

    def __init__(self, message: str, validation_type: str = "general") -> None:
        super().__init__(
            f"Validation error ({validation_type}): {message}", error_code=1007
        )
        self.validation_type = validation_type


class LibvirtError(KVMCloneError):
    """Libvirt API errors."""

    def __init__(self, message: str, operation: str = "unknown") -> None:
        super().__init__(
            f"Libvirt error during {operation}: {message}", error_code=1008
        )
        self.operation = operation


class SSHError(KVMCloneError):
    """SSH-related errors."""

    def __init__(self, message: str, host: str, operation: str = "connection") -> None:
        super().__init__(
            f"SSH error on {host} during {operation}: {message}", error_code=1009
        )
        self.host = host
        self.operation = operation


class AuthenticationError(KVMCloneError):
    """Authentication errors."""

    def __init__(self, message: str, host: str, auth_method: str = "key") -> None:
        super().__init__(
            f"Authentication failed for {host} using {auth_method}: {message}",
            error_code=1010,
        )
        self.host = host
        self.auth_method = auth_method


class PermissionError(KVMCloneError):
    """Permission-related errors."""

    def __init__(self, message: str, resource: str, operation: str = "access") -> None:
        super().__init__(
            f"Permission denied for {operation} on {resource}: {message}",
            error_code=1011,
        )
        self.resource = resource
        self.operation = operation


class TimeoutError(KVMCloneError):
    """Timeout errors."""

    def __init__(self, message: str, operation: str, timeout: int) -> None:
        super().__init__(
            f"Timeout during {operation} after {timeout}s: {message}", error_code=1012
        )
        self.operation = operation
        self.timeout = timeout


class OperationCancelledError(KVMCloneError):
    """Operation cancelled errors."""

    def __init__(self, operation_id: str, operation_type: str) -> None:
        super().__init__(
            f"{operation_type} operation {operation_id} was cancelled", error_code=1013
        )
        self.operation_id = operation_id
        self.operation_type = operation_type


class IntegrityError(KVMCloneError):
    """Data integrity errors."""

    def __init__(self, message: str, file_path: str) -> None:
        super().__init__(
            f"Integrity check failed for {file_path}: {message}", error_code=1014
        )
        self.file_path = file_path


class DiskSpaceError(InsufficientResourcesError):
    """Disk space errors."""

    def __init__(self, required: int, available: int, path: str) -> None:
        message = (
            f"Required {required} bytes, only {available} bytes available at {path}"
        )
        super().__init__(message, "disk_space")
        self.required = required
        self.available = available
        self.path = path


class MemoryError(InsufficientResourcesError):
    """Memory errors."""

    def __init__(self, required: int, available: int, host: str) -> None:
        message = f"Required {required} MB, only {available} MB available on {host}"
        super().__init__(message, "memory")
        self.required = required
        self.available = available
        self.host = host


class NetworkError(KVMCloneError):
    """Network-related errors."""

    def __init__(
        self, message: str, network_name: str, operation: str = "configuration"
    ) -> None:
        super().__init__(
            f"Network error in {network_name} during {operation}: {message}",
            error_code=1015,
        )
        self.network_name = network_name
        self.operation = operation
