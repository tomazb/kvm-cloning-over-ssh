"""
Configuration management for KVM cloning operations.

This module handles loading and validating configuration from files and environment variables.
"""

import os
import yaml
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict

from .exceptions import ConfigurationError
from .logging import logger


class AppConfig(BaseModel):
    """Application configuration with Pydantic validation.

    Configuration can be loaded from:
    1. Explicit config file path
    2. Default config file locations
    3. Environment variables (highest priority)

    Environment variables:
    - KVM_CLONE_SSH_KEY_PATH: Path to SSH private key
    - KVM_CLONE_SSH_PORT: Default SSH port
    - KVM_CLONE_TIMEOUT: Default timeout in seconds
    - KVM_CLONE_LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - KVM_CLONE_KNOWN_HOSTS_FILE: Path to known_hosts file
    - KVM_CLONE_PARALLEL_TRANSFERS: Number of parallel transfers
    - KVM_CLONE_BANDWIDTH_LIMIT: Bandwidth limit (e.g., "100M", "1G")
    - KVM_CLONE_SSH_HOST_KEY_POLICY: Host key policy (strict, warn, accept)
    """

    model_config = ConfigDict(extra="forbid")  # Reject unknown fields

    ssh_key_path: Optional[str] = None
    ssh_port: int = Field(default=22, gt=0, le=65535, description="Default SSH port")
    default_timeout: int = Field(
        default=30, gt=0, description="Default SSH timeout in seconds"
    )
    log_level: str = Field(default="INFO", description="Logging level")
    known_hosts_file: Optional[str] = None

    # Default values for operations
    default_parallel_transfers: int = Field(
        default=4, gt=0, description="Number of parallel transfers"
    )
    default_bandwidth_limit: Optional[str] = Field(default=None, pattern=r"^\d+[KMG]?$")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate and normalize log level."""
        v = v.upper()
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v


class ConfigLoader:
    """Loads and validates configuration."""

    def __init__(self) -> None:
        self.logger = logger

    def load_config(self, config_path: Optional[str] = None) -> AppConfig:
        """
        Load configuration from file and environment variables.

        Priority (highest to lowest):
        1. Environment variables
        2. Config file (explicit path or default locations)
        3. Default values

        Args:
            config_path: Path to configuration file. If None, looks in default locations.

        Returns:
            AppConfig: Loaded configuration
        """
        # Start with file-based config
        if config_path:
            config_data = self._load_data_from_file(config_path)
        else:
            # Check default locations
            default_paths = [
                os.path.expanduser("~/.config/kvm-clone/config.yaml"),
                "/etc/kvm-clone/config.yaml",
                "config.yaml",
            ]

            config_data = {}
            for path in default_paths:
                if os.path.exists(path):
                    self.logger.info(f"Loading configuration from {path}", path=path)
                    config_data = self._load_data_from_file(path)
                    break

            if not config_data:
                self.logger.info("No configuration file found, using defaults and environment variables")

        # Apply environment variable overrides (highest priority)
        config_data = self._apply_env_overrides(config_data)

        # Create validated config
        try:
            return AppConfig(**config_data)
        except ValueError as e:
            self.logger.error(f"Invalid configuration: {e}", exc_info=True)
            raise ConfigurationError(f"Invalid configuration: {e}")

    def _apply_env_overrides(self, config_data: dict) -> dict:
        """Apply environment variable overrides to config data."""
        env_mappings = {
            'KVM_CLONE_SSH_KEY_PATH': 'ssh_key_path',
            'KVM_CLONE_SSH_PORT': ('ssh_port', int),
            'KVM_CLONE_TIMEOUT': ('default_timeout', int),
            'KVM_CLONE_LOG_LEVEL': 'log_level',
            'KVM_CLONE_KNOWN_HOSTS_FILE': 'known_hosts_file',
            'KVM_CLONE_PARALLEL_TRANSFERS': ('default_parallel_transfers', int),
            'KVM_CLONE_BANDWIDTH_LIMIT': 'default_bandwidth_limit',
        }

        for env_var, mapping in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # Handle type conversion
                if isinstance(mapping, tuple):
                    config_key, converter = mapping
                    try:
                        config_data[config_key] = converter(env_value)
                        self.logger.debug(f"Applied environment override: {env_var}={env_value}")
                    except (ValueError, TypeError) as e:
                        self.logger.warning(
                            f"Invalid value for {env_var}: {env_value}, ignoring. Error: {e}"
                        )
                else:
                    config_key = mapping
                    config_data[config_key] = env_value
                    self.logger.debug(f"Applied environment override: {env_var}={env_value}")

        return config_data

    def _load_data_from_file(self, path: str) -> dict:
        """Load configuration data from a specific file."""
        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)

            if data is None:
                # Empty file, return empty dict
                return {}

            if not isinstance(data, dict):
                raise ConfigurationError(f"Invalid configuration format in {path}")

            return data

        except yaml.YAMLError as e:
            self.logger.error(
                f"Failed to parse configuration file {path}: {e}",
                path=path,
                exc_info=True,
            )
            raise ConfigurationError(f"Failed to parse configuration file: {e}")
        except Exception as e:
            self.logger.error(
                f"Failed to load configuration from {path}: {e}",
                path=path,
                exc_info=True,
            )
            raise ConfigurationError(f"Failed to load configuration: {e}")


# Global config loader
config_loader = ConfigLoader()
