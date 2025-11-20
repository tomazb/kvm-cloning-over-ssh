"""
Libvirt API wrapper for KVM operations.

This module provides a high-level interface to libvirt for VM management operations.
"""

import random
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


class LibvirtWrapper:
    """Wrapper for libvirt operations."""

    def __init__(self) -> None:
        """Initialize libvirt wrapper."""
        self._connections: Dict[str, Any] = {}

    async def connect_to_host(self, ssh_conn: SSHConnection) -> Any:
        """Connect to libvirt on a remote host via SSH."""
        try:
            # Build libvirt URI for SSH connection
            uri = f"qemu+ssh://{ssh_conn.username or 'root'}@{ssh_conn.host}/system"

            # Check if we already have a connection
            if uri in self._connections:
                conn = self._connections[uri]
                if conn.isAlive():
                    return conn
                else:
                    # Connection is dead, remove it
                    del self._connections[uri]

            # Create new connection
            conn = libvirt.open(uri)
            if not conn:
                raise LibvirtError(
                    f"Failed to connect to libvirt on {ssh_conn.host}", "connection"
                )

            self._connections[uri] = conn
            logger.info(f"Connected to libvirt on {ssh_conn.host}", host=ssh_conn.host)
            return conn

        except libvirt.libvirtError as e:
            logger.error(
                f"Libvirt connection failed on {ssh_conn.host}: {e}",
                host=ssh_conn.host,
                exc_info=True,
            )
            raise LibvirtError(str(e), "connection")
        except Exception as e:
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

    async def _get_vm_info(self, domain: libvirt.virDomain, host: str) -> VMInfo:
        """Extract VM information from libvirt domain."""
        try:
            # Get basic info
            info = domain.info()
            name = domain.name()
            uuid = domain.UUIDString()

            # Map libvirt state to our enum
            state_map = {
                libvirt.VIR_DOMAIN_RUNNING: VMState.RUNNING,
                libvirt.VIR_DOMAIN_BLOCKED: VMState.RUNNING,
                libvirt.VIR_DOMAIN_PAUSED: VMState.PAUSED,
                libvirt.VIR_DOMAIN_SHUTDOWN: VMState.STOPPED,
                libvirt.VIR_DOMAIN_SHUTOFF: VMState.STOPPED,
                libvirt.VIR_DOMAIN_CRASHED: VMState.STOPPED,
                libvirt.VIR_DOMAIN_PMSUSPENDED: VMState.SUSPENDED,
            }
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

                    # Get disk size (this would need additional libvirt calls)
                    disk_size = 0  # Placeholder

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
                created=datetime.now(),  # Placeholder
                last_modified=datetime.now(),  # Placeholder
            )

        except Exception as e:
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
                    # Generate new MAC address
                    mac = "52:54:00:%02x:%02x:%02x" % (
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

            return ResourceInfo(
                total_memory=total_memory,
                available_memory=free_memory,
                total_disk=0,  # Would need additional calls to get disk info
                available_disk=0,
                cpu_count=node_info[2],
                cpu_usage=0.0,  # Would need additional monitoring
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

    def close_all_connections(self) -> None:
        """Close all libvirt connections."""
        for uri, conn in self._connections.items():
            try:
                conn.close()
            except Exception:
                pass
        self._connections.clear()
        logger.info("All libvirt connections closed")
