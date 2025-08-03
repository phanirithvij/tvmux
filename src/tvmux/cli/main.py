#!/usr/bin/env python3
"""Main CLI entry point for tvmux."""
import os
import click

from .server import server
from .record import rec
from ..config import load_config, set_config


@click.group()
@click.option('--log-level', default='INFO', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']),
              help='Set logging level')
@click.option('--config-file', type=click.Path(exists=True),
              help='Path to configuration file')
@click.version_option()
def cli(log_level, config_file):
    """Per-window recorder for tmux."""
    os.environ['TVMUX_LOG_LEVEL'] = log_level

    # Load configuration
    config = load_config(config_file)
    set_config(config)


cli.add_command(server)
cli.add_command(rec)


if __name__ == "__main__":
    cli()
