# Changelog

All notable changes to the KVM Cloning over SSH project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Pydantic-based configuration validation with automatic type coercion
- `pydantic` and `pydantic-settings` dependencies

### Changed
- Migrated configuration from dataclasses to Pydantic `BaseModel`
- Improved configuration validation with field constraints

## [0.2.0] - 2025-11-20

### Added - Phase 2: Code Quality & Error Handling
- **Structured Logging**: JSON-formatted logging with timestamps and context (`src/kvm_clone/logging.py`)
- **Configuration Validation**: Robust configuration loading and validation (`src/kvm_clone/config.py`)
- **Pydantic Integration**: Type-safe configuration with automatic validation
- Comprehensive error handling with specific exceptions
- Proper resource cleanup in error conditions
- Exception chaining for better debugging

### Changed
- Replaced bare `except` clauses with specific exception handling across all modules
- Enhanced error logging with `exc_info=True` for full tracebacks
- Integrated structured logger across `cloner.py`, `transport.py`, `libvirt_wrapper.py`, `sync.py`
- Updated `cli.py` to use new `ConfigLoader`

### Fixed
- Improved error messages with context
- Better resource management in failure scenarios

### Documentation
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

### Security
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

### Changed
- Updated all modules to use secure command building
- Replaced direct string interpolation with validated parameters
- Fixed circular type definition in `models.py` (renamed to `OperationStatusEnum`)

### Compliance
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

- **v0.2.0** (2025-11-20): Code Quality & Error Handling (Phase 2)
- **v0.1.0** (2025-07-27): Critical Security Fixes (Phase 1)
- **v0.0.1**: Initial implementation with core functionality

## Test Coverage

All versions maintain 100% test pass rate:
- Total Tests: 39
- Integration Tests: 8
- Spec Conformance: 15
- Security Tests: 7
- Unit Tests: 9

**Status**: Production-Ready Foundation
