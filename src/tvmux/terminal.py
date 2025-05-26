"""Terminal state tracker."""
import asyncio
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class Terminal:
    """Tracks state of a single tmux pane."""

    def __init__(self, pane_id: str, state_fifo: Path, stream_fifo: Path):
        """Initialize terminal."""
        self.pane_id = pane_id
        self.state_fifo = state_fifo
        self.stream_fifo = stream_fifo

        # Parse pane_id (session:window.pane)
        parts = pane_id.replace(":", ".").split(".")
        self.session = parts[0]
        self.window = int(parts[1]) if len(parts) > 1 else 0
        self.pane = int(parts[2]) if len(parts) > 2 else 0

        # Terminal state
        self.state = {
            "width": 80,
            "height": 24,
            "cursor_x": 0,
            "cursor_y": 0,
            "cursor_visible": True,
        }

        self._running = True

    async def process(self):
        """Main processing loop."""
        logger.info(f"Starting terminal {self.pane_id}")

        while self._running:
            try:
                # Process state updates first (atomic)
                await self._process_state_fifo()

                # Then process stream data
                await self._process_stream_fifo()

            except Exception as e:
                logger.error(f"Error in terminal {self.pane_id}: {e}")
                await asyncio.sleep(1)

    async def _process_state_fifo(self):
        """Read state updates from fifo."""
        try:
            # Non-blocking read with timeout
            reader = asyncio.create_task(self._read_fifo(self.state_fifo))
            data = await asyncio.wait_for(reader, timeout=0.1)

            if data:
                # Process escape sequences for state updates
                logger.debug(f"State update for {self.pane_id}: {data}")
                self._handle_escape(data)

        except asyncio.TimeoutError:
            pass

    async def _process_stream_fifo(self):
        """Read stream data from fifo."""
        try:
            reader = asyncio.create_task(self._read_fifo(self.stream_fifo))
            data = await asyncio.wait_for(reader, timeout=0.1)

            if data:
                # Process stream data
                logger.debug(f"Stream data for {self.pane_id}: {len(data)} bytes")
                # TODO: Parse ANSI sequences, update state

        except asyncio.TimeoutError:
            pass

    async def _read_fifo(self, path: Path) -> Optional[str]:
        """Read from a fifo asynchronously."""
        try:
            # Open in non-blocking mode
            async with asyncio.open_file(str(path), "r") as f:
                return await f.read()
        except Exception:
            return None

    def _handle_escape(self, seq: str):
        """Handle escape sequence to update state."""
        # TODO: Parse actual escape sequences
        # For now, just log
        logger.debug(f"State change: {seq}")

        # Example: terminal size change
        if "resize" in seq:
            # Parse width/height from sequence
            pass

    async def stop(self):
        """Stop processing."""
        logger.info(f"Stopping terminal {self.pane_id}")
        self._running = False

        # Clean up fifos
        self.state_fifo.unlink(missing_ok=True)
        self.stream_fifo.unlink(missing_ok=True)
