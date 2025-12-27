# Code Validation TODO

This document tracks issues found during code validation for completeness, code smells, performance issues, security concerns, and error handling.

---

## IMPLEMENTATION STATUS

**Date**: 2025-12-27 (audit updated)
**Completed**: See phase summary below
**Remaining**: See "Remaining Tasks (verified)" below

| Severity | Total | Completed | Remaining |
|----------|-------|-----------|------------|
| **CRITICAL** | 6 | 6 | 0 |
| **HIGH** | 8 | 5 | 3 |
| **MEDIUM** | 12 | 7 | 5 |
| **LOW** | 8 | 4 | 4 |

Note: Severity counts above are stale and need recalculation after the audit corrections below.

### Completed Summary

**Phase 1 - CRITICAL (4/6 completed):**
- ✅ Fixed progress tracking (total_bytes calculation)
- ✅ Implemented real delta calculation (rsync --dry-run --stats)
- ✅ Fixed resource leaks (connection cleanup)
- ⏳ Disk size retrieval still uses `blockStats` wr_bytes (not capacity)
- ⏳ CPU usage monitoring incomplete (ALL_CPUS stats handling)
- ✅ Implemented disk space retrieval (df command)

**Phase 2 - HIGH (6/8 completed):**
- ✅ Fixed resource leaks in transport.py (TTL + LRU eviction)
- ✅ Fixed resource leaks in libvirt_wrapper.py (TTL cleanup)
- ✅ Fixed resource leaks in client.py (__aexit__ cleanup)
- ✅ Fixed silent failures in list_vms (returns error strings)
- ✅ Implemented concurrent list_vms (asyncio.gather)
- ✅ Added dedicated thread pool for blocking operations
- ⏳ Replace broad exception handlers (23 instances)
- ⏳ Implement SSH known hosts policy

**Phase 3 - MEDIUM (2/6 completed):**
- ⏳ Timeout inconsistency still present (CLI sync default 7200, config init 30)
- ✅ Fixed disk mismatch handling (allow_disk_mismatch flag)
- ✅ Extracted VM state mapping to constant (LIBVIRT_STATE_MAP)
- ⏳ progress.py helpers not wired into cloner/sync (module exists only)
- ⏳ Parallelize disk transfers
- ⏳ Add logging helper functions

**Phase 4 - LOW (2/3 completed):**
- ✅ Replaced Unicode characters (✓ → [OK], ✗ → [ERROR])
- ✅ Fixed empty pass statements (added explanatory comments)
- ⏳ Standardize type annotations

### Remaining Tasks (Detailed Implementation Plan)

Target: **Python 3.9+** with `from __future__ import annotations` for modern type syntax.

Each task will be committed individually with tests run between commits.

| # | Task | File(s) | Status |
|---|------|---------|--------|
| 1 | **Fix disk size retrieval** | `libvirt_wrapper.py` | ✅ Done |
| 2 | **Fix CPU usage monitoring** | `libvirt_wrapper.py` | ✅ Done |
| 3 | **Align timeout defaults** | `cli.py` | ✅ Done |
| 4 | **Expose allow_disk_mismatch** | `cli.py`, `client.py` | ✅ Done |
| 5 | **Add logging helper functions** | `logging.py` | ✅ Done |
| 6 | **Preserve exception context** | `cloner.py`, `sync.py`, `transport.py`, `config.py` | ✅ Done |
| 7 | **Fix rsync stats parsing** | `sync.py` | ✅ Done |
| 8 | **Adopt progress helpers** | `cloner.py`, `sync.py` | ✅ Done |
| 9 | **Parallelize disk transfers** | `cloner.py`, `sync.py`, `models.py` | ✅ Done |
| 10 | **Implement resource validation** | `cloner.py` | ✅ Done |
| 11 | **Implement SSH host key verification** | `security.py`, `transport.py`, `cli.py` | ⏳ In Progress |
| 12 | **Replace broad exception handlers** | 7 files, 23 instances | ⏳ Pending |
| 13 | **Standardize type annotations** | All source files | ⏳ Pending |

---

#### Task 1: Fix disk size retrieval
- **Problem**: Uses `blockStats[3]` (wr_bytes) which is bytes written, not disk capacity
- **Solution**: Replace with `domain.blockInfo(disk_target)` which returns `(capacity, allocation, physical)`
- **Use**: `capacity` (index 0) for logical disk size

#### Task 2: Fix CPU usage monitoring
- **Problem**: `getCPUStats(VIR_NODE_CPU_STATS_ALL_CPUS)` returns dict with keys `kernel`, `user`, `idle`, `iowait`, not `cpu_time`
- **Solution**: Calculate `(user + kernel) / (user + kernel + idle + iowait) * 100`

#### Task 3: Align timeout defaults
- **Problem**: CLI sync default is 7200, config init writes 30
- **Solution**: Import and use `DEFAULT_OPERATION_TIMEOUT` (3600) consistently

#### Task 4: Expose allow_disk_mismatch
- **Problem**: `SyncOptions.allow_disk_mismatch` exists but not exposed in CLI
- **Solution**: Add `--allow-disk-mismatch` flag to sync command, pass through `client.sync_vm()`

#### Task 5: Add logging helper functions
- **Problem**: Repetitive `logger.error(..., exc_info=True)` pattern
- **Solution**: Add `log_error()`, `log_warning()`, `log_info()`, `log_debug()` module functions

#### Task 6: Preserve exception context
- **Problem**: ~6 `raise` statements lose original exception context
- **Solution**: Use `raise ... from e` pattern

#### Task 7: Fix rsync stats parsing
- **Problem**: `--stats` flag missing from actual sync command; stats go to stderr
- **Solution**: Add `--stats` to rsync command in `_sync_disk()`, parse combined output

#### Task 8: Adopt progress helpers
- **Problem**: Manual `ProgressInfo` construction duplicated in cloner.py and sync.py
- **Solution**: Use `create_disk_progress_info()` from `progress.py`

#### Task 9: Parallelize disk transfers
- **Problem**: Disk transfers are sequential despite `parallel` option
- **Solution**: Use `asyncio.Semaphore(options.parallel)` + `asyncio.gather()`

#### Task 10: Implement resource validation
- **Problem**: Stub in `_validate_clone_request()` with comment "Add resource validation logic here"
- **Solution**: Check `available_memory >= vm_info.memory` and `available_disk >= sum(disk.size)`

#### Task 11: Implement SSH host key verification
- **Problem**: `RejectPolicy()` rejects all unknown hosts, unusable in practice
- **Solution**: Create `CustomKnownHostsPolicy` that reads `~/.ssh/known_hosts`; add `--trust-host` for session-only trust (no auto-add for safety)

#### Task 12: Replace broad exception handlers
- **Problem**: 23 instances of `except Exception` across 7 files
- **Solution**: Replace with specific types: `libvirt.libvirtError`, `paramiko.SSHException`, `OSError`, `json.JSONDecodeError`

#### Task 13: Standardize type annotations
- **Problem**: Mixed `Optional[X]` and `X | None`; inconsistent `List` vs `list`
- **Solution**: Add `from __future__ import annotations` to all files; use lowercase `list`, `dict`; use `X | None` syntax

---

## Summary by Severity

| Severity | Count | Key Items |
|----------|-------|-----------|
| **CRITICAL** | 6 | ~~Progress tracking broken~~, ~~Delta calculation fake~~, Disk size/CPU monitoring still inaccurate |
| **HIGH** | 8 | ~~Resource leaks~~, ~~Silent failures in list_vms~~, Broad exception handling (23 instances), SSH host key rejection |
| **MEDIUM** | 12 | Code duplication, Magic numbers, ~~Blocking operations without thread pool~~, Serial disk transfers, Default timeout inconsistency, ~~Disk mismatch handling~~ |
| **LOW** | 8 | ~~Empty pass statements~~, Placeholder comments, Minor type annotation issues, ~~Unicode characters in output~~ |

---

## 1. COMPLETENESS ISSUES

### 1.1 Placeholder/Stub Implementations (CRITICAL) - ⏳ PARTIAL

| File | Line | Issue | Status |
|------|------|-------|--------|
| `libvirt_wrapper.py` | 169 | `disk_size = 0  # Placeholder` | ⏳ Partial - uses `blockStats` wr_bytes (not disk capacity) |
| `libvirt_wrapper.py` | 217-218 | `created`/`last_modified` set to `datetime.now()` | ⚠️ Libvirt limitation - documented |
| `libvirt_wrapper.py` | 314-315 | `total_disk=0`, `available_disk=0` | ✅ Fixed - uses `df` command |
| `libvirt_wrapper.py` | 317 | `cpu_usage=0.0` | ⏳ Partial - ALL_CPUS stats handling likely returns list |
| `sync.py` | 215-232 | Delta calculation uses hardcoded 10% estimate | ✅ Fixed - uses `rsync --dry-run --stats` |
| `sync.py` | 365-373 | Rsync stats parsing returns zeros | ⚠️ Needs verification - parsing only stdout |

**Action Items:**
- [ ] Implement actual disk size retrieval using `blockInfo`/`domblkinfo` (blockStats wr_bytes is not size)
- [ ] Store/fetch actual VM creation and modification times from libvirt (Libvirt limitation)
- [x] Implement actual disk space checking on destination host
- [ ] Implement CPU usage monitoring via libvirt CPU stats (handle ALL_CPUS return shape)
- [x] Implement proper delta calculation using `rsync --dry-run`
- [ ] Parse actual rsync output for transfer statistics (capture correct stream or add `--stats`)

### 1.2 Comments Suggesting Incomplete Features - ⏳ PARTIAL

| File | Lines | Comment | Status |
|------|-------|---------|--------|
| `libvirt_wrapper.py` | 268 | `# Add resource validation logic here` | ⚠️ Documented limitation |
| `sync.py` | 221 | `# In a real implementation...` | ✅ Implemented |
| `sync.py` | 368 | `# In a real implementation...` | ✅ Implemented |

**Action Items:**
- [ ] Add actual resource sufficiency validation (deferred - requires design)
- [x] Implement rsync dry-run for accurate delta calculation
- [x] Implement rsync output parsing for real statistics

---

## 2. CODE SMELLS

### 2.1 Excessive Broad Exception Handling (HIGH) - ⏳ IN PROGRESS

**Pattern**: `except Exception as e` used 23 times across the codebase.

| File | Function | Issue | Status |
|------|----------|-------|--------|
| `transport.py` | connect/execute/transfer | Catches all exceptions | ⏳ Pending |
| `client.py` | list_vms, __aexit__ | Broad exception handlers remain | ⏳ Pending |
| `cloner.py` | validation/transfer | Broad exception handlers | ⏳ Pending |
| `sync.py` | sync/delta/checkpoint | Broad exception handlers | ⏳ Pending |
| `libvirt_wrapper.py` | connect/cleanup | Broad exception handlers | ⏳ Pending |
| `cli.py` | clone/sync/list | Broad exception handlers | ⏳ Pending |
| `config.py` | ConfigLoader._load_from_file | Broad exception handler | ⏳ Pending |

**Action Items:**
- [ ] Replace remaining `except Exception` with specific exception types
- [ ] Add separate handler for `KeyboardInterrupt` and `SystemExit`
- [ ] Ensure critical errors are propagated

### 2.2 Code Duplication (MEDIUM) - ⏳ PARTIAL

| Pattern | Locations | Status |
|---------|-----------|--------|
| ProgressInfo construction | `cloner.py:127-142`, `sync.py:110-124` | ⏳ Partial - helpers exist but not used |
| VM state mapping | `libvirt_wrapper.py:139-147` | ✅ Extracted to `LIBVIRT_STATE_MAP` |
| SSH connection setup | `transport.py:52-72` | ✅ Refactored with TTL/reuse |
| Error logging pattern | `logger.error(..., exc_info=True)` | ⏳ Pending - helper functions |

**Action Items:**
- [x] Extract ProgressInfo construction into helper module
- [ ] Refactor cloner/sync to use `progress.py` helpers
- [x] Move VM state mapping to module-level constant
- [x] Refactor SSH connection setup to reduce duplication
- [ ] Create error logging helper function

### 2.3 Magic Numbers (MEDIUM) - ✅ COMPLETED

| File | Value | Status |
|------|-------|--------|
| `sync.py` | 0.1, 4096, 100 MB/s | ✅ Created `constants.py` |
| `libvirt_wrapper.py` | MAC prefix `52:54:00:` | ✅ Created `LIBVIRT_MAC_PREFIX` |
| `models.py` | `parallel: int = 4` | ✅ Created `DEFAULT_PARALLEL_TRANSFERS` |

**Action Items:**
- [x] Define all constants in `constants.py`
- [x] Update all files to use constants

### 2.4 Dead Code / Unused Variables - ✅ COMPLETED

| File | Lines | Issue | Status |
|------|-------|---------------------------------------------------------------|
| `cloner.py` | 123-124 | `total_bytes = 0` never updated | ✅ Fixed |
| `sync.py` | 93-94 | `total_bytes = 0` never updated | ✅ Fixed |

**Action Items:**
- [x] Fix `total_bytes` calculation in cloner.py
- [x] Fix `total_bytes` calculation in sync.py

### 2.5 Inconsistent Type Annotations - ⏳ PENDING

| File | Issue | Status |
|------|-------|--------|
| `libvirt_wrapper.py` | TYPE_CHECKING usage | ⏳ Pending |
| `models.py` | Optional[str] inconsistency | ⏳ Pending |

**Action Items:**
- [ ] Standardize type annotation approach
- [ ] Review and standardize Optional usage

### 2.6 Empty Pass Statements - ✅ COMPLETED

| File | Line | Context | Status |
|------|-------|---------|--------|
| `transport.py` | 261 | finally block | ✅ Added explanatory comment |
| `libvirt_wrapper.py` | 343 | exception handler | ✅ Added debug logging |
| `cli.py` | 376 | config group | ✅ Valid placeholder |

**Action Items:**
- [x] Add comment explaining why connection is kept
- [x] Add comment explaining why close errors are ignored
- [x] Document config group purpose

---

## 3. PERFORMANCE ISSUES

### 3.1 Resource Leaks (HIGH) - ✅ COMPLETED

| File | Lines | Issue | Status |
|------|-------|---------------------------------------------------------------|
| `libvirt_wrapper.py` | 337-345 | Connections never cleaned up | ✅ Added TTL + `cleanup_stale_connections()` |
| `transport.py` | 232, 241-261 | Connections never closed | ✅ Added TTL + LRU eviction |
| `client.py` | __aexit__ | Missing cleanup | ✅ Added full cleanup |

**Action Items:**
- [x] Implement connection TTL/timeout for cached connections
- [x] Add automatic cleanup in `__aexit__` of KVMCloneClient
- [x] Add connection validation before reuse (`is_alive()`)
- [x] Implement max connection pool size with LRU eviction

### 3.2 Blocking Operations in Async Context (MEDIUM) - ✅ COMPLETED

| File | Lines | Issue | Status |
|------|-------|---------------------------------------------------------------|
| `transport.py` | 68-72, 112-114, etc. | Uses default executor | ✅ Added dedicated `ThreadPoolExecutor` |

**Action Items:**
- [x] Create dedicated thread pool for SSH operations
- [x] Configure executor with appropriate max_workers (10)

### 3.3 Inefficient Patterns - ⏳ PARTIAL

| File | Issue | Status |
|------|-------|--------|
| `sync.py` | Serial disk transfer | ⏳ Pending |
| `client.py` | Sequential list_vms | ✅ Fixed - uses `asyncio.gather()` |
| `logging.py` | Dict iteration on log call | ⏳ Pending |
| `libvirt_wrapper.py` | Paused VM filtering | ✅ Uses `VIR_CONNECT_LIST_DOMAINS_PAUSED` with fallback |

**Action Items:**
- [ ] Implement parallel disk transfers using `asyncio.gather()`
- [x] Rewrite `list_vms()` to query hosts concurrently
- [ ] Cache standard attribute names in logging
- [x] Use libvirt's native filtering flags

### 3.4 Lack of Connection Pooling/Reuse Strategy - ✅ COMPLETED

| File | Issue | Status |
|------|-------|--------|
| `transport.py` | No health check on reuse | ✅ Added `is_alive()` and `is_stale()` |
| `libvirt_wrapper.py` | No health check on reuse | ✅ Added TTL-based cleanup |

**Action Items:**
- [x] Add connection health check before reuse
- [x] Implement cleanup logic for stale connections
- [x] Add connection state tracking

---

## 4. SECURITY ISSUES

### 4.1 SSH Host Key Verification (MEDIUM) - ⏳ PENDING

| File | Lines | Issue | Status |
|------|-------|---------------------------------------------------------------|
| `security.py` | 282-288 | `RejectPolicy()` breaks usability | ⏳ Pending |
| `transport.py` | 45-46 | Uses `RejectPolicy` | ⏳ Pending |

**Action Items:**
- [ ] Implement `CustomKnownHostsPolicy` reading from `~/.ssh/known_hosts`
- [ ] Add `--trust-host` flag for testing
- [ ] Document SSH host key verification behavior

### 4.2 Missing Input Validation - ⏳ PARTIAL

| File | Lines | Issue | Status |
|------|-------|---------------------------------------------------------------|
| `cli.py` | default_timeout: 30 | ⏳ Partial - config init still writes 30; sync default is 7200 |
| `config.py` | default_timeout: 30 | ✅ Fixed - uses `DEFAULT_OPERATION_TIMEOUT` |
| `models.py` | parallel: int = 4 | ✅ Fixed - added upper bound validation (le=32) |

**Action Items:**
- [ ] Consolidate timeout defaults to 3600s (CLI sync + config init)
- [x] Add max_parallel limit validation (max 32)

---

## 5. ERROR HANDLING ISSUES

### 5.1 Silent Failures (HIGH) - ✅ COMPLETED

| File | Lines | Issue | Status |
|------|-------|---------------------------------------------------------------|
| `client.py:221-223` | `list_vms()` returns empty list | ✅ Fixed - returns error strings |
| `libvirt_wrapper.py:342-343` | Close errors ignored | ✅ Fixed - logs at debug level |

**Action Items:**
- [x] Modify `list_vms()` to return `Dict[str, Union[List[VMInfo], str]]`
- [x] Log connection close errors at debug level

### 5.2 Loss of Exception Context - ⏳ PENDING

| File | Lines | Issue | Status |
|------|-------|---------------------------------------------------------------|
| `sync.py:375-377` | Loses validation context | ⏳ Pending |
| `cloner.py:341-344` | Loses validation context | ⏳ Pending |

**Action Items:**
- [ ] Use `raise ... from e` to preserve exception chain

### 5.3 Inconsistent Error Returns - ✅ COMPLETED

| File | Issue | Status |
|------|-------|--------|
| `cli.py` | Unicode checkmarks | ✅ Replaced with ASCII [OK]/[ERROR] |

**Action Items:**
- [x] Replace Unicode checkmark/cross with ASCII equivalents

---

## 6. LOGIC BUGS

### 6.1 Progress Tracking Broken (HIGH) - ✅ COMPLETED

| File | Lines | Issue | Status |
|------|-------|---------------------------------------------------------------|
| `cloner.py:123-124` | `total_bytes` never updated | ✅ Fixed - calculates sum before loop |
| `sync.py:93-94` | `total_bytes` never updated | ✅ Fixed - calculates sum before loop |

**Action Items:**
- [x] Calculate `total_bytes` before transfer
- [x] Handle case where total_bytes is 0 (avoid division by zero)

### 6.2 Disk Mismatch Warning Not Handled (MEDIUM) - ⏳ PARTIAL

| File | Lines | Issue | Status |
|------|-------|---------------------------------------------------------------|
| `sync.py:98-104` | Warning only, sync continues | ✅ Fixed - raises `ValidationError` by default (CLI flag still missing) |

**Action Items:**
- [x] Make disk count mismatch an error by default
- [x] Add `allow_disk_mismatch` flag to `SyncOptions`
- [x] Document behavior in error message
- [ ] Expose `allow_disk_mismatch` in CLI and `KVMCloneClient.sync_vm`

---

## 7. POSITIVE FINDINGS (No Action Needed)

The codebase also has several good practices:

1. **Security**: Good input validation via `SecurityValidator` class
2. **Command building**: Proper use of `shlex.quote()` to prevent injection
3. **Type safety**: Extensive use of Pydantic for configuration validation
4. **Structured logging**: JSON-formatted logging with context
5. **Async/await**: Proper use of async patterns throughout
6. **Context managers**: Proper use of `@asynccontextmanager` for SSH connections
7. **Path security**: `is_relative_to()` check for path traversal prevention
8. **Comprehensive exceptions**: Well-defined exception hierarchy with error codes

---

## NEW FILES CREATED

1. **`src/kvm_clone/constants.py`** - Centralized constants module
2. **`src/kvm_clone/progress.py`** - Progress tracking helper functions

---

## MODIFIED FILES

1. `src/kvm_clone/libvirt_wrapper.py` - Major refactoring (TTL, cleanup, stats)
2. `src/kvm_clone/transport.py` - Major refactoring (TTL, LRU, thread pool)
3. `src/kvm_clone/sync.py` - Delta calculation, rsync stats, disk mismatch
4. `src/kvm_clone/cloner.py` - Progress tracking
5. `src/kvm_clone/client.py` - Cleanup, list_vms
6. `src/kvm_clone/config.py` - Timeout defaults
7. `src/kvm_clone/models.py` - allow_disk_mismatch, constants
8. `src/kvm_clone/cli.py` - ASCII markers
9. `src/kvm_clone/__init__.py` - Exports
