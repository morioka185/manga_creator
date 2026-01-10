from dataclasses import dataclass, field
from typing import Optional
import uuid


@dataclass
class Panel:
    x: float = 0
    y: float = 0
    width: float = 200
    height: float = 200
    border_width: float = 2.0
    rotation: float = 0
    image_path: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
