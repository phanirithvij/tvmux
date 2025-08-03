"""Server management commands."""
import click

from ..connection import Connection


@click.group()
def server():
    """Manage the tvmux server."""
    pass


@server.command("start")
def start():
    conn = Connection()
    if conn.start():
        click.echo(f"Server running at {conn.base_url}")
    else:
        click.echo("Failed to start server", err=True)
        raise click.Abort()


@server.command("stop")
def stop():
    conn = Connection()
    if conn.stop():
        click.echo("Server stopped")
    else:
        click.echo("Failed to stop server", err=True)
        raise click.Abort()


@server.command("status")
def status():
    conn = Connection()
    if conn.is_running:
        click.echo(f"Server running at {conn.base_url} (PID: {conn.server_pid})")

        # Query server status using the API client
        try:
            api = conn.api()

            # Get basic info
            data = api.get("/").json()

            # Get sessions
            sessions = api.get("/sessions/").json()

            # Get windows
            windows = api.get("/windows/").json()

            # Get all panes
            panes = api.get("/panes/").json()

            click.echo(f"\nSessions: {len(sessions)}")
            click.echo(f"Windows: {len(windows)}")
            click.echo(f"Panes: {len(panes)}")
            click.echo(f"Active recordings: {data['recorders']}")

        except Exception as e:
            click.echo(f"Error querying server: {e}", err=True)
    else:
        click.echo("Server not running")
