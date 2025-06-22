"""Recording management endpoints."""
import asyncio
import logging
import os
import signal
import subprocess
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ...recorder import Recorder
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


class Recording(BaseModel):
    """Recording resource."""
    id: str  # session:window_id
    session_id: str
    window_id: str
    recording: bool
    cast_path: Optional[str] = None
    active_pane: Optional[str] = None


@router.post("/", response_model=Recording)
async def create_recording(recording: RecordingCreate) -> Recording:
    """Start a new recording."""
    try:
        logger.info(f"Recording request: session={recording.session_id}, window={recording.window_id}, pane={recording.active_pane}")

        # Create unique ID from session and window
        recording_id = f"{recording.session_id}:{recording.window_id}"

        # Check if already recording
        if recording_id in recorders:
            recorder = recorders[recording_id]
            if recorder.state and recorder.state.recording:
                logger.info(f"Recording already active for {recording_id}")
                return Recording(
                    id=recording_id,
                    session_id=recording.session_id,
                    window_id=recording.window_id,
                    recording=True,
                    cast_path=str(recorder.state.cast_path),
                    active_pane=recorder.state.active_pane
                )

        # Determine output directory
        if recording.output_dir:
            output_dir = Path(recording.output_dir).expanduser()
        else:
            # Default to ~/Videos/tmux
            output_dir = Path.home() / "Videos" / "tmux"

        logger.info(f"Creating recorder for {recording_id}, output_dir={output_dir}")

        # Create recorder
        recorder = Recorder(
            session_id=recording.session_id,
            window_id=recording.window_id,
            output_dir=output_dir
        )

        # Start recording
        logger.info(f"Starting recording for {recording_id}")
        if await recorder.start(recording.active_pane):
            recorders[recording_id] = recorder
            logger.info(f"Recording started successfully for {recording_id}")
            return Recording(
                id=recording_id,
                session_id=recording.session_id,
                window_id=recording.window_id,
                recording=True,
                cast_path=str(recorder.state.cast_path) if recorder.state else None,
                active_pane=recorder.state.active_pane if recorder.state else None
            )
        else:
            logger.error(f"Failed to start recording for {recording_id}")
            raise HTTPException(status_code=500, detail="Failed to start recording")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Exception in create_recording: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.delete("/{recording_id}")
async def delete_recording(recording_id: str) -> dict:
    """Stop a recording."""
    if recording_id not in recorders:
        raise HTTPException(status_code=404, detail="Recording not found")

    recorder = recorders[recording_id]
    recorder.stop()

    # Remove from active recorders
    del recorders[recording_id]

    # Auto-shutdown server if no more recordings
    if not recorders:
        logger.info("No more recordings active, scheduling server shutdown...")
        # Schedule shutdown after a brief delay to allow response to be sent
        asyncio.create_task(_shutdown_server_delayed())

    return {"status": "stopped", "recording_id": recording_id}


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

    recorder = recorders[recording_id]
    session_id, window_id = recording_id.split(":", 1)

    return Recording(
        id=recording_id,
        session_id=session_id,
        window_id=window_id,
        recording=recorder.state.recording if recorder.state else False,
        cast_path=str(recorder.state.cast_path) if recorder.state else None,
        active_pane=recorder.state.active_pane if recorder.state else None
    )


@router.get("/", response_model=list[Recording])
async def list_recordings() -> list[Recording]:
    """List all active recordings."""
    result = []
    for recording_id, recorder in recorders.items():
        session_id, window_id = recording_id.split(":", 1)
        result.append(Recording(
            id=recording_id,
            session_id=session_id,
            window_id=window_id,
            recording=recorder.state.recording if recorder.state else False,
            cast_path=str(recorder.state.cast_path) if recorder.state else None,
            active_pane=recorder.state.active_pane if recorder.state else None
        ))
    return result
