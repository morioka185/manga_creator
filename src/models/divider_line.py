from dataclasses import dataclass, field
import uuid

from src.utils.constants import DEFAULT_MARGIN


@dataclass
class DividerLine:
    """ページを分割する線"""
    x1: float = 0
    y1: float = 0
    x2: float = 100
    y2: float = 100
    gutter_width: float = DEFAULT_MARGIN  # コマ間の余白幅
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
