"""Test configuration and fixtures for kvm-clone."""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# Custom marker for spec conformance tests
def spec(spec_id: str):
    """Mark a test as conforming to a specific specification ID.
    
    Args:
        spec_id: The specification ID (e.g., "FUNC-1", "REQ-2")
    """
    return pytest.mark.spec(spec_id=spec_id)


@pytest.fixture
def sample_vm_config():
    """Sample VM configuration for testing."""
    return {
        "name": "test-vm",
        "memory": "2048M",
        "vcpus": 2,
        "disk_path": "/var/lib/libvirt/images/test-vm.qcow2",
        "network": "default"
    }


@pytest.fixture
def mock_ssh_connection():
    """Mock SSH connection for testing without actual connections."""
    # This would be implemented with proper mocking in real tests
    pass


@pytest.fixture
def temp_clone_config():
    """Temporary clone configuration for testing."""
    return {
        "source_vm": "template-vm",
        "target_vm": "cloned-vm",
        "target_host": "remote-host",
        "ssh_key": "/path/to/key"
    }
