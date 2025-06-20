"""Global state management for tvmux server."""
import os
from pathlib import Path
from typing import Dict

from ..recorder import WindowRecorder

# Global state - key is "session:window" ID
recorders: Dict[str, WindowRecorder] = {}
server_dir = Path(f"/tmp/tvmux-{os.getenv('USER', 'nobody')}")

# Server configuration
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 21590  # "TV" in ASCII
