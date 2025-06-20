"""Window recorder for tmux."""
import asyncio
import logging
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

from .utils import get_session_dir

logger = logging.getLogger(__name__)


@dataclass
class RecordingState:
    """State of a window recording."""
    window_id: str
    session_name: str
    window_name: str
    active_pane: Optional[str]
    asciinema_pid: Optional[int]
    fifo_path: Path
    cast_path: Path
    recording: bool = False


class WindowRecorder:
    """Records a single tmux window by following the active pane."""

    def __init__(self, session_id: str, window_id: str, output_dir: Path):
        """Initialize window recorder.

        Args:
            session_id: tmux session ID (e.g., "main")
            window_id: tmux window ID (e.g., "@1")
            output_dir: Base directory for recordings (e.g., ~/Videos/tmux)
        """
        self.session_id = session_id
        self.window_id = window_id
        self.output_dir = output_dir

        # Get session info
        self.hostname = os.uname().nodename
        self.tmux_var = os.environ.get("TMUX", "")

        # Create session directory
        self.session_dir = get_session_dir(
            self.hostname,
            session_id,
            self.tmux_var,
            base_dir="/run/tvmux"
        )
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Initialize state
        self.state: Optional[RecordingState] = None
        self._running = False

    def start_recording(self, window_name: str, active_pane: str) -> bool:
        """Start recording this window.

        Args:
            window_name: Human-readable window name
            active_pane: Currently active pane ID

        Returns:
            True if recording started successfully
        """
        if self.state and self.state.recording:
            logger.warning(f"Window {self.window_id} already recording")
            return False

        # Create FIFO
        fifo_path = self.session_dir / f"window_{self.window_id.strip('@')}.fifo"
        if fifo_path.exists():
            fifo_path.unlink()
        os.mkfifo(fifo_path)

        # Create output directory with date
        date_dir = self.output_dir / datetime.now().strftime("%Y-%m")
        date_dir.mkdir(parents=True, exist_ok=True)

        # Generate cast filename
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        safe_window_name = window_name.replace("/", "_").replace(" ", "_")
        cast_filename = f"{timestamp}_{self.hostname}_{self.session_id}_{safe_window_name}.cast"
        cast_path = date_dir / cast_filename

        # Initialize state
        self.state = RecordingState(
            window_id=self.window_id,
            session_name=self.session_id,
            window_name=window_name,
            active_pane=active_pane,
            asciinema_pid=None,
            fifo_path=fifo_path,
            cast_path=cast_path,
            recording=False
        )

        # Start asciinema process
        if self._start_asciinema():
            self.state.recording = True
            self._dump_pane(active_pane)
            self._start_streaming(active_pane)
            logger.info(f"Started recording window {self.window_id} to {cast_path}")
            return True
        else:
            logger.error(f"Failed to start recording for window {self.window_id}")
            return False

    def switch_active_pane(self, new_pane_id: str):
        """Switch recording to a different pane in the window."""
        if not self.state or not self.state.recording:
            logger.warning(f"Window {self.window_id} not recording")
            return

        if self.state.active_pane == new_pane_id:
            return  # Already recording this pane

        # Stop streaming from old pane
        if self.state.active_pane:
            self._stop_streaming(self.state.active_pane)

        # Dump new pane state and start streaming
        self._dump_pane(new_pane_id)
        self._start_streaming(new_pane_id)

        self.state.active_pane = new_pane_id
        logger.info(f"Switched to pane {new_pane_id} in window {self.window_id}")

    def stop_recording(self) -> bool:
        """Stop recording this window."""
        if not self.state or not self.state.recording:
            return False

        # Stop streaming from active pane
        if self.state.active_pane:
            self._stop_streaming(self.state.active_pane)

        # Kill asciinema process
        if self.state.asciinema_pid:
            try:
                os.kill(self.state.asciinema_pid, 15)  # SIGTERM
            except ProcessLookupError:
                pass

        # Clean up FIFO
        if self.state.fifo_path.exists():
            self.state.fifo_path.unlink()

        self.state.recording = False
        logger.info(f"Stopped recording window {self.window_id}")
        return True

    def _start_asciinema(self) -> bool:
        """Start the asciinema process."""
        if not self.state:
            return False

        # Get terminal dimensions from active pane
        dims = subprocess.run(
            ["tmux", "display-message", "-p", "-t", self.state.active_pane,
             "#{pane_width} #{pane_height}"],
            capture_output=True,
            text=True
        )
        if dims.returncode == 0:
            width, height = dims.stdout.strip().split()
        else:
            width, height = "80", "24"

        # Build asciinema command
        cmd = [
            "script", "-qfc",
            f"stty rows {height} cols {width} 2>/dev/null; "
            f"asciinema rec \"{self.state.cast_path}\" "
            f"-c \"stdbuf -o0 tail -F {self.state.fifo_path} 2>&1\"",
            "/dev/null"
        ]

        # Start process
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.state.asciinema_pid = proc.pid

        # Wait for process to be ready
        # TODO: Better readiness check
        asyncio.create_task(asyncio.sleep(1))

        return True

    def _dump_pane(self, pane_id: str):
        """Dump current pane contents to FIFO."""
        if not self.state:
            return

        # Clear screen and reset terminal
        reset_seq = "\033[2J\033[H\033[0m"

        # Capture pane content with escape sequences
        content = subprocess.run(
            ["tmux", "capture-pane", "-e", "-p", "-t", pane_id],
            capture_output=True,
            text=True
        ).stdout

        # Get cursor position
        cursor_info = subprocess.run(
            ["tmux", "display-message", "-p", "-t", pane_id,
             "#{cursor_x} #{cursor_y} #{cursor_flag}"],
            capture_output=True,
            text=True
        ).stdout.strip()

        # Write to FIFO
        with open(self.state.fifo_path, "w") as f:
            f.write(reset_seq)
            f.write(content)
            # TODO: Restore cursor position

    def _start_streaming(self, pane_id: str):
        """Start streaming pane output to FIFO."""
        if not self.state:
            return

        cmd = ["tmux", "pipe-pane", "-t", pane_id, f"cat >> {self.state.fifo_path}"]
        subprocess.run(cmd)

    def _stop_streaming(self, pane_id: str):
        """Stop streaming from pane."""
        cmd = ["tmux", "pipe-pane", "-t", pane_id]
        subprocess.run(cmd)
