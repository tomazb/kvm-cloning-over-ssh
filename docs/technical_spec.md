# Technical Specification

## Overview
This document outlines the technical specifications for the KVM Cloning over SSH system, including architecture, configuration, security considerations, and performance targets.

## Architecture

The system is built as a modular Python application:

- **KVMCloneClient (`client.py`)**: The main entry point and orchestrator.
- **VMCloner (`cloner.py`)**: Manages the high-level cloning workflow.
- **SSHTransport (`transport.py`)**: Handles secure SSH connections and command execution using `paramiko`.
- **LibvirtWrapper (`libvirt_wrapper.py`)**: Interfaces with the local libvirt daemon using `libvirt-python`.
- **VMSynchronizer (`sync.py`)**: Manages incremental synchronization and rsync operations.
- **Configuration (`config.py`)**: Handles configuration loading and validation using Pydantic.
- **Structured Logging (`logging.py`)**: Provides JSON-formatted logging for observability.
- **Security (`security.py`)**: Enforces input validation, secure command building, and SSH security policies.

## Configuration

The system uses a unified YAML configuration structure managed by `AppConfig`.

**Structure:**
- **General**: Log levels, dry-run mode.
- **SSH**: User, key path, connection timeout, known_hosts policy.
- **Libvirt**: Connection URI (default: `qemu:///system`).
- **Transfer**: Bandwidth limits, compression, progress reporting.

## Security Architecture

Security is enforced at multiple layers:

1.  **Input Validation**: All user inputs (VM names, hostnames, paths) are validated against strict regex patterns via `SecurityValidator`.
2.  **Command Injection Prevention**: Shell commands are constructed using `CommandBuilder`, which uses `shlex.quote()` to sanitize all arguments.
3.  **SSH Security**: Strict host key checking is enforced (RejectPolicy) by default. `AutoAddPolicy` is disabled.
4.  **Path Traversal Protection**: File paths are sanitized to prevent access outside allowed directories (e.g., `/var/lib/libvirt/images`).

## Observability

- **Structured Logging**: All logs are output in JSON format, including timestamps, severity, logger names, and context-specific fields.
- **Audit Trail**: Critical actions (cloning, syncing, deletions) are logged with high severity.

## Requirements Traceability

| Requirement | Component | Implementation File |
|-------------|-----------|---------------------|
| **REQ-01** Orchestration | Controller | `src/kvm_clone/cloner.py` |
| **REQ-02** Secure Transport | SSH Transport | `src/kvm_clone/transport.py` |
| **REQ-03** VM Management | Libvirt Wrapper | `src/kvm_clone/libvirt_wrapper.py` |
| **REQ-04** Data Transfer | Synchronizer | `src/kvm_clone/sync.py` |
| **REQ-05** Security Compliance | Security Module | `src/kvm_clone/security.py` |
| **REQ-06** Configuration | Config Loader | `src/kvm_clone/config.py` |
| **REQ-07** Observability | Structured Logger | `src/kvm_clone/logging.py` |

## Performance Targets

1.  **Reliability**: Zero data corruption during transfers (verified by rsync checksums).
2.  **Efficiency**: Incremental syncs should only transfer changed blocks.
3.  **Scalability**: Capable of handling large VM images (100GB+).
