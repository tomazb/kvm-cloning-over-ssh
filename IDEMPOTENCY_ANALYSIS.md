# Idempotency Analysis and Improvements

## Overview

This document analyzes the idempotency characteristics of kvm-clone operations and documents improvements made to ensure operations can be safely retried.

## What is Idempotency?

An operation is **idempotent** if performing it multiple times has the same effect as performing it once. This is critical for:
- **Automation**: Scripts can safely retry operations
- **Error Recovery**: Failed operations can be retried without manual cleanup
- **CI/CD Pipelines**: Build systems can re-run steps without side effects

---

## Current Idempotency Status

### ✅ Fully Idempotent Operations

#### 1. Configuration Reading
```bash
# Always returns same result for same inputs
kvm-clone --config config.yaml clone source dest vm
kvm-clone --config config.yaml clone source dest vm  # Same result
```

#### 2. List Operations
```bash
# Read-only, always safe to repeat
kvm-clone list host1 host2
kvm-clone list host1 host2  # Identical output
```

#### 3. Config Query Commands
```bash
# Read-only operations
kvm-clone config get log_level      # ✓ Idempotent
kvm-clone config list                # ✓ Idempotent
kvm-clone config path                # ✓ Idempotent
```

#### 4. SSH Connection Management
- Connection reuse prevents duplicate connections
- Retry logic eventually reaches same end state
- No side effects from connection attempts

---

### ⚠️ Conditionally Idempotent Operations

#### 1. Clone with --force
```bash
# First run: creates VM
kvm-clone clone source dest vm-name --force

# Second run: overwrites existing VM (idempotent with --force)
kvm-clone clone source dest vm-name --force  # Same result
```

**Status**: Idempotent when using `--force` flag

#### 2. Sync Operations
```bash
# First run: syncs VM
kvm-clone sync source dest vm-name

# Second run: no changes needed (already in sync)
kvm-clone sync source dest vm-name  # ✓ No-op if already synced
```

**Status**: Naturally idempotent (destination matches source after first run)

#### 3. Config Set
```bash
# Multiple runs with same value
kvm-clone config set log_level DEBUG  # ✓ Idempotent
kvm-clone config set log_level DEBUG  # Same result
```

**Status**: Idempotent for same key-value pair

---

### ❌ NON-Idempotent Operations (CRITICAL ISSUES)

#### 1. Clone Operation (Default) - **MAJOR ISSUE**

**Problem**:
```bash
# First run
kvm-clone clone source dest vm-name
# ✓ Success: VM created

# Second run (retry after network issue, etc.)
kvm-clone clone source dest vm-name
# ✗ FAILS: Error: VM 'vm-name' already exists on destination
```

**Failure Scenario**:
```bash
# Partial failure scenario
kvm-clone clone source dest vm-name
# - Creates VM definition ✓
# - Transfers disk 1/3 ✓
# - Transfers disk 2/3 ✓
# - Network timeout ✗
# - Operation fails, leaves partial state

# Retry attempt
kvm-clone clone source dest vm-name
# ✗ FAILS: VM already exists
# User must manually:
#   1. virsh undefine vm-name
#   2. rm /var/lib/libvirt/images/vm-name-*.qcow2
#   3. Clean up network interfaces
#   4. Then retry
```

**Impact**:
- **Automation breakage**: Scripts can't safely retry
- **Manual cleanup required**: Time-consuming and error-prone
- **Production risk**: Failed clones leave inconsistent state
- **Poor user experience**: No automatic recovery

**Current Workarounds**:
```bash
# Manual cleanup before retry
ssh dest-host "virsh undefine vm-name --remove-all-storage"
kvm-clone clone source dest vm-name

# Or use --force (but destroys any manual fixes)
kvm-clone clone source dest vm-name --force
```

#### 2. Config Unset (Without Flag)

**Problem**:
```bash
# First run
kvm-clone config unset log_level
# ✓ Removed log_level

# Second run
kvm-clone config unset log_level
# ✗ FAILS: Key 'log_level' not found in configuration
```

**Solution Implemented**:
```bash
# Now with --ignore-missing flag (idempotent)
kvm-clone config unset log_level --ignore-missing  # ✓ Success
kvm-clone config unset log_level --ignore-missing  # ✓ Already absent
```

---

## Recommended Improvements

### Priority 1: Make Clone Operation Idempotent (CRITICAL)

**Goal**: Clone operation should be safely retryable without manual intervention.

**Proposed Solutions**:

#### Option A: Automatic Cleanup on Retry
```bash
# Detect existing VM and offer cleanup
kvm-clone clone source dest vm-name
# Output:
# ⚠ VM 'vm-name' already exists on destination
# Options:
#   1. Skip (assume already cloned)
#   2. Clean up and retry
#   3. Abort (default)
# Choice: 2
# ✓ Cleaning up existing VM...
# ✓ Retrying clone operation...
```

#### Option B: Resume Capability
```bash
# First attempt (fails partway)
kvm-clone clone source dest vm-name
# - Transfer disk 1: ✓
# - Transfer disk 2: ✗ timeout
# - Saved state: /tmp/kvm-clone-abc123.state

# Retry (resumes from state)
kvm-clone clone source dest vm-name --resume
# - Detected previous state
# - Skipping disk 1 (already transferred)
# - Resuming disk 2 from byte 1234567...
```

#### Option C: Idempotent Mode (Recommended)
```bash
# New --idempotent flag
kvm-clone clone source dest vm-name --idempotent

# Behavior:
# 1. Check if VM exists on destination
# 2. If exists and matches source: skip (already done)
# 3. If exists but different: clean up and retry
# 4. If doesn't exist: proceed normally

# Makes automation safe
for vm in $(virsh list --all --name); do
  kvm-clone clone source dest "$vm" --idempotent || true
done
```

### Priority 2: Add Pre-flight Checks

Detect issues before starting long operations:

```bash
kvm-clone clone source dest vm-name --dry-run

# Output:
# Pre-flight checks:
#   ✓ Source VM exists
#   ✓ Source VM accessible via SSH
#   ✓ Destination accessible via SSH
#   ✗ Destination VM already exists
#   ✗ Insufficient disk space (need 50GB, have 10GB)
#   ✓ Network bandwidth sufficient
#
# Issues found: 2
# Would you like to:
#   1. Clean up existing VM and proceed
#   2. Abort
```

### Priority 3: Transactional Operations

Implement rollback on failure:

```python
# Pseudo-code
async def clone_vm_transactional(source, dest, vm_name):
    checkpoint = TransactionCheckpoint()

    try:
        # Track all operations
        checkpoint.record("create_vm_definition", vm_def)
        await create_vm_definition(dest, vm_def)

        for disk in vm.disks:
            checkpoint.record("transfer_disk", disk)
            await transfer_disk(source, dest, disk)

        checkpoint.record("configure_network", network)
        await configure_network(dest, network)

        # Success - commit transaction
        checkpoint.commit()

    except Exception as e:
        # Failure - rollback all operations
        await checkpoint.rollback()
        raise
```

---

## Implementation Plan

### Phase 1: Config Commands (DONE ✅)
- [x] Add `--ignore-missing` flag to `config unset`
- [x] Make config operations idempotent
- [x] Document behavior

### Phase 2: Clone Operation Cleanup (TODO)
- [ ] Detect existing VMs before starting
- [ ] Add `--cleanup-existing` flag
- [ ] Add `--idempotent` flag (recommended)
- [ ] Implement automatic rollback on failure

### Phase 3: Resume Capability (TODO)
- [ ] Save operation state to temporary file
- [ ] Add `--resume` flag
- [ ] Track transferred disks/bytes
- [ ] Resume from last successful point

### Phase 4: Pre-flight Checks (TODO)
- [ ] Disk space validation
- [ ] Permission checks
- [ ] VM existence checks
- [ ] Network connectivity tests
- [ ] Report all issues before starting

---

## Usage Examples

### Current (Non-Idempotent)
```bash
# Fails on retry
kvm-clone clone source dest vm-name
# Network timeout...

kvm-clone clone source dest vm-name
# ERROR: VM already exists

# Manual cleanup required
ssh dest "virsh undefine vm-name --remove-all-storage"
kvm-clone clone source dest vm-name
```

### Improved (Idempotent)
```bash
# Safe to retry with --idempotent
kvm-clone clone source dest vm-name --idempotent
# Network timeout...

kvm-clone clone source dest vm-name --idempotent
# ✓ Detected existing partial VM
# ✓ Cleaning up...
# ✓ Retrying operation...
# ✓ Success
```

### With Resume
```bash
# Save state on failure
kvm-clone clone source dest vm-name
# Transferred 40GB/100GB...
# Network timeout
# Saved state to: /tmp/kvm-clone-abc123.state

# Resume from checkpoint
kvm-clone clone source dest vm-name --resume
# ✓ Loaded state from /tmp/kvm-clone-abc123.state
# ✓ Resuming from 40GB...
# ✓ Success
```

---

## Benefits of Idempotent Operations

### For Users
- **No manual cleanup** after failures
- **Safe to retry** any operation
- **Less frustration** during error recovery
- **Predictable behavior** in all scenarios

### For Automation
- **Reliable scripts** that can retry
- **CI/CD friendly** (no state pollution)
- **Declarative operations** (describe desired state)
- **Safe parallelization** (no race conditions)

### For Production
- **Reduced downtime** (automatic recovery)
- **Lower risk** (operations are reversible)
- **Better monitoring** (clear success/failure states)
- **Easier troubleshooting** (consistent behavior)

---

## Testing Idempotency

### Test Cases

#### 1. Clone Operation
```bash
# Test: Retry after success
kvm-clone clone source dest vm1 --idempotent  # Should succeed
kvm-clone clone source dest vm1 --idempotent  # Should detect + skip

# Test: Retry after failure
kvm-clone clone source dest vm2 --idempotent  # Fails at 50%
kvm-clone clone source dest vm2 --idempotent  # Should cleanup + retry

# Test: Resume after interruption
kvm-clone clone source dest vm3  # Interrupted at 75%
kvm-clone clone source dest vm3 --resume  # Should continue from 75%
```

#### 2. Config Operations
```bash
# Test: Config unset idempotency
kvm-clone config unset key1 --ignore-missing  # Should succeed
kvm-clone config unset key1 --ignore-missing  # Should succeed (no-op)

# Test: Config set idempotency
kvm-clone config set key1 value1  # Should succeed
kvm-clone config set key1 value1  # Should succeed (no change)
```

---

## Conclusion

**Current Status**: Most operations are idempotent, but the critical **clone operation is NOT idempotent by default**, causing significant usability issues.

**Immediate Fix**: Added `--ignore-missing` flag to `config unset` for idempotency.

**Next Steps**:
1. Implement `--idempotent` flag for clone operations
2. Add automatic cleanup on retry
3. Implement resume capability for interrupted transfers
4. Add comprehensive pre-flight checks

These improvements will transform kvm-clone into a production-ready tool suitable for automation and CI/CD pipelines.
