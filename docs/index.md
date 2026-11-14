# KVM Cloning over SSH - Documentation

Welcome to the comprehensive documentation for the KVM Cloning over SSH project. This tool enables secure cloning and synchronization of KVM virtual machines between hosts using libvirt API over SSH connections.

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/tomazb/kvm-cloning-over-ssh.git
cd kvm-cloning-over-ssh

# Install dependencies
poetry install
```

### Basic Usage

```bash
# Clone a VM
kvm-clone clone source-host dest-host vm-name

# Synchronize a VM
kvm-clone sync source-host dest-host vm-name

# List VMs
kvm-clone list host1 host2
```

## 📚 Documentation Sections

### Core Documentation
- **[API Reference](api.md)** - Complete API documentation with type annotations
- **[Functional Specification](specs/functional_spec.md)** - Detailed functional requirements

### Technical Resources
- **[API Specification](../api_spec.md)** - Complete CLI and Python API specification
- **[Technical Specification](../technical_spec.md)** - Architecture and design details
- **[Contributing Guide](../CONTRIBUTING.md)** - How to contribute to the project

## 🏗️ Architecture Overview

The project follows a modular architecture with clear separation of concerns:

```
src/kvm_clone/
├── client.py          # Main KVMCloneClient class
├── cloner.py          # VM cloning operations
├── sync.py            # VM synchronization operations
├── transport.py       # SSH transport layer
├── libvirt_wrapper.py # Libvirt API wrapper
├── models.py          # Data models and structures
├── exceptions.py      # Custom exceptions
└── cli.py             # Command-line interface
```

## ✨ Key Features

### ✅ Implemented
- **Complete VM Cloning** - Full VM cloning with disk images and configuration
- **Incremental Synchronization** - Delta-based sync for efficient updates
- **SSH Transport** - Secure transfers using SSH with key-based authentication
- **Libvirt Integration** - Native libvirt API support for VM management
- **CLI Interface** - Comprehensive command-line interface
- **Async Operations** - Non-blocking operations with progress tracking
- **Type Safety** - Full type annotations for better development experience

### 🚧 In Development
- **Enhanced Test Coverage** - Expanding test suite to reach 90% coverage
- **Performance Optimization** - Parallel transfers and bandwidth limiting
- **Advanced Features** - Resume capability, compression, integrity verification

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

# Build documentation
make docs
```

## 🐍 Python API Example

```python
import asyncio
from kvm_clone import KVMCloneClient


async def clone_vm():
    async with KVMCloneClient() as client:
        result = await client.clone_vm(
            source_host="source.example.com",
            dest_host="dest.example.com",
            vm_name="my-vm",
            new_name="my-vm-clone",
            compress=True,
            verify=True,
        )

        if result.success:
            print(f"Successfully cloned VM: {result.new_vm_name}")
        else:
            print(f"Clone failed: {result.error}")


asyncio.run(clone_vm())
```

## 📊 Project Status

This project has recently completed a major implementation milestone, moving from placeholder code to a fully functional system:

- ✅ **Core Implementation Complete** - All major components implemented
- ✅ **CLI Interface** - Full command-line interface with all specified commands
- ✅ **Package Structure** - Proper Python package with modular design
- 🚧 **Test Coverage** - Working to reach 90% coverage requirement
- 🚧 **Documentation** - Expanding user guides and examples

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](../CONTRIBUTING.md) for details on our development process.

### Development Workflow
1. **Development Branch**: `develop` - All new features and fixes
2. **Production Branch**: `master` - Protected with 90% test coverage requirement
3. **Pull Requests**: Create PRs from `develop` to `master` when ready

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

---

!!! note "Auto-generated Content"
    Parts of this documentation are automatically generated from source code docstrings.
    Spec IDs in the code are automatically linked to their implementations for easy navigation.

## Building Documentation

To build this documentation locally:

```bash
make docs
```

This will generate the HTML documentation in the `site/` directory.