"""
Test security fixes to ensure vulnerabilities are properly addressed.
"""

import pytest
from src.kvm_clone.security import SecurityValidator, CommandBuilder, SSHSecurity
from src.kvm_clone.exceptions import ValidationError


class TestSecurityFixes:
    """Test security vulnerability fixes."""
    
    def test_vm_name_validation(self):
        """Test VM name validation prevents injection."""
        # Valid VM names should pass
        assert SecurityValidator.validate_vm_name("test-vm") == "test-vm"
        assert SecurityValidator.validate_vm_name("vm_123") == "vm_123"
        
        # Invalid VM names should raise ValidationError
        with pytest.raises(ValidationError):
            SecurityValidator.validate_vm_name("test; rm -rf /")
        
        with pytest.raises(ValidationError):
            SecurityValidator.validate_vm_name("test`whoami`")
        
        with pytest.raises(ValidationError):
            SecurityValidator.validate_vm_name("test$(id)")
    
    def test_hostname_validation(self):
        """Test hostname validation prevents injection."""
        # Valid hostnames should pass
        assert SecurityValidator.validate_hostname("example.com") == "example.com"
        assert SecurityValidator.validate_hostname("192.168.1.1") == "192.168.1.1"
        
        # Invalid hostnames should raise ValidationError
        with pytest.raises(ValidationError):
            SecurityValidator.validate_hostname("host; cat /etc/passwd")
        
        with pytest.raises(ValidationError):
            SecurityValidator.validate_hostname("host`id`")
    
    def test_safe_command_building(self):
        """Test that command building properly quotes parameters."""
        # Test basic command building (simple paths don't need quotes)
        cmd = CommandBuilder.build_safe_command(
            "cp {source} {dest}",
            source="/path/to/file",
            dest="/dest/path"
        )
        assert cmd == "cp /path/to/file /dest/path"
        
        # Test with potentially dangerous input (should be properly quoted)
        cmd = CommandBuilder.build_safe_command(
            "cp {source} {dest}",
            source="/path; rm -rf /",
            dest="/dest`whoami`"
        )
        # Should be properly quoted to prevent injection
        assert "'/path; rm -rf /'" in cmd
        assert "'/dest`whoami`'" in cmd
        # Dangerous parts should not be executable
        assert cmd == "cp '/path; rm -rf /' '/dest`whoami`'"
    
    def test_virsh_command_building(self):
        """Test virsh command building with validation."""
        # Valid command should work (simple strings don't need quotes)
        cmd = CommandBuilder.build_virsh_command(
            "snapshot-create-as",
            "test-vm",
            "snapshot-name",
            "description"
        )
        expected = "virsh snapshot-create-as test-vm snapshot-name description"
        assert cmd == expected
        
        # Test with potentially dangerous input (should be quoted)
        cmd = CommandBuilder.build_virsh_command(
            "snapshot-create-as",
            "test-vm",
            "snap; rm -rf /",
            "desc`whoami`"
        )
        assert "'snap; rm -rf /'" in cmd
        assert "'desc`whoami`'" in cmd
        
        # Invalid action should raise ValidationError
        with pytest.raises(ValidationError):
            CommandBuilder.build_virsh_command(
                "dangerous-action",
                "test-vm"
            )
    
    def test_rsync_command_building(self):
        """Test rsync command building with proper quoting."""
        # Local rsync (simple paths don't need quotes)
        cmd = CommandBuilder.build_rsync_command(
            source_path="/source/path",
            dest_path="/dest/path"
        )
        assert "rsync -avz --progress" in cmd
        assert "/source/path" in cmd
        assert "/dest/path" in cmd
        
        # Test with potentially dangerous paths (should be quoted)
        cmd = CommandBuilder.build_rsync_command(
            source_path="/source; rm -rf /",
            dest_path="/dest`whoami`"
        )
        assert "'/source; rm -rf /'" in cmd
        assert "'/dest`whoami`'" in cmd
        
        # Remote rsync
        cmd = CommandBuilder.build_rsync_command(
            source_path="/source/path",
            dest_path="/dest/path",
            dest_host="remote.host"
        )
        assert "remote.host:/dest/path" in cmd
        
        # With bandwidth limit
        cmd = CommandBuilder.build_rsync_command(
            source_path="/source/path",
            dest_path="/dest/path",
            bandwidth_limit="100M"
        )
        assert "--bwlimit 100M" in cmd
        
        # Invalid bandwidth limit should raise ValidationError
        with pytest.raises(ValidationError):
            CommandBuilder.build_rsync_command(
                source_path="/source/path",
                dest_path="/dest/path",
                bandwidth_limit="invalid; rm -rf /"
            )
    
    def test_path_sanitization(self):
        """Test path sanitization prevents traversal attacks."""
        # Valid paths should work
        path = SecurityValidator.sanitize_path("file.txt", "/safe/base")
        assert path.startswith("/safe/base")
        
        # Path traversal should be prevented
        with pytest.raises(ValidationError):
            SecurityValidator.sanitize_path("../../../etc/passwd", "/safe/base")
        
        with pytest.raises(ValidationError):
            SecurityValidator.sanitize_path("/etc/passwd", "/safe/base")
    
    def test_ssh_security_policy(self):
        """Test SSH security policy is not AutoAddPolicy."""
        import paramiko
        policy = SSHSecurity.get_known_hosts_policy()
        
        # Should not be AutoAddPolicy (which is insecure)
        assert not isinstance(policy, paramiko.AutoAddPolicy)
        
        # Should be RejectPolicy (secure default)
        assert isinstance(policy, paramiko.RejectPolicy)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])