from dataclasses import dataclass, field
import uuid


@dataclass
class TextElement:
    x: float = 0
    y: float = 0
    text: str = ""
    font_family: str = "Yu Gothic"
    font_size: int = 14
    color: str = "#000000"
    rotation: float = 0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
