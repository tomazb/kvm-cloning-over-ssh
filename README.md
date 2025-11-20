# KVM Cloning over SSH

A tool for copying/syncing KVM virtual machines from one machine to another using libvirt API over SSH.

This project provides functionality to clone and synchronize KVM virtual machines between different hosts by leveraging the libvirt API through SSH connections. The code uses the fastest method to achieve reliable VM transfer between machines.

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/tomazb/kvm-cloning-over-ssh.git
cd kvm-cloning-over-ssh

# Install dependencies (includes CLI entry point)
poetry install
```

### Basic Usage

```bash
# Clone a VM from one host to another
kvm-clone clone source-host dest-host vm-name

# Clone with custom name
kvm-clone clone source-host dest-host vm-name --new-name my-vm

# Idempotent clone (safe for automation/CI-CD)
kvm-clone clone source-host dest-host vm-name --idempotent

# Clone with bandwidth limit
kvm-clone clone source-host dest-host vm-name --bandwidth-limit 100M

# Synchronize an existing VM (incremental update)
kvm-clone sync source-host dest-host vm-name

# List VMs on hosts
kvm-clone list host1 host2

# Get help
kvm-clone --help
```

### Advanced Usage Examples

```bash
# Safe retry in automation - automatically cleans up on conflict
kvm-clone clone source dest vm --idempotent

# If the operation fails or is interrupted, just retry
# The --idempotent flag ensures clean state
kvm-clone clone source dest vm --idempotent

# Use in CI/CD pipelines with environment variables
export KVM_CLONE_SSH_KEY_PATH=/path/to/key
export KVM_CLONE_SSH_HOST_KEY_POLICY=auto_add  # For new hosts
kvm-clone clone source dest vm --idempotent

# Batch clone multiple VMs with safe retry
for vm in $(virsh list --all --name); do
  kvm-clone clone source dest "$vm" --idempotent || true
done

# Clone with all safety features
kvm-clone clone source dest vm \
  --idempotent \
  --bandwidth-limit 500M \
  --preserve-mac \
  --timeout 7200
```

## 📋 Features

### ✅ Implemented
- **Complete VM Cloning** - Full VM cloning between hosts with disk images and configuration
- **Incremental Synchronization** - Delta-based sync for efficient updates
- **SSH Transport** - Secure transfers using SSH with key-based authentication
- **Libvirt Integration** - Native libvirt API support for VM management
- **CLI Interface** - Comprehensive command-line interface with all major operations
- **Async Operations** - Non-blocking operations with progress tracking
- **Configuration Management** - YAML-based configuration files
- **Error Handling** - Robust error handling with detailed error messages
- **Type Safety** - Full type annotations for better development experience

### 🔒 Security (Phase 1 - COMPLETED ✅)
- **Command Injection Protection** - All shell commands use secure parameter quoting
- **SSH Security Hardening** - Secure host key verification (no auto-accept)
- **Path Traversal Prevention** - File path validation and sanitization
- **Input Validation** - Comprehensive validation for VM names, hostnames, and paths
- **Security Test Suite** - Dedicated security tests ensuring vulnerability protection

### 🎯 Code Quality (Phase 2 - COMPLETED ✅)
- **Structured Logging** - JSON-formatted logs with timestamps and context
- **Error Handling** - Specific exception handling with proper chaining
- **Configuration Validation** - Type-safe configuration loading and validation
- **Resource Management** - Proper cleanup in error conditions

### 🌐 Real-World Usability (Phase 3 - COMPLETED ✅)
- **SSH Infrastructure Integration** - Full SSH config file support (~/.ssh/config)
- **SSH Agent Support** - Automatic SSH agent authentication
- **Connection Retry Logic** - Exponential backoff for transient failures (1s, 2s, 4s)
- **Environment Variable Overrides** - Configure via env vars (KVM_CLONE_SSH_KEY_PATH, etc.)
- **Enhanced Error Messages** - Actionable error messages with step-by-step remediation
- **Bandwidth Limiting** - Control transfer speed with --bandwidth-limit flag
- **Comprehensive Config CLI** - Full config management (init/get/set/unset/list/path)
- **Username Auto-Detection** - Smart username resolution (SSH config > env > current user)

### 🛡️ Data Safety & Robustness (Phase 4 - COMPLETED ✅)
- **Disk Space Verification** - Pre-flight checks prevent out-of-space failures
  - Queries storage pools for available space
  - Calculates required space with 15% safety margin
  - Fails fast with clear error messages before starting long operations
- **Transactional Cloning** - Atomic operations with automatic rollback
  - Staging directory for temporary files
  - All-or-nothing commits (no partial clones on failure)
  - Automatic cleanup of all resources on any error
  - Transaction logs for debugging failures
- **Idempotent Operations** - Safe retry without manual cleanup
  - `--idempotent` flag for automation and CI/CD
  - Auto-detect and cleanup existing VMs before retry
  - Comprehensive audit logging of all actions
  - Operations produce same result on retry

### 🚧 In Development
- **Enhanced Test Coverage** - Expanding test suite to reach 90% coverage
- **Checksum Validation** - Data integrity verification after transfers
- **Operation Timeouts** - Prevent indefinite hangs with configurable timeouts
- **Advanced Features** - Resume capability, compression

## 🏗️ Architecture

The project follows a modular architecture:

```
src/kvm_clone/
├── client.py          # Main client class (KVMCloneClient)
├── cloner.py          # VM cloning operations
├── sync.py            # VM synchronization operations
├── transport.py       # SSH transport layer
├── libvirt_wrapper.py # Libvirt API wrapper
├── transaction.py     # Transaction management for atomic operations
├── models.py          # Data models and structures
├── exceptions.py      # Custom exceptions
├── security.py        # Security utilities and validation
├── config.py          # Configuration loading and validation
├── logging.py         # Structured JSON logging
└── cli.py             # Command-line interface
```

## 📖 Documentation

- **[API Specification](docs/api_spec.md)** - Complete API documentation
- **[TODO](TODO.md)** - Current status and roadmap

### Implementation Guides
- **[Phase 4: Data Safety & Robustness](docs/PHASE4_DATA_SAFETY.md)** - Critical safety features guide
- **[Phase 3: Real-World Improvements](docs/REAL_WORLD_IMPROVEMENTS.md)** - Usability enhancements
- **[Idempotency Analysis](docs/IDEMPOTENCY_ANALYSIS.md)** - Idempotent operations design

### Project Documentation
- **[Technical Specification](docs/technical_spec.md)** - Architecture and design details
- **[Security Report](docs/SECURITY_FIXES_REPORT.md)** - Security fixes and improvements
- **[Contributing](docs/CONTRIBUTING.md)** - How to contribute to the project
- **[Changelog](docs/CHANGELOG.md)** - Version history and changes

## 🔧 Development

### Requirements

- Python 3.10+
- Poetry for dependency management
- libvirt development libraries
- SSH access to target hosts

### Setting up Development Environment

```bash
# Clone and switch to develop branch
git clone https://github.com/tomazb/kvm-cloning-over-ssh.git
cd kvm-cloning-over-ssh
git checkout develop

# Install dependencies
poetry install

# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src/kvm_clone

# Install pre-commit hooks (when available)
pre-commit install
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run specific test categories
poetry run pytest -m unit
poetry run pytest -m integration
poetry run pytest -m slow

# Run with coverage report
poetry run pytest --cov=src/kvm_clone --cov-report=html
```

## 🌟 Usage Examples

### Clone a VM

```bash
# Basic clone
kvm-clone clone source.example.com dest.example.com my-vm

# Clone with custom name and compression
kvm-clone clone source.example.com dest.example.com my-vm \
  --new-name my-vm-backup \
  --compress \
  --verify

# Force overwrite existing VM
kvm-clone clone source.example.com dest.example.com my-vm \
  --force \
  --new-name existing-vm
```

### Synchronize VMs

```bash
# Basic sync
kvm-clone sync source.example.com dest.example.com my-vm

# Sync with bandwidth limit and checkpoint
kvm-clone sync source.example.com dest.example.com my-vm \
  --bandwidth-limit 100M \
  --checkpoint
```

### List and Manage VMs

```bash
# List all VMs on multiple hosts
kvm-clone list host1.example.com host2.example.com

# List only running VMs
kvm-clone list host1.example.com --status running

# Output as JSON
kvm-clone list host1.example.com --format json
```

### Configuration

```bash
# Initialize default configuration
kvm-clone config init

# Show current configuration
kvm-clone config show
```

## 🐍 Python API

```python
import asyncio
from kvm_clone import KVMCloneClient, CloneOptions

async def clone_vm():
    async with KVMCloneClient() as client:
        result = await client.clone_vm(
            source_host="source.example.com",
            dest_host="dest.example.com", 
            vm_name="my-vm",
            new_name="my-vm-clone",
            compress=True,
            verify=True
        )
        
        if result.success:
            print(f"Successfully cloned VM: {result.new_vm_name}")
        else:
            print(f"Clone failed: {result.error}")

# Run the async function
asyncio.run(clone_vm())
```

## 📊 Project Status

This repository is **under active development**. We recently completed a major implementation milestone:

### What's Implemented
- ✅ Core logic for cloning KVM virtual machines over SSH via libvirt
- ✅ Complete package structure with proper modules
- ✅ SSH transport layer with paramiko
- ✅ Libvirt wrapper for VM management
- ✅ Comprehensive CLI interface
- ✅ Data models and exception handling
- ✅ Security hardening (Phase 1 complete)
- ✅ Structured logging and error handling (Phase 2 complete)
- ✅ Configuration validation (Phase 2 complete)
- ✅ Full test suite (39/39 tests passing)

### What's Next
- 🚧 Progress tracking implementation (byte-level monitoring)
- 🚧 Performance optimization and advanced features
- 🚧 Enhanced documentation and user guides

See [TODO.md](TODO.md) for the complete roadmap and current status.

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) to understand our spec-first process. 

### Development Workflow
1. **Development Branch**: `develop` - All new features and fixes
2. **Production Branch**: `master` - Protected with 90% test coverage requirement
3. **Pull Requests**: Create PRs from `develop` to `master` when ready

If you are proposing a change, start by opening an issue to discuss the specification.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🔗 Links

- **Repository**: https://github.com/tomazb/kvm-cloning-over-ssh
- **Issues**: https://github.com/tomazb/kvm-cloning-over-ssh/issues
- **Discussions**: https://github.com/tomazb/kvm-cloning-over-ssh/discussions