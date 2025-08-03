"""Recording management commands."""
import os
import subprocess
from functools import partial

import click

from ..connection import Connection
from ..api_client import api_call, APIError
from ..server.routers.recording import Recording, RecordingCreate


@click.group()
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
        # Create API client function
        create_recording = partial(api_call, conn.base_url, "POST", "/recordings/",
                                   response_model=Recording)

        # Create request data
        request_data = RecordingCreate(
            session_id=session_name,
            window_id=window_id,
            active_pane=pane_id
        )

        # Make the call
        recording = create_recording(data=request_data)

        click.echo(f"Started recording window '{window_id}' in session '{session_name}'")
        click.echo(f"Recording to: {recording.cast_path}")

    except APIError as e:
        click.echo(f"Failed to start recording: {e.detail}", err=True)
        raise click.Abort()
    except Exception as e:
        import traceback
        click.echo(f"Error starting recording: {e}", err=True)
        click.echo(f"Stack trace:\n{traceback.format_exc()}", err=True)
        raise click.Abort()


@record.command("list")
def list_recordings():
    conn = Connection()
    if not conn.is_running:
        click.echo("Server not running", err=True)
        raise click.Abort()

    # Call API to list recordings
    try:
        api = conn.client()
        response = api.get("/recordings/")

        if response.status_code == 200:
            recordings = response.json()
            if recordings:
                click.echo("Active recordings:")
                for rec in recordings:
                    click.echo(f"  - Session: {rec['session_id']}, Window: {rec['window_id']}")
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
        # Create recording ID from session and window
        recording_id = f"{session_name}:{window_id}"
        response = api.delete(f"/recordings/{recording_id}", timeout=10.0)

        if response.status_code == 200:
            click.echo(f"Stopped recording window in session '{session_name}'")
        else:
            click.echo(f"Failed to stop recording: {response.text}", err=True)
            raise click.Abort()

    except Exception as e:
        click.echo(f"Error stopping recording: {e}", err=True)
        raise click.Abort()
