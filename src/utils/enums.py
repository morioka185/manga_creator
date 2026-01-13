from enum import Enum, auto


class ToolType(Enum):
    SELECT = auto()
    PANEL = auto()
    SPEECH_BUBBLE = auto()


class BubbleType(Enum):
    TEXT_ONLY = auto()   # 文字のみ（形状なし、尻尾なし）
    OVAL = auto()        # 楕円（尻尾なし）
    SPEECH = auto()      # 吹き出し（楕円＋尻尾）
    RECTANGLE = auto()   # 長方形（角丸度調整可能）
    CLOUD = auto()       # 雲形（尻尾あり）
    EXPLOSION = auto()   # 爆発（尻尾なし）
