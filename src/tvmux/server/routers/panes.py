"""Pane router for tmux control."""
import subprocess
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ...models.pane import Pane
from ...models.position import Position

router = APIRouter()


class PaneCreate(BaseModel):
    """Create pane request."""
    window_id: str  # Window to split
    target_pane_id: Optional[str] = None  # Specific pane to split (default: active)
    horizontal: bool = False  # False for vertical split, True for horizontal
    size: Optional[int] = None  # Percentage or lines/columns
    start_directory: Optional[str] = None
    command: Optional[str] = None


class PaneResize(BaseModel):
    """Resize pane request."""
    direction: str  # U, D, L, or R
    amount: int = 5


class PaneSendKeys(BaseModel):
    """Send keys request."""
    keys: str
    enter: bool = True


@router.get("/", response_model=List[Pane])
async def list_panes(window_id: Optional[str] = Query(None, description="Filter by window ID")):
    """List all panes or panes in a specific window."""
    if window_id:
        cmd = ["tmux", "list-panes", "-t", window_id, "-F",
               "#{pane_id}|#{pane_index}|#{pane_active}|#{pane_left},#{pane_top}|#{pane_width}x#{pane_height}|#{pane_current_command}|#{pane_pid}|#{pane_title}|#{window_id}"]
    else:
        cmd = ["tmux", "list-panes", "-a", "-F",
               "#{pane_id}|#{pane_index}|#{pane_active}|#{pane_left},#{pane_top}|#{pane_width}x#{pane_height}|#{pane_current_command}|#{pane_pid}|#{pane_title}|#{window_id}"]

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
                    window_id=parts[8] if len(parts) > 8 else ""
                )
                panes.append(pane)

    return panes


@router.post("/", response_model=Pane)
async def create_pane(pane: PaneCreate):
    """Create a new pane by splitting a window."""
    if pane.target_pane_id:
        target = pane.target_pane_id
    else:
        target = pane.window_id

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
    return await get_pane(new_pane_id)


@router.get("/{pane_id}", response_model=Pane)
async def get_pane(pane_id: str):
    """Get a specific pane by ID."""
    panes = await list_panes()
    for pane in panes:
        if pane.id == pane_id:
            return pane
    raise HTTPException(status_code=404, detail="Pane not found")


@router.delete("/{pane_id}")
async def delete_pane(pane_id: str):
    """Kill a pane."""
    result = subprocess.run(
        ["tmux", "kill-pane", "-t", pane_id],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=f"Failed to kill pane: {result.stderr}")

    return {"status": "deleted", "pane": pane_id}


@router.post("/{pane_id}/select")
async def select_pane(pane_id: str):
    """Select/switch to a pane."""
    result = subprocess.run(
        ["tmux", "select-pane", "-t", pane_id],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=f"Failed to select pane: {result.stderr}")

    return {"status": "selected", "pane": pane_id}


@router.post("/{pane_id}/resize")
async def resize_pane(pane_id: str, resize: PaneResize):
    """Resize a pane."""
    if resize.direction not in ["U", "D", "L", "R"]:
        raise HTTPException(status_code=400, detail="Direction must be U, D, L, or R")

    result = subprocess.run(
        ["tmux", "resize-pane", "-t", pane_id, f"-{resize.direction}", str(resize.amount)],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=f"Failed to resize pane: {result.stderr}")

    return {"status": "resized", "pane": pane_id}


@router.post("/{pane_id}/send-keys")
async def send_keys(pane_id: str, send: PaneSendKeys):
    """Send keys to a pane."""
    cmd = ["tmux", "send-keys", "-t", pane_id, send.keys]

    if send.enter:
        cmd.append("Enter")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=f"Failed to send keys: {result.stderr}")

    return {"status": "sent", "pane": pane_id, "keys": send.keys}


@router.get("/{pane_id}/capture")
async def capture_pane(pane_id: str, start: Optional[int] = Query(None), end: Optional[int] = Query(None)):
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
