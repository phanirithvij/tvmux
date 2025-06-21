"""Utility functions for tvmux."""
import hashlib
import logging
import os
import re
import signal
import time
from pathlib import Path
from typing import List, Set

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


def get_process_children(pid: int) -> List[int]:
    """
    Get all child process IDs for a given parent PID.

    Args:
        pid: Parent process ID

    Returns:
        List of child process IDs
    """
    children = []
    try:
        # Read /proc/*/stat files to find children
        for proc_dir in Path("/proc").iterdir():
            if not proc_dir.is_dir() or not proc_dir.name.isdigit():
                continue

            try:
                stat_file = proc_dir / "stat"
                if stat_file.exists():
                    with open(stat_file, 'r') as f:
                        fields = f.read().split()
                        if len(fields) >= 4:
                            ppid = int(fields[3])  # Parent PID is 4th field
                            if ppid == pid:
                                children.append(int(proc_dir.name))
            except (ValueError, IOError):
                continue

    except OSError:
        pass

    return children


def get_process_tree(pid: int) -> Set[int]:
    """
    Get all processes in a process tree (descendants).

    Args:
        pid: Root process ID

    Returns:
        Set of all process IDs in the tree including root
    """
    tree = {pid}
    to_process = [pid]

    while to_process:
        current_pid = to_process.pop()
        children = get_process_children(current_pid)
        for child in children:
            if child not in tree:
                tree.add(child)
                to_process.append(child)

    return tree


def kill_process_tree(pid: int, signal_num: int = signal.SIGTERM, timeout: float = 1.0) -> bool:
    """
    Kill a process and all its descendants, gracefully then forcefully.

    Ported from the Bash version's proc_kill function.

    Args:
        pid: Root process ID to kill
        signal_num: Signal to send first (default SIGTERM)
        timeout: Time to wait before sending SIGKILL

    Returns:
        True if all processes were killed, False otherwise
    """
    try:
        # Check if root process exists
        os.kill(pid, 0)
    except ProcessLookupError:
        return True  # Already dead
    except PermissionError:
        logger.warning(f"No permission to signal process {pid}")
        return False

    # Get all processes in the tree
    tree = get_process_tree(pid)

    if not tree:
        return True

    logger.debug(f"Killing process tree: {sorted(tree)}")

    # Send initial signal to all processes
    surviving = set()
    for proc_pid in tree:
        try:
            os.kill(proc_pid, signal_num)
        except ProcessLookupError:
            continue  # Already dead
        except PermissionError:
            logger.warning(f"No permission to signal process {proc_pid}")
            surviving.add(proc_pid)
        else:
            surviving.add(proc_pid)

    if not surviving:
        return True

    # Wait briefly for graceful shutdown
    time.sleep(min(0.1, timeout / 10))

    # Check which processes are still alive
    still_alive = set()
    for proc_pid in surviving:
        try:
            os.kill(proc_pid, 0)
            still_alive.add(proc_pid)
        except ProcessLookupError:
            continue  # Process died
        except PermissionError:
            still_alive.add(proc_pid)  # Assume still alive

    if not still_alive:
        return True

    # Wait remaining timeout then force kill
    if timeout > 0.1:
        time.sleep(timeout - 0.1)

    # Force kill remaining processes
    for proc_pid in still_alive:
        try:
            os.kill(proc_pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            continue

    # Final check
    time.sleep(0.1)
    final_survivors = []
    for proc_pid in still_alive:
        try:
            os.kill(proc_pid, 0)
            final_survivors.append(proc_pid)
        except ProcessLookupError:
            continue
        except PermissionError:
            final_survivors.append(proc_pid)

    if final_survivors:
        logger.warning(f"Failed to kill processes: {final_survivors}")
        return False

    return True
