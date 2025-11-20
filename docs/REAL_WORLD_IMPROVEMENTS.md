# Real-World Usability Improvements

This document describes the comprehensive improvements made to enhance the real-world usability of the KVM cloning over SSH tool.

## Summary of Improvements

The following critical improvements have been implemented to make this tool production-ready:

### 1. SSH Agent Support and Configuration Reading ✅

**Problem**: Tool only supported explicit SSH key paths, making it difficult for users who rely on SSH agents or existing SSH configurations.

**Solution**:
- **SSH Agent Support**: Automatically tries SSH agent first before falling back to explicit keys
- **SSH Config File Reading**: Reads `~/.ssh/config` for host aliases, ports, usernames, and identity files
- **Identity File Detection**: Automatically uses IdentityFile entries from SSH config

**Benefits**:
- Users can use existing SSH infrastructure without changes
- Supports host aliases (e.g., `kvm-clone clone my-host ...` works with SSH config Host entries)
- No need to specify username or port if configured in SSH config
- Works seamlessly with SSH agent (ssh-add)

**Usage Example**:
```bash
# If you have this in ~/.ssh/config:
# Host production
#   HostName prod.example.com
#   User admin
#   Port 2222
#   IdentityFile ~/.ssh/prod_key

# You can simply use:
kvm-clone clone production dest-host vm-name

# No need to specify --ssh-key, username, or port!
```

---

### 2. Username Auto-Detection ✅

**Problem**: Tool defaulted to 'root' which often failed, requiring users to always specify username.

**Solution**:
- Automatically detects username from:
  1. Explicit `--username` parameter (highest priority)
  2. SSH config file `User` directive
  3. Current user environment variables (`$USER`, `$USERNAME`)
  4. Current process user (as fallback)

**Benefits**:
- Works out of the box for most users
- No need to repeatedly specify username
- Respects SSH config preferences

---

### 3. Connection Retry Logic with Exponential Backoff ✅

**Problem**: Single connection failures caused immediate operation failure, even for transient network issues.

**Solution**:
- Automatic retry for network errors (up to 3 attempts by default)
- Exponential backoff: 1s, 2s, 4s between retries
- Smart retry decision:
  - Retries: Network errors, connection refused, timeout
  - No retry: Authentication failures (won't succeed anyway)
- Configurable retry count via `SSHTransport(max_retries=N)`

**Benefits**:
- Resilient to temporary network hiccups
- Reduced failures due to transient issues
- Clear logging of retry attempts

**Log Example**:
```
WARNING: Connection refused to host.example.com, retrying in 1s (attempt 1/3)
WARNING: Network error connecting to host.example.com: timeout, retrying in 2s (attempt 2/3)
INFO: SSH connection established to host.example.com:22 as myuser (attempt 3/3)
```

---

### 4. Actionable Error Messages ✅

**Problem**: Generic error messages didn't tell users HOW to fix problems.

**Solution**:
Comprehensive, context-aware error messages with step-by-step remediation:

#### Authentication Errors
```
Authentication failed for user@hostname

Possible solutions:
1. Verify your SSH key is authorized on the remote host:
   ssh-copy-id -i ~/.ssh/id_rsa.pub user@hostname

2. Check that your SSH key exists and has correct permissions:
   ls -l /path/to/key
   chmod 600 /path/to/key

3. Make sure SSH agent is running with your key loaded:
   ssh-add -l
   ssh-add ~/.ssh/id_rsa

4. Test SSH connection manually:
   ssh -v user@hostname
```

#### Host Key Verification Errors
```
Host key verification failed for hostname.

Possible solutions:
1. Add the host to your known_hosts file by connecting manually:
   ssh hostname

2. If you trust this host, add to your SSH config (~/.ssh/config):
   Host hostname
       StrictHostKeyChecking accept-new

3. For testing only (NOT recommended for production):
   Set environment variable: KVM_CLONE_SSH_HOST_KEY_POLICY=warn
```

#### Network Errors
```
Network error connecting to hostname:22: Connection timeout
Please check network connectivity and hostname.
```

**Benefits**:
- Users can self-service common issues
- Reduced support burden
- Faster problem resolution
- Educational for new users

---

### 5. Configurable Host Key Policy ✅

**Problem**: Strict RejectPolicy made initial setup difficult, blocking ALL unknown hosts.

**Solution**:
Environment variable `KVM_CLONE_SSH_HOST_KEY_POLICY` with three modes:

- **`strict`** (default): Reject unknown hosts - most secure
- **`warn`**: Warn but accept unknown hosts - for trusted networks
- **`accept`**: Auto-accept unknown hosts - testing only, not recommended

**Usage**:
```bash
# For production (default)
kvm-clone clone source dest vm-name

# For testing/development
KVM_CLONE_SSH_HOST_KEY_POLICY=warn kvm-clone clone source dest vm-name

# For automated testing only (insecure!)
KVM_CLONE_SSH_HOST_KEY_POLICY=accept kvm-clone clone source dest vm-name
```

**Benefits**:
- Secure by default
- Flexible for different environments
- Clear warnings when using insecure modes
- Respects security best practices

---

### 6. Environment Variable Configuration Overrides ✅

**Problem**: No way to override configuration without editing files, making CI/CD and automation difficult.

**Solution**:
Full environment variable support for all configuration options:

| Environment Variable | Configuration Key | Example |
|---------------------|-------------------|---------|
| `KVM_CLONE_SSH_KEY_PATH` | ssh_key_path | `~/.ssh/production_key` |
| `KVM_CLONE_SSH_PORT` | ssh_port | `2222` |
| `KVM_CLONE_TIMEOUT` | default_timeout | `60` |
| `KVM_CLONE_LOG_LEVEL` | log_level | `DEBUG` |
| `KVM_CLONE_KNOWN_HOSTS_FILE` | known_hosts_file | `~/.ssh/known_hosts_prod` |
| `KVM_CLONE_PARALLEL_TRANSFERS` | default_parallel_transfers | `8` |
| `KVM_CLONE_BANDWIDTH_LIMIT` | default_bandwidth_limit | `100M` |
| `KVM_CLONE_SSH_HOST_KEY_POLICY` | - | `strict`/`warn`/`accept` |

**Configuration Priority** (highest to lowest):
1. Environment variables
2. Explicit config file (`--config`)
3. Default config locations
4. Built-in defaults

**Usage Example**:
```bash
# Override for single operation
KVM_CLONE_LOG_LEVEL=DEBUG KVM_CLONE_TIMEOUT=120 \
  kvm-clone clone source dest vm-name

# Set for entire session
export KVM_CLONE_SSH_KEY_PATH=~/.ssh/prod_key
export KVM_CLONE_LOG_LEVEL=INFO
kvm-clone clone ...  # Uses environment settings

# Perfect for CI/CD
env:
  KVM_CLONE_SSH_KEY_PATH: ${{ secrets.SSH_KEY_PATH }}
  KVM_CLONE_SSH_HOST_KEY_POLICY: warn
```

**Benefits**:
- Easy automation and scripting
- CI/CD friendly
- No file editing required
- Temporary overrides for testing

---

### 7. Bandwidth Limiting for Clone Operations ✅

**Problem**: Clone operations could saturate network links, impacting other services.

**Solution**:
Added `--bandwidth-limit` option to clone command (previously only available for sync).

**Usage**:
```bash
# Limit to 100 megabytes per second
kvm-clone clone source dest vm-name --bandwidth-limit 100M

# Limit to 1 gigabyte per second
kvm-clone clone source dest vm-name -b 1G

# Set default in config
kvm-clone config set default_bandwidth_limit 100M
```

**Benefits**:
- Prevents network saturation
- Production-friendly cloning
- Fair bandwidth sharing
- Configurable per-operation or globally

---

### 8. Enhanced Configuration Management Commands ✅

**Problem**: No way to view or modify configuration from CLI, forcing manual YAML editing.

**Solution**:
Complete suite of configuration management commands:

#### `kvm-clone config init`
Initialize default configuration file:
```bash
kvm-clone config init
# Creates ~/.config/kvm-clone/config.yaml with sensible defaults
```

#### `kvm-clone config list`
List all configuration values:
```bash
kvm-clone config list
# Output:
# Configuration from ~/.config/kvm-clone/config.yaml:
#   default_bandwidth_limit: 100M
#   default_parallel_transfers: 4
#   log_level: INFO
#   ssh_port: 22
```

#### `kvm-clone config get <key>`
Get a specific configuration value:
```bash
kvm-clone config get log_level
# Output: log_level: INFO
```

#### `kvm-clone config set <key> <value>`
Set a configuration value:
```bash
kvm-clone config set log_level DEBUG
# Output: ✓ Set log_level = DEBUG

kvm-clone config set default_bandwidth_limit 100M
# Output: ✓ Set default_bandwidth_limit = 100M

# Smart type conversion
kvm-clone config set default_parallel_transfers 8  # Stored as int
kvm-clone config set ssh_key_path null              # Stored as None
```

#### `kvm-clone config unset <key>`
Remove a configuration value:
```bash
kvm-clone config unset default_bandwidth_limit
# Output: ✓ Removed default_bandwidth_limit
```

#### `kvm-clone config path`
Show configuration file locations:
```bash
kvm-clone config path
# Output:
# Configuration search paths (in order):
#   1. ✓ /home/user/.config/kvm-clone/config.yaml
#   2. ✗ /etc/kvm-clone/config.yaml
#   3. ✗ config.yaml
#
# Currently using: /home/user/.config/kvm-clone/config.yaml
```

**Benefits**:
- No manual YAML editing required
- Discoverable configuration options
- Type-safe value conversion
- Easy troubleshooting (config path command)
- Consistent with modern CLI tools

---

## Quick Start with Improvements

### First-Time Setup

1. **Initialize configuration**:
   ```bash
   kvm-clone config init
   ```

2. **Set your preferences** (optional):
   ```bash
   kvm-clone config set log_level INFO
   kvm-clone config set default_bandwidth_limit 100M
   ```

3. **Test SSH connection** to your host:
   ```bash
   ssh myhost  # If this works, kvm-clone will work too
   ```

4. **Clone a VM**:
   ```bash
   kvm-clone clone source-host dest-host my-vm
   ```

### Common Workflows

#### Using with SSH Agent
```bash
# Start SSH agent and add your key
eval $(ssh-agent)
ssh-add ~/.ssh/id_rsa

# Clone without specifying key
kvm-clone clone source dest vm-name
```

#### Using with SSH Config
```bash
# ~/.ssh/config
Host prod
  HostName production.example.com
  User admin
  Port 2222
  IdentityFile ~/.ssh/prod_key

# Use the alias
kvm-clone clone prod dest vm-name
```

#### CI/CD Pipeline
```bash
# Set environment for automated operations
export KVM_CLONE_SSH_HOST_KEY_POLICY=warn
export KVM_CLONE_SSH_KEY_PATH=/secrets/ssh_key
export KVM_CLONE_LOG_LEVEL=INFO

# Run clone operation
kvm-clone clone source dest vm-name --bandwidth-limit 50M
```

#### Debugging Connection Issues
```bash
# Enable debug logging
KVM_CLONE_LOG_LEVEL=DEBUG kvm-clone clone source dest vm-name

# Or set it in config
kvm-clone config set log_level DEBUG
kvm-clone clone source dest vm-name
```

---

## Migration Guide

### From Manual SSH Key Management

**Before**:
```bash
kvm-clone clone source dest vm-name \
  --ssh-key ~/.ssh/id_rsa \
  --username myuser
```

**After**:
```bash
# Just use SSH agent or SSH config
kvm-clone clone source dest vm-name
```

### From Hardcoded Configuration

**Before**:
- Edit config.yaml manually
- No environment variable support
- Restart required

**After**:
```bash
# Set once
kvm-clone config set default_bandwidth_limit 100M

# Or override for one operation
KVM_CLONE_BANDWIDTH_LIMIT=200M kvm-clone clone ...
```

---

## Troubleshooting

### Connection Issues

1. **Check configuration**:
   ```bash
   kvm-clone config path
   kvm-clone config list
   ```

2. **Test SSH manually**:
   ```bash
   ssh -v hostname  # Verbose output shows what's wrong
   ```

3. **Enable debug logging**:
   ```bash
   KVM_CLONE_LOG_LEVEL=DEBUG kvm-clone clone source dest vm-name
   ```

4. **Check SSH agent**:
   ```bash
   ssh-add -l  # List loaded keys
   ssh-add ~/.ssh/id_rsa  # Add key if needed
   ```

### Host Key Verification Failures

1. **Add host to known_hosts**:
   ```bash
   ssh hostname  # Accept key interactively
   ```

2. **For testing only**:
   ```bash
   KVM_CLONE_SSH_HOST_KEY_POLICY=warn kvm-clone clone ...
   ```

### Authentication Failures

1. **Verify key is authorized**:
   ```bash
   ssh-copy-id -i ~/.ssh/id_rsa.pub user@hostname
   ```

2. **Check key permissions**:
   ```bash
   chmod 600 ~/.ssh/id_rsa
   ```

3. **Test with verbose SSH**:
   ```bash
   ssh -vvv hostname
   ```

---

## Best Practices

### Security

1. **Always use strict mode in production**:
   ```bash
   # Default is strict, which is good
   # Only use warn/accept for development
   ```

2. **Use SSH config for host verification**:
   ```bash
   # ~/.ssh/config
   Host production-*
       StrictHostKeyChecking yes

   Host dev-*
       StrictHostKeyChecking accept-new
   ```

3. **Protect your SSH keys**:
   ```bash
   chmod 600 ~/.ssh/id_rsa
   ```

### Performance

1. **Use bandwidth limiting in production**:
   ```bash
   kvm-clone config set default_bandwidth_limit 100M
   ```

2. **Adjust parallel transfers based on network**:
   ```bash
   # For fast local network
   kvm-clone clone source dest vm --parallel 8

   # For WAN connections
   kvm-clone clone source dest vm --parallel 2
   ```

### Automation

1. **Use environment variables in CI/CD**:
   ```yaml
   env:
     KVM_CLONE_SSH_KEY_PATH: ${{ secrets.SSH_KEY }}
     KVM_CLONE_SSH_HOST_KEY_POLICY: warn
     KVM_CLONE_LOG_LEVEL: INFO
   ```

2. **Create wrapper scripts**:
   ```bash
   #!/bin/bash
   # clone-to-backup.sh
   export KVM_CLONE_SSH_KEY_PATH=~/.ssh/backup_key
   export KVM_CLONE_BANDWIDTH_LIMIT=50M

   kvm-clone clone "$@"
   ```

---

## What's Next

Future improvements planned:

- **Cleanup on failure**: Automatic removal of partial artifacts when operations fail
- **Pre-flight checks**: Disk space and permission validation before starting
- **Resume capability**: Continue interrupted transfers from where they left off
- **Real progress tracking**: Byte-level progress with accurate ETAs
- **Better dry-run**: Show detailed transfer plan before executing

---

## Summary

These improvements transform kvm-clone from a prototype to a production-ready tool:

- ✅ Works with existing SSH infrastructure (agent, config)
- ✅ Auto-detects sensible defaults (username, keys)
- ✅ Resilient to network issues (retries, backoff)
- ✅ Helpful error messages (actionable solutions)
- ✅ Flexible security policies (strict/warn/accept)
- ✅ Easy configuration (CLI commands, environment variables)
- ✅ Production-friendly (bandwidth limiting)

The tool now provides an excellent user experience while maintaining security and reliability.
