"""Callback endpoints for tmux hooks."""
import logging
import subprocess
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from ..state import recorders, SERVER_HOST
from ..window_monitor import cleanup_closed_windows
from ... import proc
from ...config import get_config

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory storage for callback events (could be replaced with DB)
callback_history: List[Dict] = []


class CallbackEvent(BaseModel):
    """Event data from tmux hooks."""
    hook_name: str
    pane_id: Optional[str] = None
    session_name: Optional[str] = None
    window_id: Optional[str] = None
    window_index: Optional[str] = None  # Changed to string to handle empty values
    pane_index: Optional[str] = None    # Changed to string to handle empty values
    pane_pid: Optional[int] = None
    # Any other tmux variables can be passed
    extra: Dict[str, Any] = {}


class CallbackEventResponse(BaseModel):
    """Response for callback events."""
    id: str
    timestamp: datetime
    event: CallbackEvent
    status: str
    action: str


class HookConfig(BaseModel):
    """Configuration for a tmux hook."""
    name: str
    enabled: bool = True
    description: Optional[str] = None


@router.get("/")
async def list_callbacks() -> List[CallbackEventResponse]:
    """List recent callback events."""
    return callback_history[-50:]  # Return last 50 events


@router.post("/")
async def create_callback(event: CallbackEvent) -> CallbackEventResponse:
    """Create a new callback event (called by tmux hooks)."""
    event_id = str(uuid.uuid4())
    timestamp = datetime.now()

    # Process the callback event
    status = "ok"
    action = await _process_callback_event(event)

    # Store in history
    response = CallbackEventResponse(
        id=event_id,
        timestamp=timestamp,
        event=event,
        status=status,
        action=action
    )
    callback_history.append(response)

    # Keep only last 100 events
    if len(callback_history) > 100:
        callback_history.pop(0)

    return response


@router.get("/{event_id}")
async def get_callback(event_id: str) -> CallbackEventResponse:
    """Get a specific callback event."""
    for event in callback_history:
        if event.id == event_id:
            return event
    raise HTTPException(status_code=404, detail="Callback event not found")


@router.delete("/{event_id}")
async def delete_callback(event_id: str) -> Dict[str, str]:
    """Remove a callback event from history."""
    for i, event in enumerate(callback_history):
        if event.id == event_id:
            callback_history.pop(i)
            return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Callback event not found")


async def _process_callback_event(event: CallbackEvent) -> str:
    """Process a callback event and return the action taken."""
    hook_name = event.hook_name
    logger.debug(f"Processing callback: {hook_name}, session={event.session_name}, window={event.window_id}, pane={event.pane_id}")

    # Log if we get empty critical values
    if not event.session_name:
        logger.warning(f"Hook {hook_name} fired with empty session_name")
    if not event.window_id:
        logger.warning(f"Hook {hook_name} fired with empty window_id")
    if not event.pane_id and hook_name in ['after-select-pane', 'after-split-window', 'after-kill-pane']:
        logger.warning(f"Hook {hook_name} fired with empty pane_id")
    if not event.window_index:
        logger.warning(f"Hook {hook_name} fired with empty window_index")
    if not event.pane_index and hook_name in ['after-select-pane', 'after-split-window', 'after-kill-pane']:
        logger.warning(f"Hook {hook_name} fired with empty pane_index")

    if hook_name == "after-new-session":
        return "session_created"
    elif hook_name == "after-new-window":
        return "window_created"
    elif hook_name == "after-split-window":
        return "pane_created"
    elif hook_name == "after-kill-pane":
        return "pane_closed"
    elif hook_name == "window-unlinked":
        # Window was unlinked - but we can't trust the window_id here
        # The cleanup will happen on the next pane switch via cleanup_closed_windows()
        return "window_unlinked"
    elif hook_name == "session-closed":
        # Session died - stop all recordings for this session
        if event.session_name:
            session_recorders = [key for key in recorders.keys() if key.startswith(f"{event.session_name}:")]
            for recorder_key in session_recorders:
                logger.info(f"Session {event.session_name} closed, stopping recording {recorder_key}")
                recorder = recorders[recorder_key]
                recorder.stop()
                del recorders[recorder_key]
        return "session_destroyed"
    elif hook_name == "after-select-pane":
        # Active pane changed within a window
        logger.debug(f"Pane select event: session={event.session_name}, window={event.window_id}, pane={event.pane_id}")

        # Clean up any recordings for windows that no longer exist
        cleanup_closed_windows()

        if event.session_name and event.window_id:
            # Use session_name from callback as session_id for recorder key
            recorder_key = f"{event.session_name}:{event.window_id}"
            logger.debug(f"Looking for recorder with key: {recorder_key}")
            logger.debug(f"Available recorders: {list(recorders.keys())}")

            if recorder_key in recorders:
                # Switch recording to new active pane
                recorder = recorders[recorder_key]
                if event.pane_id:
                    logger.info(f"Triggering pane switch to {event.pane_id} for recorder {recorder_key}")
                    recorder.switch_pane(event.pane_id)
                else:
                    logger.warning("No pane_id in select-pane event")
            else:
                logger.debug(f"No recorder found for {recorder_key}")
        else:
            logger.warning("Missing session_name or window_id in select-pane event")
        return "pane_switched"
    elif hook_name == "after-resize-pane":
        return "pane_resized"
    elif hook_name == "after-rename-window":
        return "window_renamed"
    elif hook_name == "after-rename-session":
        return "session_renamed"
    else:
        return f"unknown_hook_{hook_name}"


def setup_tmux_hooks():
    """Set up tmux hooks to call our callbacks."""
    logger.info("Setting up tmux hooks...")

    config = get_config()
    base_url = f"http://{SERVER_HOST}:{config.server.port}/callbacks/"
    logger.debug(f"Using base URL: {base_url}")

    # Define hooks we want to monitor
    hooks = [
        "after-new-session",
        "after-new-window",
        "after-split-window",
        "after-kill-pane",
        # Note: after-kill-window doesn't exist in tmux
        "after-resize-pane",
        "after-rename-window",
        "after-rename-session",
        "after-select-pane",     # When active pane changes
        "window-unlinked",       # When window is unlinked from session
        "session-closed",        # When session ends
    ]

    for hook in hooks:
        # Create a Pydantic model instance for the JSON payload
        event = CallbackEvent(
            hook_name=hook,
            session_name="#{session_name}",
            window_id="#{window_id}",
            pane_id="#{pane_id}",
            window_index="#{window_index}",
            pane_index="#{pane_index}"
        )
        json_data = event.model_dump_json().replace('"', '\\"')

        hook_cmd = (
            f'curl -s -X POST {base_url} '
            f'-H "Content-Type: application/json" '
            f'-d "{json_data}" >/dev/null 2>&1'
        )

        logger.debug(f"Setting hook {hook} with command: {hook_cmd}")

        # Set the hook
        proc.run(["tmux", "set-hook", "-g", hook, f"run-shell '{hook_cmd}'"])


def remove_tmux_hooks():
    """Remove our tmux hooks."""
    hooks = [
        "after-new-session",
        "after-new-window",
        "after-split-window",
        "after-kill-pane",
        # Note: after-kill-window doesn't exist in tmux
        "after-resize-pane",
        "after-rename-window",
        "after-rename-session",
        "after-select-pane",
        "window-unlinked",
        "session-closed",
    ]

    for hook in hooks:
        subprocess.run(["tmux", "set-hook", "-gu", hook])
