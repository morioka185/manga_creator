from dataclasses import dataclass, field
from typing import Optional
import uuid

from src.utils.enums import BubbleType


@dataclass
class SpeechBubble:
    x: float = 0
    y: float = 0
    width: float = 150
    height: float = 100
    text: str = ""
    bubble_type: BubbleType = BubbleType.OVAL
    font_family: str = "Yu Gothic"
    font_size: int = 14
    tail_x: float = 0
    tail_y: float = 0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
