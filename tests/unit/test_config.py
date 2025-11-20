"""Comprehensive unit tests for configuration management."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
import yaml

from kvm_clone.config import AppConfig, ConfigLoader, config_loader
from kvm_clone.exceptions import ConfigurationError


class TestAppConfig:
    """Test AppConfig Pydantic model."""
    
    def test_app_config_defaults(self):
        """Test AppConfig default values."""
        config = AppConfig()
        assert config.ssh_key_path is None
        assert config.default_timeout == 30
        assert config.log_level == "INFO"
        assert config.known_hosts_file is None
        assert config.default_parallel_transfers == 4
        assert config.default_bandwidth_limit is None
    
    def test_app_config_custom_values(self):
        """Test AppConfig with custom values."""
        config = AppConfig(
            ssh_key_path="/home/user/.ssh/id_rsa",
            default_timeout=60,
            log_level="DEBUG",
            known_hosts_file="/home/user/.ssh/known_hosts",
            default_parallel_transfers=8,
            default_bandwidth_limit="100M"
        )
        assert config.ssh_key_path == "/home/user/.ssh/id_rsa"
        assert config.default_timeout == 60
        assert config.log_level == "DEBUG"
        assert config.known_hosts_file == "/home/user/.ssh/known_hosts"
        assert config.default_parallel_transfers == 8
        assert config.default_bandwidth_limit == "100M"
    
    def test_app_config_log_level_validation(self):
        """Test log_level validation and normalization."""
        # Valid log levels
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            config = AppConfig(log_level=level)
            assert config.log_level == level
        
        # Lowercase should be converted to uppercase
        config = AppConfig(log_level="debug")
        assert config.log_level == "DEBUG"
        
        config = AppConfig(log_level="info")
        assert config.log_level == "INFO"
    
    def test_app_config_invalid_log_level(self):
        """Test invalid log level raises ValueError."""
        with pytest.raises(ValueError, match="log_level must be one of"):
            AppConfig(log_level="INVALID")
        
        with pytest.raises(ValueError):
            AppConfig(log_level="TRACE")
    
    def test_app_config_timeout_validation(self):
        """Test timeout must be positive."""
        # Valid timeouts
        config = AppConfig(default_timeout=1)
        assert config.default_timeout == 1
        
        config = AppConfig(default_timeout=3600)
        assert config.default_timeout == 3600
        
        # Invalid timeouts
        with pytest.raises(ValueError):
            AppConfig(default_timeout=0)
        
        with pytest.raises(ValueError):
            AppConfig(default_timeout=-1)
    
    def test_app_config_parallel_transfers_validation(self):
        """Test parallel_transfers must be positive."""
        # Valid values
        config = AppConfig(default_parallel_transfers=1)
        assert config.default_parallel_transfers == 1
        
        config = AppConfig(default_parallel_transfers=16)
        assert config.default_parallel_transfers == 16
        
        # Invalid values
        with pytest.raises(ValueError):
            AppConfig(default_parallel_transfers=0)
        
        with pytest.raises(ValueError):
            AppConfig(default_parallel_transfers=-5)
    
    def test_app_config_bandwidth_limit_validation(self):
        """Test bandwidth_limit format validation."""
        # Valid formats
        valid_limits = ["100", "100K", "100M", "100G", "1000M"]
        for limit in valid_limits:
            config = AppConfig(default_bandwidth_limit=limit)
            assert config.default_bandwidth_limit == limit
        
        # Invalid formats
        invalid_limits = ["100X", "abc", "100 M", "-100M"]
        for limit in invalid_limits:
            with pytest.raises(ValueError):
                AppConfig(default_bandwidth_limit=limit)
    
    def test_app_config_forbids_unknown_fields(self):
        """Test AppConfig rejects unknown fields."""
        with pytest.raises(ValueError):
            AppConfig(unknown_field="value")
    
    def test_app_config_serialization(self):
        """Test AppConfig can be serialized to dict."""
        config = AppConfig(
            ssh_key_path="/key",
            default_timeout=45,
            log_level="WARNING"
        )
        data = config.model_dump()
        assert data["ssh_key_path"] == "/key"
        assert data["default_timeout"] == 45
        assert data["log_level"] == "WARNING"


class TestConfigLoader:
    """Test ConfigLoader class."""
    
    def test_config_loader_initialization(self):
        """Test ConfigLoader can be initialized."""
        loader = ConfigLoader()
        assert loader.logger is not None
    
    def test_load_config_with_no_file_returns_defaults(self):
        """Test load_config returns defaults when no file exists."""
        loader = ConfigLoader()
        with patch('os.path.exists', return_value=False):
            config = loader.load_config()
            assert isinstance(config, AppConfig)
            assert config.default_timeout == 30
            assert config.log_level == "INFO"
    
    def test_load_config_from_specified_path(self):
        """Test load_config loads from specified path."""
        yaml_content = """
ssh_key_path: /custom/key
default_timeout: 120
log_level: DEBUG
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            loader = ConfigLoader()
            config = loader.load_config(temp_path)
            assert config.ssh_key_path == "/custom/key"
            assert config.default_timeout == 120
            assert config.log_level == "DEBUG"
        finally:
            os.unlink(temp_path)
    
    def test_load_config_from_default_locations(self):
        """Test load_config checks default locations."""
        loader = ConfigLoader()
        
        yaml_content = """
default_timeout: 90
log_level: ERROR
"""
        # Mock exists to return True for config.yaml
        def mock_exists(path):
            return path == "config.yaml"
        
        with patch('os.path.exists', side_effect=mock_exists):
            with patch('builtins.open', mock_open(read_data=yaml_content)):
                config = loader.load_config()
                assert config.default_timeout == 90
                assert config.log_level == "ERROR"
    
    def test_load_config_with_empty_file(self):
        """Test load_config handles empty YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("")
            temp_path = f.name
        
        try:
            loader = ConfigLoader()
            config = loader.load_config(temp_path)
            # Should return defaults
            assert config.default_timeout == 30
            assert config.log_level == "INFO"
        finally:
            os.unlink(temp_path)
    
    def test_load_config_with_invalid_yaml(self):
        """Test load_config raises ConfigurationError for invalid YAML."""
        invalid_yaml = """
key: value
  invalid indentation
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_yaml)
            temp_path = f.name
        
        try:
            loader = ConfigLoader()
            with pytest.raises(ConfigurationError, match="Failed to parse configuration file"):
                loader.load_config(temp_path)
        finally:
            os.unlink(temp_path)
    
    def test_load_config_with_invalid_format(self):
        """Test load_config raises ConfigurationError for non-dict YAML."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("- item1\n- item2\n")  # YAML list, not dict
            temp_path = f.name
        
        try:
            loader = ConfigLoader()
            with pytest.raises(ConfigurationError, match="Invalid configuration format"):
                loader.load_config(temp_path)
        finally:
            os.unlink(temp_path)
    
    def test_load_config_with_invalid_values(self):
        """Test load_config raises ConfigurationError for invalid values."""
        yaml_content = """
default_timeout: -10
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            loader = ConfigLoader()
            with pytest.raises(ConfigurationError, match="Invalid configuration"):
                loader.load_config(temp_path)
        finally:
            os.unlink(temp_path)
    
    def test_load_config_with_unknown_fields(self):
        """Test load_config raises ConfigurationError for unknown fields."""
        yaml_content = """
ssh_key_path: /key
unknown_field: value
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            loader = ConfigLoader()
            with pytest.raises(ConfigurationError):
                loader.load_config(temp_path)
        finally:
            os.unlink(temp_path)
    
    def test_load_config_file_not_found(self):
        """Test load_config handles non-existent file."""
        loader = ConfigLoader()
        with pytest.raises(ConfigurationError):
            loader.load_config("/nonexistent/path/config.yaml")
    
    def test_load_config_logs_info_messages(self):
        """Test load_config logs appropriate info messages."""
        loader = ConfigLoader()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("log_level: DEBUG\n")
            temp_path = f.name
        
        try:
            # Just ensure it doesn't raise - actual logging tested separately
            config = loader.load_config(temp_path)
            assert config.log_level == "DEBUG"
        finally:
            os.unlink(temp_path)
    
    def test_load_config_all_fields(self):
        """Test load_config with all fields specified."""
        yaml_content = """
ssh_key_path: /home/user/.ssh/custom_key
default_timeout: 180
log_level: WARNING
known_hosts_file: /home/user/.ssh/custom_known_hosts
default_parallel_transfers: 12
default_bandwidth_limit: 500M
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            loader = ConfigLoader()
            config = loader.load_config(temp_path)
            assert config.ssh_key_path == "/home/user/.ssh/custom_key"
            assert config.default_timeout == 180
            assert config.log_level == "WARNING"
            assert config.known_hosts_file == "/home/user/.ssh/custom_known_hosts"
            assert config.default_parallel_transfers == 12
            assert config.default_bandwidth_limit == "500M"
        finally:
            os.unlink(temp_path)


class TestGlobalConfigLoader:
    """Test global config_loader instance."""
    
    def test_global_config_loader_exists(self):
        """Test global config_loader is accessible."""
        assert config_loader is not None
        assert isinstance(config_loader, ConfigLoader)
    
    def test_global_config_loader_can_load_config(self):
        """Test global config_loader can load configuration."""
        with patch('os.path.exists', return_value=False):
            config = config_loader.load_config()
            assert isinstance(config, AppConfig)


class TestConfigIntegration:
    """Test configuration integration scenarios."""
    
    def test_minimal_config_file(self):
        """Test minimal valid configuration file."""
        yaml_content = "log_level: INFO\n"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            loader = ConfigLoader()
            config = loader.load_config(temp_path)
            assert config.log_level == "INFO"
            assert config.default_timeout == 30  # Default
        finally:
            os.unlink(temp_path)
    
    def test_production_like_config(self):
        """Test production-like configuration."""
        yaml_content = """
ssh_key_path: /root/.ssh/id_rsa_production
default_timeout: 3600
log_level: ERROR
known_hosts_file: /etc/ssh/known_hosts
default_parallel_transfers: 8
default_bandwidth_limit: 1000M
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            loader = ConfigLoader()
            config = loader.load_config(temp_path)
            assert config.ssh_key_path == "/root/.ssh/id_rsa_production"
            assert config.default_timeout == 3600
            assert config.log_level == "ERROR"
            assert config.default_parallel_transfers == 8
        finally:
            os.unlink(temp_path)
    
    def test_development_config(self):
        """Test development configuration."""
        yaml_content = """
ssh_key_path: ~/.ssh/id_rsa
default_timeout: 60
log_level: DEBUG
default_parallel_transfers: 2
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            loader = ConfigLoader()
            config = loader.load_config(temp_path)
            assert config.log_level == "DEBUG"
            assert config.default_parallel_transfers == 2
        finally:
            os.unlink(temp_path)


class TestConfigEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_config_with_comments(self):
        """Test configuration file with YAML comments."""
        yaml_content = """
# SSH Configuration
ssh_key_path: /key  # Path to SSH key
default_timeout: 60  # Timeout in seconds

# Logging
log_level: DEBUG
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            loader = ConfigLoader()
            config = loader.load_config(temp_path)
            assert config.ssh_key_path == "/key"
            assert config.default_timeout == 60
        finally:
            os.unlink(temp_path)
    
    def test_config_with_null_values(self):
        """Test configuration with explicit null values."""
        yaml_content = """
ssh_key_path: null
known_hosts_file: null
default_bandwidth_limit: null
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            loader = ConfigLoader()
            config = loader.load_config(temp_path)
            assert config.ssh_key_path is None
            assert config.known_hosts_file is None
            assert config.default_bandwidth_limit is None
        finally:
            os.unlink(temp_path)
    
    def test_config_bandwidth_limit_edge_cases(self):
        """Test bandwidth limit edge cases."""
        test_cases = [
            ("1", "1"),
            ("1K", "1K"),
            ("1M", "1M"),
            ("1G", "1G"),
            ("999999", "999999"),
            ("999999G", "999999G"),
        ]
        
        for input_val, expected in test_cases:
            config = AppConfig(default_bandwidth_limit=input_val)
            assert config.default_bandwidth_limit == expected
    
    def test_config_minimum_timeout(self):
        """Test minimum valid timeout value."""
        config = AppConfig(default_timeout=1)
        assert config.default_timeout == 1
    
    def test_config_minimum_parallel_transfers(self):
        """Test minimum valid parallel_transfers value."""
        config = AppConfig(default_parallel_transfers=1)
        assert config.default_parallel_transfers == 1
    
    def test_config_very_large_timeout(self):
        """Test very large timeout value."""
        config = AppConfig(default_timeout=86400)  # 24 hours
        assert config.default_timeout == 86400