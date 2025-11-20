"""Comprehensive unit tests for data models."""

from datetime import datetime
from kvm_clone.models import (
    VMState, OperationType, OperationStatusEnum,
    DiskInfo, NetworkInfo, VMInfo, CloneOptions, SyncOptions,
    ProgressInfo, ValidationResult, CloneResult, SyncResult,
    DeltaInfo, OperationStatus, SSHConnectionInfo, TransferStats,
    ResourceInfo
)


class TestEnums:
    """Test enum definitions."""
    
    def test_vm_state_enum_values(self):
        """Test VMState enum has all expected values."""
        assert VMState.RUNNING.value == "running"
        assert VMState.STOPPED.value == "stopped"
        assert VMState.PAUSED.value == "paused"
        assert VMState.SUSPENDED.value == "suspended"
        assert VMState.UNKNOWN.value == "unknown"
    
    def test_vm_state_enum_membership(self):
        """Test VMState enum membership checks."""
        assert VMState.RUNNING in VMState
        assert VMState.STOPPED in VMState
        states = [s for s in VMState]
        assert len(states) == 5
    
    def test_operation_type_enum_values(self):
        """Test OperationType enum has all expected values."""
        assert OperationType.CLONE.value == "clone"
        assert OperationType.SYNC.value == "sync"
        assert OperationType.LIST.value == "list"
    
    def test_operation_type_enum_comparison(self):
        """Test OperationType enum comparisons."""
        assert OperationType.CLONE == OperationType.CLONE
        assert OperationType.CLONE != OperationType.SYNC
    
    def test_operation_status_enum_values(self):
        """Test OperationStatusEnum has all expected values."""
        assert OperationStatusEnum.PENDING.value == "pending"
        assert OperationStatusEnum.RUNNING.value == "running"
        assert OperationStatusEnum.COMPLETED.value == "completed"
        assert OperationStatusEnum.FAILED.value == "failed"
        assert OperationStatusEnum.CANCELLED.value == "cancelled"
    
    def test_operation_status_enum_iteration(self):
        """Test OperationStatusEnum can be iterated."""
        statuses = list(OperationStatusEnum)
        assert len(statuses) == 5
        assert OperationStatusEnum.PENDING in statuses


class TestDiskInfo:
    """Test DiskInfo dataclass."""
    
    def test_disk_info_creation(self):
        """Test DiskInfo can be created with required fields."""
        disk = DiskInfo(
            path="/var/lib/libvirt/images/disk1.qcow2",
            size=10737418240,
            format="qcow2",
            target="vda"
        )
        assert disk.path == "/var/lib/libvirt/images/disk1.qcow2"
        assert disk.size == 10737418240
        assert disk.format == "qcow2"
        assert disk.target == "vda"
        assert disk.backing_file is None
    
    def test_disk_info_with_backing_file(self):
        """Test DiskInfo with backing file specified."""
        disk = DiskInfo(
            path="/path/to/overlay.qcow2",
            size=1024,
            format="qcow2",
            target="vdb",
            backing_file="/path/to/base.qcow2"
        )
        assert disk.backing_file == "/path/to/base.qcow2"
    
    def test_disk_info_equality(self):
        """Test DiskInfo equality comparison."""
        disk1 = DiskInfo("/path", 1000, "raw", "vda")
        disk2 = DiskInfo("/path", 1000, "raw", "vda")
        assert disk1 == disk2
    
    def test_disk_info_inequality(self):
        """Test DiskInfo inequality comparison."""
        disk1 = DiskInfo("/path1", 1000, "raw", "vda")
        disk2 = DiskInfo("/path2", 1000, "raw", "vda")
        assert disk1 != disk2


class TestNetworkInfo:
    """Test NetworkInfo dataclass."""
    
    def test_network_info_creation(self):
        """Test NetworkInfo can be created with required fields."""
        network = NetworkInfo(
            interface="eth0",
            mac_address="52:54:00:12:34:56",
            network="default"
        )
        assert network.interface == "eth0"
        assert network.mac_address == "52:54:00:12:34:56"
        assert network.network == "default"
        assert network.ip_address is None
        assert network.bridge is None
    
    def test_network_info_with_optional_fields(self):
        """Test NetworkInfo with optional fields."""
        network = NetworkInfo(
            interface="eth1",
            mac_address="52:54:00:AB:CD:EF",
            network="custom",
            ip_address="192.168.1.100",
            bridge="br0"
        )
        assert network.ip_address == "192.168.1.100"
        assert network.bridge == "br0"
    
    def test_network_info_mac_address_format(self):
        """Test NetworkInfo accepts various MAC address formats."""
        macs = [
            "52:54:00:12:34:56",
            "52-54-00-12-34-56",
            "525400123456"
        ]
        for mac in macs:
            network = NetworkInfo("eth0", mac, "default")
            assert network.mac_address == mac


class TestVMInfo:
    """Test VMInfo dataclass."""
    
    def test_vm_info_creation(self):
        """Test VMInfo can be created with all required fields."""
        now = datetime.now()
        vm = VMInfo(
            name="test-vm",
            uuid="12345678-1234-1234-1234-123456789012",
            state=VMState.RUNNING,
            memory=2048,
            vcpus=2,
            disks=[],
            networks=[],
            host="localhost",
            created=now,
            last_modified=now
        )
        assert vm.name == "test-vm"
        assert vm.uuid == "12345678-1234-1234-1234-123456789012"
        assert vm.state == VMState.RUNNING
        assert vm.memory == 2048
        assert vm.vcpus == 2
        assert vm.host == "localhost"
        assert vm.config_path is None
    
    def test_vm_info_with_disks_and_networks(self):
        """Test VMInfo with disks and networks."""
        disk = DiskInfo("/path", 1000, "raw", "vda")
        network = NetworkInfo("eth0", "52:54:00:12:34:56", "default")
        now = datetime.now()
        
        vm = VMInfo(
            name="full-vm",
            uuid="uuid-123",
            state=VMState.STOPPED,
            memory=4096,
            vcpus=4,
            disks=[disk],
            networks=[network],
            host="server1",
            created=now,
            last_modified=now
        )
        assert len(vm.disks) == 1
        assert len(vm.networks) == 1
        assert vm.disks[0] == disk
        assert vm.networks[0] == network
    
    def test_vm_info_with_config_path(self):
        """Test VMInfo with config path."""
        now = datetime.now()
        vm = VMInfo(
            name="vm",
            uuid="uuid",
            state=VMState.PAUSED,
            memory=1024,
            vcpus=1,
            disks=[],
            networks=[],
            host="host",
            created=now,
            last_modified=now,
            config_path="/etc/libvirt/qemu/vm.xml"
        )
        assert vm.config_path == "/etc/libvirt/qemu/vm.xml"


class TestCloneOptions:
    """Test CloneOptions dataclass."""
    
    def test_clone_options_defaults(self):
        """Test CloneOptions default values."""
        options = CloneOptions()
        assert options.new_name is None
        assert options.force is False
        assert options.dry_run is False
        assert options.parallel == 4
        assert options.compress is False
        assert options.verify is True
        assert options.preserve_mac is False
        assert options.network_config is None
    
    def test_clone_options_custom_values(self):
        """Test CloneOptions with custom values."""
        options = CloneOptions(
            new_name="cloned-vm",
            force=True,
            dry_run=True,
            parallel=8,
            compress=True,
            verify=False,
            preserve_mac=True,
            network_config={"bridge": "br0"}
        )
        assert options.new_name == "cloned-vm"
        assert options.force is True
        assert options.dry_run is True
        assert options.parallel == 8
        assert options.compress is True
        assert options.verify is False
        assert options.preserve_mac is True
        assert options.network_config == {"bridge": "br0"}
    
    def test_clone_options_partial_override(self):
        """Test CloneOptions with partial override."""
        options = CloneOptions(new_name="new-vm", parallel=16)
        assert options.new_name == "new-vm"
        assert options.parallel == 16
        assert options.force is False  # Default retained


class TestSyncOptions:
    """Test SyncOptions dataclass."""
    
    def test_sync_options_defaults(self):
        """Test SyncOptions default values."""
        options = SyncOptions()
        assert options.target_name is None
        assert options.checkpoint is False
        assert options.delta_only is True
        assert options.bandwidth_limit is None
    
    def test_sync_options_custom_values(self):
        """Test SyncOptions with custom values."""
        options = SyncOptions(
            target_name="target-vm",
            checkpoint=True,
            delta_only=False,
            bandwidth_limit="100M"
        )
        assert options.target_name == "target-vm"
        assert options.checkpoint is True
        assert options.delta_only is False
        assert options.bandwidth_limit == "100M"


class TestProgressInfo:
    """Test ProgressInfo dataclass."""
    
    def test_progress_info_creation(self):
        """Test ProgressInfo creation with all fields."""
        progress = ProgressInfo(
            operation_id="op-123",
            operation_type=OperationType.CLONE,
            progress_percent=50.0,
            bytes_transferred=5000000,
            total_bytes=10000000,
            speed=1000000.0,
            eta=300,
            status=OperationStatusEnum.RUNNING,
            message="Copying disk 1 of 2",
            current_file="/path/to/disk.img"
        )
        assert progress.operation_id == "op-123"
        assert progress.operation_type == OperationType.CLONE
        assert progress.progress_percent == 50.0
        assert progress.bytes_transferred == 5000000
        assert progress.total_bytes == 10000000
        assert progress.speed == 1000000.0
        assert progress.eta == 300
        assert progress.status == OperationStatusEnum.RUNNING
        assert progress.message == "Copying disk 1 of 2"
        assert progress.current_file == "/path/to/disk.img"
    
    def test_progress_info_optional_fields(self):
        """Test ProgressInfo with optional fields as None."""
        progress = ProgressInfo(
            operation_id="op-456",
            operation_type=OperationType.SYNC,
            progress_percent=0.0,
            bytes_transferred=0,
            total_bytes=1000,
            speed=0.0,
            eta=None,
            status=OperationStatusEnum.PENDING
        )
        assert progress.eta is None
        assert progress.message is None
        assert progress.current_file is None


class TestValidationResult:
    """Test ValidationResult dataclass."""
    
    def test_validation_result_valid(self):
        """Test ValidationResult for valid case."""
        result = ValidationResult(valid=True)
        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []
    
    def test_validation_result_with_errors(self):
        """Test ValidationResult with errors."""
        result = ValidationResult(
            valid=False,
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"]
        )
        assert result.valid is False
        assert len(result.errors) == 2
        assert len(result.warnings) == 1
        assert "Error 1" in result.errors
        assert "Warning 1" in result.warnings
    
    def test_validation_result_warnings_only(self):
        """Test ValidationResult with warnings but no errors."""
        result = ValidationResult(
            valid=True,
            warnings=["Minor issue"]
        )
        assert result.valid is True
        assert result.errors == []
        assert result.warnings == ["Minor issue"]


class TestCloneResult:
    """Test CloneResult dataclass."""
    
    def test_clone_result_success(self):
        """Test CloneResult for successful operation."""
        result = CloneResult(
            operation_id="op-789",
            success=True,
            vm_name="source-vm",
            new_vm_name="cloned-vm",
            source_host="host1",
            dest_host="host2",
            duration=300.5,
            bytes_transferred=10000000000
        )
        assert result.success is True
        assert result.vm_name == "source-vm"
        assert result.new_vm_name == "cloned-vm"
        assert result.duration == 300.5
        assert result.bytes_transferred == 10000000000
        assert result.error is None
        assert result.warnings == []
        assert result.validation is None
    
    def test_clone_result_with_error(self):
        """Test CloneResult with error."""
        result = CloneResult(
            operation_id="op-fail",
            success=False,
            vm_name="vm",
            new_vm_name="vm-clone",
            source_host="h1",
            dest_host="h2",
            duration=10.0,
            bytes_transferred=0,
            error="Connection timeout"
        )
        assert result.success is False
        assert result.error == "Connection timeout"
    
    def test_clone_result_with_validation(self):
        """Test CloneResult with validation result."""
        validation = ValidationResult(valid=True, warnings=["Minor issue"])
        result = CloneResult(
            operation_id="op-val",
            success=True,
            vm_name="vm",
            new_vm_name="vm-clone",
            source_host="h1",
            dest_host="h2",
            duration=100.0,
            bytes_transferred=5000,
            validation=validation
        )
        assert result.validation == validation
        assert result.validation.warnings == ["Minor issue"]


class TestSyncResult:
    """Test SyncResult dataclass."""
    
    def test_sync_result_success(self):
        """Test SyncResult for successful operation."""
        result = SyncResult(
            operation_id="sync-123",
            success=True,
            vm_name="vm1",
            source_host="host1",
            dest_host="host2",
            duration=150.0,
            bytes_transferred=5000000,
            blocks_synchronized=1000
        )
        assert result.success is True
        assert result.vm_name == "vm1"
        assert result.blocks_synchronized == 1000
        assert result.error is None
    
    def test_sync_result_with_error(self):
        """Test SyncResult with error."""
        result = SyncResult(
            operation_id="sync-fail",
            success=False,
            vm_name="vm",
            source_host="h1",
            dest_host="h2",
            duration=5.0,
            bytes_transferred=0,
            blocks_synchronized=0,
            error="VM not found"
        )
        assert result.success is False
        assert result.error == "VM not found"


class TestDeltaInfo:
    """Test DeltaInfo dataclass."""
    
    def test_delta_info_creation(self):
        """Test DeltaInfo with all fields."""
        delta = DeltaInfo(
            total_size=10000000,
            changed_size=1000000,
            changed_blocks=100,
            files_changed=["/path/file1", "/path/file2"],
            estimated_transfer_time=60.0
        )
        assert delta.total_size == 10000000
        assert delta.changed_size == 1000000
        assert delta.changed_blocks == 100
        assert len(delta.files_changed) == 2
        assert delta.estimated_transfer_time == 60.0
    
    def test_delta_info_no_changes(self):
        """Test DeltaInfo with no changes."""
        delta = DeltaInfo(
            total_size=10000,
            changed_size=0,
            changed_blocks=0,
            files_changed=[],
            estimated_transfer_time=0.0
        )
        assert delta.changed_size == 0
        assert delta.files_changed == []


class TestOperationStatus:
    """Test OperationStatus dataclass."""
    
    def test_operation_status_creation(self):
        """Test OperationStatus with basic fields."""
        status = OperationStatus(
            operation_id="op-001",
            operation_type=OperationType.CLONE,
            status=OperationStatusEnum.RUNNING
        )
        assert status.operation_id == "op-001"
        assert status.operation_type == OperationType.CLONE
        assert status.status == OperationStatusEnum.RUNNING
        assert status.progress is None
        assert status.result is None
        assert status.error is None
        assert status.started is None
        assert status.completed is None
        assert isinstance(status.created, datetime)
    
    def test_operation_status_with_progress(self):
        """Test OperationStatus with progress info."""
        progress = ProgressInfo(
            operation_id="op-002",
            operation_type=OperationType.SYNC,
            progress_percent=75.0,
            bytes_transferred=7500,
            total_bytes=10000,
            speed=1000.0,
            eta=25,
            status=OperationStatusEnum.RUNNING
        )
        status = OperationStatus(
            operation_id="op-002",
            operation_type=OperationType.SYNC,
            status=OperationStatusEnum.RUNNING,
            progress=progress
        )
        assert status.progress == progress
        assert status.progress.progress_percent == 75.0
    
    def test_operation_status_completed_with_result(self):
        """Test OperationStatus for completed operation."""
        result = CloneResult(
            operation_id="op-003",
            success=True,
            vm_name="vm",
            new_vm_name="vm-clone",
            source_host="h1",
            dest_host="h2",
            duration=200.0,
            bytes_transferred=10000
        )
        now = datetime.now()
        status = OperationStatus(
            operation_id="op-003",
            operation_type=OperationType.CLONE,
            status=OperationStatusEnum.COMPLETED,
            result=result,
            started=now,
            completed=now
        )
        assert status.status == OperationStatusEnum.COMPLETED
        assert status.result == result
        assert status.started is not None
        assert status.completed is not None


class TestSSHConnectionInfo:
    """Test SSHConnectionInfo dataclass."""
    
    def test_ssh_connection_info_defaults(self):
        """Test SSHConnectionInfo default values."""
        info = SSHConnectionInfo(host="example.com")
        assert info.host == "example.com"
        assert info.port == 22
        assert info.username is None
        assert info.key_path is None
        assert info.timeout == 30
    
    def test_ssh_connection_info_custom_values(self):
        """Test SSHConnectionInfo with custom values."""
        info = SSHConnectionInfo(
            host="192.168.1.100",
            port=2222,
            username="admin",
            key_path="/home/user/.ssh/id_rsa",
            timeout=60
        )
        assert info.host == "192.168.1.100"
        assert info.port == 2222
        assert info.username == "admin"
        assert info.key_path == "/home/user/.ssh/id_rsa"
        assert info.timeout == 60


class TestTransferStats:
    """Test TransferStats dataclass."""
    
    def test_transfer_stats_defaults(self):
        """Test TransferStats default values."""
        stats = TransferStats()
        assert stats.bytes_transferred == 0
        assert stats.files_transferred == 0
        assert stats.start_time is None
        assert stats.end_time is None
        assert stats.average_speed == 0.0
        assert stats.peak_speed == 0.0
    
    def test_transfer_stats_with_data(self):
        """Test TransferStats with actual data."""
        start = datetime.now()
        end = datetime.now()
        stats = TransferStats(
            bytes_transferred=10000000,
            files_transferred=5,
            start_time=start,
            end_time=end,
            average_speed=1000000.0,
            peak_speed=2000000.0
        )
        assert stats.bytes_transferred == 10000000
        assert stats.files_transferred == 5
        assert stats.average_speed == 1000000.0
        assert stats.peak_speed == 2000000.0


class TestResourceInfo:
    """Test ResourceInfo dataclass."""
    
    def test_resource_info_creation(self):
        """Test ResourceInfo with all fields."""
        info = ResourceInfo(
            total_memory=16384,
            available_memory=8192,
            total_disk=1000000000000,
            available_disk=500000000000,
            cpu_count=8,
            cpu_usage=45.5
        )
        assert info.total_memory == 16384
        assert info.available_memory == 8192
        assert info.total_disk == 1000000000000
        assert info.available_disk == 500000000000
        assert info.cpu_count == 8
        assert info.cpu_usage == 45.5
    
    def test_resource_info_calculations(self):
        """Test resource calculations."""
        info = ResourceInfo(
            total_memory=8192,
            available_memory=4096,
            total_disk=1000000,
            available_disk=500000,
            cpu_count=4,
            cpu_usage=50.0
        )
        # Memory usage percentage
        mem_usage = ((info.total_memory - info.available_memory) / info.total_memory) * 100
        assert mem_usage == 50.0
        
        # Disk usage percentage
        disk_usage = ((info.total_disk - info.available_disk) / info.total_disk) * 100
        assert disk_usage == 50.0


class TestDataclassImmutability:
    """Test that dataclasses can be modified (they are not frozen by default)."""
    
    def test_disk_info_is_mutable(self):
        """Test DiskInfo fields can be modified."""
        disk = DiskInfo("/path", 1000, "raw", "vda")
        disk.size = 2000
        assert disk.size == 2000
    
    def test_clone_options_is_mutable(self):
        """Test CloneOptions fields can be modified."""
        options = CloneOptions()
        options.parallel = 8
        assert options.parallel == 8


class TestDataclassEquality:
    """Test dataclass equality comparisons."""
    
    def test_identical_disk_info_objects_are_equal(self):
        """Test two DiskInfo objects with same data are equal."""
        disk1 = DiskInfo("/path", 1000, "raw", "vda")
        disk2 = DiskInfo("/path", 1000, "raw", "vda")
        assert disk1 == disk2
    
    def test_different_disk_info_objects_are_not_equal(self):
        """Test two DiskInfo objects with different data are not equal."""
        disk1 = DiskInfo("/path1", 1000, "raw", "vda")
        disk2 = DiskInfo("/path2", 1000, "raw", "vda")
        assert disk1 != disk2