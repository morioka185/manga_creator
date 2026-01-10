from dataclasses import dataclass, field
from typing import Optional
import uuid

from src.utils.constants import (
    DEFAULT_PANEL_WIDTH, DEFAULT_PANEL_HEIGHT, DEFAULT_PANEL_BORDER_WIDTH
)


@dataclass
class Panel:
    x: float = 0
    y: float = 0
    width: float = DEFAULT_PANEL_WIDTH
    height: float = DEFAULT_PANEL_HEIGHT
    border_width: float = DEFAULT_PANEL_BORDER_WIDTH
    rotation: float = 0
    image_path: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
