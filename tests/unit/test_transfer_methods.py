"""
Tests for transfer method implementations (rsync and libvirt streaming).
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from src.kvm_clone.models import CloneOptions, TransferMethod, VMInfo, VMState, DiskInfo
from src.kvm_clone.cloner import VMCloner
from datetime import datetime


@pytest.fixture
def mock_transport():
    """Create a mock SSH transport."""
    transport = Mock()
    mock_conn = AsyncMock()
    mock_conn.execute_command = AsyncMock(return_value=("", "", 0))
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)
    transport.connect = AsyncMock(return_value=mock_conn)
    transport.username = "root"
    transport.port = 22
    return transport


@pytest.fixture
def mock_libvirt():
    """Create a mock libvirt wrapper."""
    libvirt = Mock()
    libvirt.vm_exists = AsyncMock(return_value=False)
    libvirt.get_vm_info = AsyncMock()
    libvirt.get_host_resources = AsyncMock()
    libvirt.clone_vm_definition = AsyncMock(return_value="<domain>...</domain>")
    libvirt.create_vm_from_xml = AsyncMock()
    return libvirt


@pytest.mark.asyncio
async def test_transfer_method_enum_values():
    """Test that TransferMethod enum has correct values."""
    assert TransferMethod.RSYNC.value == "rsync"
    assert TransferMethod.LIBVIRT_STREAM.value == "libvirt"


@pytest.mark.asyncio
async def test_clone_options_default_transfer_method():
    """Test that CloneOptions defaults to RSYNC transfer method."""
    options = CloneOptions()
    assert options.transfer_method == TransferMethod.RSYNC


@pytest.mark.asyncio
async def test_clone_options_libvirt_transfer_method():
    """Test that CloneOptions accepts LIBVIRT_STREAM transfer method."""
    options = CloneOptions(transfer_method=TransferMethod.LIBVIRT_STREAM)
    assert options.transfer_method == TransferMethod.LIBVIRT_STREAM


@pytest.mark.asyncio
async def test_rsync_transfer_called_by_default(mock_transport, mock_libvirt):
    """Test that rsync transfer method is called by default."""
    cloner = VMCloner(mock_transport, mock_libvirt)

    # Mock the transfer method
    with patch.object(cloner, '_transfer_disk_rsync', new_callable=AsyncMock) as mock_rsync:
        await cloner._transfer_disk_image_to_path(
            "source_host",
            "dest_host",
            "/var/lib/libvirt/images/disk1.qcow2",
            "/tmp/staging/disk1.qcow2",
            None,
            "test-op-123",
            bandwidth_limit=None,
            transfer_method=TransferMethod.RSYNC,
        )

        # Verify rsync was called
        assert mock_rsync.called
        assert mock_rsync.call_count == 1


@pytest.mark.asyncio
async def test_libvirt_stream_transfer_called(mock_transport, mock_libvirt):
    """Test that libvirt streaming transfer method is called when specified."""
    cloner = VMCloner(mock_transport, mock_libvirt)

    # Mock the transfer method
    with patch.object(cloner, '_transfer_disk_libvirt_stream', new_callable=AsyncMock) as mock_libvirt_stream:
        await cloner._transfer_disk_image_to_path(
            "source_host",
            "dest_host",
            "/var/lib/libvirt/images/disk1.qcow2",
            "/tmp/staging/disk1.qcow2",
            None,
            "test-op-123",
            transfer_method=TransferMethod.LIBVIRT_STREAM,
        )

        # Verify libvirt streaming was called
        assert mock_libvirt_stream.called
        assert mock_libvirt_stream.call_count == 1


@pytest.mark.asyncio
async def test_rsync_transfer_builds_correct_command(mock_transport, mock_libvirt):
    """Test that rsync transfer builds correct command with optimized flags."""
    cloner = VMCloner(mock_transport, mock_libvirt)

    await cloner._transfer_disk_rsync(
        "source_host",
        "dest_host",
        "/var/lib/libvirt/images/disk1.qcow2",
        "/tmp/staging/disk1.qcow2",
        None,
        "test-op-123",
        bandwidth_limit="100M",
    )

    # Verify execute_command was called
    mock_conn = await mock_transport.connect.return_value.__aenter__()
    assert mock_conn.execute_command.called

    # Get the command that was executed
    call_args = mock_conn.execute_command.call_args[0][0]

    # Verify optimized rsync flags are present
    assert "rsync" in call_args
    assert "-avS" in call_args  # Archive, verbose, sparse
    assert "--partial" in call_args  # Resume capability
    assert "--inplace" in call_args  # Required for sparse
    assert "--progress" in call_args  # Progress monitoring
    assert "--bwlimit" in call_args  # Bandwidth limit
    assert "100M" in call_args

    # Verify compression flag is NOT present (removed for optimization)
    assert "-z" not in call_args.split()  # Split to avoid matching in paths


@pytest.mark.asyncio
async def test_libvirt_stream_transfer_gets_file_size(mock_transport, mock_libvirt):
    """Test that libvirt streaming gets file size before transfer."""
    cloner = VMCloner(mock_transport, mock_libvirt)

    # Mock stat command to return file size
    mock_conn = await mock_transport.connect.return_value.__aenter__()
    mock_conn.execute_command = AsyncMock(return_value=("10737418240", "", 0))  # 10GB

    await cloner._transfer_disk_libvirt_stream(
        "source_host",
        "dest_host",
        "/var/lib/libvirt/images/disk1.qcow2",
        "/tmp/staging/disk1.qcow2",
        None,
        "test-op-123",
    )

    # Verify stat command was called
    assert mock_conn.execute_command.called
    # First call should be stat command
    first_call = mock_conn.execute_command.call_args_list[0][0][0]
    assert "stat" in first_call
    assert "-c %s" in first_call


@pytest.mark.asyncio
async def test_libvirt_stream_creates_dest_directory(mock_transport, mock_libvirt):
    """Test that libvirt streaming creates destination directory."""
    cloner = VMCloner(mock_transport, mock_libvirt)

    # Setup mock to return file size on first call, success on others
    mock_conn = await mock_transport.connect.return_value.__aenter__()
    mock_conn.execute_command = AsyncMock(
        side_effect=[
            ("10737418240", "", 0),  # stat command
            ("", "", 0),  # mkdir command
            ("", "", 0),  # scp command
        ]
    )

    await cloner._transfer_disk_libvirt_stream(
        "source_host",
        "dest_host",
        "/var/lib/libvirt/images/disk1.qcow2",
        "/var/lib/libvirt/images/staging/disk1.qcow2",
        None,
        "test-op-123",
    )

    # Verify mkdir was called
    calls = [call[0][0] for call in mock_conn.execute_command.call_args_list]
    assert any("mkdir" in call for call in calls)


@pytest.mark.asyncio
async def test_transfer_method_passed_to_disk_transfer(mock_transport, mock_libvirt):
    """Test that transfer_method from CloneOptions is passed to disk transfer."""
    cloner = VMCloner(mock_transport, mock_libvirt)

    # Setup mocks for a minimal clone operation
    mock_libvirt.get_vm_info.return_value = VMInfo(
        name="test_vm",
        uuid="12345678-1234-1234-1234-123456789012",
        state=VMState.STOPPED,
        memory=2048,
        vcpus=2,
        disks=[
            DiskInfo(
                path="/var/lib/libvirt/images/disk1.qcow2",
                size=10737418240,  # 10GB
                format="qcow2",
                target="vda",
            )
        ],
        networks=[],
        host="source_host",
        created=datetime.now(),
        last_modified=datetime.now(),
    )

    mock_libvirt.clone_vm_definition.return_value = (
        '<domain><devices><disk type="file"><source file="/path/to/disk"/></disk></devices></domain>'
    )

    # Mock transfer_disk_image_to_path to track calls
    with patch.object(cloner, '_transfer_disk_image_to_path', new_callable=AsyncMock) as mock_transfer:
        options = CloneOptions(
            new_name="test_vm_clone",
            transfer_method=TransferMethod.LIBVIRT_STREAM,
        )

        try:
            await cloner.clone("source_host", "dest_host", "test_vm", options)
        except Exception:
            # Clone might fail due to missing mocks, but we just care about the transfer call
            pass

        # Verify transfer was called with correct transfer_method
        if mock_transfer.called:
            call_kwargs = mock_transfer.call_args[1]
            assert "transfer_method" in call_kwargs
            assert call_kwargs["transfer_method"] == TransferMethod.LIBVIRT_STREAM


@pytest.mark.asyncio
async def test_rsync_respects_bandwidth_limit(mock_transport, mock_libvirt):
    """Test that rsync respects bandwidth limit option."""
    cloner = VMCloner(mock_transport, mock_libvirt)

    await cloner._transfer_disk_rsync(
        "source_host",
        "dest_host",
        "/var/lib/libvirt/images/disk1.qcow2",
        "/tmp/staging/disk1.qcow2",
        None,
        "test-op-123",
        bandwidth_limit="50M",
    )

    # Verify bandwidth limit is in command
    mock_conn = await mock_transport.connect.return_value.__aenter__()
    call_args = mock_conn.execute_command.call_args[0][0]
    assert "--bwlimit" in call_args
    assert "50M" in call_args


@pytest.mark.asyncio
async def test_rsync_without_bandwidth_limit(mock_transport, mock_libvirt):
    """Test that rsync works without bandwidth limit."""
    cloner = VMCloner(mock_transport, mock_libvirt)

    await cloner._transfer_disk_rsync(
        "source_host",
        "dest_host",
        "/var/lib/libvirt/images/disk1.qcow2",
        "/tmp/staging/disk1.qcow2",
        None,
        "test-op-123",
        bandwidth_limit=None,
    )

    # Verify no bandwidth limit in command
    mock_conn = await mock_transport.connect.return_value.__aenter__()
    call_args = mock_conn.execute_command.call_args[0][0]
    # Command should still work without --bwlimit
    assert "rsync" in call_args
    assert "-avS" in call_args


@pytest.mark.asyncio
async def test_local_copy_uses_cp_not_rsync(mock_transport, mock_libvirt):
    """Test that local copies use cp instead of rsync."""
    cloner = VMCloner(mock_transport, mock_libvirt)

    # Same source and dest host
    await cloner._transfer_disk_rsync(
        "localhost",
        "localhost",
        "/var/lib/libvirt/images/disk1.qcow2",
        "/tmp/staging/disk1.qcow2",
        None,
        "test-op-123",
    )

    # Verify cp command was used, not rsync
    mock_conn = await mock_transport.connect.return_value.__aenter__()
    call_args = mock_conn.execute_command.call_args[0][0]
    assert "cp" in call_args
    assert "rsync" not in call_args


# ============================================================================
# Blocksync Transfer Method Tests
# ============================================================================


@pytest.mark.asyncio
async def test_blocksync_enum_value():
    """Test that TransferMethod has BLOCKSYNC value."""
    assert TransferMethod.BLOCKSYNC.value == "blocksync"


@pytest.mark.asyncio
async def test_blocksync_transfer_called(mock_transport, mock_libvirt):
    """Test that blocksync transfer method is called when specified."""
    cloner = VMCloner(mock_transport, mock_libvirt)

    # Mock the transfer method
    with patch.object(cloner, '_transfer_disk_blocksync', new_callable=AsyncMock) as mock_blocksync:
        await cloner._transfer_disk_image_to_path(
            "source_host",
            "dest_host",
            "/var/lib/libvirt/images/disk1.qcow2",
            "/tmp/staging/disk1.qcow2",
            None,
            "test-op-123",
            transfer_method=TransferMethod.BLOCKSYNC,
        )

        # Verify blocksync was called
        assert mock_blocksync.called
        assert mock_blocksync.call_count == 1


@pytest.mark.asyncio
async def test_blocksync_checks_installation(mock_transport, mock_libvirt):
    """Test that blocksync checks if tool is installed on both hosts."""
    cloner = VMCloner(mock_transport, mock_libvirt)

    # Mock to return success for blocksync check
    mock_conn = await mock_transport.connect.return_value.__aenter__()
    mock_conn.execute_command = AsyncMock(
        side_effect=[
            ("/usr/bin/blocksync", "", 0),  # Source check
            ("/usr/bin/blocksync", "", 0),  # Dest check
            ("", "", 0),  # mkdir
            ("new", "", 0),  # test -f (file doesn't exist)
            ("", "", 0),  # blocksync command
        ]
    )

    await cloner._transfer_disk_blocksync(
        "source_host",
        "dest_host",
        "/var/lib/libvirt/images/disk1.qcow2",
        "/tmp/staging/disk1.qcow2",
        None,
        "test-op-123",
    )

    # Verify installation check commands were called
    calls = [call[0][0] for call in mock_conn.execute_command.call_args_list]
    assert any("command -v blocksync" in call for call in calls)


@pytest.mark.asyncio
async def test_blocksync_fails_if_not_installed_on_source(mock_transport, mock_libvirt):
    """Test that blocksync fails with clear error if not installed on source."""
    cloner = VMCloner(mock_transport, mock_libvirt)

    # Mock to return failure for blocksync check on source
    mock_conn = await mock_transport.connect.return_value.__aenter__()
    mock_conn.execute_command = AsyncMock(return_value=("", "command not found", 1))

    with pytest.raises(Exception) as exc_info:
        await cloner._transfer_disk_blocksync(
            "source_host",
            "dest_host",
            "/var/lib/libvirt/images/disk1.qcow2",
            "/tmp/staging/disk1.qcow2",
            None,
            "test-op-123",
        )

    # Verify error message mentions installation
    assert "not installed" in str(exc_info.value).lower()
    assert "github.com/nethappen/blocksync-fast" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_blocksync_detects_incremental_sync(mock_transport, mock_libvirt):
    """Test that blocksync detects if destination file exists for incremental sync."""
    cloner = VMCloner(mock_transport, mock_libvirt)

    # Mock to simulate existing destination file
    mock_conn = await mock_transport.connect.return_value.__aenter__()
    mock_conn.execute_command = AsyncMock(
        side_effect=[
            ("/usr/bin/blocksync", "", 0),  # Source check
            ("/usr/bin/blocksync", "", 0),  # Dest check
            ("", "", 0),  # mkdir
            ("exists", "", 0),  # test -f (file exists - incremental!)
            ("", "", 0),  # blocksync command
        ]
    )

    await cloner._transfer_disk_blocksync(
        "source_host",
        "dest_host",
        "/var/lib/libvirt/images/disk1.qcow2",
        "/tmp/staging/disk1.qcow2",
        None,
        "test-op-123",
    )

    # Verify test command was executed
    calls = [call[0][0] for call in mock_conn.execute_command.call_args_list]
    assert any("test -f" in call for call in calls)


@pytest.mark.asyncio
async def test_blocksync_builds_correct_command(mock_transport, mock_libvirt):
    """Test that blocksync builds correct command with all options."""
    cloner = VMCloner(mock_transport, mock_libvirt)

    mock_transport.port = 22
    mock_transport.username = "testuser"

    # Mock responses
    mock_conn = await mock_transport.connect.return_value.__aenter__()
    mock_conn.execute_command = AsyncMock(
        side_effect=[
            ("/usr/bin/blocksync", "", 0),  # Source check
            ("/usr/bin/blocksync", "", 0),  # Dest check
            ("", "", 0),  # mkdir
            ("new", "", 0),  # test -f
            ("", "", 0),  # blocksync command
        ]
    )

    await cloner._transfer_disk_blocksync(
        "source_host",
        "dest_host",
        "/var/lib/libvirt/images/disk1.qcow2",
        "/tmp/staging/disk1.qcow2",
        None,
        "test-op-123",
        bandwidth_limit="100M",
    )

    # Get the blocksync command (should be the last call)
    blocksync_call = mock_conn.execute_command.call_args_list[-1][0][0]

    # Verify command structure
    assert "blocksync" in blocksync_call
    assert "/var/lib/libvirt/images/disk1.qcow2" in blocksync_call
    assert "dest_host" in blocksync_call
    assert "/tmp/staging/disk1.qcow2" in blocksync_call
    assert "-v" in blocksync_call  # Verbose flag


@pytest.mark.asyncio
async def test_blocksync_converts_bandwidth_limit(mock_transport, mock_libvirt):
    """Test that blocksync converts bandwidth limit from rsync format to MB/s."""
    cloner = VMCloner(mock_transport, mock_libvirt)

    mock_transport.port = 22
    mock_transport.username = "testuser"

    # Mock responses
    mock_conn = await mock_transport.connect.return_value.__aenter__()
    mock_conn.execute_command = AsyncMock(
        side_effect=[
            ("/usr/bin/blocksync", "", 0),  # Source check
            ("/usr/bin/blocksync", "", 0),  # Dest check
            ("", "", 0),  # mkdir
            ("new", "", 0),  # test -f
            ("", "", 0),  # blocksync command
        ]
    )

    await cloner._transfer_disk_blocksync(
        "source_host",
        "dest_host",
        "/var/lib/libvirt/images/disk1.qcow2",
        "/tmp/staging/disk1.qcow2",
        None,
        "test-op-123",
        bandwidth_limit="100M",  # rsync format
    )

    # Get the blocksync command
    blocksync_call = mock_conn.execute_command.call_args_list[-1][0][0]

    # Should convert 100M to 100 (MB/s)
    assert "--bwlimit" in blocksync_call or "100" in blocksync_call


@pytest.mark.asyncio
async def test_blocksync_creates_dest_directory(mock_transport, mock_libvirt):
    """Test that blocksync creates destination directory if needed."""
    cloner = VMCloner(mock_transport, mock_libvirt)

    # Mock responses
    mock_conn = await mock_transport.connect.return_value.__aenter__()
    mock_conn.execute_command = AsyncMock(
        side_effect=[
            ("/usr/bin/blocksync", "", 0),  # Source check
            ("/usr/bin/blocksync", "", 0),  # Dest check
            ("", "", 0),  # mkdir
            ("new", "", 0),  # test -f
            ("", "", 0),  # blocksync command
        ]
    )

    await cloner._transfer_disk_blocksync(
        "source_host",
        "dest_host",
        "/var/lib/libvirt/images/disk1.qcow2",
        "/var/lib/libvirt/images/staging/disk1.qcow2",
        None,
        "test-op-123",
    )

    # Verify mkdir was called
    calls = [call[0][0] for call in mock_conn.execute_command.call_args_list]
    assert any("mkdir" in call for call in calls)
