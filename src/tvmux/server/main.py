"""FastAPI server that manages tmux connections."""
import logging
import os
import signal
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI

import uvicorn

from .state import server_dir, recorders, SERVER_HOST, SERVER_PORT
from .routers import session, window, panes, callback, recording


def setup_logging():
    """Configure logging for the application."""
    # Get log level from environment or default to INFO
    log_level = os.getenv('TVMUX_LOG_LEVEL', 'INFO').upper()

    # Configure root logger
    handlers = [logging.StreamHandler()]  # Console output

    # Also log to file if running as daemon
    log_file = server_dir / "server.log"
    if log_file.parent.exists():
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

    # Set specific loggers to appropriate levels
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)  # Reduce HTTP noise
    logging.getLogger('uvicorn.error').setLevel(logging.INFO)

    # Our application loggers
    logging.getLogger('tvmux').setLevel(getattr(logging, log_level, logging.INFO))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    # Set up logging first
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting tvmux server...")

    # Startup
    server_dir.mkdir(exist_ok=True)
    # Write PID file
    (server_dir / "server.pid").write_text(str(os.getpid()))

    # Clean up any existing hooks first (in case of previous crash)
    callback.remove_tmux_hooks()

    # Set up tmux hooks to call our callbacks
    callback.setup_tmux_hooks()
    logger.info("tmux hooks configured")

    # TODO: Discover existing panes and start tracking them

    yield

    # Shutdown
    # Remove tmux hooks
    callback.remove_tmux_hooks()

    # Remove PID file
    (server_dir / "server.pid").unlink(missing_ok=True)

    # Clean up recorders
    for recorder in recorders.values():
        recorder.stop()


app = FastAPI(title="tvmux server", lifespan=lifespan)

# Include routers
app.include_router(session.router, prefix="/sessions", tags=["sessions"])
app.include_router(window.router, prefix="/windows", tags=["windows"])
app.include_router(panes.router, prefix="/panes", tags=["panes"])
app.include_router(callback.router, prefix="/callbacks", tags=["callbacks"])
app.include_router(recording.router, prefix="/recordings", tags=["recordings"])


@app.get("/")
async def root():
    """Server info."""
    return {
        "status": "running",
        "pid": os.getpid(),
        "recorders": len(recorders)
    }




def cleanup_and_exit(signum=None, frame=None):
    """Clean up and exit gracefully."""
    print("\nCleaning up...")

    # Stop all recorders first (kills asciinema processes)
    print(f"Stopping {len(recorders)} active recordings...")
    for recorder in recorders.values():
        try:
            recorder.stop()
        except Exception as e:
            print(f"Error stopping recorder: {e}")

    # Remove tmux hooks
    callback.remove_tmux_hooks()

    # Remove PID file
    (server_dir / "server.pid").unlink(missing_ok=True)

    sys.exit(0)


def run_server():
    """Run the server on HTTP port."""
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, cleanup_and_exit)
    signal.signal(signal.SIGTERM, cleanup_and_exit)

    try:
        uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)
    except KeyboardInterrupt:
        pass  # cleanup_and_exit will be called by signal handler
    finally:
        # Ensure cleanup happens even on unexpected exits
        cleanup_and_exit()


if __name__ == "__main__":
    run_server()
