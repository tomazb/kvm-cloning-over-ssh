"""
Constants for KVM cloning operations.

This module defines all magic numbers and configuration defaults used throughout
the codebase, providing a single source of truth for common values.
"""

from __future__ import annotations

# Transfer defaults
DEFAULT_BLOCK_SIZE = 4096  # bytes (4KB blocks)
DEFAULT_NETWORK_SPEED_MBPS = 100  # MB/s
DEFAULT_NETWORK_SPEED_BYTES = DEFAULT_NETWORK_SPEED_MBPS * 1024 * 1024
DEFAULT_PARALLEL_TRANSFERS = 4

# Delta calculation defaults
DEFAULT_DELTA_RATIO = 0.1  # 10% estimate (fallback only)

# Libvirt constants
LIBVIRT_MAC_PREFIX = "52:54:00:"  # Standard libvirt MAC prefix

# Connection defaults
DEFAULT_CONNECTION_TTL = 300  # seconds (5 minutes)
DEFAULT_MAX_CONNECTIONS = 50
DEFAULT_SSH_TIMEOUT = 30  # seconds
DEFAULT_OPERATION_TIMEOUT = 3600  # seconds (1 hour) - for VM operations

# Disk defaults
DEFAULT_DISK_POOL_PATH = "/var/lib/libvirt/images"

# Logging
DEFAULT_LOG_LEVEL = "INFO"

# Config keys (for consistent access)
CONFIG_SSH_KEY_PATH = "ssh_key_path"
CONFIG_TIMEOUT = "default_timeout"
CONFIG_PARALLEL_TRANSFERS = "default_parallel_transfers"
CONFIG_BANDWIDTH_LIMIT = "default_bandwidth_limit"
CONFIG_LOG_LEVEL = "log_level"
CONFIG_KNOWN_HOSTS_FILE = "known_hosts_file"
