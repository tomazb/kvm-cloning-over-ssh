"""
Tests for transaction management module.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from src.kvm_clone.transaction import (
    CloneTransaction,
    ResourceType,
    TransactionResource,
    TransactionLog,
)


@pytest.fixture
def mock_transport():
    """Create a mock SSH transport."""
    transport = Mock()
    transport.connect = AsyncMock()

    # Create a mock connection
    mock_conn = AsyncMock()
    mock_conn.execute_command = AsyncMock(return_value="")
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)

    transport.connect.return_value = mock_conn

    return transport


@pytest.mark.asyncio
async def test_transaction_commit_success(mock_transport):
    """Test successful transaction commit."""
    async with CloneTransaction("test-op-123", mock_transport) as txn:
        # Register some resources
        txn.register_disk("/tmp/disk1.qcow2", "host1", is_temporary=True, final_path="/var/lib/libvirt/images/disk1.qcow2")
        txn.register_vm("test_vm", "host1")

        # Commit transaction
        await txn.commit()

    # Verify transaction was committed
    assert txn.committed is True
    assert txn.rolled_back is False
    assert txn.log.status == "committed"


@pytest.mark.asyncio
async def test_transaction_rollback_on_exception(mock_transport):
    """Test automatic rollback when exception occurs."""
    try:
        async with CloneTransaction("test-op-456", mock_transport) as txn:
            # Register resources
            txn.register_disk("/tmp/disk1.qcow2", "host1")
            txn.register_vm("test_vm", "host1")

            # Simulate an error
            raise RuntimeError("Simulated error")
    except RuntimeError:
        pass  # Expected

    # Verify rollback was called
    # The transaction should have tried to clean up resources
    assert mock_transport.connect.called


@pytest.mark.asyncio
async def test_register_disk(mock_transport):
    """Test registering a disk resource."""
    async with CloneTransaction("test-op-789", mock_transport) as txn:
        txn.register_disk("/path/to/disk.qcow2", "host1", is_temporary=False)

        assert len(txn.resources) == 1
        assert txn.resources[0].resource_type == ResourceType.DISK_FILE
        assert txn.resources[0].resource_id == "/path/to/disk.qcow2"
        assert txn.resources[0].host == "host1"

        await txn.commit()


@pytest.mark.asyncio
async def test_register_vm(mock_transport):
    """Test registering a VM resource."""
    async with CloneTransaction("test-op-101", mock_transport) as txn:
        txn.register_vm("my_vm", "host2")

        assert len(txn.resources) == 1
        assert txn.resources[0].resource_type == ResourceType.VM_DEFINITION
        assert txn.resources[0].resource_id == "my_vm"
        assert txn.resources[0].host == "host2"

        await txn.commit()


@pytest.mark.asyncio
async def test_register_directory(mock_transport):
    """Test registering a directory resource."""
    async with CloneTransaction("test-op-202", mock_transport) as txn:
        txn.register_directory("/tmp/staging", "host3")

        assert len(txn.resources) == 1
        assert txn.resources[0].resource_type == ResourceType.DIRECTORY
        assert txn.resources[0].resource_id == "/tmp/staging"
        assert txn.resources[0].host == "host3"

        await txn.commit()


@pytest.mark.asyncio
async def test_staging_path(mock_transport):
    """Test getting staging path."""
    async with CloneTransaction("test-op-303", mock_transport) as txn:
        staging_path = txn.get_staging_path("disk1.qcow2")

        assert "/tmp/kvm-clone-test-op-303" in staging_path
        assert "disk1.qcow2" in staging_path

        await txn.commit()


@pytest.mark.asyncio
async def test_rollback_order(mock_transport):
    """Test that rollback happens in reverse order."""
    rollback_order = []

    async def cleanup_func_1(conn):
        rollback_order.append(1)

    async def cleanup_func_2(conn):
        rollback_order.append(2)

    async def cleanup_func_3(conn):
        rollback_order.append(3)

    try:
        async with CloneTransaction("test-op-404", mock_transport) as txn:
            txn.register_resource(
                ResourceType.DISK_FILE, "/disk1", "host1", cleanup_func=cleanup_func_1
            )
            txn.register_resource(
                ResourceType.DISK_FILE, "/disk2", "host1", cleanup_func=cleanup_func_2
            )
            txn.register_resource(
                ResourceType.DISK_FILE, "/disk3", "host1", cleanup_func=cleanup_func_3
            )

            # Simulate failure
            raise RuntimeError("Test failure")
    except RuntimeError:
        pass

    # Verify rollback happened in reverse order
    assert rollback_order == [3, 2, 1]


@pytest.mark.asyncio
async def test_transaction_log(mock_transport, tmp_path):
    """Test transaction logging."""
    async with CloneTransaction("test-op-505", mock_transport) as txn:
        txn.register_disk("/disk1", "host1")
        txn.register_vm("vm1", "host1")

        # Save log
        log_file = tmp_path / "transaction.json"
        txn.log.save_to_file(str(log_file))

        await txn.commit()

    # Verify log file was created
    assert log_file.exists()

    # Verify log content
    import json

    with open(log_file) as f:
        log_data = json.load(f)

    assert log_data["transaction_id"] == "test-op-505"
    assert log_data["operation_type"] == "clone"
    assert len(log_data["resources"]) == 2


@pytest.mark.asyncio
async def test_multiple_resources_same_type(mock_transport):
    """Test registering multiple resources of the same type."""
    async with CloneTransaction("test-op-606", mock_transport) as txn:
        txn.register_disk("/disk1.qcow2", "host1")
        txn.register_disk("/disk2.qcow2", "host1")
        txn.register_disk("/disk3.qcow2", "host1")

        assert len(txn.resources) == 3
        assert all(r.resource_type == ResourceType.DISK_FILE for r in txn.resources)

        await txn.commit()


@pytest.mark.asyncio
async def test_commit_without_resources(mock_transport):
    """Test committing empty transaction."""
    async with CloneTransaction("test-op-707", mock_transport) as txn:
        # No resources registered
        await txn.commit()

    assert txn.committed is True
    assert txn.log.status == "committed"


@pytest.mark.asyncio
async def test_double_commit_ignored(mock_transport):
    """Test that double commit is ignored."""
    async with CloneTransaction("test-op-808", mock_transport) as txn:
        txn.register_disk("/disk1", "host1")

        await txn.commit()
        await txn.commit()  # Should be ignored

    assert txn.committed is True


@pytest.mark.asyncio
async def test_custom_staging_dir(mock_transport):
    """Test custom staging directory."""
    custom_staging = "/custom/staging/dir"
    async with CloneTransaction(
        "test-op-909", mock_transport, staging_dir=custom_staging
    ) as txn:
        assert txn.staging_dir == custom_staging

        staging_path = txn.get_staging_path("file.txt")
        assert staging_path.startswith(custom_staging)

        await txn.commit()


@pytest.mark.asyncio
async def test_temp_disk_move_on_commit(mock_transport):
    """Test that temporary disks are moved to final location on commit."""
    mock_conn = AsyncMock()
    mock_conn.execute_command = AsyncMock(return_value="")
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)
    mock_transport.connect.return_value = mock_conn

    async with CloneTransaction("test-op-1010", mock_transport) as txn:
        txn.register_disk(
            "/tmp/staging/disk1.qcow2",
            "host1",
            is_temporary=True,
            final_path="/var/lib/libvirt/images/disk1.qcow2",
        )

        await txn.commit()

    # Verify move command was executed
    assert mock_conn.execute_command.called
    # Check that mv command was in the call
    call_args = [call[0][0] for call in mock_conn.execute_command.call_args_list]
    assert any("mv" in arg for arg in call_args)


def test_transaction_resource_creation():
    """Test creating transaction resource."""
    resource = TransactionResource(
        resource_type=ResourceType.DISK_FILE,
        resource_id="/path/to/disk.qcow2",
        host="host1",
        metadata={"size": 1000},
    )

    assert resource.resource_type == ResourceType.DISK_FILE
    assert resource.resource_id == "/path/to/disk.qcow2"
    assert resource.host == "host1"
    assert resource.metadata["size"] == 1000
    assert resource.created_at is not None


def test_transaction_log_to_dict():
    """Test converting transaction log to dictionary."""
    log = TransactionLog(
        transaction_id="test-123",
        operation_type="clone",
        started_at=datetime.now().isoformat(),
    )

    log.resources.append(
        TransactionResource(
            resource_type=ResourceType.DISK_FILE,
            resource_id="/disk1",
            host="host1",
        )
    )

    log_dict = log.to_dict()

    assert log_dict["transaction_id"] == "test-123"
    assert log_dict["operation_type"] == "clone"
    assert len(log_dict["resources"]) == 1
    # cleanup_func should be removed
    assert "cleanup_func" not in log_dict["resources"][0]
