from enum import Enum, auto


class ToolType(Enum):
    SELECT = auto()
    PANEL = auto()
    SPEECH_BUBBLE = auto()
    TEXT = auto()


class BubbleType(Enum):
    OVAL = auto()
    ROUNDED_RECT = auto()
    CLOUD = auto()
    EXPLOSION = auto()
