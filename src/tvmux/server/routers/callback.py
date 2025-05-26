"""Callback endpoints for tmux hooks."""
import subprocess
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any

from ..state import terminals, SERVER_HOST, SERVER_PORT

router = APIRouter()


class HookEvent(BaseModel):
    """Event data from tmux hooks."""
    pane_id: Optional[str] = None
    session_name: Optional[str] = None
    window_id: Optional[str] = None
    window_index: Optional[int] = None
    pane_index: Optional[int] = None
    pane_pid: Optional[int] = None
    # Any other tmux variables can be passed
    extra: Dict[str, Any] = {}


@router.post("/{hook_name}")
async def handle_callback(hook_name: str, event: HookEvent):
    """Handle callbacks from tmux hooks."""

    if hook_name == "after-new-session":
        # New session created
        return {"status": "ok", "action": "session_created"}

    elif hook_name == "after-new-window":
        # New window created
        return {"status": "ok", "action": "window_created"}

    elif hook_name == "after-split-window":
        # New pane created - start tracking
        if event.pane_id and event.pane_id not in terminals:
            terminals[event.pane_id] = {
                "pane_id": event.pane_id,
                "session": event.session_name,
                "window_id": event.window_id,
                "state": {
                    "cursor_x": 0,
                    "cursor_y": 0,
                    "width": 80,
                    "height": 24
                }
            }
        return {"status": "ok", "action": "pane_created"}

    elif hook_name == "pane-died":
        # Pane closed - stop tracking
        if event.pane_id and event.pane_id in terminals:
            del terminals[event.pane_id]
        return {"status": "ok", "action": "pane_closed"}

    elif hook_name == "after-resize-pane":
        # Pane resized
        if event.pane_id and event.pane_id in terminals:
            # TODO: Update size in tracking state
            pass
        return {"status": "ok", "action": "pane_resized"}

    elif hook_name == "window-renamed":
        # Window renamed
        return {"status": "ok", "action": "window_renamed"}

    elif hook_name == "session-renamed":
        # Session renamed
        return {"status": "ok", "action": "session_renamed"}

    else:
        return {"status": "ok", "action": "unknown", "hook": hook_name}


def setup_tmux_hooks():
    """Set up tmux hooks to call our callbacks."""
    base_url = f"http://{SERVER_HOST}:{SERVER_PORT}/callback"

    # Define hooks we want to monitor
    hooks = [
        "after-new-session",
        "after-new-window",
        "after-split-window",
        "pane-died",
        "after-resize-pane",
        "window-renamed",
        "session-renamed",
    ]

    for hook in hooks:
        # Build the curl command with common tmux variables
        curl_cmd = (
            f"curl -s -X POST {base_url}/{hook} "
            f"-H 'Content-Type: application/json' "
            f"-d '{{\"pane_id\":\"#{{pane_id}}\","
            f"\"session_name\":\"#{{session_name}}\","
            f"\"window_id\":\"#{{window_id}}\","
            f"\"window_index\":#{{window_index}},"
            f"\"pane_index\":#{{pane_index}}}}'"
        )

        # Set the hook
        subprocess.run(["tmux", "set-hook", "-g", hook, f"run-shell '{curl_cmd}'"])


def remove_tmux_hooks():
    """Remove our tmux hooks."""
    hooks = [
        "after-new-session",
        "after-new-window",
        "after-split-window",
        "pane-died",
        "after-resize-pane",
        "window-renamed",
        "session-renamed",
    ]

    for hook in hooks:
        subprocess.run(["tmux", "set-hook", "-gu", hook])
