"""Pane model for tvmux."""
from pydantic import BaseModel, Field


class Pane(BaseModel):
    """A tmux pane."""

    id: str = Field(..., description="Pane unique ID (%pane_id)")
    index: int = Field(..., description="Pane index in window")
    active: bool = Field(False, description="Is active pane")
    size: str = Field(..., description="Pane size (width x height)")
    command: str = Field(..., description="Running command")
    pid: int = Field(..., description="Process ID")
    title: str = Field("", description="Pane title")
