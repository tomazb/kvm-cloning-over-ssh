"""
Libvirt API wrapper for KVM operations.

This module provides a high-level interface to libvirt for VM management operations.
"""

from __future__ import annotations

import asyncio
import random
import shlex
import uuid
import xml.etree.ElementTree as ET
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    import libvirt
else:
    try:
        import libvirt  # type: ignore[import-untyped,import-not-found]
    except ImportError:
        libvirt = None  # type: ignore[assignment]

from .models import VMInfo, DiskInfo, NetworkInfo, VMState, ResourceInfo
from .exceptions import LibvirtError, VMNotFoundError, ConnectionError
from .transport import SSHConnection
from .logging import logger
from .constants import LIBVIRT_MAC_PREFIX, DEFAULT_DISK_POOL_PATH

# Module-level constant: libvirt state to VMState mapping
# Built lazily to avoid errors when libvirt is not installed (e.g., during testing)
LIBVIRT_STATE_MAP: Dict[int, VMState] = {}


def _init_libvirt_state_map() -> Dict[int, VMState]:
    """Initialize libvirt state map lazily."""
    global LIBVIRT_STATE_MAP
    if libvirt is not None and not LIBVIRT_STATE_MAP:
        LIBVIRT_STATE_MAP = {
            libvirt.VIR_DOMAIN_RUNNING: VMState.RUNNING,
            libvirt.VIR_DOMAIN_BLOCKED: VMState.RUNNING,
            libvirt.VIR_DOMAIN_PAUSED: VMState.PAUSED,
            libvirt.VIR_DOMAIN_SHUTDOWN: VMState.STOPPED,
            libvirt.VIR_DOMAIN_SHUTOFF: VMState.STOPPED,
            libvirt.VIR_DOMAIN_CRASHED: VMState.STOPPED,
            libvirt.VIR_DOMAIN_PMSUSPENDED: VMState.SUSPENDED,
        }
    return LIBVIRT_STATE_MAP


class LibvirtWrapper:
    """Wrapper for libvirt operations."""

    def __init__(self, connection_ttl: int = 300) -> None:
        """Initialize libvirt wrapper.

        Args:
            connection_ttl: Connection time-to-live in seconds (default: 5 minutes)
        """
        self._connections: Dict[str, Any] = {}
        self._connection_timestamps: Dict[str, float] = {}
        self._connection_ttl = connection_ttl
        # Cache: host -> (timestamp, total_cpu_time, active_cpu_time)
        self._cpu_stats_cache: Dict[str, tuple[float, int, int]] = {}

    async def connect_to_host(self, ssh_conn: SSHConnection) -> Any:
        """Connect to libvirt on a remote host via SSH."""
        try:
            # Build libvirt URI for SSH connection
            uri = f"qemu+ssh://{ssh_conn.username or 'root'}@{ssh_conn.host}/system"
            current_time = asyncio.get_event_loop().time()

            # Check if we already have a connection
            if uri in self._connections:
                conn = self._connections[uri]
                timestamp = self._connection_timestamps.get(uri, 0)

                # Check if connection is still alive and not stale
                if conn.isAlive():
                    if (current_time - timestamp) < self._connection_ttl:
                        # Connection is valid, update timestamp and return
                        self._connection_timestamps[uri] = current_time
                        return conn
                    else:
                        # Connection is stale, close and remove
                        try:
                            conn.close()
                        except Exception:
                            pass
                        del self._connections[uri]
                        del self._connection_timestamps[uri]
                else:
                    # Connection is dead, remove it
                    del self._connections[uri]
                    if uri in self._connection_timestamps:
                        del self._connection_timestamps[uri]

            # Create new connection
            conn = libvirt.open(uri)
            if not conn:
                raise LibvirtError(
                    f"Failed to connect to libvirt on {ssh_conn.host}", "connection"
                )

            self._connections[uri] = conn
            self._connection_timestamps[uri] = current_time
            logger.info(f"Connected to libvirt on {ssh_conn.host}", host=ssh_conn.host)
            return conn

        except libvirt.libvirtError as e:
            logger.error(
                f"Libvirt connection failed on {ssh_conn.host}: {e}",
                host=ssh_conn.host,
                exc_info=True,
            )
            raise LibvirtError(str(e), "connection")
        except (OSError, ConnectionError) as e:
            logger.error(
                f"Connection error to {ssh_conn.host}: {e}",
                host=ssh_conn.host,
                exc_info=True,
            )
            raise ConnectionError(str(e), ssh_conn.host)

    async def list_vms(
        self, ssh_conn: SSHConnection, status_filter: Optional[str] = None
    ) -> List[VMInfo]:
        """List VMs on a host."""
        try:
            conn = await self.connect_to_host(ssh_conn)

            # Get all domains based on filter
            if status_filter == "running":
                domains = conn.listAllDomains(libvirt.VIR_CONNECT_LIST_DOMAINS_ACTIVE)
            elif status_filter == "stopped":
                domains = conn.listAllDomains(libvirt.VIR_CONNECT_LIST_DOMAINS_INACTIVE)
            elif status_filter == "paused":
                try:
                    domains = conn.listAllDomains(
                        libvirt.VIR_CONNECT_LIST_DOMAINS_PAUSED
                    )
                except AttributeError:
                    # Fallback: filter paused manually
                    all_domains = conn.listAllDomains()
                    domains = [
                        d
                        for d in all_domains
                        if d.info()[0] == libvirt.VIR_DOMAIN_PAUSED
                    ]
            else:
                domains = conn.listAllDomains()

            vms = []
            for domain in domains:
                vm_info = await self._get_vm_info(domain, ssh_conn.host)
                vms.append(vm_info)

            return vms

        except libvirt.libvirtError as e:
            raise LibvirtError(str(e), "list_vms")

    async def get_vm_info(self, ssh_conn: SSHConnection, vm_name: str) -> VMInfo:
        """Get detailed information about a specific VM."""
        try:
            conn = await self.connect_to_host(ssh_conn)

            try:
                domain = conn.lookupByName(vm_name)
            except libvirt.libvirtError:
                raise VMNotFoundError(vm_name, ssh_conn.host)

            return await self._get_vm_info(domain, ssh_conn.host)

        except libvirt.libvirtError as e:
            raise LibvirtError(str(e), "get_vm_info")

    async def _get_vm_info(self, domain: "libvirt.virDomain", host: str) -> VMInfo:
        """Extract VM information from libvirt domain."""
        try:
            # Get basic info
            info = domain.info()
            name = domain.name()
            uuid = domain.UUIDString()

            # Map libvirt state to our enum using lazily-initialized mapping
            state_map = _init_libvirt_state_map()
            state = state_map.get(info[0], VMState.UNKNOWN)

            # Get XML configuration
            xml_desc = domain.XMLDesc(0)
            root = ET.fromstring(xml_desc)

            # Parse disk information
            disks = []
            for disk_elem in root.findall(".//disk[@type='file']"):
                source = disk_elem.find("source")
                target = disk_elem.find("target")
                driver = disk_elem.find("driver")

                if source is not None and target is not None:
                    disk_path = source.get("file", "")
                    disk_target = target.get("dev", "")
                    disk_format = (
                        driver.get("type", "raw") if driver is not None else "raw"
                    )

                    # Get disk size using libvirt blockInfo API
                    # blockInfo returns: (capacity, allocation, physical)
                    # - capacity: logical size of the disk in bytes
                    # - allocation: host storage actually used (sparse files)
                    # - physical: physical size on disk
                    disk_size = 0
                    try:
                        block_info = domain.blockInfo(disk_target)
                        if block_info and len(block_info) >= 1:
                            disk_size = block_info[0]  # capacity (logical size)
                            logger.debug(
                                f"Got disk size from libvirt blockInfo: {disk_size}",
                                disk=disk_path,
                                host=host,
                            )
                    except (libvirt.libvirtError, IndexError, AttributeError) as e:
                        logger.debug(
                            f"Could not get disk size via blockInfo for {disk_path}: {e}",
                            disk=disk_path,
                            host=host,
                        )
                        # Fallback to 0 - actual size would require SSH access to run qemu-img
                        disk_size = 0

                    disks.append(
                        DiskInfo(
                            path=disk_path,
                            size=disk_size,
                            format=disk_format,
                            target=disk_target,
                        )
                    )

            # Parse network information
            networks = []
            for interface_elem in root.findall(".//interface"):
                mac_elem = interface_elem.find("mac")
                source_elem = interface_elem.find("source")
                target_elem = interface_elem.find("target")

                if mac_elem is not None:
                    mac_address = mac_elem.get("address", "")
                    network_name = ""
                    interface_name = ""

                    if source_elem is not None:
                        network_name = source_elem.get(
                            "network", source_elem.get("bridge", "")
                        )

                    if target_elem is not None:
                        interface_name = target_elem.get("dev", "")

                    networks.append(
                        NetworkInfo(
                            interface=interface_name,
                            mac_address=mac_address,
                            network=network_name,
                        )
                    )

            return VMInfo(
                name=name,
                uuid=uuid,
                state=state,
                memory=info[1] // 1024,  # Convert KB to MB
                vcpus=info[3],
                disks=disks,
                networks=networks,
                host=host,
                created=datetime.now(),  # Libvirt doesn't track creation time
                last_modified=datetime.now(),  # Libvirt doesn't track modification time
            )

        except libvirt.libvirtError as e:
            raise LibvirtError(str(e), "parse_vm_info")

    async def clone_vm_definition(
        self,
        ssh_conn: SSHConnection,
        source_vm: str,
        target_vm: str,
        preserve_mac: bool = False,
    ) -> str:
        """Clone VM definition XML."""
        try:
            conn = await self.connect_to_host(ssh_conn)

            # Get source domain
            try:
                source_domain = conn.lookupByName(source_vm)
            except libvirt.libvirtError:
                raise VMNotFoundError(source_vm, ssh_conn.host)

            # Get XML and modify it
            xml_desc = source_domain.XMLDesc(0)
            root = ET.fromstring(xml_desc)

            # Change name
            name_elem = root.find("name")
            if name_elem is not None:
                name_elem.text = target_vm

            # Generate new UUID
            uuid_elem = root.find("uuid")
            if uuid_elem is not None:
                uuid_elem.text = str(uuid.uuid4())

            # Handle MAC addresses
            if not preserve_mac:
                for interface in root.findall(".//interface/mac"):
                    # Generate new MAC address using standard libvirt prefix
                    mac = f"{LIBVIRT_MAC_PREFIX}%02x:%02x:%02x" % (
                        random.randint(0, 255),
                        random.randint(0, 255),
                        random.randint(0, 255),
                    )
                    interface.set("address", mac)

            return ET.tostring(root, encoding="unicode")

        except libvirt.libvirtError as e:
            raise LibvirtError(str(e), "clone_vm_definition")

    async def create_vm_from_xml(
        self, ssh_conn: SSHConnection, xml_config: str
    ) -> None:
        """Create a new VM from XML configuration."""
        try:
            conn = await self.connect_to_host(ssh_conn)

            # Define the domain
            domain = conn.defineXML(xml_config)
            if not domain:
                raise LibvirtError("Failed to define VM", "create_vm")

            logger.info(
                f"VM {domain.name()} created on {ssh_conn.host}",
                vm_name=domain.name(),
                host=ssh_conn.host,
            )

        except libvirt.libvirtError as e:
            logger.error(
                f"Failed to define VM on {ssh_conn.host}: {e}",
                host=ssh_conn.host,
                exc_info=True,
            )
            raise LibvirtError(str(e), "create_vm")

    async def get_host_resources(self, ssh_conn: SSHConnection) -> ResourceInfo:
        """Get host resource information."""
        try:
            conn = await self.connect_to_host(ssh_conn)

            # Get node info
            node_info = conn.getInfo()

            # Get memory info
            mem_stats = conn.getMemoryStats(libvirt.VIR_NODE_MEMORY_STATS_ALL_CELLS)

            total_memory = mem_stats.get("total", 0) // 1024  # Convert KB to MB
            free_memory = mem_stats.get("free", 0) // 1024

            # Get CPU usage using caching mechanism
            # getCPUStats(VIR_NODE_CPU_STATS_ALL_CPUS) returns dict with keys:
            # 'kernel', 'user', 'idle', 'iowait' - all in nanoseconds
            cpu_usage = 0.0
            try:
                cpu_stats = conn.getCPUStats(libvirt.VIR_NODE_CPU_STATS_ALL_CPUS)
                if cpu_stats:
                    # Get the individual CPU time components (nanoseconds)
                    kernel = cpu_stats.get("kernel", 0)
                    user = cpu_stats.get("user", 0)
                    idle = cpu_stats.get("idle", 0)
                    iowait = cpu_stats.get("iowait", 0)
                    
                    # Total CPU time = sum of all components
                    total_cpu_time = kernel + user + idle + iowait
                    # Active CPU time = kernel + user (non-idle)
                    active_cpu_time = kernel + user
                    
                    current_time = asyncio.get_event_loop().time()
                    host = ssh_conn.host
                    
                    if host in self._cpu_stats_cache:
                        prev_time, prev_total, prev_active = self._cpu_stats_cache[host]
                        time_delta = current_time - prev_time  # seconds
                        total_delta = total_cpu_time - prev_total
                        active_delta = active_cpu_time - prev_active

                        if time_delta > 0 and total_delta > 0:
                            # CPU usage = (active_time / total_time) * 100
                            cpu_usage = (active_delta / total_delta) * 100
                            # Clamp to reasonable range [0, 100]
                            cpu_usage = max(0.0, min(100.0, cpu_usage))

                    # Cache: (time, total_cpu_time, active_cpu_time)
                    self._cpu_stats_cache[host] = (current_time, total_cpu_time, active_cpu_time)
            except (libvirt.libvirtError, AttributeError, KeyError) as e:
                logger.debug(f"Could not get CPU stats for {ssh_conn.host}: {e}")
                cpu_usage = 0.0

            # Get disk space via df command
            total_disk = 0
            available_disk = 0
            try:
                df_command = f"df -B1 {shlex.quote(DEFAULT_DISK_POOL_PATH)}"
                stdout, stderr, exit_code = await ssh_conn.execute_command(df_command)

                if exit_code == 0:
                    # Parse df output:
                    # Filesystem 1K-blocks Used Available Use% Mounted on
                    # /dev/sda1  1234567890 987654321 123456789 80% /
                    lines = stdout.strip().split('\n')
                    if len(lines) >= 2:
                        parts = lines[1].split()
                        if len(parts) >= 4:
                            total_disk = int(parts[1])
                            available_disk = int(parts[3])
            except Exception as e:
                logger.debug(f"Could not get disk space for {ssh_conn.host}: {e}")

            return ResourceInfo(
                total_memory=total_memory,
                available_memory=free_memory,
                total_disk=total_disk,
                available_disk=available_disk,
                cpu_count=node_info[2],
                cpu_usage=cpu_usage,
            )

        except libvirt.libvirtError as e:
            raise LibvirtError(str(e), "get_host_resources")

    async def vm_exists(self, ssh_conn: SSHConnection, vm_name: str) -> bool:
        """Check if a VM exists on the host."""
        try:
            conn = await self.connect_to_host(ssh_conn)

            try:
                conn.lookupByName(vm_name)
                return True
            except libvirt.libvirtError:
                return False

        except libvirt.libvirtError as e:
            raise LibvirtError(str(e), "vm_exists")

    async def cleanup_stale_connections(self) -> int:
        """Clean up stale libvirt connections.

        Returns:
            int: Number of closed connections
        """
        current_time = asyncio.get_event_loop().time()
        stale_uris = []

        for uri, conn in self._connections.items():
            timestamp = self._connection_timestamps.get(uri, 0)
            age = current_time - timestamp

            # Check if stale or dead
            if age > self._connection_ttl or not conn.isAlive():
                stale_uris.append(uri)

        for uri in stale_uris:
            conn = self._connections[uri]
            try:
                conn.close()
            except Exception as e:
                # Log at debug level - connection close errors are not critical
                logger.debug(f"Error closing libvirt connection {uri}: {e}")
            del self._connections[uri]
            del self._connection_timestamps[uri]

        if stale_uris:
            logger.info(f"Cleaned up {len(stale_uris)} stale libvirt connections")

        return len(stale_uris)

    def close_all_connections(self) -> None:
        """Close all libvirt connections."""
        for uri, conn in self._connections.items():
            try:
                conn.close()
            except Exception as e:
                # Log at debug level - connection close errors are not critical
                logger.debug(f"Error closing libvirt connection {uri}: {e}")
        self._connections.clear()
        self._connection_timestamps.clear()
        logger.info("All libvirt connections closed")
