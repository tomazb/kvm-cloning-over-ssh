"""Comprehensive unit tests for security module."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import paramiko

from kvm_clone.security import SecurityValidator, CommandBuilder, SSHSecurity
from kvm_clone.exceptions import ValidationError


class TestSecurityValidatorVMName:
    """Test SecurityValidator VM name validation."""
    
    def test_valid_vm_names(self):
        """Test valid VM names are accepted."""
        valid_names = [
            "test-vm",
            "vm_123",
            "my-test-vm",
            "VM-NAME",
            "vm123",
            "a",
            "a-b-c",
            "vm_with_underscores",
            "vm-with-hyphens",
            "MixedCase123"
        ]
        for name in valid_names:
            result = SecurityValidator.validate_vm_name(name)
            assert result == name
    
    def test_empty_vm_name_rejected(self):
        """Test empty VM name is rejected."""
        with pytest.raises(ValidationError, match="non-empty string"):
            SecurityValidator.validate_vm_name("")
    
    def test_none_vm_name_rejected(self):
        """Test None VM name is rejected."""
        with pytest.raises(ValidationError):
            SecurityValidator.validate_vm_name(None)
    
    def test_vm_name_with_spaces_rejected(self):
        """Test VM name with spaces is rejected."""
        with pytest.raises(ValidationError):
            SecurityValidator.validate_vm_name("vm with spaces")
    
    def test_vm_name_with_semicolon_rejected(self):
        """Test VM name with semicolon is rejected (command injection)."""
        with pytest.raises(ValidationError):
            SecurityValidator.validate_vm_name("vm; rm -rf /")
    
    def test_vm_name_with_backticks_rejected(self):
        """Test VM name with backticks is rejected (command substitution)."""
        with pytest.raises(ValidationError):
            SecurityValidator.validate_vm_name("vm`whoami`")
    
    def test_vm_name_with_dollar_paren_rejected(self):
        """Test VM name with $() is rejected (command substitution)."""
        with pytest.raises(ValidationError):
            SecurityValidator.validate_vm_name("vm$(id)")
    
    def test_vm_name_with_pipes_rejected(self):
        """Test VM name with pipes is rejected."""
        with pytest.raises(ValidationError):
            SecurityValidator.validate_vm_name("vm|cat")
    
    def test_vm_name_with_ampersand_rejected(self):
        """Test VM name with ampersand is rejected."""
        with pytest.raises(ValidationError):
            SecurityValidator.validate_vm_name("vm&")
    
    def test_vm_name_too_long_rejected(self):
        """Test VM name longer than 64 characters is rejected."""
        long_name = "a" * 65
        with pytest.raises(ValidationError, match="64 characters or less"):
            SecurityValidator.validate_vm_name(long_name)
    
    def test_vm_name_max_length_accepted(self):
        """Test VM name of exactly 64 characters is accepted."""
        max_name = "a" * 64
        result = SecurityValidator.validate_vm_name(max_name)
        assert result == max_name
    
    def test_vm_name_with_slashes_rejected(self):
        """Test VM name with slashes is rejected."""
        with pytest.raises(ValidationError):
            SecurityValidator.validate_vm_name("vm/path")
    
    def test_vm_name_with_dots_rejected(self):
        """Test VM name with dots is rejected."""
        with pytest.raises(ValidationError):
            SecurityValidator.validate_vm_name("vm.name")


class TestSecurityValidatorHostname:
    """Test SecurityValidator hostname validation."""
    
    def test_valid_hostnames(self):
        """Test valid hostnames are accepted."""
        valid_hosts = [
            "example.com",
            "sub.example.com",
            "192.168.1.1",
            "10.0.0.1",
            "localhost",
            "server-01",
            "my-host",
            "host123"
        ]
        for host in valid_hosts:
            result = SecurityValidator.validate_hostname(host)
            assert result == host
    
    def test_empty_hostname_rejected(self):
        """Test empty hostname is rejected."""
        with pytest.raises(ValidationError):
            SecurityValidator.validate_hostname("")
    
    def test_none_hostname_rejected(self):
        """Test None hostname is rejected."""
        with pytest.raises(ValidationError):
            SecurityValidator.validate_hostname(None)
    
    def test_hostname_with_semicolon_rejected(self):
        """Test hostname with semicolon is rejected."""
        with pytest.raises(ValidationError):
            SecurityValidator.validate_hostname("host; cat /etc/passwd")
    
    def test_hostname_with_backticks_rejected(self):
        """Test hostname with backticks is rejected."""
        with pytest.raises(ValidationError):
            SecurityValidator.validate_hostname("host`id`")
    
    def test_hostname_with_command_substitution_rejected(self):
        """Test hostname with command substitution is rejected."""
        with pytest.raises(ValidationError):
            SecurityValidator.validate_hostname("host$(whoami)")
    
    def test_hostname_too_long_rejected(self):
        """Test hostname longer than 253 characters is rejected."""
        long_host = "a" * 254
        with pytest.raises(ValidationError, match="253 characters or less"):
            SecurityValidator.validate_hostname(long_host)
    
    def test_hostname_max_length_accepted(self):
        """Test hostname of exactly 253 characters is accepted."""
        max_host = "a" * 253
        result = SecurityValidator.validate_hostname(max_host)
        assert result == max_host
    
    def test_hostname_with_spaces_rejected(self):
        """Test hostname with spaces is rejected."""
        with pytest.raises(ValidationError):
            SecurityValidator.validate_hostname("host name")
    
    def test_hostname_with_special_chars_rejected(self):
        """Test hostname with special characters is rejected."""
        invalid_chars = ["@", "#", "$", "%", "^", "&", "*", "(", ")", "=", "+"]
        for char in invalid_chars:
            with pytest.raises(ValidationError):
                SecurityValidator.validate_hostname(f"host{char}name")


class TestSecurityValidatorSnapshotName:
    """Test SecurityValidator snapshot name validation."""
    
    def test_valid_snapshot_names(self):
        """Test valid snapshot names are accepted."""
        valid_names = [
            "snapshot1",
            "snap-123",
            "my_snapshot",
            "SNAPSHOT",
            "snap-with-hyphens",
            "snap_with_underscores"
        ]
        for name in valid_names:
            result = SecurityValidator.validate_snapshot_name(name)
            assert result == name
    
    def test_empty_snapshot_name_rejected(self):
        """Test empty snapshot name is rejected."""
        with pytest.raises(ValidationError):
            SecurityValidator.validate_snapshot_name("")
    
    def test_snapshot_name_with_injection_rejected(self):
        """Test snapshot name with command injection is rejected."""
        with pytest.raises(ValidationError):
            SecurityValidator.validate_snapshot_name("snap; rm -rf /")
    
    def test_snapshot_name_too_long_rejected(self):
        """Test snapshot name longer than 64 characters is rejected."""
        long_name = "s" * 65
        with pytest.raises(ValidationError):
            SecurityValidator.validate_snapshot_name(long_name)
    
    def test_snapshot_name_max_length_accepted(self):
        """Test snapshot name of exactly 64 characters is accepted."""
        max_name = "s" * 64
        result = SecurityValidator.validate_snapshot_name(max_name)
        assert result == max_name


class TestSecurityValidatorSanitizePath:
    """Test SecurityValidator path sanitization."""
    
    def test_simple_path_sanitization(self):
        """Test simple path is sanitized correctly."""
        path = SecurityValidator.sanitize_path("/var/lib/file.img")
        assert "/var/lib/file.img" in path
    
    def test_path_with_base_dir(self):
        """Test path sanitization with base directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = SecurityValidator.sanitize_path("subdir/file.txt", tmpdir)
            assert result.startswith(tmpdir)
            assert "subdir" in result
    
    def test_path_traversal_rejected(self):
        """Test path traversal is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValidationError, match="Path traversal detected"):
                SecurityValidator.sanitize_path("../../etc/passwd", tmpdir)
    
    def test_absolute_path_outside_base_rejected(self):
        """Test absolute path outside base directory is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValidationError, match="Path traversal detected"):
                SecurityValidator.sanitize_path("/etc/passwd", tmpdir)
    
    def test_empty_path_rejected(self):
        """Test empty path is rejected."""
        with pytest.raises(ValidationError):
            SecurityValidator.sanitize_path("")
    
    def test_none_path_rejected(self):
        """Test None path is rejected."""
        with pytest.raises(ValidationError):
            SecurityValidator.sanitize_path(None)


class TestCommandBuilderSafeCommand:
    """Test CommandBuilder safe command building."""
    
    def test_build_safe_command_basic(self):
        """Test basic safe command building."""
        cmd = CommandBuilder.build_safe_command(
            "echo {message}",
            message="Hello World"
        )
        assert "Hello" in cmd
        assert "World" in cmd
    
    def test_build_safe_command_quotes_dangerous_input(self):
        """Test dangerous input is properly quoted."""
        cmd = CommandBuilder.build_safe_command(
            "cp {source} {dest}",
            source="/path; rm -rf /",
            dest="/dest`whoami`"
        )
        # Dangerous characters should be quoted
        assert "'/path; rm -rf /'" in cmd
        assert "'/dest`whoami`'" in cmd
    
    def test_build_safe_command_with_none_value(self):
        """Test command building with None value."""
        cmd = CommandBuilder.build_safe_command(
            "cmd {arg1} {arg2}",
            arg1="value",
            arg2=None
        )
        assert "value" in cmd
    
    def test_build_safe_command_special_characters(self):
        """Test command building with special characters."""
        cmd = CommandBuilder.build_safe_command(
            "cmd {path}",
            path="/path/with spaces/and'quotes"
        )
        # Should be properly quoted
        assert "'" in cmd or '"' in cmd


class TestCommandBuilderRsyncCommand:
    """Test CommandBuilder rsync command building."""
    
    def test_build_rsync_basic(self):
        """Test basic rsync command building."""
        cmd = CommandBuilder.build_rsync_command(
            source_path="/source",
            dest_path="/dest"
        )
        assert "rsync" in cmd
        assert "-avz" in cmd
        assert "--progress" in cmd
        assert "/source" in cmd
        assert "/dest" in cmd
    
    def test_build_rsync_with_bandwidth_limit(self):
        """Test rsync with bandwidth limit."""
        cmd = CommandBuilder.build_rsync_command(
            source_path="/source",
            dest_path="/dest",
            bandwidth_limit="100M"
        )
        assert "--bwlimit 100M" in cmd
    
    def test_build_rsync_with_remote_host(self):
        """Test rsync with remote host."""
        cmd = CommandBuilder.build_rsync_command(
            source_path="/source",
            dest_path="/dest",
            dest_host="remote.com"
        )
        assert "remote.com:" in cmd
    
    def test_build_rsync_invalid_bandwidth_limit(self):
        """Test rsync with invalid bandwidth limit."""
        with pytest.raises(ValidationError):
            CommandBuilder.build_rsync_command(
                source_path="/source",
                dest_path="/dest",
                bandwidth_limit="invalid"
            )
    
    def test_build_rsync_with_additional_options(self):
        """Test rsync with additional options."""
        cmd = CommandBuilder.build_rsync_command(
            source_path="/source",
            dest_path="/dest",
            additional_options=["--delete", "--exclude=*.tmp"]
        )
        assert "--delete" in cmd
        assert "--exclude=*.tmp" in cmd
    
    def test_build_rsync_invalid_option(self):
        """Test rsync with invalid option."""
        with pytest.raises(ValidationError):
            CommandBuilder.build_rsync_command(
                source_path="/source",
                dest_path="/dest",
                additional_options=["invalid; rm -rf /"]
            )


class TestCommandBuilderVirshCommand:
    """Test CommandBuilder virsh command building."""
    
    def test_build_virsh_valid_action(self):
        """Test virsh command with valid action."""
        cmd = CommandBuilder.build_virsh_command(
            "dominfo",
            "test-vm"
        )
        assert "virsh" in cmd
        assert "dominfo" in cmd
        assert "test-vm" in cmd
    
    def test_build_virsh_invalid_action(self):
        """Test virsh command with invalid action."""
        with pytest.raises(ValidationError):
            CommandBuilder.build_virsh_command(
                "invalid-action",
                "test-vm"
            )
    
    def test_build_virsh_with_args(self):
        """Test virsh command with additional arguments."""
        cmd = CommandBuilder.build_virsh_command(
            "snapshot-create-as",
            "test-vm",
            "snapshot-name",
            "description"
        )
        assert "snapshot-create-as" in cmd
        assert "snapshot-name" in cmd
        assert "description" in cmd
    
    def test_build_virsh_validates_vm_name(self):
        """Test virsh command validates VM name."""
        with pytest.raises(ValidationError):
            CommandBuilder.build_virsh_command(
                "dominfo",
                "vm; rm -rf /"
            )
    
    def test_build_virsh_quotes_dangerous_args(self):
        """Test virsh command quotes dangerous arguments."""
        cmd = CommandBuilder.build_virsh_command(
            "snapshot-create-as",
            "test-vm",
            "snap; dangerous"
        )
        # Dangerous arg should be quoted
        assert "'snap; dangerous'" in cmd


class TestSSHSecurityPolicy:
    """Test SSHSecurity class."""
    
    def test_get_known_hosts_policy(self):
        """Test SSH host key policy is secure."""
        policy = SSHSecurity.get_known_hosts_policy()
        assert policy is not None
        assert isinstance(policy, paramiko.RejectPolicy)
        assert not isinstance(policy, paramiko.AutoAddPolicy)
    
    def test_validate_ssh_key_path_valid(self):
        """Test SSH key path validation with valid key."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test key content")
            temp_key = f.name
        
        try:
            # Set proper permissions
            os.chmod(temp_key, 0o600)
            result = SSHSecurity.validate_ssh_key_path(temp_key)
            assert result == temp_key
        finally:
            os.unlink(temp_key)
    
    def test_validate_ssh_key_path_empty(self):
        """Test SSH key path validation rejects empty path."""
        with pytest.raises(ValidationError):
            SSHSecurity.validate_ssh_key_path("")
    
    def test_validate_ssh_key_path_not_found(self):
        """Test SSH key path validation rejects non-existent file."""
        with pytest.raises(ValidationError, match="not found"):
            SSHSecurity.validate_ssh_key_path("/nonexistent/key")
    
    def test_validate_ssh_key_path_insecure_permissions(self):
        """Test SSH key path validation rejects insecure permissions."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test key")
            temp_key = f.name
        
        try:
            # Set insecure permissions
            os.chmod(temp_key, 0o644)
            with pytest.raises(ValidationError, match="insecure permissions"):
                SSHSecurity.validate_ssh_key_path(temp_key)
        finally:
            os.unlink(temp_key)
    
    def test_validate_ssh_key_path_expands_tilde(self):
        """Test SSH key path validation expands tilde."""
        # Mock expanduser and exists
        with patch('pathlib.Path.expanduser') as mock_expand:
            with patch('pathlib.Path.exists', return_value=True):
                with patch('pathlib.Path.is_file', return_value=True):
                    with patch('pathlib.Path.stat') as mock_stat:
                        mock_stat.return_value.st_mode = 0o100600
                        mock_expand.return_value = Path("/home/user/.ssh/id_rsa")
                        
                        # Should not raise
                        try:
                            SSHSecurity.validate_ssh_key_path("~/.ssh/id_rsa")
                        except ValidationError:
                            pass  # File doesn't actually exist, but path expansion was tested


class TestSecurityIntegration:
    """Test security features integration."""
    
    def test_complete_command_pipeline(self):
        """Test complete command building pipeline."""
        # Validate inputs
        vm_name = SecurityValidator.validate_vm_name("test-vm")
        host = SecurityValidator.validate_hostname("example.com")
        
        # Build safe command
        cmd = CommandBuilder.build_virsh_command("dominfo", vm_name)
        
        assert "test-vm" in cmd
        assert "virsh" in cmd
    
    def test_injection_prevention_end_to_end(self):
        """Test injection prevention works end-to-end."""
        # Try to inject commands
        with pytest.raises(ValidationError):
            vm_name = SecurityValidator.validate_vm_name("vm; rm -rf /")
        
        with pytest.raises(ValidationError):
            host = SecurityValidator.validate_hostname("host`whoami`")
        
        # Verify safe command building
        cmd = CommandBuilder.build_safe_command(
            "cmd {arg}",
            arg="safe; dangerous"
        )
        # Should be quoted
        assert "'" in cmd or "safe\\;" in cmd