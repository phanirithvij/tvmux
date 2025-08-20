"""Session router for tmux control."""
import subprocess
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...models.session import Session
from ...models.position import Position

router = APIRouter()


class SessionCreate(BaseModel):
    """Create session request."""
    name: str
    start_directory: str = "."
    window_name: str = "default"


class SessionUpdate(BaseModel):
    """Update session request."""
    new_name: Optional[str] = None


class WindowReference(BaseModel):
    """Reference to a window in a session."""
    window_id: str
    index: int
    name: str


class SessionWindows(BaseModel):
    """Session windows response."""
    session: str
    windows: List[WindowReference]


# Session operations
@router.get("", response_model=List[Session])
async def list():
    result = subprocess.run(
        ["tmux", "list-sessions", "-F",
         "#{session_name}|#{session_id}|#{session_created}|#{session_attached}|#{session_windows}|#{session_width}x#{session_height}"],
        capture_output=True,
        text=True
    )

    sessions = []
    if result.returncode == 0 and result.stdout.strip():
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split("|")
                if len(parts) >= 6:  # Ensure we have all expected fields
                    sessions.append(Session(
                        name=parts[0],
                        id=parts[1],
                        created=int(parts[2]),
                        attached=parts[3] == "1",
                        windows=int(parts[4]),
                        size=Position.from_string(parts[5])
                    ))

    return sessions


@router.get("/{session_id}", response_model=Session)
async def get(session_id: str):
    sessions = await list()
    for session in sessions:
        if session.id == session_id:
            return session
    raise HTTPException(status_code=404, detail="Session not found")


@router.post("", response_model=Session)
async def create(session: SessionCreate):
    cmd = ["tmux", "new-session", "-d", "-s", session.name, "-c", session.start_directory]
    if session.window_name:
        cmd.extend(["-n", session.window_name])

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=f"Failed to create session: {result.stderr}")

    # Get the session by name to find its ID, then return by ID
    sessions = await list()
    for s in sessions:
        if s.name == session.name:
            return await get(s.id)
    raise HTTPException(status_code=404, detail="Session not found after creation")


@router.patch("/{session_id}")
async def update(session_id: str, update: SessionUpdate):
    """Update a session (rename)."""
    # Get current session to find its name for tmux command
    session = await get(session_id)

    if update.new_name:
        result = subprocess.run(
            ["tmux", "rename-session", "-t", session.name, update.new_name],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise HTTPException(status_code=400, detail=f"Failed to rename session: {result.stderr}")

        # Return the updated session (ID stays the same, name changes)
        return await get(session_id)

    return session


@router.delete("/{session_id}")
async def delete(session_id: str):
    # Get session to find its name for tmux command
    session = await get(session_id)

    result = subprocess.run(
        ["tmux", "kill-session", "-t", session.name],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=f"Failed to kill session: {result.stderr}")

    return {"status": "deleted", "session": session.name, "id": session_id}


@router.post("/{session_id}/attach")
async def attach_session(session_id: str):
    """Attach to a session (returns attach command for client to execute)."""
    # Get session to find its name for tmux command
    session = await get(session_id)

    return {
        "command": f"tmux attach-session -t {session.name}",
        "note": "Execute this command in your terminal to attach"
    }


@router.post("/{session_id}/detach")
async def detach_session(session_id: str):
    """Detach all clients from a session."""
    # Get session to find its name for tmux command
    session = await get(session_id)

    result = subprocess.run(
        ["tmux", "detach-client", "-s", session.name],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=f"Failed to detach clients: {result.stderr}")

    return {"status": "detached", "session": session.name, "id": session_id}


@router.get("/{session_id}/windows", response_model=SessionWindows)
async def get_session_windows(session_id: str):
    """Get all window references for a session."""
    # Get session to find its name for tmux command
    session = await get(session_id)

    cmd = ["tmux", "list-windows", "-t", session.name, "-F", "#{window_id}|#{window_index}|#{window_name}"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    windows = []
    if result.returncode == 0:
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split("|")
                windows.append(WindowReference(
                    window_id=parts[0],
                    index=int(parts[1]),
                    name=parts[2]
                ))

    return SessionWindows(session=session.name, windows=windows)
