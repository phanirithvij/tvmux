#!/usr/bin/env python3
"""Main CLI entry point for tvmux."""
import click


@click.group()
@click.version_option()
def cli():
    """Terminal session recorder for tmux."""
    pass


@cli.command()
def start():
    """Start the tvmux server and begin recording current window."""
    click.echo("Starting tvmux server...")
    # TODO: Start uvicorn daemon
    # TODO: Start recording current tmux window
    click.echo("Recording started")


@cli.command()
def stop():
    """Stop the tvmux server and recording."""
    click.echo("Stopping tvmux server...")
    # TODO: Stop recording
    # TODO: Stop daemon
    click.echo("Server stopped")


if __name__ == "__main__":
    cli()
