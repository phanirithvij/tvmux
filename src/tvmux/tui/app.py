"""Main TUI application with CRT TV interface."""
import logging
from pathlib import Path
from typing import Optional, List

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Label, ListView, ListItem
from textual.reactive import reactive
from textual.screen import Screen
from textual_asciinema import AsciinemaPlayer

from ..connection import Connection
from ..config import get_config

logger = logging.getLogger(__name__)


class RecordingList(Static):
    """Widget to display and select recordings."""
    
    recordings: reactive[List[Path]] = reactive([])
    selected_index: reactive[int] = reactive(0)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connection = Connection()
    
    async def on_mount(self) -> None:
        """Load recordings when widget mounts."""
        await self.refresh_recordings()
    
    async def refresh_recordings(self) -> None:
        """Refresh the list of recordings and active sessions."""
        try:
            config = get_config()
            output_dir = Path(config.output.directory).expanduser()
            
            # Find all .cast files
            cast_files = []
            if output_dir.exists():
                cast_files = list(output_dir.rglob("*.cast"))
                cast_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            self.recordings = cast_files
            
            # TODO: Also fetch active sessions/recordings from API
            # if self.connection.is_running:
            #     try:
            #         client = self.connection.client()
            #         sessions_response = client.get("/sessions")
            #         recordings_response = client.get("/recordings")
            #         # Combine with file list to show active recordings
            #     except Exception as e:
            #         logger.debug(f"Could not fetch active sessions: {e}")
            
        except Exception as e:
            logger.error(f"Error loading recordings: {e}")
            self.recordings = []
    
    def render(self) -> str:
        """Render the recordings list."""
        if not self.recordings:
            return "📺 No recordings found\n\nStart recording with: tvmux rec start"
        
        lines = ["📺 Recordings (↑↓ to select, Enter to play):\n"]
        
        for i, recording in enumerate(self.recordings[:10]):  # Show last 10
            marker = "▶ " if i == self.selected_index else "  "
            name = recording.name
            size = recording.stat().st_size
            size_str = f"{size // 1024}KB" if size > 1024 else f"{size}B"
            
            lines.append(f"{marker}{name} ({size_str})")
        
        if len(self.recordings) > 10:
            lines.append(f"\n... and {len(self.recordings) - 10} more")
        
        return "\n".join(lines)
    
    def action_select_next(self) -> None:
        """Select next recording."""
        if self.recordings:
            self.selected_index = (self.selected_index + 1) % min(10, len(self.recordings))
    
    def action_select_previous(self) -> None:
        """Select previous recording."""
        if self.recordings:
            self.selected_index = (self.selected_index - 1) % min(10, len(self.recordings))
    
    def get_selected_recording(self) -> Optional[Path]:
        """Get the currently selected recording."""
        if self.recordings and 0 <= self.selected_index < len(self.recordings):
            return self.recordings[self.selected_index]
        return None


class CRTPlayer(Static):
    """CRT-style video player widget."""
    
    current_file: reactive[Optional[Path]] = reactive(None)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.player: Optional[AsciinemaPlayer] = None
    
    def compose(self) -> ComposeResult:
        """Compose the CRT player."""
        with Container(classes="crt-container"):
            with Container(classes="crt-screen"):
                if self.current_file:
                    # Create asciinema player
                    self.player = AsciinemaPlayer(str(self.current_file))
                    yield self.player
                else:
                    yield Label("📺 tvmux", classes="crt-logo")
                    yield Label("Select a recording to play", classes="crt-subtitle")
    
    async def play_recording(self, recording_path: Path) -> None:
        """Play a recording file."""
        try:
            self.current_file = recording_path
            
            # Remove existing player
            if self.player:
                await self.player.remove()
            
            # Create new player
            self.player = AsciinemaPlayer(str(recording_path))
            
            # Find the screen container and add player
            screen_container = self.query_one(".crt-screen")
            await screen_container.mount(self.player)
            
            logger.info(f"Playing recording: {recording_path.name}")
            
        except Exception as e:
            logger.error(f"Error playing recording: {e}")


class TVMuxApp(App):
    """Main tvmux TUI application."""
    
    CSS = """
    /* CRT TV styling */
    .crt-container {
        border: thick white;
        background: black;
        margin: 1;
        padding: 1;
    }
    
    .crt-screen {
        background: #001100;
        color: #00ff00;
        border: solid #333333;
        min-height: 20;
        padding: 1;
    }
    
    .crt-logo {
        text-align: center;
        color: #00ff00;
        text-style: bold;
        margin-top: 5;
    }
    
    .crt-subtitle {
        text-align: center;
        color: #666666;
        margin-top: 2;
    }
    
    /* Control panel styling */
    .controls {
        background: #111111;
        border: solid #333333;
        min-height: 10;
        max-height: 15;
        padding: 1;
    }
    
    /* Layout */
    .main-layout {
        height: 100%;
    }
    
    .video-area {
        height: 75%;
    }
    
    .control-area {
        height: 25%;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("up", "select_previous", "Previous"),
        ("down", "select_next", "Next"),
        ("enter", "play_selected", "Play"),
        ("space", "toggle_playback", "Play/Pause"),
    ]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.player: Optional[CRTPlayer] = None
        self.recording_list: Optional[RecordingList] = None
    
    def compose(self) -> ComposeResult:
        """Compose the application layout."""
        yield Header()
        
        with Vertical(classes="main-layout"):
            # Top area - CRT TV player
            with Container(classes="video-area"):
                self.player = CRTPlayer()
                yield self.player
            
            # Bottom area - controls and recording list
            with Container(classes="control-area controls"):
                self.recording_list = RecordingList()
                yield self.recording_list
        
        yield Footer()
    
    async def action_refresh(self) -> None:
        """Refresh recordings list."""
        if self.recording_list:
            await self.recording_list.refresh_recordings()
    
    def action_select_next(self) -> None:
        """Select next recording."""
        if self.recording_list:
            self.recording_list.action_select_next()
    
    def action_select_previous(self) -> None:
        """Select previous recording."""
        if self.recording_list:
            self.recording_list.action_select_previous()
    
    async def action_play_selected(self) -> None:
        """Play the selected recording."""
        if self.recording_list and self.player:
            selected = self.recording_list.get_selected_recording()
            if selected:
                await self.player.play_recording(selected)
    
    def action_toggle_playback(self) -> None:
        """Toggle playback of current recording."""
        if self.player and self.player.player:
            # Toggle play/pause - this depends on textual-asciinema API
            # May need to check the actual API
            pass


def run_tui():
    """Run the tvmux TUI application."""
    app = TVMuxApp()
    app.run()


if __name__ == "__main__":
    run_tui()