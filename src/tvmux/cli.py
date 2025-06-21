#!/usr/bin/env python3
"""Main CLI entry point for tvmux."""
import os
import subprocess

import click

from .connection import Connection


@click.group()
@click.option('--log-level', default='INFO', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']),
              help='Set logging level')
@click.version_option()
def cli(log_level):
    """Per-window recorder for tmux."""
    os.environ['TVMUX_LOG_LEVEL'] = log_level


@cli.group()
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
            click.echo(f"Window recorders: {data['recorders']}")

        except Exception as e:
            click.echo(f"Error querying server: {e}", err=True)
    else:
        click.echo("Server not running")


@cli.group()
def record():
    """Manage window recordings."""
    pass


@record.command("start")
def start():
    conn = Connection()
    if not conn.is_running:
        click.echo("Server not running, starting automatically...")
        if not conn.start():
            click.echo("Failed to start server", err=True)
            raise click.Abort()
        click.echo(f"Server started at {conn.base_url}")

    # Check if we're in tmux
    if not os.environ.get("TMUX"):
        click.echo("Not in a tmux session", err=True)
        raise click.Abort()

    # Get current tmux session and window info
    try:
        info = subprocess.run(
            ["tmux", "display-message", "-p",
             "#{session_name}:#{window_id}:#{pane_id}"],
            capture_output=True,
            text=True,
            check=True
        )
        session_name, window_id, pane_id = info.stdout.strip().split(":")
    except subprocess.CalledProcessError:
        click.echo("Failed to get tmux info", err=True)
        raise click.Abort()

    # Call API to start recording
    try:
        api = conn.client()
        response = api.post("/recording/start", json={
            "session_id": session_name,
            "window_name": window_id,
            "active_pane": pane_id
        })

        if response.status_code == 200:
            data = response.json()
            click.echo(f"Started recording window '{window_id}' in session '{session_name}'")
            click.echo(f"Recording to: {data['cast_path']}")
        else:
            click.echo(f"Failed to start recording: {response.text}", err=True)
            raise click.Abort()

    except Exception as e:
        click.echo(f"Error starting recording: {e}", err=True)
        raise click.Abort()


@record.command("list")
def list():
    conn = Connection()
    if not conn.is_running:
        click.echo("Server not running", err=True)
        raise click.Abort()

    # Call API to list recordings
    try:
        api = conn.client()
        response = api.get("/recording/list")

        if response.status_code == 200:
            recordings = response.json()
            if recordings:
                click.echo("Active recordings:")
                for rec in recordings:
                    click.echo(f"  - Session: {rec['session_id']}, Window: {rec['window_name']}")
                    if rec.get('cast_path'):
                        click.echo(f"    Recording to: {rec['cast_path']}")
            else:
                click.echo("No active recordings")
        else:
            click.echo(f"Failed to list recordings: {response.text}", err=True)
            raise click.Abort()

    except Exception as e:
        click.echo(f"Error listing recordings: {e}", err=True)
        raise click.Abort()


@record.command("stop")
def stop():
    conn = Connection()
    if not conn.is_running:
        click.echo("Server not running", err=True)
        raise click.Abort()

    # Check if we're in tmux
    if not os.environ.get("TMUX"):
        click.echo("Not in a tmux session", err=True)
        raise click.Abort()

    # Get current tmux session and window info
    try:
        info = subprocess.run(
            ["tmux", "display-message", "-p",
             "#{session_name}:#{window_id}"],
            capture_output=True,
            text=True,
            check=True
        )
        session_name, window_id = info.stdout.strip().split(":")
    except subprocess.CalledProcessError:
        click.echo("Failed to get tmux info", err=True)
        raise click.Abort()

    # Call API to stop recording
    try:
        api = conn.client()
        response = api.post(f"/recording/stop?session_id={session_name}&window_name={window_id}")

        if response.status_code == 200:
            click.echo(f"Stopped recording window in session '{session_name}'")
        else:
            click.echo(f"Failed to stop recording: {response.text}", err=True)
            raise click.Abort()

    except Exception as e:
        click.echo(f"Error stopping recording: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    cli()
