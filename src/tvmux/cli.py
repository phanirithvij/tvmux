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
        click.echo(f"Server running at {conn.base_url}")
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
        click.echo(f"Server running at {conn.base_url} (PID: {conn.server_pid})")

        # Query server status using the API client
        try:
            api = conn.api()

            # Get basic info
            data = api.get("/").json()

            # Get sessions
            sessions = api.get("/session/").json()

            # Get windows
            windows = api.get("/window/").json()

            # Count total panes
            total_panes = 0
            for window in windows:
                panes = api.get(f"/window/{window['id']}/pane").json()
                total_panes += len(panes)

            click.echo(f"\nSessions: {len(sessions)}")
            click.echo(f"Windows: {len(windows)}")
            click.echo(f"Panes: {total_panes}")
            click.echo(f"Terminal trackers: {data['terminals']}")

        except Exception as e:
            click.echo(f"Error querying server: {e}", err=True)
    else:
        click.echo("Server not running")


if __name__ == "__main__":
    cli()
