# Changelog

All notable changes to the KVM Cloning over SSH project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2025-11-20

### Added - Phase 3: Real-World Usability & Transactional Safety

- **SSH Infrastructure Integration**:
  - SSH agent support with automatic fallback
  - SSH config file (`~/.ssh/config`) reading for host aliases, ports, users, and identity files
  - System known_hosts loading for enhanced security
  - Username auto-detection from SSH config, environment variables, or current user
  - Hostname resolution from SSH config (supports Host aliases)
  - Port auto-detection from SSH config

- **Connection Resilience**:
  - Automatic retry logic with exponential backoff (1s, 2s, 4s)
  - Configurable max retries (default: 3 attempts)
  - Smart retry decisions (skip authentication errors, retry network errors)
  - Detailed retry progress logging

- **Enhanced Error Messages**:
  - Actionable authentication error messages with step-by-step remediation
  - Context-aware host key verification error guidance
  - Network error troubleshooting hints with specific suggestions
  - Helpful command examples for common issues

- **Flexible Security Configuration**:
  - Configurable SSH host key policy via `KVM_CLONE_SSH_HOST_KEY_POLICY` environment variable
  - Three modes: `strict` (default, most secure), `warn` (accept with warning), `accept` (auto-add)
  - Clear security warnings for insecure modes
  - Maintains secure defaults while allowing flexibility

- **Environment Variable Configuration**:
  - Full environment variable override support for all configuration options
  - Priority order: env vars > config file > defaults
  - Supported variables: `KVM_CLONE_SSH_KEY_PATH`, `KVM_CLONE_SSH_PORT`, `KVM_CLONE_TIMEOUT`, `KVM_CLONE_LOG_LEVEL`, `KVM_CLONE_KNOWN_HOSTS_FILE`, `KVM_CLONE_PARALLEL_TRANSFERS`, `KVM_CLONE_BANDWIDTH_LIMIT`, `KVM_CLONE_SSH_HOST_KEY_POLICY`
  - CI/CD and automation friendly

- **Bandwidth Management**:
  - `--bandwidth-limit` (`-b`) option for clone command
  - Previously only available for sync operations
  - Support for M/G suffixes (e.g., `100M`, `1G`)
  - Prevents network saturation during production operations

- **Configuration Management CLI**:
  - `config init` - Initialize default configuration file
  - `config list` - List all configuration values
  - `config get <key>` - Get specific configuration value
  - `config set <key> <value>` - Set configuration value with smart type conversion
  - `config unset <key>` - Remove configuration value
  - `config path` - Show configuration file locations and search order
  - Smart type conversion for int, float, bool, and null values
  - No manual YAML editing required

- **Transactional Clone Operations**:
  - New `transaction.py` module for atomic clone operations
  - Automatic rollback on failure with resource cleanup
  - Transaction logging for debugging and recovery
  - Staging directory for safe file transfers
  - Resource tracking (disks, VMs, directories)
  - Commit/rollback pattern ensures no partial clones

- **Idempotent Clone Mode**:
  - `--idempotent` flag for automatic cleanup and retry
  - Safe for automation and scripting
  - Automatically removes existing VM before cloning
  - Prevents "VM already exists" errors in automation scenarios

- **Resource Validation**:
  - Pre-clone validation of destination resources
  - Disk space checking with 15% safety margin
  - Memory availability warnings
  - CPU core availability warnings
  - Storage pool discovery and aggregation
  - Graceful handling of pool query failures

- **New Test Suites**:
  - `tests/unit/test_idempotent.py` - Idempotent operation tests
  - `tests/unit/test_transaction.py` - Transaction management tests
  - Enhanced security tests for new command builders

- **Documentation**:
  - `docs/REAL_WORLD_IMPROVEMENTS.md` - Comprehensive guide to all improvements
  - `docs/IDEMPOTENCY_ANALYSIS.md` - Idempotency analysis and implementation plan
  - `docs/PHASE4_DATA_SAFETY.md` - Future data safety enhancements

### Changed

- **SSH Connection Handling**:
  - SSH key precedence: explicit key now takes priority over SSH config IdentityFile
  - Improved SSH config parsing with proper fallback chain
  - Better error context in connection failures
  - Non-blocking SFTP initialization using executor

- **Configuration System**:
  - Environment variable overrides now have highest priority
  - Improved type conversion in configuration loading
  - Default config directory changed to `~/.config/kvm-clone` (XDG-compliant)
  - Support for negative numbers and floats in config values

- **Clone Operation**:
  - Uses transactional framework for atomic operations
  - Disks transferred to staging directory first, then moved on commit
  - Automatic cleanup on failure via transaction rollback
  - Better progress reporting during multi-step operations

- **Code Quality**:
  - Moved all imports to top of files (security.py)
  - Refactored duplicate config loading code into `_load_config_file()` helper
  - Improved type hints (`any` → `Any`)
  - Better code organization and consistency

### Fixed

- **Critical**: SSH key precedence issue where SSH config IdentityFile would override explicit `--ssh-key`
- Removed unused `time` import from transport.py (flake8 F401)
- Fixed f-string without placeholders (flake8 F541)
- Added missing `os` import in cli.py (flake8 F821)
- Fixed type hint `any` to `Any` in transport.py
- Type conversion in `config set` now handles negative numbers and floats correctly
- Reduced code duplication in config management commands

### Security

- SSH host key policy now configurable while maintaining secure defaults
- System known_hosts files loaded for better security
- Clear warnings when insecure modes are enabled
- Path validation in all new command builders (rm_file, rm_directory, move_file, mkdir)

### Performance

- Connection retry reduces failures from transient network issues
- Bandwidth limiting prevents network saturation
- Parallel transfer settings now configurable via environment

## [0.2.0] - 2025-11-20

### Added - Phase 2: Code Quality & Error Handling

- **Structured Logging**: JSON-formatted logging with timestamps and context (`src/kvm_clone/logging.py`)
- **Configuration Validation**: Robust configuration loading and validation (`src/kvm_clone/config.py`)
- **Pydantic Integration**: Type-safe configuration with automatic validation
- Comprehensive error handling with specific exceptions
- Proper resource cleanup in error conditions
- Exception chaining for better debugging

### Code Quality Improvements

- Replaced bare `except` clauses with specific exception handling across all modules
- Enhanced error logging with `exc_info=True` for full tracebacks
- Integrated structured logger across `cloner.py`, `transport.py`, `libvirt_wrapper.py`, `sync.py`
- Updated `cli.py` to use new `ConfigLoader`

### Bug Fixes

- Improved error messages with context
- Better resource management in failure scenarios

### Documentation Updates

- Created comprehensive `docs/SECURITY_FIXES_REPORT.md`
- Updated `docs/technical_spec.md` with current architecture
- Updated `README.md` to reflect Phase 2 completion
- Updated `TODO.md` with current status
- Created `docs/CHANGELOG.md`

## [0.1.0] - 2025-07-27

### Added - Phase 1: Critical Security Fixes

- **Security Module** (`src/kvm_clone/security.py`):
  - `SecurityValidator` class for input validation
  - `CommandBuilder` class for secure command construction
  - `SSHSecurity` class for SSH security policies
- Comprehensive security test suite (7 tests)
- Input validation for VM names, hostnames, and paths using regex patterns
- Path sanitization to prevent traversal attacks

### Security Enhancements

- **CRITICAL**: Fixed command injection vulnerabilities (CVE-level risk)
  - Implemented `shlex.quote()` for all shell command parameters
  - Secure command building with `CommandBuilder`
- **CRITICAL**: Fixed SSH security misconfiguration
  - Replaced `AutoAddPolicy()` with `RejectPolicy()`
  - Added SSH key validation
- **HIGH**: Fixed path traversal vulnerabilities
  - Implemented path sanitization with base directory restrictions
- **HIGH**: Added comprehensive input validation
  - VM names: `^[a-zA-Z0-9_-]+$`
  - Hostnames: `^[a-zA-Z0-9.-]+$`
  - Snapshot names: `^[a-zA-Z0-9_-]+$`

### Code Updates

- Updated all modules to use secure command building
- Replaced direct string interpolation with validated parameters
- Fixed circular type definition in `models.py` (renamed to `OperationStatusEnum`)

### Compliance Achievements

- ✅ OWASP Top 10: Injection vulnerabilities resolved
- ✅ CWE-78: Command injection mitigated
- ✅ CWE-22: Path traversal prevented
- ✅ CWE-295: SSH security improved

## [0.0.1] - Initial Implementation

### Added

- Core package structure (`src/kvm_clone/`)
- SSH transport layer with `paramiko`
- Libvirt wrapper for VM management
- VM cloning functionality
- VM synchronization with incremental updates
- CLI interface with `click`
- Data models and exception hierarchy
- Basic test suite (39 tests)

### Features

- Complete VM cloning between hosts
- Incremental synchronization
- SSH-based secure transport
- Libvirt API integration
- Async operations support
- YAML-based configuration
- Type annotations throughout

---

## Version History Summary

- **v0.3.0** (2025-11-20): Real-World Usability & Transactional Safety (Phase 3)
- **v0.2.0** (2025-11-20): Code Quality & Error Handling (Phase 2)
- **v0.1.0** (2025-07-27): Critical Security Fixes (Phase 1)
- **v0.0.1**: Initial implementation with core functionality

## Test Coverage

All versions maintain high test coverage:

- Total Tests: 50+
- Integration Tests: 8
- Spec Conformance: 15
- Security Tests: 10+
- Unit Tests: 17+
- Idempotency Tests: New in v0.3.0
- Transaction Tests: New in v0.3.0

**Status**: Production-Ready with Enterprise Features
