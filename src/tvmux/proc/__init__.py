"""Process utilities."""
import asyncio
import logging
import subprocess
from typing import List

from .bg import spawn

logger = logging.getLogger(__name__)


def run(cmd: List[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a subprocess synchronously with automatic logging.

    Args:
        cmd: Command to run as list of strings
        **kwargs: Additional arguments passed to subprocess.run

    Returns:
        CompletedProcess result
    """
    logger.debug(f"Running: {' '.join(cmd)}")

    # Capture output by default for logging
    kwargs.setdefault('capture_output', True)
    kwargs.setdefault('text', True)

    try:
        result = subprocess.run(cmd, **kwargs)

        if result.stdout:
            logger.debug(f"stdout: {result.stdout.strip()}")
        if result.stderr:
            logger.debug(f"stderr: {result.stderr.strip()}")

        if result.returncode != 0:
            logger.error(f"Command failed with exit code {result.returncode}: {' '.join(cmd)}")
        else:
            logger.debug(f"Command succeeded: {' '.join(cmd)}")

        return result

    except Exception as e:
        logger.error(f"Command failed with exception: {' '.join(cmd)} - {e}")
        raise


async def run_bg(cmd: List[str], **kwargs) -> subprocess.Popen:
    """Run a subprocess in the background asynchronously.

    Args:
        cmd: Command to run as list of strings
        **kwargs: Additional arguments passed to subprocess.Popen

    Returns:
        The Popen process object
    """
    return await asyncio.get_event_loop().run_in_executor(None, lambda: spawn(cmd, **kwargs))
