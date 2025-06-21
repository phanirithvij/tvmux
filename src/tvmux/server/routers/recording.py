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
    """Get window ID from window name/index."""
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


class StartRecordingRequest(BaseModel):
    """Request to start recording a window."""
    session_id: str
    window_name: str
    active_pane: str
    output_dir: Optional[str] = None


class RecordingStatus(BaseModel):
    """Status of a recording."""
    session_id: str
    window_name: str
    recording: bool
    cast_path: Optional[str] = None
    active_pane: Optional[str] = None


@router.post("/start")
async def start(request: StartRecordingRequest) -> RecordingStatus:
    # Always use window_id as the stable key
    window_id = resolve_id(request.session_id, request.window_name)
    recorder_key = f"{request.session_id}:{window_id}"

    # Check if already recording
    if recorder_key in recorders:
        recorder = recorders[recorder_key]
        if recorder.state and recorder.state.recording:
            return RecordingStatus(
                session_id=request.session_id,
                window_name=request.window_name,
                recording=True,
                cast_path=str(recorder.state.cast_path),
                active_pane=recorder.state.active_pane
            )

    # Determine output directory
    if request.output_dir:
        output_dir = Path(request.output_dir).expanduser()
    else:
        # Default to ~/Videos/tmux
        output_dir = Path.home() / "Videos" / "tmux"

    # Create recorder
    recorder = Recorder(
        session_id=request.session_id,
        window_name=window_id,
        output_dir=output_dir
    )

    # Start recording
    if await recorder.start(request.active_pane):
        recorders[recorder_key] = recorder
        return RecordingStatus(
            session_id=request.session_id,
            window_name=request.window_name,
            recording=True,
            cast_path=str(recorder.state.cast_path) if recorder.state else None,
            active_pane=recorder.state.active_pane if recorder.state else None
        )
    else:
        raise HTTPException(status_code=500, detail="Failed to start recording")


@router.post("/stop")
async def stop(session_id: str, window_name: str) -> RecordingStatus:
    # Always use window_id as the stable key
    window_id = resolve_id(session_id, window_name)
    recorder_key = f"{session_id}:{window_id}"

    if recorder_key not in recorders:
        raise HTTPException(status_code=404, detail="Recording not found")

    recorder = recorders[recorder_key]
    recorder.stop()

    # Remove from active recorders
    del recorders[recorder_key]

    # Auto-shutdown server if no more recordings
    if not recorders:
        logger.info("No more recordings active, scheduling server shutdown...")
        # Schedule shutdown after a brief delay to allow response to be sent
        asyncio.create_task(_shutdown_server_delayed())

    return RecordingStatus(
        session_id=session_id,
        window_name=window_name,
        recording=False
    )


async def _shutdown_server_delayed():
    """Shutdown server after a short delay."""
    # Wait a moment to ensure the HTTP response is sent
    await asyncio.sleep(1)

    # Send SIGTERM to ourselves to trigger graceful shutdown
    os.kill(os.getpid(), signal.SIGTERM)


@router.get("/status")
async def status(session_id: str, window_name: str) -> RecordingStatus:
    recorder_key = f"{session_id}:{window_name}"

    if recorder_key not in recorders:
        return RecordingStatus(
            session_id=session_id,
            window_name=window_name,
            recording=False
        )

    recorder = recorders[recorder_key]
    return RecordingStatus(
        session_id=session_id,
        window_name=window_name,
        recording=recorder.state.recording if recorder.state else False,
        cast_path=str(recorder.state.cast_path) if recorder.state else None,
        active_pane=recorder.state.active_pane if recorder.state else None
    )


@router.get("/list")
async def list() -> list[RecordingStatus]:
    result = []
    for key, recorder in recorders.items():
        session_id, window_name = key.split(":", 1)
        result.append(RecordingStatus(
            session_id=session_id,
            window_name=window_name,
            recording=recorder.state.recording if recorder.state else False,
            cast_path=str(recorder.state.cast_path) if recorder.state else None,
            active_pane=recorder.state.active_pane if recorder.state else None
        ))
    return result
