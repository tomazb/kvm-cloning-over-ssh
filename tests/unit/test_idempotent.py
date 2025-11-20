"""
Tests for idempotent clone operations.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from src.kvm_clone.models import CloneOptions


@pytest.fixture
def mock_libvirt():
    """Create a mock libvirt wrapper."""
    libvirt = Mock()
    libvirt.vm_exists = AsyncMock()
    libvirt.cleanup_vm = AsyncMock()
    libvirt.get_vm_info = AsyncMock()
    libvirt.get_host_resources = AsyncMock()
    libvirt.clone_vm_definition = AsyncMock(return_value="<domain>...</domain>")
    libvirt.create_vm_from_xml = AsyncMock()
    return libvirt


@pytest.fixture
def mock_transport():
    """Create a mock SSH transport."""
    transport = Mock()
    mock_conn = AsyncMock()
    mock_conn.execute_command = AsyncMock(return_value=("", "", 0))
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)
    transport.connect = AsyncMock(return_value=mock_conn)
    return transport


@pytest.mark.asyncio
async def test_idempotent_flag_in_clone_options():
    """Test that CloneOptions accepts idempotent flag."""
    options = CloneOptions(idempotent=True)
    assert options.idempotent is True

    options = CloneOptions(idempotent=False)
    assert options.idempotent is False

    options = CloneOptions()  # Default
    assert options.idempotent is False


@pytest.mark.asyncio
async def test_cleanup_vm_stops_running_vm(mock_libvirt, mock_transport):
    """Test that cleanup_vm stops a running VM before cleanup."""
    from src.kvm_clone.libvirt_wrapper import LibvirtWrapper

    wrapper = LibvirtWrapper()

    # Mock libvirt connection and domain
    mock_conn = Mock()
    mock_domain = Mock()
    mock_domain.isActive = Mock(return_value=True)
    mock_domain.destroy = Mock()
    mock_domain.undefine = Mock()
    mock_domain.XMLDesc = Mock(return_value="<domain><devices></devices></domain>")

    mock_conn.lookupByName = Mock(return_value=mock_domain)

    with patch.object(wrapper, "connect_to_host", new=AsyncMock(return_value=mock_conn)):
        await wrapper.cleanup_vm(mock_transport.connect.return_value, "test_vm")

    # Verify VM was stopped
    assert mock_domain.destroy.called


@pytest.mark.asyncio
async def test_cleanup_vm_extracts_disk_paths(mock_libvirt, mock_transport):
    """Test that cleanup_vm extracts and deletes disk files."""
    from src.kvm_clone.libvirt_wrapper import LibvirtWrapper

    wrapper = LibvirtWrapper()

    # Mock libvirt connection and domain with disk
    mock_conn = Mock()
    mock_domain = Mock()
    mock_domain.isActive = Mock(return_value=False)
    mock_domain.undefine = Mock()
    mock_domain.XMLDesc = Mock(
        return_value='<domain><devices><disk type="file"><source file="/var/lib/libvirt/images/disk1.qcow2"/></disk></devices></domain>'
    )

    mock_conn.lookupByName = Mock(return_value=mock_domain)

    mock_ssh_conn = AsyncMock()
    mock_ssh_conn.execute_command = AsyncMock(return_value=("", "", 0))

    with patch.object(wrapper, "connect_to_host", new=AsyncMock(return_value=mock_conn)):
        await wrapper.cleanup_vm(mock_ssh_conn, "test_vm")

    # Verify disk deletion command was executed
    assert mock_ssh_conn.execute_command.called
    call_args = mock_ssh_conn.execute_command.call_args[0][0]
    assert "rm" in call_args
    assert "/var/lib/libvirt/images/disk1.qcow2" in call_args


@pytest.mark.asyncio
async def test_cleanup_vm_handles_nonexistent_vm(mock_libvirt, mock_transport):
    """Test that cleanup_vm handles non-existent VM gracefully."""
    from src.kvm_clone.libvirt_wrapper import LibvirtWrapper
    import libvirt

    wrapper = LibvirtWrapper()

    # Mock libvirt connection that raises error for non-existent VM
    mock_conn = Mock()
    mock_conn.lookupByName = Mock(side_effect=libvirt.libvirtError("VM not found"))

    mock_ssh_conn = AsyncMock()

    with patch.object(wrapper, "connect_to_host", new=AsyncMock(return_value=mock_conn)):
        # Should not raise, just return
        await wrapper.cleanup_vm(mock_ssh_conn, "nonexistent_vm")


@pytest.mark.asyncio
async def test_idempotent_mode_triggers_cleanup(mock_transport, mock_libvirt):
    """Test that idempotent mode triggers VM cleanup."""
    from src.kvm_clone.cloner import VMCloner
    from src.kvm_clone.models import VMInfo, VMState, DiskInfo
    from datetime import datetime

    cloner = VMCloner(mock_transport, mock_libvirt)

    # Setup mocks
    mock_libvirt.vm_exists.return_value = True  # VM already exists
    mock_libvirt.get_vm_info.return_value = VMInfo(
        name="test_vm",
        uuid="123",
        state=VMState.STOPPED,
        memory=1024,
        vcpus=2,
        disks=[
            DiskInfo(path="/test/disk.qcow2", size=1000000, format="qcow2", target="vda")
        ],
        networks=[],
        host="source",
        created=datetime.now(),
        last_modified=datetime.now(),
    )

    options = CloneOptions(idempotent=True)

    # This will fail at some point, but we just want to verify cleanup is called
    try:
        await cloner.clone("source", "dest", "test_vm", options)
    except Exception:
        pass

    # Verify cleanup_vm was called
    assert mock_libvirt.cleanup_vm.called


@pytest.mark.asyncio
async def test_force_mode_triggers_cleanup(mock_transport, mock_libvirt):
    """Test that force mode triggers VM cleanup."""
    from src.kvm_clone.cloner import VMCloner
    from src.kvm_clone.models import VMInfo, VMState, DiskInfo
    from datetime import datetime

    cloner = VMCloner(mock_transport, mock_libvirt)

    # Setup mocks
    mock_libvirt.vm_exists.return_value = True  # VM already exists
    mock_libvirt.get_vm_info.return_value = VMInfo(
        name="test_vm",
        uuid="123",
        state=VMState.STOPPED,
        memory=1024,
        vcpus=2,
        disks=[
            DiskInfo(path="/test/disk.qcow2", size=1000000, format="qcow2", target="vda")
        ],
        networks=[],
        host="source",
        created=datetime.now(),
        last_modified=datetime.now(),
    )

    options = CloneOptions(force=True)

    # This will fail at some point, but we just want to verify cleanup is called
    try:
        await cloner.clone("source", "dest", "test_vm", options)
    except Exception:
        pass

    # Verify cleanup_vm was called
    assert mock_libvirt.cleanup_vm.called


@pytest.mark.asyncio
async def test_validation_accepts_existing_vm_with_idempotent(mock_transport, mock_libvirt):
    """Test that validation allows existing VM when idempotent flag is set."""
    from src.kvm_clone.cloner import VMCloner
    from src.kvm_clone.models import VMInfo, VMState
    from datetime import datetime

    cloner = VMCloner(mock_transport, mock_libvirt)

    # Setup: Both source and destination VMs exist
    mock_libvirt.vm_exists = AsyncMock(return_value=True)
    mock_libvirt.get_vm_info.return_value = VMInfo(
        name="test_vm",
        uuid="123",
        state=VMState.STOPPED,
        memory=1024,
        vcpus=2,
        disks=[],
        networks=[],
        host="source",
        created=datetime.now(),
        last_modified=datetime.now(),
    )

    options = CloneOptions(idempotent=True)

    # Validation should pass with warning
    result = await cloner.validate_prerequisites("source", "dest", "test_vm", options)

    # Should be valid with idempotent warning
    assert result.valid is True
    assert len(result.errors) == 0
    assert any("idempotent mode" in w.lower() for w in result.warnings)


@pytest.mark.asyncio
async def test_validation_rejects_existing_vm_without_flags(mock_transport, mock_libvirt):
    """Test that validation rejects existing VM without idempotent or force flags."""
    from src.kvm_clone.cloner import VMCloner
    from src.kvm_clone.models import VMInfo, VMState
    from datetime import datetime

    cloner = VMCloner(mock_transport, mock_libvirt)

    # Setup: VM exists on destination
    call_count = [0]

    async def vm_exists_side_effect(conn, name):
        call_count[0] += 1
        # Source VM exists (first call), destination VM exists (second call)
        return call_count[0] == 2

    mock_libvirt.vm_exists = AsyncMock(side_effect=vm_exists_side_effect)
    mock_libvirt.get_vm_info.return_value = VMInfo(
        name="test_vm",
        uuid="123",
        state=VMState.STOPPED,
        memory=1024,
        vcpus=2,
        disks=[],
        networks=[],
        host="source",
        created=datetime.now(),
        last_modified=datetime.now(),
    )

    options = CloneOptions(idempotent=False, force=False)

    # Validation should fail
    result = await cloner.validate_prerequisites("source", "dest", "test_vm", options)

    # Should have error
    assert not result.valid
    assert any("already exists" in e for e in result.errors)


def test_clone_options_idempotent_and_force_both_allowed():
    """Test that both idempotent and force can be set (idempotent takes precedence)."""
    options = CloneOptions(idempotent=True, force=True)
    assert options.idempotent is True
    assert options.force is True
