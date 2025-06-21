"""Window router for tmux control."""
import subprocess
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...models.window import Window
from ...models.position import Position

router = APIRouter()


class WindowCreate(BaseModel):
    """Create window request."""
    session: Optional[str] = None  # Session to attach to (optional)
    name: Optional[str] = None
    start_directory: Optional[str] = None
    command: Optional[str] = None


class WindowUpdate(BaseModel):
    """Update window request."""
    new_name: Optional[str] = None


# Window operations
@router.get("/", response_model=List[Window])
async def list():
    cmd = ["tmux", "list-windows", "-a", "-F",
           "#{window_id}|#{window_name}|#{window_active}|#{window_panes}|#{window_width}x#{window_height}|#{window_layout}|#{session_name}|#{window_index}"]

    result = subprocess.run(cmd, capture_output=True, text=True)

    windows = []
    if result.returncode == 0:
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split("|")
                windows.append(Window(
                    id=parts[0],
                    name=parts[1],
                    active=parts[2] == "1",
                    panes=int(parts[3]),
                    size=Position.from_string(parts[4]),
                    layout=parts[5]
                ))

    return windows


@router.get("/{window_id}", response_model=Window)
async def get(window_id: str):
    windows = await list()
    for window in windows:
        if window.id == window_id:
            return window
    raise HTTPException(status_code=404, detail="Window not found")


@router.post("/", response_model=Window)
async def create(window: WindowCreate):
    if window.session:
        cmd = ["tmux", "new-window", "-d", "-t", window.session, "-P", "-F", "#{window_id}"]
    else:
        # Create detached window
        cmd = ["tmux", "new-window", "-d", "-P", "-F", "#{window_id}"]

    if window.name:
        cmd.extend(["-n", window.name])

    if window.start_directory:
        cmd.extend(["-c", window.start_directory])

    if window.command:
        cmd.append(window.command)

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=f"Failed to create window: {result.stderr}")

    new_window_id = result.stdout.strip()
    return await get(new_window_id)


@router.patch("/{window_id}")
async def update_window(window_id: str, update: WindowUpdate):
    """Update a window."""
    if update.new_name:
        result = subprocess.run(
            ["tmux", "rename-window", "-t", window_id, update.new_name],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise HTTPException(status_code=400, detail=f"Failed to rename window: {result.stderr}")

    return await get(window_id)


@router.delete("/{window_id}")
async def delete_window(window_id: str):
    """Kill a tmux window."""
    result = subprocess.run(
        ["tmux", "kill-window", "-t", window_id],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=f"Failed to kill window: {result.stderr}")

    return {"status": "deleted", "window": window_id}


@router.post("/{window_id}/select")
async def select_window(window_id: str):
    """Select/switch to a window."""
    result = subprocess.run(
        ["tmux", "select-window", "-t", window_id],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=f"Failed to select window: {result.stderr}")

    return {"status": "selected", "window": window_id}


@router.post("/{window_id}/unlink")
async def unlink_window(window_id: str):
    """Unlink window from its session."""
    result = subprocess.run(
        ["tmux", "unlink-window", "-t", window_id],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=f"Failed to unlink window: {result.stderr}")

    return {"status": "unlinked", "window": window_id}


@router.post("/{window_id}/link")
async def link_window(window_id: str, target_session: str, target_index: Optional[int] = None):
    """Link window to a session."""
    if target_index is not None:
        target = f"{target_session}:{target_index}"
    else:
        target = target_session

    result = subprocess.run(
        ["tmux", "link-window", "-s", window_id, "-t", target],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=f"Failed to link window: {result.stderr}")

    return {"status": "linked", "window": window_id, "session": target_session}


@router.get("/{window_id}/panes")
async def get_window_panes(window_id: str):
    """Get all panes in a window - redirects to panes endpoint."""
    return {"message": "Use GET /panes?window_id={window_id} instead", "window_id": window_id}
