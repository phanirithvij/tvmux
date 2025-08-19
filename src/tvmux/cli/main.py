#!/usr/bin/env python3
"""Main CLI entry point for tvmux."""
import os
import click

from .server import server
from .record import rec
from .config import config
from .api_cli import api
from ..config import load_config, set_config
from ..connection import Connection
from .. import __version__


def print_version(ctx, param, value):
    """Print version information for client and server."""
    if not value or ctx.resilient_parsing:
        return

    click.echo(f"tvmux client version: {__version__}")

    # Try to get server version if running
    conn = Connection()
    if conn.is_running:
        try:
            api = conn.client()
            response = api.get("/version")
            if response.status_code == 200:
                server_version = response.json().get("version", "unknown")
                click.echo(f"tvmux server version: {server_version}")
            else:
                click.echo("tvmux server version: unable to retrieve")
        except Exception:
            click.echo("tvmux server version: error connecting")
    else:
        click.echo("tvmux server: not running")

    ctx.exit()


@click.group()
@click.option('--log-level', default='INFO', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']),
              help='Set logging level')
@click.option('--config-file', type=click.Path(exists=True),
              help='Path to configuration file')
@click.option('--version', is_flag=True, callback=print_version,
              expose_value=False, is_eager=True, help='Show version information')
def cli(log_level, config_file):
    """Per-window recorder for tmux."""
    os.environ['TVMUX_LOG_LEVEL'] = log_level

    # Load configuration
    config = load_config(config_file)
    set_config(config)


cli.add_command(server)
cli.add_command(rec)
cli.add_command(config)
cli.add_command(api)


if __name__ == "__main__":
    cli()
