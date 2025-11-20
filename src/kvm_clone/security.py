"""
Security utilities for KVM cloning operations.

This module provides input validation, command sanitization, and path security
functions to prevent common security vulnerabilities.
"""

import re
import shlex
from pathlib import Path
from typing import List, Optional, Any

from .exceptions import ValidationError


class SecurityValidator:
    """Security validation utilities."""

    # Valid patterns for various inputs
    VM_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
    HOSTNAME_PATTERN = re.compile(r"^[a-zA-Z0-9.-]+$")
    SNAPSHOT_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

    @staticmethod
    def validate_vm_name(name: str) -> str:
        """
        Validate and sanitize VM name.

        Args:
            name: VM name to validate

        Returns:
            str: Validated VM name

        Raises:
            ValidationError: If VM name is invalid
        """
        if not name or not isinstance(name, str):
            raise ValidationError("VM name must be a non-empty string")

        if len(name) > 64:
            raise ValidationError("VM name must be 64 characters or less")

        if not SecurityValidator.VM_NAME_PATTERN.match(name):
            raise ValidationError(
                "VM name can only contain letters, numbers, underscores, and hyphens"
            )

        return name

    @staticmethod
    def validate_hostname(hostname: str) -> str:
        """
        Validate and sanitize hostname.

        Args:
            hostname: Hostname to validate

        Returns:
            str: Validated hostname

        Raises:
            ValidationError: If hostname is invalid
        """
        if not hostname or not isinstance(hostname, str):
            raise ValidationError("Hostname must be a non-empty string")

        if len(hostname) > 253:
            raise ValidationError("Hostname must be 253 characters or less")

        if not SecurityValidator.HOSTNAME_PATTERN.match(hostname):
            raise ValidationError(
                "Hostname can only contain letters, numbers, dots, and hyphens"
            )

        return hostname

    @staticmethod
    def validate_snapshot_name(name: str) -> str:
        """
        Validate and sanitize snapshot name.

        Args:
            name: Snapshot name to validate

        Returns:
            str: Validated snapshot name

        Raises:
            ValidationError: If snapshot name is invalid
        """
        if not name or not isinstance(name, str):
            raise ValidationError("Snapshot name must be a non-empty string")

        if len(name) > 64:
            raise ValidationError("Snapshot name must be 64 characters or less")

        if not SecurityValidator.SNAPSHOT_NAME_PATTERN.match(name):
            raise ValidationError(
                "Snapshot name can only contain letters, numbers, underscores, and hyphens"
            )

        return name

    @staticmethod
    def sanitize_path(path: str, base_dir: Optional[str] = None) -> str:
        """
        Sanitize and validate file path to prevent path traversal attacks.

        Args:
            path: File path to sanitize
            base_dir: Base directory to restrict access to

        Returns:
            str: Sanitized path

        Raises:
            ValidationError: If path is invalid or attempts traversal
        """
        if not path or not isinstance(path, str):
            raise ValidationError("Path must be a non-empty string")

        # Convert to Path object for normalization
        path_obj = Path(path)

        # If base_dir is provided, ensure path stays within it
        if base_dir:
            base_path = Path(base_dir).resolve()
            try:
                # Resolve the path and check if it's within base_dir
                resolved_path = (base_path / path_obj).resolve()
                if not str(resolved_path).startswith(str(base_path)):
                    raise ValidationError(f"Path traversal detected: {path}")
                return str(resolved_path)
            except (OSError, ValueError) as e:
                raise ValidationError(f"Invalid path: {path}") from e

        # Basic path validation without base directory restriction
        try:
            normalized_path = path_obj.resolve()
            return str(normalized_path)
        except (OSError, ValueError) as e:
            raise ValidationError(f"Invalid path: {path}") from e


class CommandBuilder:
    """Secure command building utilities."""

    @staticmethod
    def build_safe_command(template: str, **kwargs: Any) -> str:
        """
        Build a safe shell command with properly quoted parameters.

        Args:
            template: Command template with {param} placeholders
            **kwargs: Parameters to substitute in template

        Returns:
            str: Safe command with quoted parameters
        """
        # Quote all parameters to prevent injection
        quoted_kwargs = {}
        for key, value in kwargs.items():
            if value is not None:
                quoted_kwargs[key] = shlex.quote(str(value))
            else:
                quoted_kwargs[key] = ""

        return template.format(**quoted_kwargs)

    @staticmethod
    def build_rsync_command(
        source_path: str,
        dest_path: str,
        dest_host: Optional[str] = None,
        bandwidth_limit: Optional[str] = None,
        additional_options: Optional[List[str]] = None,
    ) -> str:
        """
        Build a safe rsync command.

        Args:
            source_path: Source file/directory path
            dest_path: Destination file/directory path
            dest_host: Destination host (for remote sync)
            bandwidth_limit: Bandwidth limit (e.g., "100M")
            additional_options: Additional rsync options

        Returns:
            str: Safe rsync command
        """
        cmd_parts = ["rsync", "-avz", "--progress"]

        # Add bandwidth limit if specified
        if bandwidth_limit:
            # Validate bandwidth limit format
            if not re.match(r"^\d+[KMG]?$", bandwidth_limit):
                raise ValidationError(
                    f"Invalid bandwidth limit format: {bandwidth_limit}"
                )
            cmd_parts.extend(["--bwlimit", bandwidth_limit])

        # Add additional options if provided
        if additional_options:
            for option in additional_options:
                # Basic validation for rsync options
                if not re.match(r"^--?[a-zA-Z0-9-]+(?:=.+)?$", option):
                    raise ValidationError(f"Invalid rsync option: {option}")
                cmd_parts.append(option)

        # Add source and destination
        cmd_parts.append(shlex.quote(source_path))

        if dest_host:
            dest_target = f"{shlex.quote(dest_host)}:{shlex.quote(dest_path)}"
        else:
            dest_target = shlex.quote(dest_path)

        cmd_parts.append(dest_target)

        return " ".join(cmd_parts)

    @staticmethod
    def build_virsh_command(action: str, vm_name: str, *args: Any) -> str:
        """
        Build a safe virsh command.

        Args:
            action: Virsh action (e.g., "snapshot-create-as")
            vm_name: VM name
            *args: Additional arguments

        Returns:
            str: Safe virsh command
        """
        # Validate action
        valid_actions = {
            "snapshot-create-as",
            "snapshot-delete",
            "snapshot-list",
            "dominfo",
            "list",
            "start",
            "shutdown",
            "destroy",
        }

        if action not in valid_actions:
            raise ValidationError(f"Invalid virsh action: {action}")

        # Validate VM name
        vm_name = SecurityValidator.validate_vm_name(vm_name)

        # Build command with quoted parameters
        cmd_parts = ["virsh", action, shlex.quote(vm_name)]

        for arg in args:
            if arg is not None:
                cmd_parts.append(shlex.quote(str(arg)))

        return " ".join(cmd_parts)


class SSHSecurity:
    """SSH security utilities."""

    @staticmethod
    def get_known_hosts_policy() -> Any:
        """
        Get a secure SSH host key policy.

        Returns:
            paramiko.MissingHostKeyPolicy: Secure host key policy
        """
        import paramiko

        # Use RejectPolicy by default for security
        # In production, you might want to implement a custom policy
        # that checks against a known_hosts file
        return paramiko.RejectPolicy()

    @staticmethod
    def validate_ssh_key_path(key_path: str) -> str:
        """
        Validate SSH private key path.

        Args:
            key_path: Path to SSH private key

        Returns:
            str: Validated key path

        Raises:
            ValidationError: If key path is invalid
        """
        if not key_path:
            raise ValidationError("SSH key path cannot be empty")

        key_file = Path(key_path).expanduser()

        if not key_file.exists():
            raise ValidationError(f"SSH key file not found: {key_path}")

        if not key_file.is_file():
            raise ValidationError(f"SSH key path is not a file: {key_path}")

        # Check file permissions (should be readable only by owner)
        stat_info = key_file.stat()
        if stat_info.st_mode & 0o077:
            raise ValidationError(
                f"SSH key file has insecure permissions: {key_path}. "
                "Key files should be readable only by the owner (chmod 600)."
            )

        return str(key_file)
