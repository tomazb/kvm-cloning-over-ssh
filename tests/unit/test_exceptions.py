"""Comprehensive unit tests for custom exceptions."""

import pytest
from kvm_clone.exceptions import (
    KVMCloneError, ConfigurationError, ConnectionError, VMNotFoundError,
    VMExistsError, InsufficientResourcesError, TransferError, ValidationError,
    LibvirtError, SSHError, AuthenticationError, PermissionError,
    TimeoutError, OperationCancelledError, IntegrityError,
    DiskSpaceError, MemoryError, NetworkError
)


class TestKVMCloneError:
    """Test base KVMCloneError exception."""
    
    def test_base_exception_initialization(self):
        """Test base exception can be created with message and error code."""
        error = KVMCloneError("Test error", error_code=9999)
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.error_code == 9999
    
    def test_base_exception_default_error_code(self):
        """Test base exception has default error code."""
        error = KVMCloneError("Test error")
        assert error.error_code == 1000
    
    def test_base_exception_inheritance(self):
        """Test base exception inherits from Exception."""
        error = KVMCloneError("Test error")
        assert isinstance(error, Exception)


class TestConfigurationError:
    """Test ConfigurationError exception."""
    
    def test_configuration_error_creation(self):
        """Test ConfigurationError can be created."""
        error = ConfigurationError("Invalid configuration")
        assert "Invalid configuration" in str(error)
        assert error.error_code == 1001
    
    def test_configuration_error_inheritance(self):
        """Test ConfigurationError inherits from KVMCloneError."""
        error = ConfigurationError("Test")
        assert isinstance(error, KVMCloneError)
        assert isinstance(error, Exception)


class TestConnectionError:
    """Test ConnectionError exception."""
    
    def test_connection_error_with_host(self):
        """Test ConnectionError includes host information."""
        error = ConnectionError("Connection failed", "192.168.1.100")
        assert "192.168.1.100" in str(error)
        assert "Connection failed" in str(error)
        assert error.host == "192.168.1.100"
        assert error.error_code == 1002
    
    def test_connection_error_attributes(self):
        """Test ConnectionError stores host attribute."""
        error = ConnectionError("Timeout", "example.com")
        assert error.host == "example.com"


class TestVMNotFoundError:
    """Test VMNotFoundError exception."""
    
    def test_vm_not_found_error_creation(self):
        """Test VMNotFoundError includes VM name and host."""
        error = VMNotFoundError("test-vm", "host1")
        assert "test-vm" in str(error)
        assert "host1" in str(error)
        assert error.vm_name == "test-vm"
        assert error.host == "host1"
        assert error.error_code == 1003
    
    def test_vm_not_found_error_message_format(self):
        """Test VMNotFoundError message is properly formatted."""
        error = VMNotFoundError("my-vm", "server.example.com")
        expected = "VM 'my-vm' not found on host 'server.example.com'"
        assert str(error) == expected


class TestVMExistsError:
    """Test VMExistsError exception."""
    
    def test_vm_exists_error_creation(self):
        """Test VMExistsError includes VM name and host."""
        error = VMExistsError("existing-vm", "host2")
        assert "existing-vm" in str(error)
        assert "host2" in str(error)
        assert error.vm_name == "existing-vm"
        assert error.host == "host2"
        assert error.error_code == 1004
    
    def test_vm_exists_error_message_format(self):
        """Test VMExistsError message is properly formatted."""
        error = VMExistsError("duplicate-vm", "target-host")
        expected = "VM 'duplicate-vm' already exists on host 'target-host'"
        assert str(error) == expected


class TestInsufficientResourcesError:
    """Test InsufficientResourcesError exception."""
    
    def test_insufficient_resources_error_creation(self):
        """Test InsufficientResourcesError with resource type."""
        error = InsufficientResourcesError("Not enough space", "disk")
        assert "disk" in str(error)
        assert "Not enough space" in str(error)
        assert error.resource_type == "disk"
        assert error.error_code == 1005
    
    def test_insufficient_resources_various_types(self):
        """Test InsufficientResourcesError with various resource types."""
        for resource_type in ["memory", "cpu", "disk", "network"]:
            error = InsufficientResourcesError("Insufficient", resource_type)
            assert error.resource_type == resource_type
            assert resource_type in str(error)


class TestTransferError:
    """Test TransferError exception."""
    
    def test_transfer_error_creation(self):
        """Test TransferError includes source and destination."""
        error = TransferError("Network failure", "/source/path", "/dest/path")
        assert "/source/path" in str(error)
        assert "/dest/path" in str(error)
        assert "Network failure" in str(error)
        assert error.source == "/source/path"
        assert error.destination == "/dest/path"
        assert error.error_code == 1006
    
    def test_transfer_error_with_hosts(self):
        """Test TransferError with host information."""
        error = TransferError("Timeout", "host1:/path1", "host2:/path2")
        assert error.source == "host1:/path1"
        assert error.destination == "host2:/path2"


class TestValidationError:
    """Test ValidationError exception."""
    
    def test_validation_error_default_type(self):
        """Test ValidationError with default validation type."""
        error = ValidationError("Invalid input")
        assert "Invalid input" in str(error)
        assert error.validation_type == "general"
        assert error.error_code == 1007
    
    def test_validation_error_custom_type(self):
        """Test ValidationError with custom validation type."""
        error = ValidationError("Invalid VM name", "vm_name")
        assert "vm_name" in str(error)
        assert error.validation_type == "vm_name"
    
    def test_validation_error_various_types(self):
        """Test ValidationError with various validation types."""
        types = ["hostname", "path", "port", "email", "url"]
        for val_type in types:
            error = ValidationError("Invalid", val_type)
            assert error.validation_type == val_type


class TestLibvirtError:
    """Test LibvirtError exception."""
    
    def test_libvirt_error_default_operation(self):
        """Test LibvirtError with default operation."""
        error = LibvirtError("Connection failed")
        assert "unknown" in str(error)
        assert error.operation == "unknown"
        assert error.error_code == 1008
    
    def test_libvirt_error_custom_operation(self):
        """Test LibvirtError with custom operation."""
        error = LibvirtError("Failed to create domain", "domain_creation")
        assert "domain_creation" in str(error)
        assert error.operation == "domain_creation"
    
    def test_libvirt_error_various_operations(self):
        """Test LibvirtError with various operations."""
        operations = ["connection", "list_vms", "get_vm_info", "clone", "snapshot"]
        for operation in operations:
            error = LibvirtError("Error", operation)
            assert error.operation == operation


class TestSSHError:
    """Test SSHError exception."""
    
    def test_ssh_error_default_operation(self):
        """Test SSHError with default operation."""
        error = SSHError("Connection timeout", "host1")
        assert "host1" in str(error)
        assert "connection" in str(error)
        assert error.host == "host1"
        assert error.operation == "connection"
        assert error.error_code == 1009
    
    def test_ssh_error_custom_operation(self):
        """Test SSHError with custom operation."""
        error = SSHError("Command failed", "server.com", "command_execution")
        assert error.host == "server.com"
        assert error.operation == "command_execution"
        assert "command_execution" in str(error)
    
    def test_ssh_error_file_transfer_operation(self):
        """Test SSHError for file transfer operations."""
        error = SSHError("Transfer interrupted", "192.168.1.1", "file_transfer")
        assert error.operation == "file_transfer"
        assert error.host == "192.168.1.1"


class TestAuthenticationError:
    """Test AuthenticationError exception."""
    
    def test_authentication_error_default_method(self):
        """Test AuthenticationError with default auth method."""
        error = AuthenticationError("Auth failed", "host1")
        assert "host1" in str(error)
        assert "key" in str(error)
        assert error.host == "host1"
        assert error.auth_method == "key"
        assert error.error_code == 1010
    
    def test_authentication_error_custom_method(self):
        """Test AuthenticationError with custom auth method."""
        error = AuthenticationError("Invalid password", "server.com", "password")
        assert error.auth_method == "password"
        assert "password" in str(error)
    
    def test_authentication_error_various_methods(self):
        """Test AuthenticationError with various auth methods."""
        methods = ["key", "password", "kerberos", "certificate"]
        for method in methods:
            error = AuthenticationError("Failed", "host", method)
            assert error.auth_method == method


class TestPermissionError:
    """Test PermissionError exception."""
    
    def test_permission_error_default_operation(self):
        """Test PermissionError with default operation."""
        error = PermissionError("Denied", "/etc/config")
        assert "/etc/config" in str(error)
        assert "access" in str(error)
        assert error.resource == "/etc/config"
        assert error.operation == "access"
        assert error.error_code == 1011
    
    def test_permission_error_custom_operation(self):
        """Test PermissionError with custom operation."""
        error = PermissionError("Cannot write", "/var/data", "write")
        assert error.operation == "write"
        assert error.resource == "/var/data"
    
    def test_permission_error_various_operations(self):
        """Test PermissionError with various operations."""
        operations = ["read", "write", "execute", "delete", "create"]
        for operation in operations:
            error = PermissionError("Denied", "/path", operation)
            assert error.operation == operation


class TestTimeoutError:
    """Test TimeoutError exception."""
    
    def test_timeout_error_creation(self):
        """Test TimeoutError includes operation and timeout value."""
        error = TimeoutError("Operation timed out", "clone", 300)
        assert "clone" in str(error)
        assert "300" in str(error)
        assert error.operation == "clone"
        assert error.timeout == 300
        assert error.error_code == 1012
    
    def test_timeout_error_various_timeouts(self):
        """Test TimeoutError with various timeout values."""
        for timeout in [30, 60, 300, 3600]:
            error = TimeoutError("Timeout", "operation", timeout)
            assert error.timeout == timeout
            assert str(timeout) in str(error)


class TestOperationCancelledError:
    """Test OperationCancelledError exception."""
    
    def test_operation_cancelled_error_creation(self):
        """Test OperationCancelledError includes operation details."""
        error = OperationCancelledError("op-123", "clone")
        assert "op-123" in str(error)
        assert "clone" in str(error)
        assert error.operation_id == "op-123"
        assert error.operation_type == "clone"
        assert error.error_code == 1013
    
    def test_operation_cancelled_various_types(self):
        """Test OperationCancelledError with various operation types."""
        for op_type in ["clone", "sync", "backup", "restore"]:
            error = OperationCancelledError("id-456", op_type)
            assert error.operation_type == op_type


class TestIntegrityError:
    """Test IntegrityError exception."""
    
    def test_integrity_error_creation(self):
        """Test IntegrityError includes file path and message."""
        error = IntegrityError("Checksum mismatch", "/path/to/file.img")
        assert "Checksum mismatch" in str(error)
        assert "/path/to/file.img" in str(error)
        assert error.file_path == "/path/to/file.img"
        assert error.error_code == 1014
    
    def test_integrity_error_various_messages(self):
        """Test IntegrityError with various integrity issues."""
        messages = ["Checksum failed", "Size mismatch", "Corruption detected"]
        for message in messages:
            error = IntegrityError(message, "/file")
            assert message in str(error)


class TestDiskSpaceError:
    """Test DiskSpaceError exception."""
    
    def test_disk_space_error_creation(self):
        """Test DiskSpaceError includes space requirements."""
        error = DiskSpaceError(1000000, 500000, "/var/lib/libvirt")
        assert "1000000" in str(error)
        assert "500000" in str(error)
        assert "/var/lib/libvirt" in str(error)
        assert error.required == 1000000
        assert error.available == 500000
        assert error.path == "/var/lib/libvirt"
        assert error.error_code == 1005
        assert error.resource_type == "disk_space"
    
    def test_disk_space_error_inheritance(self):
        """Test DiskSpaceError inherits from InsufficientResourcesError."""
        error = DiskSpaceError(100, 50, "/tmp")
        assert isinstance(error, InsufficientResourcesError)
        assert isinstance(error, KVMCloneError)
    
    def test_disk_space_error_various_sizes(self):
        """Test DiskSpaceError with various size values."""
        sizes = [(1000, 500), (1024*1024, 512*1024), (0, 0)]
        for required, available in sizes:
            error = DiskSpaceError(required, available, "/path")
            assert error.required == required
            assert error.available == available


class TestMemoryError:
    """Test MemoryError exception."""
    
    def test_memory_error_creation(self):
        """Test MemoryError includes memory requirements."""
        error = MemoryError(8192, 4096, "host1")
        assert "8192" in str(error)
        assert "4096" in str(error)
        assert "host1" in str(error)
        assert error.required == 8192
        assert error.available == 4096
        assert error.host == "host1"
        assert error.error_code == 1005
        assert error.resource_type == "memory"
    
    def test_memory_error_inheritance(self):
        """Test MemoryError inherits from InsufficientResourcesError."""
        error = MemoryError(1024, 512, "server")
        assert isinstance(error, InsufficientResourcesError)
        assert isinstance(error, KVMCloneError)
    
    def test_memory_error_various_amounts(self):
        """Test MemoryError with various memory amounts."""
        amounts = [(2048, 1024), (16384, 8192), (1000, 999)]
        for required, available in amounts:
            error = MemoryError(required, available, "host")
            assert error.required == required
            assert error.available == available


class TestNetworkError:
    """Test NetworkError exception."""
    
    def test_network_error_default_operation(self):
        """Test NetworkError with default operation."""
        error = NetworkError("Bridge not found", "br0")
        assert "br0" in str(error)
        assert "configuration" in str(error)
        assert error.network_name == "br0"
        assert error.operation == "configuration"
        assert error.error_code == 1015
    
    def test_network_error_custom_operation(self):
        """Test NetworkError with custom operation."""
        error = NetworkError("Connection failed", "default", "attach")
        assert error.operation == "attach"
        assert error.network_name == "default"
    
    def test_network_error_various_operations(self):
        """Test NetworkError with various network operations."""
        operations = ["create", "delete", "attach", "detach", "configuration"]
        for operation in operations:
            error = NetworkError("Error", "network", operation)
            assert error.operation == operation


class TestExceptionChaining:
    """Test exception chaining and context preservation."""
    
    def test_exception_can_be_raised_from_another(self):
        """Test exceptions can be chained using 'from' keyword."""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise ConfigurationError("Config error") from e
        except ConfigurationError as error:
            assert error.__cause__ is not None
            assert isinstance(error.__cause__, ValueError)
    
    def test_exception_context_is_preserved(self):
        """Test exception context is preserved in try-except blocks."""
        try:
            try:
                raise RuntimeError("First error")
            except RuntimeError:
                raise VMNotFoundError("vm1", "host1")
        except VMNotFoundError as error:
            assert error.__context__ is not None
            assert isinstance(error.__context__, RuntimeError)


class TestExceptionRepresentation:
    """Test exception string representation."""
    
    def test_exception_str_is_informative(self):
        """Test exception string contains useful information."""
        error = TransferError("Network timeout", "host1:/path1", "host2:/path2")
        error_str = str(error)
        assert "Network timeout" in error_str
        assert "host1:/path1" in error_str
        assert "host2:/path2" in error_str
    
    def test_exception_repr_includes_class_name(self):
        """Test exception repr includes class name."""
        error = VMNotFoundError("test-vm", "test-host")
        error_repr = repr(error)
        # Standard Python exception repr includes the exception class
        assert "VMNotFoundError" in error_repr or "VM 'test-vm'" in error_repr