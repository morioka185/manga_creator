from dataclasses import dataclass, field
from typing import Optional
import uuid

from src.utils.enums import BubbleType
from src.utils.constants import (
    DEFAULT_BUBBLE_WIDTH, DEFAULT_BUBBLE_HEIGHT,
    DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE
)


@dataclass
class SpeechBubble:
    x: float = 0
    y: float = 0
    width: float = DEFAULT_BUBBLE_WIDTH
    height: float = DEFAULT_BUBBLE_HEIGHT
    text: str = ""
    bubble_type: BubbleType = BubbleType.OVAL
    font_family: str = DEFAULT_FONT_FAMILY
    font_size: int = DEFAULT_FONT_SIZE
    tail_x: float = 0
    tail_y: float = 0
    vertical: bool = True  # 縦書き（デフォルト）
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
