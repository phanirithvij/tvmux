"""Global state management for tvmux server."""
import os
from pathlib import Path
from typing import Dict

from ..terminal import Terminal

# Global state
terminals: Dict[str, Terminal] = {}
server_dir = Path(f"/tmp/tvmux-{os.getenv('USER', 'nobody')}")

# Server configuration
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 21590  # "TV" in ASCII
