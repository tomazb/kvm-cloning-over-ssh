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
    """Application configuration with Pydantic validation."""

    model_config = ConfigDict(extra="forbid")  # Reject unknown fields

    ssh_key_path: Optional[str] = None
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
        Load configuration from file.

        Args:
            config_path: Path to configuration file. If None, looks in default locations.

        Returns:
            AppConfig: Loaded configuration
        """
        if config_path:
            return self._load_from_file(config_path)

        # Check default locations
        default_paths = [
            os.path.expanduser("~/.config/kvm-clone/config.yaml"),
            "/etc/kvm-clone/config.yaml",
            "config.yaml",
        ]

        for path in default_paths:
            if os.path.exists(path):
                self.logger.info(f"Loading configuration from {path}", path=path)
                return self._load_from_file(path)

        self.logger.info("No configuration file found, using defaults")
        return AppConfig()

    def _load_from_file(self, path: str) -> AppConfig:
        """Load configuration from a specific file."""
        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)

            if data is None:
                # Empty file, use defaults
                return AppConfig()

            if not isinstance(data, dict):
                raise ConfigurationError(f"Invalid configuration format in {path}")

            # Pydantic handles all validation
            return AppConfig(**data)

        except yaml.YAMLError as e:
            self.logger.error(
                f"Failed to parse configuration file {path}: {e}",
                path=path,
                exc_info=True,
            )
            raise ConfigurationError(f"Failed to parse configuration file: {e}")
        except ValueError as e:
            # Pydantic validation error
            self.logger.error(
                f"Invalid configuration in {path}: {e}", path=path, exc_info=True
            )
            raise ConfigurationError(f"Invalid configuration: {e}")
        except Exception as e:
            self.logger.error(
                f"Failed to load configuration from {path}: {e}",
                path=path,
                exc_info=True,
            )
            raise ConfigurationError(f"Failed to load configuration: {e}")


# Global config loader
config_loader = ConfigLoader()
