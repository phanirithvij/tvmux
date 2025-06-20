"""Callback endpoints for tmux hooks."""
import subprocess
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any

from ..state import recorders, SERVER_HOST, SERVER_PORT

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
        # New window created - ready for recording
        return {"status": "ok", "action": "window_created"}

    elif hook_name == "after-split-window":
        # New pane created - no action needed (we track windows, not panes)
        return {"status": "ok", "action": "pane_created"}

    elif hook_name == "pane-died":
        # Pane closed - check if window should stop recording
        # TODO: Check if this was the last pane in a recording window
        return {"status": "ok", "action": "pane_closed"}

    elif hook_name == "window-pane-changed":
        # Active pane changed within a window
        if event.session_name and event.window_id:
            recorder_key = f"{event.session_name}:{event.window_id}"
            if recorder_key in recorders:
                # Switch recording to new active pane
                recorder = recorders[recorder_key]
                if event.pane_id:
                    recorder.switch_active_pane(event.pane_id)
        return {"status": "ok", "action": "pane_switched"}

    elif hook_name == "pane-focus-in":
        # Pane gained focus
        if event.session_name and event.window_id:
            recorder_key = f"{event.session_name}:{event.window_id}"
            if recorder_key in recorders:
                # Switch recording to focused pane
                recorder = recorders[recorder_key]
                if event.pane_id:
                    recorder.switch_active_pane(event.pane_id)
        return {"status": "ok", "action": "pane_focused"}

    elif hook_name == "after-resize-pane":
        # Pane resized - may need to update recording dimensions
        return {"status": "ok", "action": "pane_resized"}

    elif hook_name == "window-renamed":
        # Window renamed - update recording filename/symlink
        # TODO: Update recorder with new window name
        return {"status": "ok", "action": "window_renamed"}

    elif hook_name == "session-renamed":
        # Session renamed
        # TODO: Update all recorders for this session
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
        "window-pane-changed",  # When active pane changes
        "pane-focus-in",        # When pane gets focus
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
        "window-pane-changed",
        "pane-focus-in",
    ]

    for hook in hooks:
        subprocess.run(["tmux", "set-hook", "-gu", hook])
