"""Recording management endpoints."""
import asyncio
import logging
import os
import signal
import subprocess
from pathlib import Path
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from typing import Optional

from ...models import Recording
from ..state import recorders

logger = logging.getLogger(__name__)


def resolve_id(session_id: str, window_name: str) -> str:
    """Get window ID from window name/index/id.

    Args:
        session_id: The session ID
        window_name: Window name, index, or ID

    Returns:
        Window ID (e.g., "@1")
    """
    try:
        # Use display-message to get the window ID for the specific window
        result = subprocess.run([
            "tmux", "display-message", "-t", f"{session_id}:{window_name}",
            "-p", "#{window_id}"
        ], capture_output=True, text=True)

        if result.returncode == 0 and result.stdout.strip():
            window_id = result.stdout.strip()
            logger.debug(f"tmux returned window_id: {repr(window_id)}")
            return window_id

        # Fallback: assume it's already a window_id
        return window_name

    except Exception:
        return window_name


def display_name(session_id: str, window_id: str) -> str:
    """Get friendly display name for a window ID."""
    try:
        result = subprocess.run([
            "tmux", "display-message", "-t", f"{session_id}:{window_id}",
            "-p", "#{window_name}"
        ], capture_output=True, text=True)

        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()

        # Fallback to window_id itself
        return window_id

    except Exception:
        return window_id

router = APIRouter()


class RecordingCreate(BaseModel):
    """Request to start recording a window."""
    session_id: str
    window_id: str  # Window ID to record
    active_pane: str
    output_dir: Optional[str] = None


@router.post("/", response_model=Recording)
async def create_recording(request: RecordingCreate, response: Response) -> Recording:
    """Start a new recording."""
    logger.info(f"Recording request: session={request.session_id}, window={request.window_id}, pane={request.active_pane}")

    # Create unique ID from session and window
    recording_id = f"{request.session_id}:{request.window_id}"

    # Check if already recording
    if recording_id in recorders:
        recording = recorders[recording_id]
        if recording.active:
            logger.info(f"Recording already active for {recording_id}")
            response.status_code = 202  # Accepted - already exists
            return recording

    # Determine output directory
    if request.output_dir:
        output_dir = Path(request.output_dir).expanduser()
    else:
        # Default to ~/Videos/tmux
        output_dir = Path.home() / "Videos" / "tmux"

    logger.info(f"Creating recording for {recording_id}, output_dir={output_dir}")

    # Create recording
    recording = Recording(
        id=recording_id,
        session_id=request.session_id,
        window_id=request.window_id
    )

    # Start recording
    try:
        await recording.start(request.active_pane, output_dir)
        recorders[recording_id] = recording
        logger.info(f"Recording started successfully for {recording_id}")
        response.status_code = 201  # Created - new recording
        return recording
    except Exception as e:
        logger.error(f"Failed to start recording for {recording_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{recording_id}")
async def delete_recording(recording_id: str) -> dict:
    """Stop a recording."""
    if recording_id not in recorders:
        raise HTTPException(status_code=404, detail="Recording not found")

    recording = recorders[recording_id]
    cast_path = recording.cast_path  # Get path before stopping
    recording.stop()

    # Remove from active recorders
    del recorders[recording_id]

    # Auto-shutdown server if no more recordings
    if not recorders:
        logger.info("No more recordings active, scheduling server shutdown...")
        # Schedule shutdown after a brief delay to allow response to be sent
        asyncio.create_task(_shutdown_server_delayed())

    return {"status": "stopped", "recording_id": recording_id, "cast_path": cast_path}


async def _shutdown_server_delayed():
    """Shutdown server after a short delay."""
    # Wait a moment to ensure the HTTP response is sent
    await asyncio.sleep(1)

    # Send SIGTERM to ourselves to trigger graceful shutdown
    os.kill(os.getpid(), signal.SIGTERM)


@router.get("/{recording_id}", response_model=Recording)
async def get_recording(recording_id: str) -> Recording:
    """Get recording status."""
    if recording_id not in recorders:
        raise HTTPException(status_code=404, detail="Recording not found")

    return recorders[recording_id]


@router.get("/", response_model=list[Recording])
async def list_recordings() -> list[Recording]:
    """List all active recordings."""
    return list(recorders.values())
