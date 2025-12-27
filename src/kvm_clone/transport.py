"""
SSH transport layer for KVM cloning operations.

This module handles SSH connections and secure data transfer between hosts.
"""

import asyncio
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Callable, AsyncIterator
from pathlib import Path
from datetime import datetime
import paramiko
from contextlib import asynccontextmanager

from .logging import logger
from .constants import DEFAULT_CONNECTION_TTL, DEFAULT_MAX_CONNECTIONS

from .models import SSHConnectionInfo, TransferStats
from .exceptions import SSHError, AuthenticationError, ConnectionError, TimeoutError
from .security import SSHSecurity


class SSHConnection:
    """Represents a single SSH connection."""

    def __init__(
        self,
        host: str,
        port: int = 22,
        username: Optional[str] = None,
        key_path: Optional[str] = None,
        timeout: int = 30,
        executor: Optional[ThreadPoolExecutor] = None,
    ):
        """Initialize SSH connection."""
        self.host = host
        self.port = port
        self.username = username
        self.key_path = key_path
        self.timeout = timeout
        self._executor = executor
        self.client: Optional[paramiko.SSHClient] = None
        self.sftp: Optional[paramiko.SFTPClient] = None
        self._created_at: float = asyncio.get_event_loop().time()
        self._last_used: float = self._created_at

    def is_stale(self, ttl_seconds: int = DEFAULT_CONNECTION_TTL) -> bool:
        """Check if connection is stale (not used recently).

        Args:
            ttl_seconds: Time-to-live in seconds

        Returns:
            True if connection is stale
        """
        current_time = asyncio.get_event_loop().time()
        return (current_time - self._last_used) > ttl_seconds

    def mark_used(self) -> None:
        """Mark connection as recently used."""
        self._last_used = asyncio.get_event_loop().time()

    async def is_alive(self) -> bool:
        """Check if SSH connection is still alive.

        Returns:
            True if connection is alive
        """
        if not self.client:
            return False

        try:
            transport = self.client.get_transport() if self.client else None
            return transport is not None and transport.is_active()
        except (paramiko.SSHException, OSError):
            return False

    async def connect(self) -> None:
        """Establish SSH connection."""
        try:
            self.client = paramiko.SSHClient()
            # Use secure host key policy instead of AutoAddPolicy
            self.client.set_missing_host_key_policy(
                SSHSecurity.get_known_hosts_policy()
            )

            # Prepare connection parameters - type as Any to handle dynamic kwargs
            from typing import Any

            connect_kwargs: dict[str, Any] = {
                "hostname": self.host,
                "port": self.port,
                "timeout": self.timeout,
            }

            # Add authentication
            if self.key_path:
                # Validate SSH key path for security
                validated_key_path = SSHSecurity.validate_ssh_key_path(self.key_path)
                connect_kwargs["key_filename"] = validated_key_path

            if self.username:
                connect_kwargs["username"] = self.username

            # Connect in executor to avoid blocking
            loop = asyncio.get_event_loop()
            executor = self._executor or None
            await loop.run_in_executor(
                executor,
                lambda: self.client.connect(**connect_kwargs),  # type: ignore[union-attr]
            )

            # Initialize SFTP
            self.sftp = self.client.open_sftp()

            logger.info(
                f"SSH connection established to {self.host}:{self.port}",
                host=self.host,
                port=self.port,
            )

        except paramiko.AuthenticationException as e:
            logger.error(
                f"Authentication failed for {self.host}: {e}",
                host=self.host,
                exc_info=True,
            )
            raise AuthenticationError(str(e), self.host) from e
        except paramiko.SSHException as e:
            logger.error(
                f"SSH error connecting to {self.host}: {e}",
                host=self.host,
                exc_info=True,
            )
            raise SSHError(str(e), self.host, "connection") from e
        except OSError as e:
            logger.error(
                f"Connection error to {self.host}: {e}", host=self.host, exc_info=True
            )
            raise ConnectionError(str(e), self.host) from e

    async def execute_command(
        self, command: str, timeout: Optional[int] = None
    ) -> tuple[str, str, int]:
        """Execute a command over SSH."""
        if not self.client:
            raise SSHError("Not connected", self.host, "command_execution")

        try:
            loop = asyncio.get_event_loop()
            executor = self._executor or None
            stdin, stdout, stderr = await loop.run_in_executor(
                executor, self.client.exec_command, command
            )

            # Wait for command completion with timeout
            cmd_timeout = timeout or self.timeout
            stdout_data = await asyncio.wait_for(
                loop.run_in_executor(executor, stdout.read), timeout=cmd_timeout
            )
            stderr_data = await asyncio.wait_for(
                loop.run_in_executor(executor, stderr.read), timeout=cmd_timeout
            )

            # Retrieve exit status without blocking event loop
            exit_code = await loop.run_in_executor(
                executor, stdout.channel.recv_exit_status
            )

            return (stdout_data.decode("utf-8"), stderr_data.decode("utf-8"), exit_code)

        except asyncio.TimeoutError:
            logger.error(
                f"Command execution timed out on {self.host}",
                host=self.host,
                command=command,
                timeout=cmd_timeout,
            )
            raise TimeoutError(
                "Command execution timed out", "command_execution", cmd_timeout
            )
        except (paramiko.SSHException, OSError) as e:
            logger.error(
                f"Command execution failed on {self.host}: {e}",
                host=self.host,
                command=command,
                exc_info=True,
            )
            raise SSHError(str(e), self.host, "command_execution") from e

    async def transfer_file(
        self,
        local_path: str,
        remote_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> TransferStats:
        """Transfer a file to the remote host."""
        if not self.sftp:
            raise SSHError("SFTP not available", self.host, "file_transfer")

        try:
            loop = asyncio.get_event_loop()

            # Get file size for progress tracking
            local_file = Path(local_path)
            if not local_file.exists():
                raise SSHError(
                    f"Local file not found: {local_path}", self.host, "file_transfer"
                )

            file_size = local_file.stat().st_size

            # Transfer file
            from datetime import datetime

            stats = TransferStats()
            stats.start_time = datetime.now()

            def progress_wrapper(transferred: int, total: int) -> None:
                if progress_callback:
                    progress_callback(transferred, total)

            await loop.run_in_executor(
                self._executor or None,
                self.sftp.put,
                local_path,
                remote_path,
                progress_wrapper if progress_callback else None,
            )

            stats.end_time = datetime.now()
            stats.bytes_transferred = file_size
            stats.files_transferred = 1

            if stats.end_time and stats.start_time:
                duration = (stats.end_time - stats.start_time).total_seconds()
                if duration > 0:
                    stats.average_speed = file_size / duration

            return stats

        except (paramiko.SSHException, OSError) as e:
            logger.error(
                f"File transfer failed to {self.host}: {e}",
                host=self.host,
                local_path=local_path,
                remote_path=remote_path,
                exc_info=True,
            )
            raise SSHError(str(e), self.host, "file_transfer") from e

    async def close(self) -> None:
        """Close SSH connection."""
        if self.sftp:
            self.sftp.close()
            self.sftp = None

        if self.client:
            self.client.close()
            self.client = None

        logger.info(f"SSH connection closed to {self.host}", host=self.host)


class SSHTransport:
    """SSH transport manager for multiple connections."""

    def __init__(
        self,
        key_path: Optional[str] = None,
        timeout: int = 30,
        connection_ttl: int = DEFAULT_CONNECTION_TTL,
        max_connections: int = DEFAULT_MAX_CONNECTIONS,
        max_workers: int = 10,
    ):
        """Initialize SSH transport.

        Args:
            key_path: Default SSH key path
            timeout: Default connection timeout in seconds
            connection_ttl: Connection time-to-live in seconds (default: 5 minutes)
            max_connections: Maximum number of cached connections
            max_workers: Maximum number of thread pool workers
        """
        self.key_path = key_path
        self.timeout = timeout
        self.connection_ttl = connection_ttl
        self.max_connections = max_connections
        self.max_workers = max_workers
        self.connections: OrderedDict[str, SSHConnection] = OrderedDict()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    @asynccontextmanager
    async def connect(
        self, host: str, port: int = 22, username: Optional[str] = None
    ) -> AsyncIterator[SSHConnection]:
        """Create a managed SSH connection."""
        connection_key = f"{host}:{port}"

        # Reuse existing connection if available and alive
        if connection_key in self.connections:
            conn = self.connections[connection_key]

            # Check if connection is still alive and not stale
            if await conn.is_alive() and not conn.is_stale(self.connection_ttl):
                conn.mark_used()
                # Move to end (most recently used)
                self.connections.move_to_end(connection_key)
                yield conn
                return
            else:
                # Close stale/dead connection
                await conn.close()
                del self.connections[connection_key]

        # Enforce max connection limit with LRU eviction
        if len(self.connections) >= self.max_connections:
            await self._evict_lru_connection()

        # Create new connection
        connection = SSHConnection(
            host=host,
            port=port,
            username=username,
            key_path=self.key_path,
            timeout=self.timeout,
            executor=self._executor,
        )

        try:
            await connection.connect()
            self.connections[connection_key] = connection
            connection.mark_used()
            yield connection
        finally:
            # Keep connection for reuse (managed by TTL)
            pass

    async def _evict_lru_connection(self) -> None:
        """Evict least recently used connection."""
        if not self.connections:
            return

        # First connection is LRU (OrderedDict maintains insertion order)
        lru_key, lru_conn = self.connections.popitem(last=False)
        await lru_conn.close()
        logger.info(f"Evicted LRU connection: {lru_key}")

    async def cleanup_stale_connections(self) -> int:
        """Clean up all stale connections.

        Returns:
            int: Number of closed connections
        """
        stale_keys = []

        for key, conn in self.connections.items():
            if conn.is_stale(self.connection_ttl) or not await conn.is_alive():
                stale_keys.append(key)

        for key in stale_keys:
            conn = self.connections.pop(key)
            await conn.close()

        if stale_keys:
            logger.info(f"Cleaned up {len(stale_keys)} stale SSH connections")

        return len(stale_keys)

    async def execute_on_host(
        self,
        host: str,
        command: str,
        port: int = 22,
        username: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> tuple[str, str, int]:
        """Execute a command on a remote host."""
        async with self.connect(host, port, username) as conn:
            return await conn.execute_command(command, timeout)

    async def transfer_to_host(
        self,
        host: str,
        local_path: str,
        remote_path: str,
        port: int = 22,
        username: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> TransferStats:
        """Transfer a file to a remote host."""
        async with self.connect(host, port, username) as conn:
            return await conn.transfer_file(local_path, remote_path, progress_callback)

    async def close_all(self) -> None:
        """Close all SSH connections and cleanup executor."""
        for connection in self.connections.values():
            await connection.close()
        self.connections.clear()
        self._executor.shutdown(wait=True)
        logger.info("All SSH connections closed")

    def get_connection_info(
        self, host: str, port: int = 22
    ) -> Optional[SSHConnectionInfo]:
        """Get connection information for a host."""
        connection_key = f"{host}:{port}"
        if connection_key in self.connections:
            conn = self.connections[connection_key]
            return SSHConnectionInfo(
                host=conn.host,
                port=conn.port,
                username=conn.username,
                key_path=conn.key_path,
                timeout=conn.timeout,
            )
        return None
