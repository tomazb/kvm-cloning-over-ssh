"""
SSH transport layer for KVM cloning operations.

This module handles SSH connections and secure data transfer between hosts.
"""

import asyncio
import os
import time
from typing import Optional, Dict, Callable, AsyncIterator
from pathlib import Path
import paramiko
from contextlib import asynccontextmanager

from .logging import logger

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
        max_retries: int = 3,
    ):
        """Initialize SSH connection.

        Args:
            host: Hostname to connect to
            port: SSH port (default: 22, can be overridden by SSH config)
            username: SSH username (default: auto-detect from environment)
            key_path: Path to SSH private key (default: use SSH agent if available)
            timeout: Connection timeout in seconds
            max_retries: Maximum number of connection retry attempts
        """
        self.host = host
        self.port = port
        self.username = username
        self.key_path = key_path
        self.timeout = timeout
        self.max_retries = max_retries
        self.client: Optional[paramiko.SSHClient] = None
        self.sftp: Optional[paramiko.SFTPClient] = None

        # Load SSH config for this host
        self._ssh_config = self._load_ssh_config()

    def _load_ssh_config(self) -> Optional[Dict[str, any]]:
        """Load SSH configuration for the host from ~/.ssh/config."""
        try:
            ssh_config_path = Path.home() / ".ssh" / "config"
            if not ssh_config_path.exists():
                return None

            ssh_config = paramiko.SSHConfig()
            with open(ssh_config_path) as f:
                ssh_config.parse(f)

            return ssh_config.lookup(self.host)
        except Exception as e:
            logger.debug(f"Could not load SSH config: {e}")
            return None

    def _get_username(self) -> str:
        """Get username from config, SSH config, or environment."""
        # 1. Explicit username parameter
        if self.username:
            return self.username

        # 2. SSH config file
        if self._ssh_config and 'user' in self._ssh_config:
            return self._ssh_config['user']

        # 3. Current user from environment
        username = os.getenv('USER') or os.getenv('USERNAME')
        if username:
            logger.debug(f"Auto-detected username: {username}")
            return username

        # 4. Fallback to current process user
        import getpass
        return getpass.getuser()

    def _get_port(self) -> int:
        """Get port from SSH config or use default."""
        if self._ssh_config and 'port' in self._ssh_config:
            try:
                return int(self._ssh_config['port'])
            except (ValueError, TypeError):
                pass
        return self.port

    def _get_hostname(self) -> str:
        """Get actual hostname from SSH config (handles aliases)."""
        if self._ssh_config and 'hostname' in self._ssh_config:
            return self._ssh_config['hostname']
        return self.host

    async def connect(self) -> None:
        """Establish SSH connection with retry logic and better error handling."""
        last_error = None
        actual_hostname = self._get_hostname()
        actual_port = self._get_port()
        username = self._get_username()

        for attempt in range(self.max_retries):
            try:
                self.client = paramiko.SSHClient()

                # Use configurable host key policy
                self.client.set_missing_host_key_policy(
                    SSHSecurity.get_known_hosts_policy()
                )

                # Load system host keys
                try:
                    self.client.load_system_host_keys()
                except Exception as e:
                    logger.debug(f"Could not load system host keys: {e}")

                # Prepare connection parameters
                from typing import Any
                connect_kwargs: dict[str, Any] = {
                    "hostname": actual_hostname,
                    "port": actual_port,
                    "username": username,
                    "timeout": self.timeout,
                    "allow_agent": True,  # Try SSH agent first
                    "look_for_keys": True,  # Look in ~/.ssh/ for keys
                }

                # Add explicit key if provided
                if self.key_path:
                    try:
                        validated_key_path = SSHSecurity.validate_ssh_key_path(self.key_path)
                        connect_kwargs["key_filename"] = validated_key_path
                        logger.debug(f"Using SSH key: {validated_key_path}")
                    except Exception as key_error:
                        # Log warning but continue - might work with agent or other keys
                        logger.warning(f"SSH key validation failed, will try other methods: {key_error}")
                        connect_kwargs["key_filename"] = None

                # Also check SSH config for IdentityFile
                if self._ssh_config and 'identityfile' in self._ssh_config:
                    identity_files = self._ssh_config['identityfile']
                    if isinstance(identity_files, list):
                        connect_kwargs["key_filename"] = [str(Path(f).expanduser()) for f in identity_files]
                    else:
                        connect_kwargs["key_filename"] = str(Path(identity_files).expanduser())

                # Connect in executor to avoid blocking
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self.client.connect(**connect_kwargs),  # type: ignore[union-attr]
                )

                # Initialize SFTP
                self.sftp = self.client.open_sftp()

                logger.info(
                    f"SSH connection established to {actual_hostname}:{actual_port} as {username}",
                    host=actual_hostname,
                    port=actual_port,
                    username=username,
                    attempt=attempt + 1,
                )
                return  # Success!

            except paramiko.AuthenticationException as e:
                last_error = e
                error_msg = self._format_auth_error(username, actual_hostname)
                logger.error(error_msg, host=actual_hostname, exc_info=True)
                # Don't retry auth errors - they won't succeed
                raise AuthenticationError(error_msg, actual_hostname)

            except paramiko.SSHException as e:
                last_error = e
                error_str = str(e).lower()

                # Check for specific SSH errors and provide helpful messages
                if "no hostkey" in error_str or "not found in known_hosts" in error_str:
                    error_msg = self._format_hostkey_error(actual_hostname)
                    logger.error(error_msg, host=actual_hostname, exc_info=True)
                    raise SSHError(error_msg, actual_hostname, "hostkey_verification")
                elif "connection refused" in error_str:
                    # Retry connection refused (server might be restarting)
                    if attempt < self.max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                        logger.warning(
                            f"Connection refused to {actual_hostname}, retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})",
                            host=actual_hostname
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    error_msg = f"Connection refused by {actual_hostname}:{actual_port}. " \
                               f"Please check that SSH server is running and port {actual_port} is correct."
                    logger.error(error_msg, host=actual_hostname)
                    raise SSHError(error_msg, actual_hostname, "connection_refused")
                else:
                    # Generic SSH error with retry
                    if attempt < self.max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.warning(
                            f"SSH error connecting to {actual_hostname}: {e}, retrying in {wait_time}s",
                            host=actual_hostname
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    error_msg = f"SSH error connecting to {actual_hostname}: {e}"
                    logger.error(error_msg, host=actual_hostname, exc_info=True)
                    raise SSHError(error_msg, actual_hostname, "connection")

            except (OSError, TimeoutError) as e:
                last_error = e
                # Network errors - worth retrying
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Network error connecting to {actual_hostname}: {e}, retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})",
                        host=actual_hostname
                    )
                    await asyncio.sleep(wait_time)
                    continue

                error_msg = f"Network error connecting to {actual_hostname}:{actual_port}: {e}. " \
                           f"Please check network connectivity and hostname."
                logger.error(error_msg, host=actual_hostname, exc_info=True)
                raise ConnectionError(error_msg, actual_hostname)

            except Exception as e:
                last_error = e
                logger.error(
                    f"Unexpected error connecting to {actual_hostname}: {e}",
                    host=actual_hostname,
                    exc_info=True
                )
                raise ConnectionError(str(e), actual_hostname)

        # If we got here, all retries failed
        error_msg = f"Failed to connect to {actual_hostname} after {self.max_retries} attempts. Last error: {last_error}"
        logger.error(error_msg, host=actual_hostname)
        raise ConnectionError(error_msg, actual_hostname)

    def _format_auth_error(self, username: str, hostname: str) -> str:
        """Format a helpful authentication error message."""
        suggestions = [
            f"Authentication failed for {username}@{hostname}",
            "",
            "Possible solutions:",
            "1. Verify your SSH key is authorized on the remote host:",
            f"   ssh-copy-id -i ~/.ssh/id_rsa.pub {username}@{hostname}",
        ]

        if self.key_path:
            suggestions.extend([
                "",
                f"2. Check that your SSH key exists and has correct permissions:",
                f"   ls -l {self.key_path}",
                f"   chmod 600 {self.key_path}",
            ])
        else:
            suggestions.extend([
                "",
                "2. Make sure SSH agent is running with your key loaded:",
                "   ssh-add -l",
                "   ssh-add ~/.ssh/id_rsa",
                "",
                "3. Or specify a key explicitly:",
                "   --ssh-key ~/.ssh/id_rsa",
            ])

        suggestions.extend([
            "",
            "4. Test SSH connection manually:",
            f"   ssh -v {username}@{hostname}",
        ])

        return "\n".join(suggestions)

    def _format_hostkey_error(self, hostname: str) -> str:
        """Format a helpful host key verification error message."""
        return f"""Host key verification failed for {hostname}.

Possible solutions:
1. Add the host to your known_hosts file by connecting manually:
   ssh {hostname}

2. If you trust this host, you can bypass strict checking by adding to your SSH config (~/.ssh/config):
   Host {hostname}
       StrictHostKeyChecking accept-new

3. For testing only (NOT recommended for production):
   Set environment variable: KVM_CLONE_SSH_HOST_KEY_POLICY=warn

Note: Host key verification is a security feature. Only bypass it if you understand the risks."""

    async def execute_command(
        self, command: str, timeout: Optional[int] = None
    ) -> tuple[str, str, int]:
        """Execute a command over SSH."""
        if not self.client:
            raise SSHError("Not connected", self.host, "command_execution")

        try:
            loop = asyncio.get_event_loop()
            stdin, stdout, stderr = await loop.run_in_executor(
                None, self.client.exec_command, command
            )

            # Wait for command completion with timeout
            cmd_timeout = timeout or self.timeout
            stdout_data = await asyncio.wait_for(
                loop.run_in_executor(None, stdout.read), timeout=cmd_timeout
            )
            stderr_data = await asyncio.wait_for(
                loop.run_in_executor(None, stderr.read), timeout=cmd_timeout
            )

            # Retrieve exit status without blocking event loop
            exit_code = await loop.run_in_executor(
                None, stdout.channel.recv_exit_status
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
        except Exception as e:
            logger.error(
                f"Command execution failed on {self.host}: {e}",
                host=self.host,
                command=command,
                exc_info=True,
            )
            raise SSHError(str(e), self.host, "command_execution")

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
                None,
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

        except Exception as e:
            logger.error(
                f"File transfer failed to {self.host}: {e}",
                host=self.host,
                local_path=local_path,
                remote_path=remote_path,
                exc_info=True,
            )
            raise SSHError(str(e), self.host, "file_transfer")

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

    def __init__(self, key_path: Optional[str] = None, timeout: int = 30, max_retries: int = 3):
        """Initialize SSH transport.

        Args:
            key_path: Path to SSH private key (optional, will use agent/auto-detect)
            timeout: Connection timeout in seconds
            max_retries: Maximum number of connection retry attempts
        """
        self.key_path = key_path
        self.timeout = timeout
        self.max_retries = max_retries
        self.connections: Dict[str, SSHConnection] = {}

    @asynccontextmanager
    async def connect(
        self, host: str, port: int = 22, username: Optional[str] = None
    ) -> AsyncIterator[SSHConnection]:
        """Create a managed SSH connection."""
        connection_key = f"{host}:{port}"

        # Reuse existing connection if available
        if connection_key in self.connections:
            yield self.connections[connection_key]
            return

        # Create new connection
        connection = SSHConnection(
            host=host,
            port=port,
            username=username,
            key_path=self.key_path,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )

        try:
            await connection.connect()
            self.connections[connection_key] = connection
            yield connection
        finally:
            # Keep connection for reuse
            pass

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
        """Close all SSH connections."""
        for connection in self.connections.values():
            await connection.close()
        self.connections.clear()
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
