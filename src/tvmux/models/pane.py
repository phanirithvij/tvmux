"""Pane model for tvmux."""
from typing import Optional
from pydantic import BaseModel, Field
from .position import Position


class Pane(BaseModel):
    """A tmux pane."""

    id: str = Field(..., description="Pane unique ID (%pane_id)")
    index: int = Field(..., description="Pane index in window")
    active: bool = Field(False, description="Is active pane")
    position: Position = Field(..., description="Pane position (top-left corner)")
    size: Position = Field(..., description="Pane size")
    command: str = Field(..., description="Running command")
    pid: int = Field(..., description="Process ID")
    title: str = Field("", description="Pane title")
    session: Optional[str] = Field(None, description="Session name")
    window_index: Optional[int] = Field(None, description="Window index in session")
    window_id: Optional[str] = Field(None, description="Window ID")
