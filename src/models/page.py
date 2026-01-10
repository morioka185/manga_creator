from dataclasses import dataclass, field
from typing import List, Dict
import uuid

from src.models.panel import Panel
from src.models.speech_bubble import SpeechBubble
from src.models.text_element import TextElement
from src.models.divider_line import DividerLine
from src.utils.constants import DEFAULT_PAGE_WIDTH, DEFAULT_PAGE_HEIGHT


@dataclass
class Page:
    width: int = DEFAULT_PAGE_WIDTH
    height: int = DEFAULT_PAGE_HEIGHT
    divider_lines: List[DividerLine] = field(default_factory=list)
    panel_images: Dict[str, str] = field(default_factory=dict)  # panel_id -> image_path
    speech_bubbles: List[SpeechBubble] = field(default_factory=list)
    text_elements: List[TextElement] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
