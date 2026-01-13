"""モデルクラスのユニットテスト"""

import pytest
import uuid

from src.models.page import Page
from src.models.project import Project
from src.models.divider_line import DividerLine
from src.models.speech_bubble import SpeechBubble
from src.utils.enums import BubbleType
from src.utils.constants import (
    DEFAULT_PAGE_WIDTH, DEFAULT_PAGE_HEIGHT, DEFAULT_MARGIN,
    DEFAULT_BUBBLE_WIDTH, DEFAULT_BUBBLE_HEIGHT,
    DEFAULT_FONT_SIZE, DEFAULT_FONT_FAMILY
)


class TestPage:
    """Pageモデルのテスト"""

    def test_default_values(self):
        """デフォルト値が正しく設定される"""
        page = Page()
        assert page.width == DEFAULT_PAGE_WIDTH
        assert page.height == DEFAULT_PAGE_HEIGHT
        assert page.margin == DEFAULT_MARGIN
        assert page.divider_lines == []
        assert page.speech_bubbles == []
        assert page.panel_images == {}

    def test_custom_values(self):
        """カスタム値が正しく設定される"""
        page = Page(width=1000, height=1500, margin=30)
        assert page.width == 1000
        assert page.height == 1500
        assert page.margin == 30

    def test_unique_id(self):
        """各ページにユニークなIDが付与される"""
        page1 = Page()
        page2 = Page()
        assert page1.id != page2.id
        # UUIDフォーマットの検証
        uuid.UUID(page1.id)  # 無効なら例外発生

    def test_add_divider_line(self, vertical_divider):
        """分割線の追加"""
        page = Page()
        page.divider_lines.append(vertical_divider)
        assert len(page.divider_lines) == 1
        assert page.divider_lines[0].x1 == 500

    def test_add_speech_bubble(self, speech_bubble):
        """吹き出しの追加"""
        page = Page()
        page.speech_bubbles.append(speech_bubble)
        assert len(page.speech_bubbles) == 1
        assert page.speech_bubbles[0].text == "こんにちは"


class TestDividerLine:
    """DividerLineモデルのテスト"""

    def test_default_values(self):
        """デフォルト値が正しく設定される"""
        divider = DividerLine()
        assert divider.x1 == 0
        assert divider.y1 == 0
        assert divider.x2 == 100
        assert divider.y2 == 100
        assert divider.gutter_width == DEFAULT_MARGIN

    def test_custom_values(self):
        """カスタム値が正しく設定される"""
        divider = DividerLine(x1=0, y1=500, x2=1000, y2=500, gutter_width=40)
        assert divider.x1 == 0
        assert divider.y1 == 500
        assert divider.x2 == 1000
        assert divider.y2 == 500
        assert divider.gutter_width == 40

    def test_unique_id(self):
        """各分割線にユニークなIDが付与される"""
        d1 = DividerLine()
        d2 = DividerLine()
        assert d1.id != d2.id

    def test_vertical_line(self, vertical_divider):
        """垂直線の検証"""
        assert vertical_divider.x1 == vertical_divider.x2  # x座標が同じ
        assert vertical_divider.y1 != vertical_divider.y2  # y座標が異なる

    def test_horizontal_line(self, horizontal_divider):
        """水平線の検証"""
        assert horizontal_divider.y1 == horizontal_divider.y2  # y座標が同じ
        assert horizontal_divider.x1 != horizontal_divider.x2  # x座標が異なる


class TestSpeechBubble:
    """SpeechBubbleモデルのテスト"""

    def test_default_values(self):
        """デフォルト値が正しく設定される"""
        bubble = SpeechBubble()
        assert bubble.x == 0
        assert bubble.y == 0
        assert bubble.width == DEFAULT_BUBBLE_WIDTH
        assert bubble.height == DEFAULT_BUBBLE_HEIGHT
        assert bubble.text == ""
        assert bubble.bubble_type == BubbleType.SPEECH
        assert bubble.font_family == DEFAULT_FONT_FAMILY
        assert bubble.font_size == DEFAULT_FONT_SIZE
        assert bubble.vertical is True  # デフォルトは縦書き
        assert bubble.auto_font_size is True

    def test_custom_values(self):
        """カスタム値が正しく設定される"""
        bubble = SpeechBubble(
            x=100, y=200,
            width=300, height=250,
            text="セリフ",
            bubble_type=BubbleType.CLOUD,
            vertical=False
        )
        assert bubble.x == 100
        assert bubble.y == 200
        assert bubble.width == 300
        assert bubble.height == 250
        assert bubble.text == "セリフ"
        assert bubble.bubble_type == BubbleType.CLOUD
        assert bubble.vertical is False

    def test_all_bubble_types(self):
        """全ての吹き出しタイプが正しく設定される"""
        bubble_types = [
            BubbleType.TEXT_ONLY,
            BubbleType.OVAL,
            BubbleType.SPEECH,
            BubbleType.RECTANGLE,
            BubbleType.CLOUD,
            BubbleType.EXPLOSION
        ]
        for bt in bubble_types:
            bubble = SpeechBubble(bubble_type=bt)
            assert bubble.bubble_type == bt

    def test_unique_id(self):
        """各吹き出しにユニークなIDが付与される"""
        b1 = SpeechBubble()
        b2 = SpeechBubble()
        assert b1.id != b2.id

    def test_tail_position(self):
        """尻尾の位置が設定できる"""
        bubble = SpeechBubble(tail_x=50, tail_y=100)
        assert bubble.tail_x == 50
        assert bubble.tail_y == 100

    def test_rotation(self):
        """回転角度が設定できる"""
        bubble = SpeechBubble(rotation=45.0)
        assert bubble.rotation == 45.0

    def test_color(self):
        """文字色が設定できる"""
        bubble = SpeechBubble(color="#FF0000")
        assert bubble.color == "#FF0000"


class TestProject:
    """Projectモデルのテスト"""

    def test_default_values(self):
        """デフォルト値が正しく設定される"""
        project = Project()
        assert project.name == "Untitled"
        assert len(project.pages) == 1  # デフォルトで1ページ

    def test_custom_name(self):
        """カスタム名が設定できる"""
        project = Project(name="マイマンガ")
        assert project.name == "マイマンガ"

    def test_multiple_pages(self, sample_project):
        """複数ページの管理"""
        assert len(sample_project.pages) == 2
        assert sample_project.name == "テストプロジェクト"

    def test_add_page(self):
        """ページの追加"""
        project = Project()
        initial_count = len(project.pages)
        project.pages.append(Page())
        assert len(project.pages) == initial_count + 1

    def test_remove_page(self):
        """ページの削除"""
        project = Project(pages=[Page(), Page(), Page()])
        del project.pages[1]
        assert len(project.pages) == 2


class TestBubbleType:
    """BubbleType列挙型のテスト"""

    def test_all_types_exist(self):
        """全ての吹き出しタイプが存在する"""
        expected_types = ['TEXT_ONLY', 'OVAL', 'SPEECH', 'RECTANGLE', 'CLOUD', 'EXPLOSION']
        for type_name in expected_types:
            assert hasattr(BubbleType, type_name)

    def test_type_from_name(self):
        """名前から吹き出しタイプを取得できる"""
        assert BubbleType['SPEECH'] == BubbleType.SPEECH
        assert BubbleType['CLOUD'] == BubbleType.CLOUD

    def test_invalid_type_raises(self):
        """無効な名前はKeyErrorを発生させる"""
        with pytest.raises(KeyError):
            BubbleType['INVALID_TYPE']
