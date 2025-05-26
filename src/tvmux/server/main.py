"""FastAPI server that manages tmux connections."""
import asyncio
import os
import subprocess
from fastapi import FastAPI

from .state import server_dir, terminals, SERVER_HOST, SERVER_PORT
from .routers import session, window, callback

app = FastAPI(title="tvmux server")

# Include routers
app.include_router(session.router, prefix="/session", tags=["session"])
app.include_router(window.router, prefix="/window", tags=["window"])
app.include_router(callback.router, prefix="/callback", tags=["callback"])


@app.on_event("startup")
async def startup():
    """Initialize server."""
    server_dir.mkdir(exist_ok=True)
    # Write PID file
    (server_dir / "server.pid").write_text(str(os.getpid()))

    # Set up tmux hooks to call our callbacks
    callback.setup_tmux_hooks()

    # TODO: Discover existing panes and start tracking them


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    # Remove tmux hooks
    callback.remove_tmux_hooks()

    # Remove PID file
    (server_dir / "server.pid").unlink(missing_ok=True)

    # Clean up terminals
    for term in terminals.values():
        await term.stop()


@app.get("/")
async def root():
    """Server info."""
    return {
        "status": "running",
        "pid": os.getpid(),
        "terminals": len(terminals)
    }




def run_server():
    """Run the server on HTTP port."""
    import uvicorn

    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)


if __name__ == "__main__":
    run_server()
