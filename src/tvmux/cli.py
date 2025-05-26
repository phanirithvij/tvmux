#!/usr/bin/env python3
"""Main CLI entry point for tvmux."""
import click

from .connection import Connection


@click.group()
@click.version_option()
def cli():
    """Terminal session recorder for tmux."""
    pass


@cli.command()
def start():
    """Start the tvmux server."""
    conn = Connection()
    if conn.start():
        click.echo("Server running")
        click.echo(f"Socket: {conn.socket_path}")
        click.echo(f"Use 'socat TCP-LISTEN:8080,fork UNIX-CONNECT:{conn.socket_path}' to expose to browser")
    else:
        click.echo("Failed to start server", err=True)
        raise click.Abort()


@cli.command()
def stop():
    """Stop the tvmux server."""
    conn = Connection()
    if conn.stop():
        click.echo("Server stopped")
    else:
        click.echo("Failed to stop server", err=True)
        raise click.Abort()


@cli.command()
def status():
    """Check server status."""
    conn = Connection()
    if conn.is_running:
        click.echo(f"Server running (PID: {conn.server_pid})")

        # Query server status
        try:
            with conn.client() as client:
                resp = client.get("/")
                data = resp.json()
                click.echo(f"Terminals: {data['terminals']}")
        except Exception as e:
            click.echo(f"Error querying server: {e}", err=True)
    else:
        click.echo("Server not running")


if __name__ == "__main__":
    cli()
