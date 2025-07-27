# KVM Cloning over SSH

A tool for copying/syncing KVM virtual machines from one machine to another using libvirt API over SSH.

This project provides functionality to clone and synchronize KVM virtual machines between different hosts by leveraging the libvirt API through SSH connections. The code uses the fastest method to achieve reliable VM transfer between machines.

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/tomazb/kvm-cloning-over-ssh.git
cd kvm-cloning-over-ssh

# Install dependencies
poetry install

# Install the CLI tool
poetry install
```

### Basic Usage

```bash
# Clone a VM from one host to another
kvm-clone clone source-host dest-host vm-name

# Synchronize an existing VM (incremental update)
kvm-clone sync source-host dest-host vm-name

# List VMs on hosts
kvm-clone list host1 host2

# Get help
kvm-clone --help
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

### 🚧 In Development
- **Enhanced Test Coverage** - Expanding test suite to reach 90% coverage
- **Performance Optimization** - Parallel transfers and bandwidth limiting
- **Advanced Features** - Resume capability, compression, integrity verification

## 🏗️ Architecture

The project follows a modular architecture:

```
src/kvm_clone/
├── client.py          # Main client class (KVMCloneClient)
├── cloner.py          # VM cloning operations
├── sync.py            # VM synchronization operations  
├── transport.py       # SSH transport layer
├── libvirt_wrapper.py # Libvirt API wrapper
├── models.py          # Data models and structures
├── exceptions.py      # Custom exceptions
└── cli.py             # Command-line interface
```

## 📖 Documentation

- **[API Specification](api_spec.md)** - Complete API documentation
- **[Technical Specification](technical_spec.md)** - Architecture and design details
- **[TODO](TODO.md)** - Current status and roadmap
- **[Contributing](CONTRIBUTING.md)** - How to contribute to the project

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
- ✅ Basic test scaffolding with real implementations

### What's Next
- 🚧 Improve test coverage to reach 90% requirement
- 🚧 Add integration tests with real environments
- 🚧 Performance optimization and advanced features
- 🚧 Documentation and user guides

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