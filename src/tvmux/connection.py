"""Connection to tvmux server."""
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

import httpx


class Connection:
    """Manages connection to tvmux server."""

    def __init__(self):
        """Initialize connection."""
        self.user = os.getenv("USER", "nobody")
        self.server_dir = Path(f"/tmp/tvmux-{self.user}")
        self.pid_file = self.server_dir / "server.pid"
        self.socket_path = self.server_dir / "control.sock"

    @property
    def server_pid(self) -> Optional[int]:
        """Get server PID if running."""
        try:
            if self.pid_file.exists():
                pid = int(self.pid_file.read_text().strip())
                # Check if process is actually running
                os.kill(pid, 0)
                return pid
        except (ValueError, ProcessLookupError, FileNotFoundError):
            pass
        return None

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self.server_pid is not None and self.socket_path.exists()

    def start(self) -> bool:
        """Start the server."""
        if self.is_running:
            print(f"Server already running (PID: {self.server_pid})")
            return True

        # Create server directory
        self.server_dir.mkdir(exist_ok=True)

        # Start server in background
        subprocess.Popen(
            ["python", "-m", "tvmux.server"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

        # Wait for server to start
        for _ in range(10):
            if self.is_running:
                print(f"Server started (PID: {self.server_pid})")
                return True
            time.sleep(0.1)

        print("Failed to start server")
        return False

    def stop(self) -> bool:
        """Stop the server."""
        pid = self.server_pid
        if not pid:
            print("Server not running")
            return True

        try:
            # Send SIGTERM
            os.kill(pid, 15)

            # Wait for graceful shutdown
            for _ in range(10):
                try:
                    os.kill(pid, 0)
                    time.sleep(0.1)
                except ProcessLookupError:
                    break
            else:
                # Force kill if still running
                os.kill(pid, 9)

            print(f"Server stopped (PID: {pid})")
            return True

        except ProcessLookupError:
            print("Server already stopped")
            return True
        except Exception as e:
            print(f"Error stopping server: {e}")
            return False

    def client(self) -> httpx.Client:
        """Get HTTP client connected to server socket."""
        if not self.is_running:
            raise RuntimeError("Server not running")

        transport = httpx.HTTPTransport(uds=str(self.socket_path))
        return httpx.Client(transport=transport, base_url="http://localhost")

    async def async_client(self) -> httpx.AsyncClient:
        """Get async HTTP client connected to server socket."""
        if not self.is_running:
            raise RuntimeError("Server not running")

        transport = httpx.AsyncHTTPTransport(uds=str(self.socket_path))
        return httpx.AsyncClient(transport=transport, base_url="http://localhost")
