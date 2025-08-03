"""Recording management commands."""
import os
import subprocess

import click

from ..connection import Connection
from ..api_client import APIError
from ..server.routers.recording import RecordingCreate


@click.group(invoke_without_command=True)
@click.pass_context
def rec(ctx):
    """Manage window recordings."""
    if ctx.invoked_subcommand is None:
        # Default to start command
        ctx.invoke(start)


@rec.command("start")
def start():
    """Start recording the current tmux window."""
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
        # Create request data
        request_data = RecordingCreate(
            session_id=session_name,
            window_id=window_id,
            active_pane=pane_id
        )

        # Use Connection client to get status code
        api = conn.client()
        response = api.post("/recordings/", json=request_data.model_dump())

        if response.status_code in [201, 202]:
            recording_data = response.json()
            recording_id = recording_data['id']

            if response.status_code == 201:
                click.echo(f"Started recording {recording_id}")
            else:  # 202
                click.echo(f"Recording already active {recording_id}")

            click.echo(f"Recording to: {recording_data['cast_path']}")
        else:
            click.echo(f"Failed to start recording: {response.text}", err=True)
            raise click.Abort()

    except Exception as e:
        click.echo(f"Error starting recording: {e}", err=True)
        raise click.Abort()


@rec.command("ls")
def ls():
    """List active recordings."""
    conn = Connection()
    if not conn.is_running:
        click.echo("Server not running", err=True)
        raise SystemExit(1)

    # Call API to list recordings
    try:
        api = conn.client()
        response = api.get("/recordings/")

        if response.status_code == 200:
            recordings = response.json()
            if recordings:
                click.echo("Active recordings:")
                for rec in recordings:
                    rec_id = rec['id']
                    session = rec['session_id']
                    window = rec['window_id']
                    active_pane = rec.get('active_pane', 'unknown')

                    click.echo(f"  ID: {rec_id}")
                    click.echo(f"      Session: {session}, Window: {window}, Pane: {active_pane}")

                    if rec.get('cast_path'):
                        click.echo(f"      Recording to: {rec['cast_path']}")
                    click.echo()  # Blank line between recordings
            else:
                click.echo("No active recordings")
        else:
            click.echo(f"Failed to list recordings: {response.text}", err=True)
            raise click.Abort()

    except Exception as e:
        click.echo(f"Error listing recordings: {e}", err=True)
        raise click.Abort()


@rec.command("stop")
@click.argument("recording_id", required=False)
def stop(recording_id):
    """Stop recording(s). Stop all recordings if no ID specified."""
    conn = Connection()
    if not conn.is_running:
        click.echo("Server not running", err=True)
        raise SystemExit(1)

    # Call API to stop recording(s)
    try:
        api = conn.client()

        if recording_id:
            # Stop specific recording
            response = api.delete(f"/recordings/{recording_id}", timeout=10.0)

            if response.status_code == 200:
                data = response.json()
                click.echo(f"Stopped recording '{recording_id}'")
                if 'cast_path' in data and data['cast_path']:
                    click.echo(f"Recording saved to: {data['cast_path']}")
            elif response.status_code == 404:
                click.echo(f"Recording '{recording_id}' not found", err=True)
                raise click.Abort()
            else:
                click.echo(f"Failed to stop recording: {response.text}", err=True)
                raise click.Abort()
        else:
            # Stop all recordings (default behavior)
            # First get list of active recordings
            list_response = api.get("/recordings/")

            if list_response.status_code != 200:
                click.echo(f"Failed to list recordings: {list_response.text}", err=True)
                raise click.Abort()

            recordings = list_response.json()

            if not recordings:
                click.echo("No active recordings to stop")
                return

            # Stop each recording
            stopped_count = 0
            for recording in recordings:
                rec_id = recording['id']
                response = api.delete(f"/recordings/{rec_id}", timeout=10.0)
                if response.status_code == 200:
                    stopped_count += 1
                    data = response.json()
                    click.echo(f"Stopped recording '{rec_id}'")
                    if 'cast_path' in data and data['cast_path']:
                        click.echo(f"Recording saved to: {data['cast_path']}")
                else:
                    click.echo(f"Failed to stop recording '{rec_id}': {response.text}", err=True)

            if stopped_count > 0:
                click.echo(f"Stopped {stopped_count} recording(s)")

    except Exception as e:
        click.echo(f"Error stopping recording: {e}", err=True)
        raise click.Abort()
