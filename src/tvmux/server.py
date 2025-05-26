"""FastAPI server that manages tmux connections."""
import asyncio
import os
import subprocess
from pathlib import Path
from typing import Dict, List

from fastapi import FastAPI
from pydantic import BaseModel

from .terminal import Terminal
from .models.session import Session
from .models.window import Window
from .models.pane import Pane

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

    # Discover all tmux panes and create terminals
    await discover_and_create_terminals()


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

    # Create fifos if they don't exist
    for fifo in [state_fifo, stream_fifo]:
        if not fifo.exists():
            subprocess.run(["mkfifo", str(fifo)])

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


@app.get("/sessions", response_model=List[Session])
async def list_sessions():
    """List all tmux sessions."""
    result = subprocess.run(
        ["tmux", "list-sessions", "-F",
         "#{session_name}|#{session_id}|#{session_created}|#{session_attached}|#{session_windows}|#{session_width}x#{session_height}"],
        capture_output=True,
        text=True
    )

    sessions = []
    if result.returncode == 0:
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split("|")
                sessions.append(Session(
                    name=parts[0],
                    id=parts[1],
                    created=int(parts[2]),
                    attached=parts[3] == "1",
                    windows=int(parts[4]),
                    size=parts[5]
                ))

    return sessions


@app.get("/sessions/{name}", response_model=Session)
async def get_session(name: str):
    """Get a specific session."""
    sessions = await list_sessions()
    for session in sessions:
        if session.name == name:
            return session
    return {"error": "Session not found"}


@app.get("/windows", response_model=List[Window])
async def list_windows():
    """List all tmux windows."""
    result = subprocess.run(
        ["tmux", "list-windows", "-a", "-F",
         "#{window_id}|#{window_name}|#{window_active}|#{window_panes}|#{window_width}x#{window_height}|#{window_layout}"],
        capture_output=True,
        text=True
    )

    windows = []
    if result.returncode == 0:
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split("|")
                windows.append(Window(
                    id=parts[0],
                    name=parts[1],
                    active=parts[2] == "1",
                    panes=int(parts[3]),
                    size=parts[4],
                    layout=parts[5]
                ))

    return windows


@app.get("/windows/{window_id}", response_model=Window)
async def get_window(window_id: str):
    """Get a specific window."""
    windows = await list_windows()
    for window in windows:
        if window.id == window_id:
            return window
    return {"error": "Window not found"}


@app.get("/panes", response_model=List[Pane])
async def list_panes():
    """List all tmux panes."""
    result = subprocess.run(
        ["tmux", "list-panes", "-a", "-F",
         "#{pane_id}|#{pane_index}|#{pane_active}|#{pane_width}x#{pane_height}|#{pane_current_command}|#{pane_pid}|#{pane_title}"],
        capture_output=True,
        text=True
    )

    panes = []
    if result.returncode == 0:
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split("|")
                panes.append(Pane(
                    id=parts[0],
                    index=int(parts[1]),
                    active=parts[2] == "1",
                    size=parts[3],
                    command=parts[4],
                    pid=int(parts[5]),
                    title=parts[6] if len(parts) > 6 else ""
                ))

    return panes


@app.get("/panes/{pane_id}", response_model=Pane)
async def get_pane(pane_id: str):
    """Get a specific pane."""
    panes = await list_panes()
    for pane in panes:
        if pane.id == pane_id:
            return pane
    return {"error": "Pane not found"}


async def discover_and_create_terminals():
    """Discover all tmux panes and create terminals for them."""
    try:
        # Get all panes with format: session:window.pane
        result = subprocess.run(
            ["tmux", "list-panes", "-a", "-F", "#{session_name}:#{window_index}.#{pane_index}"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            pane_ids = result.stdout.strip().split("\n")
            for pane_id in pane_ids:
                if pane_id and pane_id not in terminals:
                    await create_terminal(pane_id)

            print(f"Created {len(pane_ids)} terminals")
    except Exception as e:
        print(f"Error discovering tmux panes: {e}")


def run_server():
    """Run the server on unix socket."""
    import uvicorn

    socket_path = server_dir / "control.sock"
    socket_path.unlink(missing_ok=True)

    uvicorn.run(app, uds=str(socket_path))


if __name__ == "__main__":
    run_server()
