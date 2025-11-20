#!/usr/bin/env python3
"""
Command-line interface for KVM cloning operations.

This module provides the CLI interface as specified in the API documentation.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional, Any

import click
import yaml

from kvm_clone import KVMCloneClient, CloneOptions, SyncOptions
from kvm_clone.exceptions import KVMCloneError, ConfigurationError
from kvm_clone.config import config_loader


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def setup_logging(
    verbose: bool = False, quiet: bool = False, log_level: str = "INFO"
) -> None:
    """Setup logging configuration."""
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = getattr(logging, log_level.upper(), logging.INFO)

    logging.getLogger().setLevel(level)


def load_config(config_path: Optional[str]) -> dict[str, Any]:
    """Load configuration from file."""
    try:
        app_config = config_loader.load_config(config_path)
        # Convert back to dict for compatibility with existing code
        # In a full refactor, we would use AppConfig object directly
        return {
            "ssh_key_path": app_config.ssh_key_path,
            "default_timeout": app_config.default_timeout,
            "log_level": app_config.log_level,
            "known_hosts_file": app_config.known_hosts_file,
            "parallel_transfers": app_config.default_parallel_transfers,
            "bandwidth_limit": app_config.default_bandwidth_limit,
        }
    except ConfigurationError as e:
        click.echo(f"Warning: {e}", err=True)
        return {}


def progress_callback(progress_info: Any) -> None:
    """Progress callback for operations."""
    click.echo(
        f"\rProgress: {progress_info.progress_percent:.1f}% "
        f"({progress_info.bytes_transferred}/{progress_info.total_bytes} bytes) "
        f"Speed: {progress_info.speed / 1024 / 1024:.1f} MB/s",
        nl=False,
    )


@click.group()
@click.option("--config", "-c", default=None, help="Configuration file path")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--quiet", "-q", is_flag=True, help="Suppress non-error output")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARN", "ERROR"]),
    default="INFO",
    help="Log level",
)
@click.version_option()
@click.pass_context
def cli(
    ctx: Any, config: Any, verbose: bool, quiet: bool, output: str, log_level: str
) -> None:
    """KVM cloning over SSH tool."""
    setup_logging(verbose, quiet, log_level)

    # Load configuration
    config_data = load_config(config)

    # Store in context
    ctx.ensure_object(dict)
    ctx.obj["config"] = config_data
    ctx.obj["output_format"] = output
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet


@cli.command()
@click.argument("source_host")
@click.argument("dest_host")
@click.argument("vm_name")
@click.option("--new-name", "-n", help="Name for cloned VM")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing VM")
@click.option(
    "--idempotent",
    is_flag=True,
    help="Auto-cleanup existing VM and retry (safe for automation)",
)
@click.option("--dry-run", is_flag=True, help="Show what would be done")
@click.option(
    "--parallel", "-p", type=int, default=4, help="Number of parallel transfers"
)
@click.option("--compress", is_flag=True, help="Enable compression during transfer")
@click.option(
    "--verify", is_flag=True, default=True, help="Verify integrity after transfer"
)
@click.option("--timeout", type=int, default=3600, help="Operation timeout in seconds")
@click.option("--ssh-key", "-k", help="SSH private key path")
@click.option("--preserve-mac", is_flag=True, help="Preserve MAC addresses")
@click.option(
    "--network-config",
    type=click.Path(exists=True),
    help="Custom network configuration file",
)
@click.option("--bandwidth-limit", "-b", help='Bandwidth limit (e.g., "100M", "1G")')
@click.pass_context
def clone(
    ctx: Any,
    source_host: str,
    dest_host: str,
    vm_name: str,
    new_name: Optional[str],
    force: bool,
    idempotent: bool,
    dry_run: bool,
    parallel: int,
    compress: bool,
    verify: bool,
    timeout: int,
    ssh_key: Optional[str],
    preserve_mac: bool,
    network_config: Optional[str],
    bandwidth_limit: Optional[str],
) -> None:
    """Clone a virtual machine from source to destination host."""

    async def run_clone() -> None:
        try:
            # Load network config if provided
            network_cfg = None
            if network_config:
                with open(network_config, "r") as f:
                    network_cfg = yaml.safe_load(f)

            # Create client
            client_config = ctx.obj["config"].copy()
            if ssh_key:
                client_config["ssh_key_path"] = ssh_key

            async with KVMCloneClient(config=client_config, timeout=timeout) as client:
                clone_options = CloneOptions(
                    new_name=new_name,
                    force=force,
                    idempotent=idempotent,
                    dry_run=dry_run,
                    parallel=parallel,
                    compress=compress,
                    verify=verify,
                    preserve_mac=preserve_mac,
                    network_config=network_cfg,
                    bandwidth_limit=bandwidth_limit,
                )

                if not ctx.obj["quiet"]:
                    click.echo(
                        f"Cloning VM '{vm_name}' from {source_host} to {dest_host}..."
                    )

                result = await client.clone_vm(
                    source_host=source_host,
                    dest_host=dest_host,
                    vm_name=vm_name,
                    **clone_options.__dict__,
                    progress_callback=progress_callback
                    if not ctx.obj["quiet"]
                    else None,
                )

                if not ctx.obj["quiet"]:
                    click.echo()  # New line after progress

                if result.success:
                    click.echo(
                        f"✓ Successfully cloned VM '{vm_name}' to '{result.new_vm_name}'"
                    )
                    click.echo(f"  Duration: {result.duration:.1f}s")
                    click.echo(f"  Bytes transferred: {result.bytes_transferred}")

                    if result.warnings:
                        for warning in result.warnings:
                            click.echo(f"  Warning: {warning}", err=True)
                else:
                    click.echo(f"✗ Clone failed: {result.error}", err=True)
                    sys.exit(1)

        except KVMCloneError as e:
            click.echo(f"✗ Error: {e}", err=True)
            sys.exit(e.error_code)
        except Exception as e:
            click.echo(f"✗ Unexpected error: {e}", err=True)
            sys.exit(1)

    asyncio.run(run_clone())


@cli.command()
@click.argument("source_host")
@click.argument("dest_host")
@click.argument("vm_name")
@click.option("--target-name", "-t", help="Target VM name on destination")
@click.option("--checkpoint", is_flag=True, help="Create checkpoint before sync")
@click.option(
    "--delta-only", is_flag=True, default=True, help="Transfer only changed blocks"
)
@click.option("--bandwidth-limit", "-b", help='Bandwidth limit (e.g., "100M", "1G")')
@click.option("--ssh-key", "-k", help="SSH private key path")
@click.option("--timeout", type=int, default=7200, help="Operation timeout in seconds")
@click.pass_context
def sync(
    ctx: Any,
    source_host: str,
    dest_host: str,
    vm_name: str,
    target_name: Optional[str],
    checkpoint: bool,
    delta_only: bool,
    bandwidth_limit: Optional[str],
    ssh_key: Optional[str],
    timeout: int,
) -> None:
    """Synchronize an existing VM between hosts (incremental transfer)."""

    async def run_sync() -> None:
        try:
            # Create client
            client_config = ctx.obj["config"].copy()
            if ssh_key:
                client_config["ssh_key_path"] = ssh_key

            async with KVMCloneClient(config=client_config, timeout=timeout) as client:
                sync_options = SyncOptions(
                    target_name=target_name,
                    checkpoint=checkpoint,
                    delta_only=delta_only,
                    bandwidth_limit=bandwidth_limit,
                )

                if not ctx.obj["quiet"]:
                    click.echo(
                        f"Synchronizing VM '{vm_name}' from {source_host} to {dest_host}..."
                    )

                result = await client.sync_vm(
                    source_host=source_host,
                    dest_host=dest_host,
                    vm_name=vm_name,
                    **sync_options.__dict__,
                    progress_callback=progress_callback
                    if not ctx.obj["quiet"]
                    else None,
                )

                if not ctx.obj["quiet"]:
                    click.echo()  # New line after progress

                if result.success:
                    click.echo(f"✓ Successfully synchronized VM '{vm_name}'")
                    click.echo(f"  Duration: {result.duration:.1f}s")
                    click.echo(f"  Bytes transferred: {result.bytes_transferred}")
                    click.echo(f"  Blocks synchronized: {result.blocks_synchronized}")
                else:
                    click.echo(f"✗ Sync failed: {result.error}", err=True)
                    sys.exit(1)

        except KVMCloneError as e:
            click.echo(f"✗ Error: {e}", err=True)
            sys.exit(e.error_code)
        except Exception as e:
            click.echo(f"✗ Unexpected error: {e}", err=True)
            sys.exit(1)

    asyncio.run(run_sync())


@cli.command()
@click.argument("hosts", nargs=-1)
@click.option(
    "--status",
    "-s",
    type=click.Choice(["all", "running", "stopped", "paused"]),
    default="all",
    help="Filter by status",
)
@click.option("--ssh-key", "-k", help="SSH private key path")
@click.pass_context
def list_vms(
    ctx: Any,
    hosts: tuple[str, ...],
    status: str,
    ssh_key: Optional[str],
) -> None:
    """List virtual machines on specified hosts."""

    async def run_list() -> None:
        try:
            if not hosts:
                hosts_list = ["localhost"]
            else:
                hosts_list = list(hosts)

            # Create client
            client_config = ctx.obj["config"].copy()
            if ssh_key:
                client_config["ssh_key_path"] = ssh_key

            # Get output format from global context
            output_format = ctx.obj.get("output_format", "text")

            async with KVMCloneClient(config=client_config) as client:
                results = await client.list_vms(hosts_list, status_filter=status)

                if output_format in ("text", "table"):
                    for host, vms in results.items():
                        click.echo(f"\n{host}:")
                        if vms:
                            click.echo(
                                f"{'Name':<20} {'State':<10} {'Memory':<8} {'vCPUs':<6}"
                            )
                            click.echo("-" * 50)
                            for vm in vms:
                                click.echo(
                                    f"{vm.name:<20} {vm.state.value:<10} {vm.memory:<8} {vm.vcpus:<6}"
                                )
                        else:
                            click.echo("  No VMs found")
                elif output_format == "json":
                    import json

                    # Convert to JSON-serializable format
                    json_data = {}
                    for host, vms in results.items():
                        json_data[host] = [
                            {
                                "name": vm.name,
                                "state": vm.state.value,
                                "memory": vm.memory,
                                "vcpus": vm.vcpus,
                                "uuid": vm.uuid,
                            }
                            for vm in vms
                        ]
                    click.echo(json.dumps(json_data, indent=2))

        except KVMCloneError as e:
            click.echo(f"✗ Error: {e}", err=True)
            sys.exit(e.error_code)
        except Exception as e:
            click.echo(f"✗ Unexpected error: {e}", err=True)
            sys.exit(1)

    asyncio.run(run_list())


@cli.group()
def config() -> None:
    """Manage configuration settings."""
    pass


@config.command("show")
@click.pass_context
def config_show(ctx: Any) -> None:
    """Display current configuration."""
    config_data = ctx.obj["config"]
    if config_data:
        click.echo(yaml.dump(config_data, default_flow_style=False))
    else:
        click.echo("No configuration found")


@config.command("init")
@click.option("--config-dir", default="~/.config/kvm-clone", help="Configuration directory")
def config_init(config_dir: str) -> None:
    """Initialize default configuration."""
    config_path = Path(config_dir).expanduser()
    config_path.mkdir(parents=True, exist_ok=True)

    config_file = config_path / "config.yaml"

    # Generate config that matches AppConfig schema
    default_config = {
        "ssh_key_path": None,
        "ssh_port": 22,
        "default_timeout": 30,
        "log_level": "INFO",
        "known_hosts_file": None,
        "default_parallel_transfers": 4,
        "default_bandwidth_limit": None,
    }

    with open(config_file, "w") as f:
        yaml.dump(default_config, f, default_flow_style=False)

    click.echo(f"Configuration initialized at {config_file}")


def _load_config_file(config_dir: str) -> tuple[Path, dict]:
    """
    Helper to load configuration file.
    
    Returns:
        Tuple of (config_path, config_data)
    
    Raises:
        SystemExit if config file doesn't exist
    """
    config_path = Path(config_dir).expanduser() / "config.yaml"

    if not config_path.exists():
        click.echo(f"Configuration file not found at {config_path}", err=True)
        click.echo("Run 'kvm-clone config init' to create one.", err=True)
        sys.exit(1)

    try:
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f) or {}
        return config_path, config_data
    except Exception as e:
        click.echo(f"Error reading configuration: {e}", err=True)
        sys.exit(1)


@config.command("get")
@click.argument("key")
@click.option("--config-dir", default="~/.config/kvm-clone", help="Configuration directory")
def config_get(key: str, config_dir: str) -> None:
    """Get a configuration value."""
    config_path, config_data = _load_config_file(config_dir)

    if key in config_data:
        click.echo(f"{key}: {config_data[key]}")
    else:
        click.echo(f"Key '{key}' not found in configuration", err=True)
        sys.exit(1)


@config.command("set")
@click.argument("key")
@click.argument("value")
@click.option("--config-dir", default="~/.config/kvm-clone", help="Configuration directory")
def config_set(key: str, value: str, config_dir: str) -> None:
    """Set a configuration value."""
    config_path = Path(config_dir).expanduser() / "config.yaml"

    # Load existing config or create empty dict
    if config_path.exists():
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f) or {}
    else:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_data = {}

    # Convert value to appropriate type
    l_value = value.lower()
    if l_value in ("null", "none"):
        config_data[key] = None
    elif l_value == "true":
        config_data[key] = True
    elif l_value == "false":
        config_data[key] = False
    else:
        # Try int, then float, then keep as string
        try:
            config_data[key] = int(value)
        except ValueError:
            try:
                config_data[key] = float(value)
            except ValueError:
                config_data[key] = value

    # Save config
    try:
        with open(config_path, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False)
        click.echo(f"✓ Set {key} = {config_data[key]}")
    except Exception as e:
        click.echo(f"Error saving configuration: {e}", err=True)
        sys.exit(1)


@config.command("unset")
@click.argument("key")
@click.option("--config-dir", default="~/.config/kvm-clone", help="Configuration directory")
@click.option("--ignore-missing", is_flag=True, help="Don't error if key doesn't exist (idempotent)")
def config_unset(key: str, config_dir: str, ignore_missing: bool) -> None:
    """Remove a configuration value."""
    config_path = Path(config_dir).expanduser() / "config.yaml"

    if not config_path.exists():
        if ignore_missing:
            click.echo(f"✓ Key {key} already absent (no config file)")
            return
        click.echo(f"Configuration file not found at {config_path}", err=True)
        sys.exit(1)

    try:
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f) or {}

        if key in config_data:
            del config_data[key]
            with open(config_path, "w") as f:
                yaml.dump(config_data, f, default_flow_style=False)
            click.echo(f"✓ Removed {key}")
        else:
            if ignore_missing:
                click.echo(f"✓ Key {key} already absent")
            else:
                click.echo(f"Key '{key}' not found in configuration", err=True)
                sys.exit(1)

    except Exception as e:
        click.echo(f"Error updating configuration: {e}", err=True)
        sys.exit(1)


@config.command("list")
@click.option("--config-dir", default="~/.config/kvm-clone", help="Configuration directory")
def config_list(config_dir: str) -> None:
    """List all configuration values."""
    config_path, config_data = _load_config_file(config_dir)

    if config_data:
        click.echo(f"Configuration from {config_path}:\n")
        for key, value in sorted(config_data.items()):
            click.echo(f"  {key}: {value}")
    else:
        click.echo("Configuration file is empty")


@config.command("path")
def config_path() -> None:
    """Show the configuration file path being used."""
    default_paths = [
        os.path.expanduser("~/.config/kvm-clone/config.yaml"),
        "/etc/kvm-clone/config.yaml",
        "config.yaml",
    ]

    click.echo("Configuration search paths (in order):")
    for i, path in enumerate(default_paths, 1):
        exists = "✓" if os.path.exists(path) else "✗"
        click.echo(f"  {i}. {exists} {path}")

    # Find which one is actually being used
    for path in default_paths:
        if os.path.exists(path):
            click.echo(f"\nCurrently using: {path}")
            return

    click.echo("\nNo configuration file found. Run 'kvm-clone config init' to create one.")


if __name__ == "__main__":
    cli()
