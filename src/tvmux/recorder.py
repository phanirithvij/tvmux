"""Window recorder for tmux."""
import asyncio
import logging
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from .utils import get_session_dir, safe_filename, file_has_readers
from .repair import repair_cast_file
from . import background

logger = logging.getLogger(__name__)


@dataclass
class RecordingState:
    """State of a window recording."""
    window_id: str
    session_name: str
    active_pane: Optional[str]
    asciinema_pid: Optional[int]
    fifo_path: Path
    cast_path: Path
    recording: bool = False


class Recorder:
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
            base_dir=f"/tmp/tvmux-{os.getenv('USER', 'nobody')}/sessions"
        )
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Initialize state
        self.state: Optional[RecordingState] = None
        self._running = False

    async def start(self, active_pane: str) -> bool:
        """Start recording this window."""
        if self.state and self.state.recording:
            logger.warning(f"Window {self.window_id} already recording")
            return False

        # Create FIFO
        safe_window_id = safe_filename(self.window_id)
        fifo_path = self.session_dir / f"window_{safe_window_id}.fifo"
        if fifo_path.exists():
            fifo_path.unlink()
        os.mkfifo(fifo_path)

        # Create output directory with date
        date_dir = self.output_dir / datetime.now().strftime("%Y-%m")
        date_dir.mkdir(parents=True, exist_ok=True)

        # Generate cast filename using display name
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")

        # Get display name for filename
        try:
            result = subprocess.run([
                "tmux", "display-message", "-t", f"{self.session_id}:{self.window_id}",
                "-p", "#{window_name}"
            ], capture_output=True, text=True)

            if result.returncode == 0 and result.stdout.strip():
                display_name = result.stdout.strip()
            else:
                display_name = self.window_id
        except (subprocess.CalledProcessError, ValueError, OSError):
            display_name = self.window_id

        safe_window_name = safe_filename(display_name)
        cast_filename = f"{timestamp}_{safe_filename(self.hostname)}_{safe_filename(self.session_id)}_{safe_window_name}.cast"
        cast_path = date_dir / cast_filename

        # Initialize state
        self.state = RecordingState(
            window_id=self.window_id,
            session_name=self.session_id,
            active_pane=active_pane,
            asciinema_pid=None,
            fifo_path=fifo_path,
            cast_path=cast_path,
            recording=False
        )

        # Start asciinema process
        if await self._start_asciinema():
            # Wait for asciinema to be ready before starting pipe-pane
            if await self._wait_for_reader():
                self.state.recording = True
                self._dump_pane(active_pane)
                self._start_streaming(active_pane)
                logger.info(f"Started recording window {self.window_id} to {cast_path}")
                return True
            else:
                logger.error("Asciinema reader not ready, stopping")
                self.stop()
                return False
        else:
            logger.error(f"Failed to start recording for window {self.window_id}")
            return False

    def switch_pane(self, new_pane_id: str):
        """Switch recording to a different pane in the window."""
        logger.debug(f"switch_pane called: new_pane_id={new_pane_id}, window={self.window_id}")

        if not self.state or not self.state.recording:
            logger.warning(f"Window {self.window_name} not recording, state={self.state}, recording={self.state.recording if self.state else None}")
            return

        if self.state.active_pane == new_pane_id:
            logger.debug(f"Already recording pane {new_pane_id}, no switch needed")
            return  # Already recording this pane

        logger.info(f"Switching from pane {self.state.active_pane} to {new_pane_id} in window {self.window_name}")

        # Stop streaming from old pane
        if self.state.active_pane:
            logger.debug(f"Stopping streaming from old pane {self.state.active_pane}")
            self._stop_streaming(self.state.active_pane)

        # Dump new pane state and start streaming
        logger.debug(f"Dumping pane {new_pane_id} and starting streaming")
        self._dump_pane(new_pane_id)
        self._start_streaming(new_pane_id)

        self.state.active_pane = new_pane_id
        logger.info(f"Successfully switched to pane {new_pane_id} in window {self.window_name}")

    def stop(self) -> bool:
        """Stop recording this window."""
        if not self.state or not self.state.recording:
            return False

        # Stop streaming from active pane
        if self.state.active_pane:
            self._stop_streaming(self.state.active_pane)

        # Send terminal reset sequence to ensure clean ending
        if self.state.fifo_path.exists():
            try:
                with open(self.state.fifo_path, "w") as f:
                    # Reset terminal to sane state
                    # - Clear any partial escape sequences
                    # - Reset colors and attributes
                    # - Show cursor
                    # - Reset character set
                    # - Clear scrolling region
                    f.write("\033[0m")     # Reset all attributes
                    f.write("\033[?25h")   # Show cursor
                    f.write("\033[2J")     # Clear screen
                    f.write("\033[H")      # Home cursor
                    f.write("\017")        # Reset character set (SI)
                    f.write("\033[r")      # Reset scrolling region
                    f.write("\n")          # Final newline
            except Exception as e:
                logger.warning(f"Failed to write terminal reset: {e}")

        # Small delay to ensure reset sequences are processed
        time.sleep(0.1)

        # Kill asciinema process (background manager handles the tree)
        if self.state.asciinema_pid:
            logger.debug(f"Terminating background process {self.state.asciinema_pid}")
            background.terminate(self.state.asciinema_pid)

        # Now it's safe to clean up FIFO
        if self.state.fifo_path.exists():
            self.state.fifo_path.unlink()

        # Repair cast file if needed (fixes JSON corruption from abrupt termination)
        if self.state.cast_path.exists():
            logger.debug(f"Repairing cast file: {self.state.cast_path}")
            repair_success = repair_cast_file(self.state.cast_path, backup=True)
            if repair_success:
                logger.debug("Cast file repair completed successfully")
            else:
                logger.warning("Cast file repair failed")

        self.state.recording = False
        logger.info(f"Stopped recording window {self.window_id}")
        return True

    async def _start_asciinema(self) -> bool:
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

        logger.debug(f"Starting asciinema with command: {cmd}")

        # Start process using background manager for automatic cleanup
        proc = background.spawn(cmd)
        self.state.asciinema_pid = proc.pid

        logger.debug(f"Started asciinema process with PID: {proc.pid}")

        # Wait for process to be ready and check if it's alive
        await asyncio.sleep(2)

        try:
            os.kill(proc.pid, 0)
            logger.debug(f"Asciinema process {proc.pid} is still running")
        except ProcessLookupError:
            logger.error(f"Asciinema process {proc.pid} died immediately")
            return False

        return True

    def _dump_pane(self, pane_id: str):
        """Dump current pane contents to FIFO."""
        if not self.state:
            return

        try:
            # Get cursor position and visibility
            cursor_info = subprocess.run(
                ["tmux", "display-message", "-p", "-t", pane_id,
                 "#{cursor_x} #{cursor_y} #{cursor_flag}"],
                capture_output=True,
                text=True
            ).stdout.strip()

            cursor_x, cursor_y, cursor_flag = cursor_info.split()
            cursor_x = int(cursor_x)
            cursor_y = int(cursor_y)
            cursor_visible = cursor_flag == "1"

            # Capture pane content with escape sequences
            content = subprocess.run(
                ["tmux", "capture-pane", "-e", "-p", "-t", pane_id],
                capture_output=True,
                text=True
            ).stdout

            # Write to FIFO
            with open(self.state.fifo_path, "w") as f:
                # Clear screen first
                f.write("\033[2J")      # Clear entire screen
                f.write("\033[H")       # Move cursor to home position (1,1)
                f.write("\033[0m")      # Reset all attributes

                # Write the pane content with Clear to End of Line on each line to preserve background colors
                # This replicates the Bash version: sed 's/$/\x1b[K/'
                lines = content.rstrip('\n').split('\n')
                processed_content = '\n'.join(line + '\033[K' for line in lines)
                f.write(processed_content)

                # Restore cursor position (tmux uses 0-based, ANSI uses 1-based)
                f.write(f"\033[{cursor_y + 1};{cursor_x + 1}H")

                # Restore cursor visibility
                if cursor_visible:
                    f.write("\033[?25h")  # Show cursor
                else:
                    f.write("\033[?25l")  # Hide cursor

        except Exception as e:
            logger.error(f"Failed to dump pane {pane_id}: {e}")

    def _has_reader(self) -> bool:
        """Check if someone is reading from the FIFO to prevent deadlocks."""
        if not self.state or not self.state.fifo_path.exists():
            return False

        return file_has_readers(str(self.state.fifo_path))

    async def _wait_for_reader(self, max_retries: int = 30, retry_delay: float = 0.1) -> bool:
        """Wait for asciinema to be ready before starting pipe-pane."""
        for attempt in range(max_retries):
            has_reader = self._has_reader()
            logger.debug(f"Attempt {attempt + 1}: FIFO reader check = {has_reader}")
            if has_reader:
                logger.debug(f"FIFO reader ready after {attempt + 1} attempts")
                return True
            await asyncio.sleep(retry_delay)

        logger.warning(f"FIFO reader not ready after {max_retries} attempts")
        return False

    def _start_streaming(self, pane_id: str):
        """Start streaming pane output to FIFO."""
        if not self.state:
            return

        # Ensure FIFO reader is active to prevent deadlocks
        if not self._has_reader():
            logger.warning(f"No FIFO reader detected, not starting pipe-pane for {pane_id}")
            return

        cmd = ["tmux", "pipe-pane", "-t", pane_id, f"cat >> {self.state.fifo_path}"]
        subprocess.run(cmd)

    def _stop_streaming(self, pane_id: str):
        """Stop streaming from pane."""
        cmd = ["tmux", "pipe-pane", "-t", pane_id]
        subprocess.run(cmd)
