"""FastAPI server that manages tmux connections."""
import asyncio
import logging
import os
import signal
import subprocess
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI

from .state import server_dir, recorders, SERVER_HOST, SERVER_PORT
from .routers import session, window, callback, recording


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    # Set up debug logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Startup
    server_dir.mkdir(exist_ok=True)
    # Write PID file
    (server_dir / "server.pid").write_text(str(os.getpid()))

    # Clean up any existing hooks first (in case of previous crash)
    callback.remove_tmux_hooks()

    # Set up tmux hooks to call our callbacks
    callback.setup_tmux_hooks()

    # TODO: Discover existing panes and start tracking them

    yield

    # Shutdown
    # Remove tmux hooks
    callback.remove_tmux_hooks()

    # Remove PID file
    (server_dir / "server.pid").unlink(missing_ok=True)

    # Clean up recorders
    for recorder in recorders.values():
        recorder.stop_recording()


app = FastAPI(title="tvmux server", lifespan=lifespan)

# Include routers
app.include_router(session.router, prefix="/session", tags=["session"])
app.include_router(window.router, prefix="/window", tags=["window"])
app.include_router(callback.router, prefix="/callback", tags=["callback"])
app.include_router(recording.router, prefix="/recording", tags=["recording"])


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
    # Remove tmux hooks
    callback.remove_tmux_hooks()
    # Remove PID file
    (server_dir / "server.pid").unlink(missing_ok=True)
    sys.exit(0)


def run_server():
    """Run the server on HTTP port."""
    import uvicorn

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, cleanup_and_exit)
    signal.signal(signal.SIGTERM, cleanup_and_exit)

    try:
        uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)
    except KeyboardInterrupt:
        cleanup_and_exit()
    finally:
        # Ensure cleanup happens even on unexpected exits
        cleanup_and_exit()


if __name__ == "__main__":
    run_server()
