"""Session model for tvmux."""

from pydantic import BaseModel, Field
from .position import Position


class Session(BaseModel):
    """A tmux session."""

    name: str = Field(..., description="Session name")
    id: str = Field(..., description="Session ID (e.g. $0)")
    created: int = Field(..., description="Session creation time (unix timestamp)")
    attached: bool = Field(False, description="Is session attached")
    size: Position = Field(..., description="Session size")
    windows: int = Field(0, description="Number of windows")
