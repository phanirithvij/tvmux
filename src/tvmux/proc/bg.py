"""Background process management with automatic cleanup."""
import atexit
import logging
import os
import signal
import subprocess
import time
from typing import List, Set

logger = logging.getLogger(__name__)

# Global set of all child processes we've spawned
_managed_processes: Set[int] = set()


def _get_children(pid: int) -> Set[int]:
    """Get direct children of a process."""
    children = set()
    try:
        # Read /proc to find children
        for proc_dir in os.listdir('/proc'):
            if not proc_dir.isdigit():
                continue
            try:
                stat_path = f'/proc/{proc_dir}/stat'
                with open(stat_path, 'r') as f:
                    stat = f.read()
                    # Format: pid (name) state ppid ...
                    # Extract ppid (parent pid) which is the 4th field
                    parts = stat.split(')', 1)[1].split()
                    ppid = int(parts[1])
                    if ppid == pid:
                        children.add(int(proc_dir))
            except (OSError, IOError, ValueError, IndexError):
                continue
    except OSError:
        pass
    return children


def _get_descendants(pid: int) -> Set[int]:
    """Get all descendants of a process."""
    descendants = {pid}
    to_process = [pid]

    while to_process:
        current_pid = to_process.pop()
        children = _get_children(current_pid)
        for child in children:
            if child not in descendants:
                descendants.add(child)
                to_process.append(child)

    return descendants


def _terminate_tree(pid: int, timeout: float = 1.0) -> bool:
    """Terminate a process and all its descendants."""
    try:
        # Check if root process exists
        os.kill(pid, 0)
    except ProcessLookupError:
        return True  # Already dead
    except PermissionError:
        logger.warning(f"No permission to signal process {pid}")
        return False

    # Get all processes in the tree
    tree = _get_descendants(pid)

    if not tree:
        return True

    logger.debug(f"Terminating process tree: {sorted(tree)}")

    # Send SIGTERM to all processes
    surviving = set()
    for proc_pid in tree:
        try:
            os.kill(proc_pid, signal.SIGTERM)
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
            continue

    # If timeout allows, wait for remaining processes
    if still_alive and timeout > 0.1:
        time.sleep(timeout - 0.1)

        # Final check
        final_survivors = set()
        for proc_pid in still_alive:
            try:
                os.kill(proc_pid, 0)
                final_survivors.add(proc_pid)
            except ProcessLookupError:
                continue

        still_alive = final_survivors

    # Force kill any survivors
    if still_alive:
        logger.debug(f"Force killing surviving processes: {sorted(still_alive)}")
        for proc_pid in still_alive:
            try:
                os.kill(proc_pid, signal.SIGKILL)
            except ProcessLookupError:
                continue
            except PermissionError:
                logger.warning(f"No permission to SIGKILL process {proc_pid}")

    # Final verification
    for proc_pid in tree:
        try:
            os.kill(proc_pid, 0)
            logger.warning(f"Process {proc_pid} survived SIGKILL")
            return False
        except ProcessLookupError:
            continue

    return True


def _cleanup_on_exit():
    """Kill all tracked child processes on exit."""
    if not _managed_processes:
        return

    logger.debug(f"Cleaning up {len(_managed_processes)} background processes")
    for pid in list(_managed_processes):
        try:
            _terminate_tree(pid, timeout=1.0)
            _managed_processes.discard(pid)
        except Exception as e:
            logger.debug(f"Failed to kill process {pid}: {e}")


# Register cleanup on exit and signals
atexit.register(_cleanup_on_exit)

def _signal_handler(signum, frame):
    """Handle signals by cleaning up background processes."""
    logger.debug(f"Received signal {signum}, cleaning up background processes")
    _cleanup_on_exit()

# Register signal handlers for proper cleanup
signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)


def spawn(cmd: List[str], **kwargs) -> subprocess.Popen:
    """Run a subprocess in the background with automatic cleanup on exit.

    Args:
        cmd: Command to run as list of strings
        **kwargs: Additional arguments passed to subprocess.Popen

    Returns:
        The Popen process object
    """
    # Default to no stdin/stdout/stderr if not specified
    kwargs.setdefault('stdin', subprocess.DEVNULL)
    kwargs.setdefault('stdout', subprocess.DEVNULL)
    kwargs.setdefault('stderr', subprocess.DEVNULL)

    proc = subprocess.Popen(cmd, **kwargs)
    _managed_processes.add(proc.pid)

    logger.debug(f"Started background process {proc.pid}: {' '.join(cmd)}")

    return proc


def terminate(pid: int) -> bool:
    """Stop a tracked background process.

    Args:
        pid: Process ID to stop

    Returns:
        True if process was stopped, False if not found
    """
    if pid not in _managed_processes:
        return False

    try:
        _terminate_tree(pid, timeout=1.0)
        _managed_processes.discard(pid)
        return True
    except Exception as e:
        logger.debug(f"Failed to stop process {pid}: {e}")
        _managed_processes.discard(pid)  # Remove anyway
        return False


def reap():
    """Remove PIDs of processes that have already exited."""
    dead_pids = []
    for pid in _managed_processes:
        try:
            os.kill(pid, 0)  # Check if process exists
        except ProcessLookupError:
            dead_pids.append(pid)

    for pid in dead_pids:
        _managed_processes.discard(pid)
