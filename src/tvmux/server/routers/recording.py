"""Recording management endpoints."""
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ...recorder import WindowRecorder
from ..state import recorders

router = APIRouter()


class StartRecordingRequest(BaseModel):
    """Request to start recording a window."""
    session_id: str
    window_id: str
    window_name: str
    active_pane: str
    output_dir: Optional[str] = None


class RecordingStatus(BaseModel):
    """Status of a recording."""
    session_id: str
    window_id: str
    recording: bool
    cast_path: Optional[str] = None
    active_pane: Optional[str] = None


@router.post("/start")
async def start_recording(request: StartRecordingRequest) -> RecordingStatus:
    """Start recording a window."""
    recorder_key = f"{request.session_id}:{request.window_id}"

    # Check if already recording
    if recorder_key in recorders:
        recorder = recorders[recorder_key]
        if recorder.state and recorder.state.recording:
            return RecordingStatus(
                session_id=request.session_id,
                window_id=request.window_id,
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
    recorder = WindowRecorder(
        session_id=request.session_id,
        window_id=request.window_id,
        output_dir=output_dir
    )

    # Start recording
    if await recorder.start_recording(request.window_name, request.active_pane):
        recorders[recorder_key] = recorder
        return RecordingStatus(
            session_id=request.session_id,
            window_id=request.window_id,
            recording=True,
            cast_path=str(recorder.state.cast_path) if recorder.state else None,
            active_pane=recorder.state.active_pane if recorder.state else None
        )
    else:
        raise HTTPException(status_code=500, detail="Failed to start recording")


@router.post("/stop")
async def stop_recording(session_id: str, window_id: str) -> RecordingStatus:
    """Stop recording a window."""
    recorder_key = f"{session_id}:{window_id}"

    if recorder_key not in recorders:
        raise HTTPException(status_code=404, detail="Recording not found")

    recorder = recorders[recorder_key]
    recorder.stop_recording()

    # Remove from active recorders
    del recorders[recorder_key]

    return RecordingStatus(
        session_id=session_id,
        window_id=window_id,
        recording=False
    )


@router.get("/status")
async def get_recording_status(session_id: str, window_id: str) -> RecordingStatus:
    """Get recording status for a window."""
    recorder_key = f"{session_id}:{window_id}"

    if recorder_key not in recorders:
        return RecordingStatus(
            session_id=session_id,
            window_id=window_id,
            recording=False
        )

    recorder = recorders[recorder_key]
    return RecordingStatus(
        session_id=session_id,
        window_id=window_id,
        recording=recorder.state.recording if recorder.state else False,
        cast_path=str(recorder.state.cast_path) if recorder.state else None,
        active_pane=recorder.state.active_pane if recorder.state else None
    )


@router.get("/list")
async def list_recordings() -> list[RecordingStatus]:
    """List all active recordings."""
    result = []
    for key, recorder in recorders.items():
        session_id, window_id = key.split(":", 1)
        result.append(RecordingStatus(
            session_id=session_id,
            window_id=window_id,
            recording=recorder.state.recording if recorder.state else False,
            cast_path=str(recorder.state.cast_path) if recorder.state else None,
            active_pane=recorder.state.active_pane if recorder.state else None
        ))
    return result
