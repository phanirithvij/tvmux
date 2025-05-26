"""Position type for dimensions."""
from typing import Tuple
from pydantic import BaseModel, Field


class Position(BaseModel):
    """A position or size as (x, y) coordinates."""
    x: int = Field(..., description="X coordinate or width")
    y: int = Field(..., description="Y coordinate or height")

    @classmethod
    def from_string(cls, value: str) -> "Position":
        """Parse from tmux format like '80x24'."""
        if 'x' in value:
            parts = value.split('x')
            # Handle empty parts (e.g., "x" without numbers)
            x = int(parts[0]) if parts[0] else 0
            y = int(parts[1]) if parts[1] else 0
            return cls(x=x, y=y)
        raise ValueError(f"Invalid position format: {value}")

    def __str__(self) -> str:
        """Format as tmux string."""
        return f"{self.x}x{self.y}"

    def as_tuple(self) -> Tuple[int, int]:
        """Get as tuple."""
        return (self.x, self.y)
