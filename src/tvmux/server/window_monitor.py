"""Monitor tmux windows to detect when they're closed."""
import logging
import subprocess
from typing import Set

from .state import recorders

logger = logging.getLogger(__name__)


def get_current_windows() -> Set[str]:
    """Get the set of current window IDs as session:window_id keys."""
    try:
        result = subprocess.run(
            ["tmux", "list-windows", "-a", "-F", "#{session_name}:#{window_id}"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            windows = set()
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    windows.add(line.strip())
            return windows
    except Exception as e:
        logger.error(f"Failed to get windows: {e}")

    return set()


def cleanup_closed_windows():
    """Check for closed windows and clean up their recordings."""
    current_windows = get_current_windows()

    # Check which recordings reference windows that no longer exist
    closed_recordings = []
    for recorder_key in recorders:
        if recorder_key not in current_windows:
            closed_recordings.append(recorder_key)

    # Clean up recordings for closed windows
    for recorder_key in closed_recordings:
        logger.info(f"Window {recorder_key} was closed, stopping recording")
        recorder = recorders[recorder_key]
        recorder.stop()
        del recorders[recorder_key]

    if closed_recordings:
        logger.info(f"Cleaned up {len(closed_recordings)} recordings for closed windows")
