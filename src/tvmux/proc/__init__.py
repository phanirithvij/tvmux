"""Process utilities."""
import logging
import subprocess
from typing import List

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
