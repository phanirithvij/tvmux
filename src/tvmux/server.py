"""FastAPI server that manages tmux connections."""
import asyncio
import os
from pathlib import Path
from typing import Dict, List

from fastapi import FastAPI
from pydantic import BaseModel

from .terminal import Terminal

app = FastAPI(title="tvmux server")

# Global state
terminals: Dict[str, Terminal] = {}
server_dir = Path(f"/tmp/tvmux-{os.getenv('USER', 'nobody')}")


class TerminalInfo(BaseModel):
    """Info about a terminal."""
    pane_id: str
    session: str
    window: int
    pane: int
    state: dict


@app.on_event("startup")
async def startup():
    """Initialize server."""
    server_dir.mkdir(exist_ok=True)
    # Write PID file
    (server_dir / "server.pid").write_text(str(os.getpid()))


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    # Remove PID file
    (server_dir / "server.pid").unlink(missing_ok=True)
    # TODO: Clean up fifos and terminals


@app.get("/")
async def root():
    """Server info."""
    return {
        "status": "running",
        "pid": os.getpid(),
        "terminals": len(terminals)
    }


@app.get("/terminals")
async def list_terminals() -> List[TerminalInfo]:
    """List all terminals."""
    return [
        TerminalInfo(
            pane_id=pane_id,
            session=term.session,
            window=term.window,
            pane=term.pane,
            state=term.state
        )
        for pane_id, term in terminals.items()
    ]


@app.post("/terminals/{pane_id}")
async def create_terminal(pane_id: str):
    """Create a new terminal monitor."""
    if pane_id in terminals:
        return {"status": "already exists"}

    # Create fifos
    state_fifo = server_dir / f"{pane_id}.state.fifo"
    stream_fifo = server_dir / f"{pane_id}.stream.fifo"

    os.mkfifo(state_fifo)
    os.mkfifo(stream_fifo)

    # Create terminal
    term = Terminal(pane_id, state_fifo, stream_fifo)
    terminals[pane_id] = term

    # Start processing in background
    asyncio.create_task(term.process())

    # TODO: Install tmux hooks

    return {"status": "created", "pane_id": pane_id}


@app.delete("/terminals/{pane_id}")
async def delete_terminal(pane_id: str):
    """Stop monitoring a terminal."""
    if pane_id not in terminals:
        return {"status": "not found"}

    term = terminals.pop(pane_id)
    await term.stop()

    return {"status": "deleted"}


def run_server():
    """Run the server on unix socket."""
    import uvicorn

    socket_path = server_dir / "control.sock"
    socket_path.unlink(missing_ok=True)

    uvicorn.run(app, uds=str(socket_path))


if __name__ == "__main__":
    run_server()
