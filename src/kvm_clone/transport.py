"""
SSH transport layer for KVM cloning operations.

This module handles SSH connections and secure data transfer between hosts.
"""

import asyncio
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
    
    def __init__(self, host: str, port: int = 22, username: Optional[str] = None, 
                 key_path: Optional[str] = None, timeout: int = 30):
        """Initialize SSH connection."""
        self.host = host
        self.port = port
        self.username = username
        self.key_path = key_path
        self.timeout = timeout
        self.client: Optional[paramiko.SSHClient] = None
        self.sftp: Optional[paramiko.SFTPClient] = None
        
    async def connect(self) -> None:
        """Establish SSH connection."""
        try:
            self.client = paramiko.SSHClient()
            # Use secure host key policy instead of AutoAddPolicy
            self.client.set_missing_host_key_policy(SSHSecurity.get_known_hosts_policy())
            
            # Prepare connection parameters
            connect_kwargs = {
                'hostname': self.host,
                'port': self.port,
                'timeout': self.timeout,
            }
            
            # Add authentication
            if self.key_path:
                # Validate SSH key path for security
                validated_key_path = SSHSecurity.validate_ssh_key_path(self.key_path)
                connect_kwargs['key_filename'] = validated_key_path
            
            if self.username:
                connect_kwargs['username'] = self.username
            
            # Connect in executor to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self.client.connect(**connect_kwargs))  # type: ignore[arg-type,union-attr]
            
            # Initialize SFTP
            self.sftp = self.client.open_sftp()
            
            logger.info(f"SSH connection established to {self.host}:{self.port}", 
                       host=self.host, port=self.port)
            
        except paramiko.AuthenticationException as e:
            logger.error(f"Authentication failed for {self.host}: {e}", host=self.host, exc_info=True)
            raise AuthenticationError(str(e), self.host)
        except paramiko.SSHException as e:
            logger.error(f"SSH error connecting to {self.host}: {e}", host=self.host, exc_info=True)
            raise SSHError(str(e), self.host, "connection")
        except Exception as e:
            logger.error(f"Connection error to {self.host}: {e}", host=self.host, exc_info=True)
            raise ConnectionError(str(e), self.host)
    
    async def execute_command(self, command: str, timeout: Optional[int] = None) -> tuple[str, str, int]:
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
                loop.run_in_executor(None, stdout.read), 
                timeout=cmd_timeout
            )
            stderr_data = await asyncio.wait_for(
                loop.run_in_executor(None, stderr.read), 
                timeout=cmd_timeout
            )
            
            exit_code = stdout.channel.recv_exit_status()
            
            return (
                stdout_data.decode('utf-8'),
                stderr_data.decode('utf-8'),
                exit_code
            )
            
        except asyncio.TimeoutError:
            logger.error(f"Command execution timed out on {self.host}", host=self.host, command=command, timeout=cmd_timeout)
            raise TimeoutError("Command execution timed out", "command_execution", cmd_timeout)
        except Exception as e:
            logger.error(f"Command execution failed on {self.host}: {e}", host=self.host, command=command, exc_info=True)
            raise SSHError(str(e), self.host, "command_execution")
    
    async def transfer_file(self, local_path: str, remote_path: str, 
                          progress_callback: Optional[Callable[[int, int], None]] = None) -> TransferStats:
        """Transfer a file to the remote host."""
        if not self.sftp:
            raise SSHError("SFTP not available", self.host, "file_transfer")
        
        try:
            loop = asyncio.get_event_loop()
            
            # Get file size for progress tracking
            local_file = Path(local_path)
            if not local_file.exists():
                raise SSHError(f"Local file not found: {local_path}", self.host, "file_transfer")
            
            file_size = local_file.stat().st_size
            
            # Transfer file
            stats = TransferStats()
            stats.start_time = asyncio.get_event_loop().time()  # type: ignore[assignment]
            
            def progress_wrapper(transferred: int, total: int) -> None:
                if progress_callback:
                    progress_callback(transferred, total)
            
            await loop.run_in_executor(
                None, 
                self.sftp.put, 
                local_path, 
                remote_path,
                progress_wrapper if progress_callback else None
            )
            
            stats.end_time = asyncio.get_event_loop().time()  # type: ignore[assignment]
            stats.bytes_transferred = file_size
            stats.files_transferred = 1
            
            if stats.end_time and stats.start_time:
                duration = stats.end_time - stats.start_time
                if duration > 0:  # type: ignore[operator]
                    stats.average_speed = file_size / duration  # type: ignore[operator]
            
            return stats
            
        except Exception as e:
            logger.error(f"File transfer failed to {self.host}: {e}", host=self.host, local_path=local_path, remote_path=remote_path, exc_info=True)
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
    
    def __init__(self, key_path: Optional[str] = None, timeout: int = 30):
        """Initialize SSH transport."""
        self.key_path = key_path
        self.timeout = timeout
        self.connections: Dict[str, SSHConnection] = {}
    
    @asynccontextmanager
    async def connect(self, host: str, port: int = 22, 
                     username: Optional[str] = None) -> AsyncIterator[SSHConnection]:
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
            timeout=self.timeout
        )
        
        try:
            await connection.connect()
            self.connections[connection_key] = connection
            yield connection
        finally:
            # Keep connection for reuse
            pass
    
    async def execute_on_host(self, host: str, command: str, 
                            port: int = 22, username: Optional[str] = None,
                            timeout: Optional[int] = None) -> tuple[str, str, int]:
        """Execute a command on a remote host."""
        async with self.connect(host, port, username) as conn:
            return await conn.execute_command(command, timeout)
    
    async def transfer_to_host(self, host: str, local_path: str, remote_path: str,
                             port: int = 22, username: Optional[str] = None,
                             progress_callback: Optional[Callable[[int, int], None]] = None) -> TransferStats:
        """Transfer a file to a remote host."""
        async with self.connect(host, port, username) as conn:
            return await conn.transfer_file(local_path, remote_path, progress_callback)
    
    async def close_all(self) -> None:
        """Close all SSH connections."""
        for connection in self.connections.values():
            await connection.close()
        self.connections.clear()
        logger.info("All SSH connections closed")
    
    def get_connection_info(self, host: str, port: int = 22) -> Optional[SSHConnectionInfo]:
        """Get connection information for a host."""
        connection_key = f"{host}:{port}"
        if connection_key in self.connections:
            conn = self.connections[connection_key]
            return SSHConnectionInfo(
                host=conn.host,
                port=conn.port,
                username=conn.username,
                key_path=conn.key_path,
                timeout=conn.timeout
            )
        return None