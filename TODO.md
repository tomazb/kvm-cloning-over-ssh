# TODO

## Implementation Status

### ✅ Completed (Recent Implementation)
- [x] **Core Package Structure** - Moved from root script to proper `src/kvm_clone/` package
- [x] **SSH Transport Layer** - Full paramiko-based implementation with async support
- [x] **Libvirt Wrapper** - VM management operations via libvirt API
- [x] **VM Cloner** - Complete cloning functionality with validation and progress tracking
- [x] **VM Synchronizer** - Incremental sync operations with delta calculation
- [x] **Main Client API** - Public interface matching API specification
- [x] **Data Models** - All required data structures and enums
- [x] **Custom Exceptions** - Comprehensive error handling hierarchy
- [x] **CLI Interface** - Full Click-based command-line interface with all specified commands
- [x] **Dependencies** - Added paramiko, libvirt-python, click, pyyaml
- [x] **Entry Point** - Configured `kvm-clone` command in pyproject.toml
- [x] **Updated Tests** - Real test implementations replacing placeholders

### 🔒 Security Fixes (Phase 1 - COMPLETED ✅)
- [x] **Command Injection Vulnerabilities** - Fixed unsafe string interpolation in shell commands
- [x] **SSH Security Configuration** - Replaced AutoAddPolicy with secure RejectPolicy
- [x] **Path Traversal Protection** - Implemented path sanitization and validation
- [x] **Input Validation Framework** - Comprehensive validation for VM names, hostnames, paths
- [x] **Circular Type Definition** - Fixed OperationStatus enum naming conflict
- [x] **Security Infrastructure** - Created security.py module with SecurityValidator, CommandBuilder, SSHSecurity
- [x] **Security Test Suite** - Added 7 dedicated security tests (all passing)
- [x] **Documentation** - Created SECURITY_FIXES_REPORT.md with detailed implementation report

### ✅ Code Quality & Error Handling (Phase 2 - COMPLETED)
- [x] **Error Handling Improvements** - Replaced bare except clauses with specific exception handling
- [x] **Resource Management** - Implemented proper cleanup in error conditions
- [x] **Structured Logging** - Added JSON-formatted structured logging with audit trails
- [x] **Configuration Validation** - Implemented dataclass-based configuration with schema validation

### 🚧 In Progress / High Priority

#### Core Functionality Enhancements (Phase 3)
- [ ] **Progress Tracking Implementation** - Replace placeholder progress with real byte-level monitoring
- [ ] **Delta Synchronization** - Implement actual block-level differential sync
- [ ] **Missing CLI Commands** - Add `status`, `config set/unset` commands
- [ ] **Integrity Verification** - Implement checksum validation after transfers

#### Test Coverage & Quality
- [ ] **Install Dependencies** - Run `poetry install` to fix import errors
- [ ] **Improve Test Coverage** - Add more comprehensive unit tests to reach 90% coverage
- [ ] **Integration Tests** - Add tests with actual libvirt/SSH environments
- [ ] **Mock External Dependencies** - Better mocking for paramiko and libvirt in tests

#### Performance & Reliability
- [ ] **Parallel Transfers** - Implement actual parallel disk transfer support
- [ ] **Resume Capability** - Support for resuming interrupted transfers
- [ ] **Memory Optimization** - Efficient handling of large disk images
- [ ] **Connection Pooling** - Reuse SSH connections for multiple operations
- [ ] **Bandwidth Limiting** - Implement actual bandwidth control in transfers
- [ ] **Compression** - Add real compression support for disk transfers

### 🛡️ Data Safety & Robustness (Phase 4 - CRITICAL PRIORITY)

#### Pre-Operation Validation
- [ ] **Disk Space Verification** - Check available space on destination before cloning
  - [ ] Verify source VM total disk size
  - [ ] Check destination host free space
  - [ ] Ensure sufficient margin (10-20% extra)
  - [ ] Fail early with clear error message if insufficient space
  
- [ ] **Resource Availability Check** - Validate destination host resources
  - [ ] Check CPU availability for VM requirements
  - [ ] Verify memory availability
  - [ ] Validate network interface availability
  - [ ] Pre-validate storage pool accessibility

- [ ] **Source VM Validation** - Comprehensive checks before cloning
  - [ ] Verify VM is in expected state (running/stopped)
  - [ ] Check for pending snapshots or operations
  - [ ] Validate all disk images are accessible
  - [ ] Verify VM configuration is readable and valid

#### Atomic Operations & Rollback
- [ ] **Transactional Cloning** - Implement atomic clone operations
  - [ ] Create temporary staging area for clone
  - [ ] Only move to final location on success
  - [ ] Automatic cleanup of partial clones on failure
  - [ ] Transaction log for debugging failed operations
  
- [ ] **Rollback Mechanism** - Safe operation rollback on failure
  - [ ] Track all created resources during operation
  - [ ] Implement cleanup handlers for each operation stage
  - [ ] Rollback in reverse order of creation
  - [ ] Log all rollback actions for audit trail
  
- [ ] **Pre-Clone Snapshots** - Optional safety snapshots
  - [ ] Create snapshot of source VM before cloning (optional flag)
  - [ ] Snapshot destination VM if replacing (optional flag)
  - [ ] Automatic cleanup of safety snapshots after success
  - [ ] Retention policy for safety snapshots

#### Data Integrity & Verification
- [ ] **Checksum Validation** - Comprehensive integrity checks
  - [ ] Calculate checksums of source disk images
  - [ ] Verify checksums after transfer
  - [ ] Support multiple algorithms (SHA-256, MD5)
  - [ ] Store checksums in operation metadata
  
- [ ] **Byte-Level Verification** - Ensure complete data transfer
  - [ ] Compare file sizes before/after transfer
  - [ ] Verify block counts match
  - [ ] Optional bit-for-bit comparison (slow but thorough)
  - [ ] Report any discrepancies clearly
  
- [ ] **Post-Clone Validation** - Verify cloned VM functionality
  - [ ] Test VM can be started (dry-run boot)
  - [ ] Validate disk images are not corrupted
  - [ ] Check XML configuration validity
  - [ ] Verify network configuration if preserved

#### Connection & Network Resilience
- [ ] **Connection Retry Logic** - Handle transient network failures
  - [ ] Implement exponential backoff for retries
  - [ ] Configurable retry attempts and delays
  - [ ] Distinguish between transient and permanent failures
  - [ ] Log retry attempts for troubleshooting
  
- [ ] **Operation Timeouts** - Prevent indefinite hangs
  - [ ] Configurable timeouts per operation type
  - [ ] Separate timeouts for connection vs. data transfer
  - [ ] Progress-based timeout (fail if no progress for N seconds)
  - [ ] Clear timeout error messages with operation context
  
- [ ] **Resume Capability** - Continue interrupted operations
  - [ ] Track transfer progress persistently
  - [ ] Implement rsync resume for partial transfers
  - [ ] Store operation state to disk
  - [ ] Automatic detection of resumable operations
  
- [ ] **Graceful Degradation** - Handle partial failures intelligently
  - [ ] Continue operation if non-critical steps fail
  - [ ] Provide detailed status of what succeeded/failed
  - [ ] Allow user to complete failed steps manually
  - [ ] Log warnings for degraded operations

#### Resource Cleanup & Management
- [ ] **Temporary File Management** - Proper cleanup of temp resources
  - [ ] Use context managers for all temporary files
  - [ ] Implement atexit handlers for emergency cleanup
  - [ ] Track all temporary resources in operation state
  - [ ] Periodic cleanup of orphaned temporary files
  
- [ ] **Disk Quota Monitoring** - Track and enforce limits
  - [ ] Monitor disk usage during operations
  - [ ] Fail early if approaching quota limits
  - [ ] Support for storage pool quota enforcement
  - [ ] Alert on approaching thresholds
  
- [ ] **Resource Locks** - Prevent concurrent conflicting operations
  - [ ] Implement lock files for active operations
  - [ ] Detect and handle stale locks
  - [ ] Per-VM locking to prevent simultaneous operations
  - [ ] Cluster-aware locking for multi-host scenarios

#### Error Recovery & Debugging
- [ ] **Detailed Error Context** - Rich error information
  - [ ] Include full operation context in errors
  - [ ] Attach relevant state/configuration to exceptions
  - [ ] Provide actionable remediation suggestions
  - [ ] Include troubleshooting steps in error messages
  
- [ ] **Operation State Persistence** - Debug failed operations
  - [ ] Save complete operation state on failure
  - [ ] Include environment snapshot (host info, config, etc.)
  - [ ] Structured error reports with all context
  - [ ] Export capability for support/debugging
  
- [ ] **Health Checks** - Pre-operation validation
  - [ ] Verify SSH connectivity before starting
  - [ ] Test libvirt connection stability
  - [ ] Validate storage backend accessibility
  - [ ] Check for conflicting operations

#### Safe Deletion & Cleanup
- [ ] **Confirmation Prompts** - Prevent accidental data loss
  - [ ] Require explicit confirmation for destructive operations
  - [ ] Double-check for critical VMs (production flag)
  - [ ] Show what will be deleted before confirmation
  - [ ] Implement `--force` flag for automation (with warnings)
  
- [ ] **Backup Before Delete** - Optional safety net
  - [ ] Create backup before VM deletion (configurable)
  - [ ] Export VM configuration before removal
  - [ ] Snapshot before destructive sync operations
  - [ ] Retention policy for safety backups

#### Monitoring & Observability
- [ ] **Operation Metrics** - Track operation statistics
  - [ ] Record duration of each operation phase
  - [ ] Track bytes transferred, speed, efficiency
  - [ ] Log resource consumption (CPU, memory, network)
  - [ ] Store metrics for performance analysis
  
- [ ] **Progress Persistence** - Enable monitoring of long operations
  - [ ] Periodic progress updates to persistent storage
  - [ ] Allow external monitoring of operation status
  - [ ] Implement progress callback mechanism
  - [ ] Support for progress bars in CLI

### 📋 Contributing Infrastructure (Original TODO Items)

- [ ] Create `CODE_OF_CONDUCT.md`
  - Adopt Contributor Covenant v2.1 or similar
  - Reference it from `CONTRIBUTING.md`

- [ ] Add `.editorconfig`
  - Define indentation (spaces vs tabs) and line endings
  - Configure charset (utf-8)
  - Set trim trailing whitespace and insert final newline

- [ ] Add pre-commit configuration
  - Create `.pre-commit-config.yaml`
  - Include hooks such as:
    - trailing-whitespace
    - end-of-file-fixer
    - check-added-large-files
    - black (for Python) / other formatters as needed
  - Update documentation to instruct contributors to run `pre-commit install`

### 🔮 Future Enhancements

#### Advanced Features
- [ ] **Live Migration** - Support for migrating running VMs
- [ ] **Incremental Backups** - Snapshot-based incremental transfers
- [ ] **Multi-host Orchestration** - Coordinate transfers across multiple hosts
- [ ] **Web Interface** - Optional web UI for monitoring and management
- [ ] **API Server** - REST API for programmatic access

#### Enterprise Features
- [ ] **Authentication** - Support for various SSH auth methods (keys, certificates, etc.)
- [ ] **Logging & Monitoring** - Structured logging and metrics collection
- [ ] **Scheduling** - Cron-like scheduling for automated transfers
- [ ] **Notification System** - Email/webhook notifications for operation status

#### Documentation
- [ ] **User Guide** - Comprehensive usage documentation
- [ ] **API Documentation** - Auto-generated API docs from docstrings
- [ ] **Tutorial** - Step-by-step setup and usage guide
- [ ] **Architecture Guide** - Detailed technical documentation

---

## Development Workflow

1. **Current Branch**: `develop` - All new development happens here
2. **Production Branch**: `master` - Protected with 90% test coverage requirement
3. **Next Milestone**: Phase 4 - Data Safety & Robustness implementation

## Priority Recommendations (Phase 4)

Based on code analysis, tackle these items first for maximum impact:

1. **🔴 CRITICAL: Disk Space Verification** - Prevents most common failure mode
2. **🔴 CRITICAL: Transactional Cloning** - Prevents partial VM corruption
3. **🟠 HIGH: Checksum Validation** - Ensures data integrity
4. **🟠 HIGH: Connection Retry Logic** - Handles network instability
5. **🟠 HIGH: Operation Timeouts** - Prevents indefinite hangs

## Getting Started for Contributors

```bash
# Clone the repository
git clone https://github.com/tomazb/kvm-cloning-over-ssh.git
cd kvm-cloning-over-ssh

# Switch to develop branch
git checkout develop

# Install dependencies
poetry install

# Run tests (currently failing due to missing dependencies in CI)
poetry run pytest

# Install the CLI tool for testing
poetry install
kvm-clone --help
```

## Notes

- The project has moved from placeholder implementation to a fully functional system
- All core components are implemented and follow the API specification
- **Phase 1 (Security)** and **Phase 2 (Code Quality)** are complete ✅
- **Phase 3 (Feature Completeness)** is in progress 🚧
- **Phase 4 (Data Safety & Robustness)** is the new critical priority 🛡️
- Major fragility risks identified: no atomic operations, missing rollback, insufficient validation
- Focus areas: Data integrity, operation resilience, safe failure handling
- The develop branch is ready for collaborative development