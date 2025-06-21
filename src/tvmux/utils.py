"""Utility functions for tvmux."""
import hashlib
import logging
import re
from pathlib import Path

import psutil

logger = logging.getLogger(__name__)


def get_session_dir(hostname: str, session_name: str, tmux_var: str, base_dir: str = "/run/tvmux") -> Path:
    """
    Generate a filesystem-safe session directory name.

    Args:
        hostname: The hostname where tmux is running
        session_name: The tmux session name
        tmux_var: The $TMUX environment variable value
        base_dir: Base directory for tvmux runtime data

    Returns:
        Path to the session directory

    Example:
        >>> get_session_dir("laptop", "my project", "/tmp/tmux-1000/default,3028,0")
        PosixPath('/run/tvmux/session_laptop_my_project_a1b2c3')
    """
    # Clean session name for filesystem (keep alphanums, dash, underscore)
    clean_session = re.sub(r'[^a-zA-Z0-9_-]', '_', session_name)[:20]  # Truncate if long

    # Hash for collision protection
    hash_input = f"{hostname}_{session_name}_{tmux_var}"
    hash_suffix = hashlib.md5(hash_input.encode()).hexdigest()[:6]

    session_dir_name = f"session_{hostname}_{clean_session}_{hash_suffix}"
    return Path(base_dir) / session_dir_name


def safe_filename(name: str) -> str:
    """Make a string safe for use as a filename."""
    # Replace problematic characters with underscores
    safe = re.sub(r'[/\\\n\r\t\0<>:"|?*]', '_', name)
    # Remove any remaining control characters
    safe = ''.join(c for c in safe if ord(c) >= 32)
    # Truncate if too long
    return safe[:100]


def file_has_readers(file_path: str) -> bool:
    """Check if any process is set up to read from the file."""
    # For FIFOs, check if there's a tail process waiting to read it
    # rather than checking open file descriptors (which won't exist until both ends connect)
    fifo_name = Path(file_path).name
    logger.debug(f"Looking for tail process for: {fifo_name}")

    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and 'tail' in cmdline:
                # Check if this tail command references our FIFO
                cmdline_str = ' '.join(cmdline)
                if fifo_name in cmdline_str:
                    logger.debug(f"Found tail process {proc.info['pid']}: {cmdline_str}")
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return False
