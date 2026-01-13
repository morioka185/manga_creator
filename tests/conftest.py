"""pytest共通設定とフィクスチャ"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from src.models.page import Page
from src.models.project import Project
from src.models.divider_line import DividerLine
from src.models.speech_bubble import SpeechBubble
from src.utils.enums import BubbleType


@pytest.fixture
def empty_page():
    """空のページ"""
    return Page()


@pytest.fixture
def page_with_dividers():
    """分割線付きのページ"""
    page = Page(width=1000, height=1400, margin=0)
    page.divider_lines = [
        DividerLine(x1=500, y1=0, x2=500, y2=1400, gutter_width=20),  # 垂直分割
    ]
    return page


@pytest.fixture
def page_with_bubbles():
    """吹き出し付きのページ"""
    page = Page()
    page.speech_bubbles = [
        SpeechBubble(x=100, y=100, width=200, height=150, text="テスト1"),
        SpeechBubble(x=400, y=300, width=180, height=120, text="テスト2", bubble_type=BubbleType.CLOUD),
    ]
    return page


@pytest.fixture
def sample_project():
    """サンプルプロジェクト（2ページ）"""
    project = Project(name="テストプロジェクト")
    # __post_init__で1ページ追加されているので、上書きで2ページに設定
    project.pages = [Page(), Page()]
    return project


@pytest.fixture
def vertical_divider():
    """垂直分割線"""
    return DividerLine(x1=500, y1=0, x2=500, y2=1400, gutter_width=20)


@pytest.fixture
def horizontal_divider():
    """水平分割線"""
    return DividerLine(x1=0, y1=700, x2=1000, y2=700, gutter_width=20)


@pytest.fixture
def speech_bubble():
    """吹き出し"""
    return SpeechBubble(
        x=100, y=100,
        width=200, height=150,
        text="こんにちは",
        bubble_type=BubbleType.SPEECH,
        vertical=True
    )
