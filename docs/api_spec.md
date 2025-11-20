# API Specification - KVM Cloning over SSH

## Overview

This document provides the complete API specification for the KVM Cloning over SSH tool, including both the command-line interface (CLI) and Python library components. The tool enables secure cloning and synchronization of KVM virtual machines between hosts using libvirt API over SSH connections.

## Table of Contents

1. [CLI Interface Specification](#cli-interface-specification)
2. [Python Library Specification](#python-library-specification)  
3. [Error Codes](#error-codes)
4. [JSON Output Schemas](#json-output-schemas)
5. [Input Validation Rules](#input-validation-rules)

---

## CLI Interface Specification

### Command Synopsis

```
kvm-clone [OPTIONS] COMMAND [ARGS]...
```

### Global Options

| Option | Short | Type | Required | Default | Description |
|--------|-------|------|----------|---------|-------------|
| `--config` | `-c` | path | No | `~/.kvm-clone/config.yaml` | Configuration file path |
| `--verbose` | `-v` | flag | No | False | Enable verbose logging |
| `--quiet` | `-q` | flag | No | False | Suppress non-error output |
| `--output` | `-o` | choice | No | `text` | Output format: `text`, `json`, `yaml` |
| `--log-level` | | choice | No | `INFO` | Log level: `DEBUG`, `INFO`, `WARN`, `ERROR` |
| `--help` | `-h` | flag | No | False | Show help message |
| `--version` | | flag | No | False | Show version information |

### Commands

#### 1. clone

Clone a virtual machine from source to destination host.

```
kvm-clone clone [OPTIONS] SOURCE_HOST DEST_HOST VM_NAME
```

**Positional Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `SOURCE_HOST` | string | Yes | Source host (hostname or IP) |
| `DEST_HOST` | string | Yes | Destination host (hostname or IP) |
| `VM_NAME` | string | Yes | Name of VM to clone |

**Options:**

| Option | Short | Type | Required | Default | Description |
|--------|-------|------|----------|---------|-------------|
| `--new-name` | `-n` | string | No | `{VM_NAME}_clone` | Name for cloned VM |
| `--force` | `-f` | flag | No | False | Overwrite existing VM |
| `--dry-run` | | flag | No | False | Show what would be done |
| `--parallel` | `-p` | integer | No | 4 | Number of parallel transfers |
| `--compress` | | flag | No | False | Enable compression during transfer |
| `--verify` | | flag | No | True | Verify integrity after transfer |
| `--timeout` | | integer | No | 3600 | Operation timeout in seconds |
| `--ssh-key` | `-k` | path | No | `~/.ssh/id_rsa` | SSH private key path |
| `--ssh-port` | | integer | No | 22 | SSH port |
| `--preserve-mac` | | flag | No | False | Preserve MAC addresses |
| `--network-config` | | path | No | | Custom network configuration file |

**Examples:**

```bash
# Basic clone
kvm-clone clone host1 host2 vm-production

# Clone with new name and compression
kvm-clone clone --new-name vm-staging --compress host1 host2 vm-production

# Force overwrite existing VM
kvm-clone clone --force --new-name vm-backup host1 host2 vm-production
```

#### 2. sync

Synchronize an existing VM between hosts (incremental transfer).

```
kvm-clone sync [OPTIONS] SOURCE_HOST DEST_HOST VM_NAME
```

**Positional Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `SOURCE_HOST` | string | Yes | Source host (hostname or IP) |
| `DEST_HOST` | string | Yes | Destination host (hostname or IP) |
| `VM_NAME` | string | Yes | Name of VM to synchronize |

**Options:**

| Option | Short | Type | Required | Default | Description |
|--------|-------|------|----------|---------|-------------|
| `--target-name` | `-t` | string | No | `{VM_NAME}` | Target VM name on destination |
| `--checkpoint` | | flag | No | False | Create checkpoint before sync |
| `--delta-only` | | flag | No | True | Transfer only changed blocks |
| `--bandwidth-limit` | `-b` | string | No | | Bandwidth limit (e.g., '100M', '1G') |
| `--ssh-key` | `-k` | path | No | `~/.ssh/id_rsa` | SSH private key path |
| `--timeout` | | integer | No | 7200 | Operation timeout in seconds |

#### 3. list

List virtual machines on specified hosts.

```
kvm-clone list [OPTIONS] [HOST...]
```

**Positional Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `HOST` | string | No | Host(s) to query (default: local) |

**Options:**

| Option | Short | Type | Required | Default | Description |
|--------|-------|------|----------|---------|-------------|
| `--status` | `-s` | choice | No | `all` | Filter by status: `all`, `running`, `stopped`, `paused` |
| `--format` | | choice | No | `table` | Output format: `table`, `list`, `json` |
| `--ssh-key` | `-k` | path | No | `~/.ssh/id_rsa` | SSH private key path |

#### 4. status

Check status of clone/sync operations.

```
kvm-clone status [OPTIONS] [OPERATION_ID]
```

**Positional Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `OPERATION_ID` | string | No | Specific operation ID to check |

**Options:**

| Option | Short | Type | Required | Default | Description |
|--------|-------|------|----------|---------|-------------|
| `--all` | `-a` | flag | No | False | Show all operations |
| `--active` | | flag | No | False | Show only active operations |
| `--follow` | `-f` | flag | No | False | Follow operation progress |

#### 5. config

Manage configuration settings.

```
kvm-clone config SUBCOMMAND [OPTIONS]
```

**Subcommands:**

- `show` - Display current configuration
- `set KEY VALUE` - Set configuration value
- `unset KEY` - Remove configuration value
- `init` - Initialize default configuration

---

## Python Library Specification

### Module Structure

```
kvm_clone/
├── __init__.py
├── client.py          # Main client class
├── cloner.py          # VM cloning logic
├── sync.py            # VM synchronization logic
├── transport.py       # SSH transport layer
├── libvirt_wrapper.py # Libvirt API wrapper
├── exceptions.py      # Custom exceptions
└── models.py          # Data models
```

### Core Classes

#### KVMCloneClient

Main client class for interacting with the KVM cloning functionality.

```python
class KVMCloneClient:
    """
    Main client for KVM cloning operations.
    
    Args:
        config (Optional[Dict[str, Any]]): Configuration dictionary
        ssh_key_path (Optional[str]): Path to SSH private key
        timeout (int): Default operation timeout in seconds
        
    Attributes:
        config (Dict[str, Any]): Current configuration
        timeout (int): Operation timeout
        
    Raises:
        ConfigurationError: If configuration is invalid
        ConnectionError: If unable to establish connections
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        ssh_key_path: Optional[str] = None,
        timeout: int = 3600
    ) -> None: ...
    
    def clone_vm(
        self,
        source_host: str,
        dest_host: str,
        vm_name: str,
        *,
        new_name: Optional[str] = None,
        force: bool = False,
        dry_run: bool = False,
        parallel: int = 4,
        compress: bool = False,
        verify: bool = True,
        preserve_mac: bool = False,
        network_config: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[ProgressInfo], None]] = None
    ) -> CloneResult: ...
    
    def sync_vm(
        self,
        source_host: str,
        dest_host: str,
        vm_name: str,
        *,
        target_name: Optional[str] = None,
        checkpoint: bool = False,
        delta_only: bool = True,
        bandwidth_limit: Optional[str] = None,
        progress_callback: Optional[Callable[[ProgressInfo], None]] = None
    ) -> SyncResult: ...
    
    def list_vms(
        self,
        hosts: List[str],
        *,
        status_filter: Optional[str] = None
    ) -> Dict[str, List[VMInfo]]: ...
    
    def get_operation_status(
        self,
        operation_id: str
    ) -> OperationStatus: ...
    
    def cancel_operation(
        self,
        operation_id: str
    ) -> bool: ...
    
    def cleanup_failed_operations(self) -> List[str]: ...
```

#### VMCloner

Handles the actual VM cloning process.

```python
class VMCloner:
    """
    Handles VM cloning operations.
    
    Args:
        transport (SSHTransport): SSH transport instance
        libvirt_wrapper (LibvirtWrapper): Libvirt wrapper instance
        
    Attributes:
        transport (SSHTransport): SSH transport
        libvirt (LibvirtWrapper): Libvirt wrapper
    """
    
    def __init__(
        self,
        transport: SSHTransport,
        libvirt_wrapper: LibvirtWrapper
    ) -> None: ...
    
    async def clone(
        self,
        source_host: str,
        dest_host: str,
        vm_name: str,
        clone_options: CloneOptions
    ) -> CloneResult: ...
    
    async def validate_prerequisites(
        self,
        source_host: str,
        dest_host: str,
        vm_name: str
    ) -> ValidationResult: ...
```

#### VMSynchronizer

Handles VM synchronization operations.

```python
class VMSynchronizer:
    """
    Handles VM synchronization operations.
    
    Args:
        transport (SSHTransport): SSH transport instance
        libvirt_wrapper (LibvirtWrapper): Libvirt wrapper instance
        
    Attributes:
        transport (SSHTransport): SSH transport
        libvirt (LibvirtWrapper): Libvirt wrapper
    """
    
    def __init__(
        self,
        transport: SSHTransport,
        libvirt_wrapper: LibvirtWrapper
    ) -> None: ...
    
    async def sync(
        self,
        source_host: str,
        dest_host: str,
        vm_name: str,
        sync_options: SyncOptions
    ) -> SyncResult: ...
    
    async def calculate_delta(
        self,
        source_host: str,
        dest_host: str,
        vm_name: str
    ) -> DeltaInfo: ...
```

### Data Models

```python
@dataclass
class VMInfo:
    """Virtual machine information."""
    name: str
    uuid: str
    state: str
    memory: int  # MB
    vcpus: int
    disks: List[DiskInfo]
    networks: List[NetworkInfo]
    host: str
    created: datetime
    last_modified: datetime

@dataclass
class DiskInfo:
    """Disk information."""
    path: str
    size: int  # bytes
    format: str
    target: str

@dataclass
class NetworkInfo:
    """Network interface information."""
    interface: str
    mac_address: str
    network: str
    ip_address: Optional[str] = None

@dataclass
class CloneOptions:
    """Options for cloning operations."""
    new_name: Optional[str] = None
    force: bool = False
    dry_run: bool = False
    parallel: int = 4
    compress: bool = False
    verify: bool = True
    preserve_mac: bool = False
    network_config: Optional[Dict[str, Any]] = None

@dataclass
class SyncOptions:
    """Options for sync operations."""
    target_name: Optional[str] = None
    checkpoint: bool = False
    delta_only: bool = True
    bandwidth_limit: Optional[str] = None

@dataclass
class ProgressInfo:
    """Progress information for operations."""
    operation_id: str
    operation_type: str
    progress_percent: float
    bytes_transferred: int
    total_bytes: int
    speed: float  # bytes/sec
    eta: Optional[int]  # seconds
    status: str
    message: Optional[str] = None

@dataclass
class CloneResult:
    """Result of clone operation."""
    operation_id: str
    success: bool
    vm_name: str
    new_vm_name: str
    source_host: str
    dest_host: str
    duration: float  # seconds
    bytes_transferred: int
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

@dataclass
class SyncResult:
    """Result of sync operation."""
    operation_id: str
    success: bool
    vm_name: str
    source_host: str
    dest_host: str
    duration: float  # seconds
    bytes_transferred: int
    blocks_synchronized: int
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

@dataclass
class OperationStatus:
    """Status of an operation."""
    operation_id: str
    operation_type: str
    status: str  # pending, running, completed, failed, cancelled
    progress: Optional[ProgressInfo] = None
    result: Optional[Union[CloneResult, SyncResult]] = None
    created: datetime
    started: Optional[datetime] = None
    completed: Optional[datetime] = None
```

### Exception Classes

```python
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
        super().__init__(f"VM '{vm_name}' already exists on host '{host}'", error_code=1004)
        self.vm_name = vm_name
        self.host = host

class InsufficientResourcesError(KVMCloneError):
    """Insufficient resources errors."""
    
    def __init__(self, message: str, resource_type: str) -> None:
        super().__init__(f"Insufficient {resource_type}: {message}", error_code=1005)
        self.resource_type = resource_type

class TransferError(KVMCloneError):
    """Data transfer errors."""
    
    def __init__(self, message: str) -> None:
        super().__init__(f"Transfer error: {message}", error_code=1006)

class ValidationError(KVMCloneError):
    """Input validation errors."""
    
    def __init__(self, message: str, field: str) -> None:
        super().__init__(f"Validation error for '{field}': {message}", error_code=1007)
        self.field = field

class OperationCancelledError(KVMCloneError):
    """Operation cancelled errors."""
    
    def __init__(self, operation_id: str) -> None:
        super().__init__(f"Operation '{operation_id}' was cancelled", error_code=1008)
        self.operation_id = operation_id

class LibvirtError(KVMCloneError):
    """Libvirt-related errors."""
    
    def __init__(self, message: str) -> None:
        super().__init__(f"Libvirt error: {message}", error_code=1009)
```

---

## Error Codes

### System Error Codes (1000-1099)

| Code | Name | Description |
|------|------|-------------|
| 1000 | `GENERAL_ERROR` | General unspecified error |
| 1001 | `CONFIGURATION_ERROR` | Invalid configuration |
| 1002 | `CONNECTION_ERROR` | Network/SSH connection error |
| 1003 | `VM_NOT_FOUND_ERROR` | Virtual machine not found |
| 1004 | `VM_EXISTS_ERROR` | Virtual machine already exists |
| 1005 | `INSUFFICIENT_RESOURCES_ERROR` | Insufficient system resources |
| 1006 | `TRANSFER_ERROR` | Data transfer failed |
| 1007 | `VALIDATION_ERROR` | Input validation failed |
| 1008 | `OPERATION_CANCELLED_ERROR` | Operation was cancelled |
| 1009 | `LIBVIRT_ERROR` | Libvirt API error |

### Authentication Error Codes (1100-1199)

| Code | Name | Description |
|------|------|-------------|
| 1100 | `AUTH_ERROR` | Authentication failed |
| 1101 | `SSH_KEY_ERROR` | SSH key not found or invalid |
| 1102 | `PERMISSION_DENIED` | Insufficient permissions |
| 1103 | `HOST_KEY_ERROR` | SSH host key verification failed |

### Operation Error Codes (1200-1299)

| Code | Name | Description |
|------|------|-------------|
| 1200 | `CLONE_ERROR` | Clone operation failed |
| 1201 | `SYNC_ERROR` | Sync operation failed |
| 1202 | `OPERATION_TIMEOUT` | Operation timed out |
| 1203 | `OPERATION_NOT_FOUND` | Operation ID not found |
| 1204 | `DISK_SPACE_ERROR` | Insufficient disk space |
| 1205 | `NETWORK_ERROR` | Network configuration error |

### Validation Error Codes (1300-1399)

| Code | Name | Description |
|------|------|-------------|
| 1300 | `INVALID_HOST` | Invalid hostname or IP address |
| 1301 | `INVALID_VM_NAME` | Invalid VM name format |
| 1302 | `INVALID_PATH` | Invalid file path |
| 1303 | `INVALID_PORT` | Invalid port number |
| 1304 | `INVALID_TIMEOUT` | Invalid timeout value |
| 1305 | `INVALID_BANDWIDTH` | Invalid bandwidth limit format |

---

## JSON Output Schemas

### Clone Operation Response

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Clone Operation Response",
  "type": "object",
  "properties": {
    "operation_id": {
      "type": "string",
      "description": "Unique operation identifier"
    },
    "success": {
      "type": "boolean",
      "description": "Whether operation succeeded"
    },
    "vm_name": {
      "type": "string",
      "description": "Source VM name"
    },
    "new_vm_name": {
      "type": "string",
      "description": "Cloned VM name"
    },
    "source_host": {
      "type": "string",
      "description": "Source host identifier"
    },
    "dest_host": {
      "type": "string",
      "description": "Destination host identifier"
    },
    "duration": {
      "type": "number",
      "description": "Operation duration in seconds"
    },
    "bytes_transferred": {
      "type": "integer",
      "minimum": 0,
      "description": "Total bytes transferred"
    },
    "error": {
      "type": ["string", "null"],
      "description": "Error message if operation failed"
    },
    "error_code": {
      "type": ["integer", "null"],
      "description": "Error code if operation failed"
    },
    "warnings": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Warning messages"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "Operation completion timestamp"
    }
  },
  "required": ["operation_id", "success", "vm_name", "source_host", "dest_host", "duration", "bytes_transferred", "timestamp"],
  "additionalProperties": false
}
```

### VM List Response

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "VM List Response",
  "type": "object",
  "patternProperties": {
    "^.+$": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string",
            "description": "VM name"
          },
          "uuid": {
            "type": "string",
            "description": "VM UUID"
          },
          "state": {
            "type": "string",
            "enum": ["running", "stopped", "paused", "suspended", "crashed"],
            "description": "VM state"
          },
          "memory": {
            "type": "integer",
            "minimum": 0,
            "description": "Memory in MB"
          },
          "vcpus": {
            "type": "integer",
            "minimum": 1,
            "description": "Number of virtual CPUs"
          },
          "disks": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "path": {
                  "type": "string",
                  "description": "Disk image path"
                },
                "size": {
                  "type": "integer",
                  "minimum": 0,
                  "description": "Disk size in bytes"
                },
                "format": {
                  "type": "string",
                  "enum": ["qcow2", "raw", "vmdk", "vdi"],
                  "description": "Disk format"
                },
                "target": {
                  "type": "string",
                  "description": "Target device (e.g., vda, sda)"
                }
              },
              "required": ["path", "size", "format", "target"]
            }
          },
          "networks": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "interface": {
                  "type": "string",
                  "description": "Interface name"
                },
                "mac_address": {
                  "type": "string",
                  "pattern": "^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$",
                  "description": "MAC address"
                },
                "network": {
                  "type": "string",
                  "description": "Network name"
                },
                "ip_address": {
                  "type": ["string", "null"],
                  "description": "IP address if available"
                }
              },
              "required": ["interface", "mac_address", "network"]
            }
          },
          "host": {
            "type": "string",
            "description": "Host where VM resides"
          },
          "created": {
            "type": "string",
            "format": "date-time",
            "description": "VM creation timestamp"
          },
          "last_modified": {
            "type": "string",
            "format": "date-time",
            "description": "Last modification timestamp"
          }
        },
        "required": ["name", "uuid", "state", "memory", "vcpus", "disks", "networks", "host", "created", "last_modified"]
      }
    }
  },
  "additionalProperties": false
}
```

### Operation Status Response

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Operation Status Response",
  "type": "object",
  "properties": {
    "operation_id": {
      "type": "string",
      "description": "Operation identifier"
    },
    "operation_type": {
      "type": "string",
      "enum": ["clone", "sync"],
      "description": "Type of operation"
    },
    "status": {
      "type": "string",
      "enum": ["pending", "running", "completed", "failed", "cancelled"],
      "description": "Current operation status"
    },
    "progress": {
      "type": ["object", "null"],
      "properties": {
        "progress_percent": {
          "type": "number",
          "minimum": 0,
          "maximum": 100,
          "description": "Progress percentage"
        },
        "bytes_transferred": {
          "type": "integer",
          "minimum": 0,
          "description": "Bytes transferred so far"
        },
        "total_bytes": {
          "type": "integer",
          "minimum": 0,
          "description": "Total bytes to transfer"
        },
        "speed": {
          "type": "number",
          "minimum": 0,
          "description": "Transfer speed in bytes/sec"
        },
        "eta": {
          "type": ["integer", "null"],
          "minimum": 0,
          "description": "Estimated time to completion in seconds"
        },
        "message": {
          "type": ["string", "null"],
          "description": "Current operation message"
        }
      },
      "required": ["progress_percent", "bytes_transferred", "total_bytes", "speed"]
    },
    "created": {
      "type": "string",
      "format": "date-time",
      "description": "Operation creation timestamp"
    },
    "started": {
      "type": ["string", "null"],
      "format": "date-time",
      "description": "Operation start timestamp"
    },
    "completed": {
      "type": ["string", "null"],
      "format": "date-time",
      "description": "Operation completion timestamp"
    },
    "result": {
      "type": ["object", "null"],
      "description": "Operation result if completed"
    }
  },
  "required": ["operation_id", "operation_type", "status", "created"],
  "additionalProperties": false
}
```

### Error Response

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Error Response",
  "type": "object",
  "properties": {
    "error": {
      "type": "object",
      "properties": {
        "code": {
          "type": "integer",
          "description": "Error code"
        },
        "message": {
          "type": "string",
          "description": "Error message"
        },
        "details": {
          "type": ["object", "null"],
          "description": "Additional error details"
        },
        "field": {
          "type": ["string", "null"],
          "description": "Field name for validation errors"
        }
      },
      "required": ["code", "message"]
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "Error timestamp"
    },
    "operation_id": {
      "type": ["string", "null"],
      "description": "Operation ID if applicable"
    }
  },
  "required": ["error", "timestamp"],
  "additionalProperties": false
}
```

---

## Input Validation Rules

### Host Validation

- **Format**: Must be valid hostname, FQDN, or IP address
- **Length**: 1-255 characters
- **Pattern**: `^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$` (hostname) or valid IP
- **Reachability**: Must be reachable via SSH

### VM Name Validation

- **Format**: Alphanumeric characters, hyphens, underscores
- **Length**: 1-64 characters
- **Pattern**: `^[a-zA-Z0-9_-]+$`
- **Reserved**: Cannot be "localhost", "none", "all"
- **Uniqueness**: Must be unique on destination host (unless `--force` used)

### Path Validation

- **SSH Key Path**:
  - Must be absolute path
  - File must exist and be readable
  - Must have appropriate permissions (600 or 400)
  - Must be valid SSH private key format

- **Config File Path**:
  - Must be absolute path
  - Directory must exist and be writable
  - Must be valid YAML format

### Network Configuration Validation

- **MAC Address**: Must match pattern `^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$`
- **IP Address**: Must be valid IPv4 or IPv6 address
- **Port**: Must be integer between 1-65535
- **Bandwidth Limit**: Must match pattern `^\d+[KMGT]?$` (e.g., "100M", "1G")

### Numeric Validation

- **Timeout**: Must be positive integer (1-86400 seconds)
- **Parallel Transfers**: Must be integer between 1-16
- **SSH Port**: Must be integer between 1-65535
- **Memory**: Must be positive integer (MB)
- **VCPUs**: Must be positive integer (1-128)

### Operation Validation

- **Source and Destination**: Must be different hosts
- **VM State**: Source VM must be in valid state for cloning/sync
- **Disk Space**: Destination must have sufficient free space
- **Permissions**: User must have appropriate libvirt permissions
- **SSH Access**: Must be able to establish SSH connections to both hosts

### Configuration Validation

Configuration files must be valid YAML with the following structure:

```yaml
# ~/.kvm-clone/config.yaml
ssh:
  key_path: "~/.ssh/id_rsa"
  port: 22
  timeout: 30
  
transfer:
  parallel: 4
  compress: false
  verify: true
  bandwidth_limit: null
  
libvirt:
  uri: "qemu:///system"
  timeout: 60
  
logging:
  level: "INFO"
  file: "~/.kvm-clone/logs/kvm-clone.log"
  max_size: "10MB"
  backup_count: 5
```

All configuration values are validated according to their respective rules above.

---

This specification provides a complete contract for both CLI and Python library interfaces, including comprehensive error handling, validation rules, and machine-readable JSON schemas for integration purposes.
