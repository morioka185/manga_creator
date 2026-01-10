from dataclasses import dataclass, field
import uuid

from src.utils.constants import DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE


@dataclass
class TextElement:
    x: float = 0
    y: float = 0
    text: str = ""
    font_family: str = DEFAULT_FONT_FAMILY
    font_size: int = DEFAULT_FONT_SIZE
    color: str = "#000000"
    rotation: float = 0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
