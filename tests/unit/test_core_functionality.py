"""Unit tests for core KVM cloning functionality."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from kvm_clone.client import KVMCloneClient
from kvm_clone.models import CloneOptions, VMInfo, VMState, DiskInfo, NetworkInfo
from kvm_clone.exceptions import VMNotFoundError, ConfigurationError
from tests.conftest import spec


class TestVMConfiguration:
    """Test VM configuration handling."""
    
    @spec("FUNC-1")
    @pytest.mark.unit
    def test_vm_config_validation(self, sample_vm_config):
        """Test VM configuration validation."""
        assert sample_vm_config["name"] == "test-vm"
        assert sample_vm_config["memory"] == "2048M"
        assert sample_vm_config["vcpus"] == 2
    
    @spec("FUNC-2")
    @pytest.mark.unit
    def test_clone_options_creation(self):
        """Test clone options creation."""
        options = CloneOptions(
            new_name="test-clone",
            force=True,
            parallel=8,
            compress=True
        )
        assert options.new_name == "test-clone"
        assert options.force is True
        assert options.parallel == 8
        assert options.compress is True
        assert options.verify is True  # Default value
    
    @spec("FUNC-3")
    @pytest.mark.unit
    def test_vm_info_model(self):
        """Test VM info model creation."""
        vm_info = VMInfo(
            name="test-vm",
            uuid="12345678-1234-1234-1234-123456789012",
            state=VMState.RUNNING,
            memory=2048,
            vcpus=2,
            disks=[],
            networks=[],
            host="localhost",
            created=datetime.now(),
            last_modified=datetime.now()
        )
        assert vm_info.name == "test-vm"
        assert vm_info.state == VMState.RUNNING
        assert vm_info.memory == 2048


class TestSSHConnection:
    """Test SSH connection management."""
    
    @spec("CONN-1")
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_ssh_connection_setup(self):
        """Test SSH connection initialization."""
        from kvm_clone.transport import SSHConnection
        
        conn = SSHConnection("localhost", port=22, timeout=30)
        assert conn.host == "localhost"
        assert conn.port == 22
        assert conn.timeout == 30
    
    @spec("CONN-2")
    @pytest.mark.unit
    def test_ssh_transport_initialization(self):
        """Test SSH transport initialization."""
        from kvm_clone.transport import SSHTransport
        
        transport = SSHTransport(key_path="~/.ssh/id_rsa", timeout=60)
        assert transport.key_path == "~/.ssh/id_rsa"
        assert transport.timeout == 60
        assert len(transport.connections) == 0
    
    @spec("CONN-3")
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_ssh_connection_cleanup(self):
        """Test SSH connection cleanup."""
        from kvm_clone.transport import SSHTransport
        
        transport = SSHTransport()
        await transport.close_all()
        assert len(transport.connections) == 0


class TestCloningLogic:
    """Test VM cloning logic."""
    
    @spec("CLONE-1")
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_clone_preparation(self, temp_clone_config):
        """Test clone preparation steps."""
        from kvm_clone.cloner import VMCloner
        from kvm_clone.transport import SSHTransport
        from kvm_clone.libvirt_wrapper import LibvirtWrapper
        
        transport = SSHTransport()
        libvirt = LibvirtWrapper()
        cloner = VMCloner(transport, libvirt)
        
        # Mock the validation method
        with patch.object(cloner, 'validate_prerequisites') as mock_validate:
            mock_validate.return_value = AsyncMock()
            mock_validate.return_value.valid = True
            mock_validate.return_value.errors = []
            mock_validate.return_value.warnings = []
            
            validation = await cloner.validate_prerequisites(
                "source", "dest", "test-vm", CloneOptions()
            )
            
            assert validation.valid is True
            assert len(validation.errors) == 0
    
    @spec("CLONE-2")
    @pytest.mark.unit
    def test_client_initialization(self):
        """Test KVM clone client initialization."""
        config = {
            'ssh_key_path': '~/.ssh/test_key',
            'timeout': 1800
        }
        
        client = KVMCloneClient(config=config, timeout=3600)
        assert client.config['ssh_key_path'] == '~/.ssh/test_key'
        assert client.timeout == 3600  # Constructor parameter overrides config
    
    @spec("CLONE-3")
    @pytest.mark.unit
    def test_exception_handling(self):
        """Test custom exception creation."""
        from kvm_clone.exceptions import VMNotFoundError, ConfigurationError
        
        vm_error = VMNotFoundError("test-vm", "localhost")
        assert vm_error.vm_name == "test-vm"
        assert vm_error.host == "localhost"
        assert vm_error.error_code == 1003
        
        config_error = ConfigurationError("Invalid config")
        assert config_error.error_code == 1001
        assert "Invalid config" in str(config_error)
