"""Global state management for tvmux server."""
import os
from pathlib import Path
from typing import Dict

from ..models import Recording
from ..utils import safe_filename

# Global state - key is "session:window" ID
recorders: Dict[str, Recording] = {}
server_dir = Path(f"/tmp/tvmux-{safe_filename(os.getenv('USER', 'nobody'))}")

# Server configuration
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 21590  # "TV" in ASCII
