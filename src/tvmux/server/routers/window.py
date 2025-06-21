"""Window router for tmux control."""
import subprocess
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...models.window import Window
from ...models.pane import Pane
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


class PaneCreate(BaseModel):
    """Create pane request."""
    target_pane: Optional[int] = None  # Pane to split (default: current)
    horizontal: bool = False  # False for vertical split, True for horizontal
    size: Optional[int] = None  # Percentage or lines/columns
    start_directory: Optional[str] = None
    command: Optional[str] = None


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


# Pane operations (nested under window)
@router.get("/{window_id}/pane", response_model=List[Pane])
async def list_panes(window_id: str):
    """List all panes in a window."""
    cmd = ["tmux", "list-panes", "-t", window_id, "-F",
           "#{pane_id}|#{pane_index}|#{pane_active}|#{pane_left},#{pane_top}|#{pane_width}x#{pane_height}|#{pane_current_command}|#{pane_pid}|#{pane_title}"]

    result = subprocess.run(cmd, capture_output=True, text=True)

    panes = []
    if result.returncode == 0:
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split("|")
                # Parse position from "left,top" format
                pos_parts = parts[3].split(',')
                position = Position(x=int(pos_parts[0]), y=int(pos_parts[1]))

                pane = Pane(
                    id=parts[0],
                    index=int(parts[1]),
                    active=parts[2] == "1",
                    position=position,
                    size=Position.from_string(parts[4]),
                    command=parts[5],
                    pid=int(parts[6]),
                    title=parts[7] if len(parts) > 7 else "",
                    window_id=window_id
                )
                panes.append(pane)

    return panes


@router.get("/{window_id}/pane/{pane_id}", response_model=Pane)
async def get_pane(window_id: str, pane_id: str):
    """Get a specific pane by ID."""
    panes = await list_panes(window_id)
    for pane in panes:
        if pane.id == pane_id:
            return pane
    raise HTTPException(status_code=404, detail="Pane not found")


@router.post("/{window_id}/pane", response_model=Pane)
async def create_pane(window_id: str, pane: PaneCreate):
    """Create a new pane by splitting the window."""
    if pane.target_pane is not None:
        target = f"{window_id}.{pane.target_pane}"
    else:
        target = window_id

    cmd = ["tmux", "split-window", "-d", "-t", target]

    if pane.horizontal:
        cmd.append("-h")
    else:
        cmd.append("-v")

    if pane.size:
        cmd.extend(["-l", str(pane.size)])

    if pane.start_directory:
        cmd.extend(["-c", pane.start_directory])

    # Print the new pane info
    cmd.extend(["-P", "-F", "#{pane_id}"])

    if pane.command:
        cmd.append(pane.command)

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=f"Failed to create pane: {result.stderr}")

    new_pane_id = result.stdout.strip()
    return await get_pane(window_id, new_pane_id)


@router.delete("/{window_id}/pane/{pane_id}")
async def delete_pane(window_id: str, pane_id: str):
    """Kill a pane."""
    result = subprocess.run(
        ["tmux", "kill-pane", "-t", pane_id],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=f"Failed to kill pane: {result.stderr}")

    return {"status": "deleted", "pane": pane_id}


@router.post("/{window_id}/pane/{pane_id}/select")
async def select_pane(window_id: str, pane_id: str):
    """Select/switch to a pane."""
    result = subprocess.run(
        ["tmux", "select-pane", "-t", pane_id],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=f"Failed to select pane: {result.stderr}")

    return {"status": "selected", "pane": pane_id}


@router.post("/{window_id}/pane/{pane_id}/resize")
async def resize_pane(window_id: str, pane_id: str, direction: str, amount: int = 5):
    """Resize a pane."""
    if direction not in ["U", "D", "L", "R"]:
        raise HTTPException(status_code=400, detail="Direction must be U, D, L, or R")

    result = subprocess.run(
        ["tmux", "resize-pane", "-t", pane_id, f"-{direction}", str(amount)],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=f"Failed to resize pane: {result.stderr}")

    return {"status": "resized", "pane": pane_id}


@router.post("/{window_id}/pane/{pane_id}/send-keys")
async def send_keys(window_id: str, pane_id: str, keys: str, enter: bool = True):
    """Send keys to a pane."""
    cmd = ["tmux", "send-keys", "-t", pane_id, keys]

    if enter:
        cmd.append("Enter")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=f"Failed to send keys: {result.stderr}")

    return {"status": "sent", "pane": pane_id, "keys": keys}


@router.get("/{window_id}/pane/{pane_id}/capture")
async def capture_pane(window_id: str, pane_id: str, start: Optional[int] = None, end: Optional[int] = None):
    """Capture pane contents."""
    cmd = ["tmux", "capture-pane", "-t", pane_id, "-p"]

    if start is not None:
        cmd.extend(["-S", str(start)])

    if end is not None:
        cmd.extend(["-E", str(end)])

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=f"Failed to capture pane: {result.stderr}")

    return {"pane": pane_id, "content": result.stdout}
