from dataclasses import dataclass, field
from typing import Optional
import uuid

from src.utils.enums import BubbleType
from src.utils.constants import (
    DEFAULT_BUBBLE_WIDTH, DEFAULT_BUBBLE_HEIGHT,
    DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE,
    ROUNDED_RECT_RADIUS
)


@dataclass
class SpeechBubble:
    x: float = 0
    y: float = 0
    width: float = DEFAULT_BUBBLE_WIDTH
    height: float = DEFAULT_BUBBLE_HEIGHT
    text: str = ""
    bubble_type: BubbleType = BubbleType.SPEECH
    font_family: str = DEFAULT_FONT_FAMILY
    font_size: int = DEFAULT_FONT_SIZE
    tail_x: float = 0
    tail_y: float = 0
    vertical: bool = True  # 縦書き（デフォルト）
    auto_font_size: bool = True  # フォントサイズ自動調整（デフォルトON）
    rotation: float = 0  # 回転角度（度）
    color: str = "#000000"  # 文字色（TEXT_ONLY用）
    corner_radius: float = ROUNDED_RECT_RADIUS  # 角丸半径（RECTANGLE用）
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
