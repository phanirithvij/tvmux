#!/usr/bin/env python3
"""Main CLI entry point for tvmux."""
import os
import click

from .server import server
from .record import rec


@click.group()
@click.option('--log-level', default='INFO', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']),
              help='Set logging level')
@click.version_option()
def cli(log_level):
    """Per-window recorder for tmux."""
    os.environ['TVMUX_LOG_LEVEL'] = log_level


cli.add_command(server)
cli.add_command(rec)


if __name__ == "__main__":
    cli()
