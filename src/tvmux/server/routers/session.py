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


class SessionWindows(BaseModel):
    """Session windows response."""
    session: str
    windows: List[WindowReference]


# Session operations
@router.get("/", response_model=List[Session])
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


@router.get("/{name}", response_model=Session)
async def get(name: str):
    sessions = await list()
    for session in sessions:
        if session.name == name:
            return session
    raise HTTPException(status_code=404, detail="Session not found")


@router.post("/", response_model=Session)
async def create(session: SessionCreate):
    cmd = ["tmux", "new-session", "-d", "-s", session.name, "-c", session.start_directory]
    if session.window_name:
        cmd.extend(["-n", session.window_name])

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=f"Failed to create session: {result.stderr}")

    return await get(session.name)


@router.patch("/{name}")
async def update(name: str, update: SessionUpdate):
    """Update a session (rename)."""
    if update.new_name:
        result = subprocess.run(
            ["tmux", "rename-session", "-t", name, update.new_name],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise HTTPException(status_code=400, detail=f"Failed to rename session: {result.stderr}")

        return await get(update.new_name)

    return await get(name)


@router.delete("/{name}")
async def delete(name: str):
    result = subprocess.run(
        ["tmux", "kill-session", "-t", name],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=f"Failed to kill session: {result.stderr}")

    return {"status": "deleted", "session": name}


@router.post("/{name}/attach")
async def attach_session(name: str):
    """Attach to a session (returns attach command for client to execute)."""
    # Check session exists
    sessions = await list()
    if not any(s.name == name for s in sessions):
        raise HTTPException(status_code=404, detail=f"Session '{name}' not found")

    return {
        "command": f"tmux attach-session -t {name}",
        "note": "Execute this command in your terminal to attach"
    }


@router.post("/{name}/detach")
async def detach_session(name: str):
    """Detach all clients from a session."""
    result = subprocess.run(
        ["tmux", "detach-client", "-s", name],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=f"Failed to detach clients: {result.stderr}")

    return {"status": "detached", "session": name}


@router.get("/{name}/windows", response_model=SessionWindows)
async def get_session_windows(name: str):
    """Get all window references for a session."""
    # Check session exists
    sessions = await list()
    if not any(s.name == name for s in sessions):
        raise HTTPException(status_code=404, detail=f"Session '{name}' not found")

    cmd = ["tmux", "list-windows", "-t", name, "-F", "#{window_id}|#{window_index}"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    windows = []
    if result.returncode == 0:
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split("|")
                windows.append(WindowReference(
                    window_id=parts[0],
                    index=int(parts[1])
                ))

    return SessionWindows(session=name, windows=windows)
