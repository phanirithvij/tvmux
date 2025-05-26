"""Window model for tvmux."""
from pydantic import BaseModel, Field
from .position import Position


class Window(BaseModel):
    """A tmux window."""

    id: str = Field(..., description="Window unique ID (@window_id)")
    name: str = Field(..., description="Window name")
    active: bool = Field(False, description="Is active window")
    panes: int = Field(1, description="Number of panes")
    size: Position = Field(..., description="Window size")
    layout: str = Field(..., description="Window layout")
