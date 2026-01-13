from PyQt6.QtWidgets import QGraphicsScene, QGraphicsLineItem
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QLineF
from PyQt6.QtGui import QPen, QColor, QBrush

from src.models.page import Page
from src.models.divider_line import DividerLine
from src.models.speech_bubble import SpeechBubble
from src.models.panel_image_data import PanelImageData
from src.graphics.panel_polygon_item import PanelPolygonItem
from src.graphics.divider_line_item import DividerLineItem
from src.graphics.speech_bubble_item import SpeechBubbleGraphicsItem
from src.services.panel_calculator import PanelCalculator
from src.utils.enums import ToolType, BubbleType
from src.utils.constants import (
    COLOR_WHITE, COLOR_BLACK, COLOR_GRAY, COLOR_TEMP_LINE,
    DEFAULT_PANEL_BORDER_WIDTH, BUBBLE_BORDER_WIDTH,
    ZVALUE_BACKGROUND, ZVALUE_PANEL, ZVALUE_DIVIDER, ZVALUE_BUBBLE, ZVALUE_TEXT, ZVALUE_PAGE_BORDER,
    BUBBLE_TAIL_OFFSET, MIN_BUBBLE_DRAG_SIZE,
    MIN_DIVIDER_LENGTH, DIVIDER_SNAP_RANGE
)
from src.commands.undo_commands import (
    AddDividerCommand, DeleteDividerCommand,
    AddBubbleCommand, DeleteBubbleCommand
)
from src.services.settings_service import SettingsService


class CanvasScene(QGraphicsScene):
    item_selected = pyqtSignal(object)
    page_modified = pyqtSignal()
    divider_changed = pyqtSignal()
    ai_generate_requested = pyqtSignal(str, int, int)  # panel_id, width, height
    ai_regenerate_requested = pyqtSignal(str, int, int, dict)  # panel_id, width, height, settings

    def __init__(self, parent=None):
        super().__init__(parent)
        self._page = None
        self._current_tool = ToolType.SELECT
        self._current_bubble_type = BubbleType.OVAL
        self._drawing = False
        self._start_pos = None
        self._temp_line = None
        self._panel_items = []
        self._undo_stack = None

        # 残像防止: アイテムインデックスを最適化
        self.setItemIndexMethod(QGraphicsScene.ItemIndexMethod.BspTreeIndex)

        self.divider_changed.connect(self._on_divider_changed)

    def set_undo_stack(self, undo_stack):
        """UndoStackを設定"""
        self._undo_stack = undo_stack

    def set_page(self, page: Page):
        self.clear()
        self._page = page
        self._panel_items = []

        self.setSceneRect(0, 0, page.width, page.height)

        # 背景（ページ全体）
        bg_rect = self.addRect(0, 0, page.width, page.height,
                               QPen(QColor(*COLOR_GRAY)),
                               QBrush(QColor(*COLOR_WHITE)))
        bg_rect.setZValue(ZVALUE_BACKGROUND)

        # ページ全体の外枠（黒い枠線）
        page_border = self.addRect(0, 0, page.width, page.height,
                                   QPen(QColor(*COLOR_BLACK), DEFAULT_PANEL_BORDER_WIDTH),
                                   QBrush(Qt.BrushStyle.NoBrush))
        page_border.setZValue(ZVALUE_PAGE_BORDER)

        # 内側の枠（マージン内のコンテンツエリア）
        margin = page.margin
        if margin > 0:
            inner_rect = self.addRect(margin, margin,
                                      page.width - margin * 2,
                                      page.height - margin * 2,
                                      QPen(QColor(*COLOR_BLACK), 1),
                                      QBrush(Qt.BrushStyle.NoBrush))
            inner_rect.setZValue(ZVALUE_PAGE_BORDER)

        # コマ領域を計算して描画
        self._update_panels()

        # 分割線を描画
        for divider in page.divider_lines:
            item = DividerLineItem(divider)
            item.setZValue(ZVALUE_DIVIDER)
            self.addItem(item)

        # 吹き出し
        for bubble in page.speech_bubbles:
            item = SpeechBubbleGraphicsItem(bubble)
            item.setZValue(ZVALUE_BUBBLE)
            self.addItem(item)

    def _update_panels(self):
        """分割線からコマ領域を再計算"""
        # 既存のパネルアイテムを削除
        for item in self._panel_items:
            self.removeItem(item)
        self._panel_items = []

        if not self._page:
            return

        # コマ領域を計算（マージン内に制限）
        panels = PanelCalculator.calculate_panels(
            self._page.width, self._page.height,
            self._page.divider_lines,
            self._page.margin
        )

        # 各コマを描画
        for i, polygon in enumerate(panels):
            panel_id = f"panel_{i}"
            item = PanelPolygonItem(polygon, panel_id)
            item.setZValue(ZVALUE_PANEL)

            # 保存された画像データがあれば適用
            if panel_id in self._page.panel_images:
                image_data = self._page.panel_images[panel_id]
                item.set_image_data(image_data)

            self.addItem(item)
            self._panel_items.append(item)

    def _save_panel_image(self, panel_id: str, image_data: PanelImageData):
        """パネルの画像データを保存"""
        if self._page:
            self._page.panel_images[panel_id] = image_data
            self.page_modified.emit()

    def _clear_panel_image(self, panel_id: str):
        """パネルの画像データをクリア"""
        if self._page and panel_id in self._page.panel_images:
            del self._page.panel_images[panel_id]
            self.page_modified.emit()

    def _on_divider_changed(self):
        """分割線が変更されたときの処理"""
        self._update_panels()
        self.page_modified.emit()

    def get_page(self) -> Page:
        return self._page

    def set_tool(self, tool: ToolType):
        self._current_tool = tool
        # 選択ツールまたは分割線ツールの時だけ分割線を表示
        show_dividers = tool in (ToolType.SELECT, ToolType.PANEL)
        self._set_dividers_visible(show_dividers)

    def _set_dividers_visible(self, visible: bool):
        """分割線の表示/非表示を切り替える"""
        for item in self.items():
            if isinstance(item, DividerLineItem):
                item.setVisible(visible)

    def set_bubble_type(self, bubble_type: BubbleType):
        self._current_bubble_type = bubble_type

    def mousePressEvent(self, event):
        if self._current_tool == ToolType.SELECT:
            super().mousePressEvent(event)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self._drawing = True
            self._start_pos = event.scenePos()

            # 分割線ツールの場合は一時線を表示
            if self._current_tool == ToolType.PANEL:
                self._temp_line = self.addLine(
                    QLineF(self._start_pos, self._start_pos),
                    QPen(QColor(*COLOR_TEMP_LINE), BUBBLE_BORDER_WIDTH, Qt.PenStyle.DashLine)
                )

    def mouseMoveEvent(self, event):
        if self._current_tool == ToolType.SELECT:
            super().mouseMoveEvent(event)
            return

        if self._drawing and self._temp_line:
            end_pos = event.scenePos()
            # Shiftキーが押されている場合のみ水平・垂直にスナップ
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                dx = abs(end_pos.x() - self._start_pos.x())
                dy = abs(end_pos.y() - self._start_pos.y())
                if dx > dy:
                    end_pos = QPointF(end_pos.x(), self._start_pos.y())
                else:
                    end_pos = QPointF(self._start_pos.x(), end_pos.y())
            self._temp_line.setLine(QLineF(self._start_pos, end_pos))

    def mouseReleaseEvent(self, event):
        if self._current_tool == ToolType.SELECT:
            super().mouseReleaseEvent(event)
            return

        if not self._drawing:
            return

        self._drawing = False
        end_pos = event.scenePos()

        # Shiftキーが押されている場合は水平・垂直にスナップ
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            dx = abs(end_pos.x() - self._start_pos.x())
            dy = abs(end_pos.y() - self._start_pos.y())
            if dx > dy:
                end_pos = QPointF(end_pos.x(), self._start_pos.y())
            else:
                end_pos = QPointF(self._start_pos.x(), end_pos.y())

        # 一時線を削除
        if self._temp_line:
            self.removeItem(self._temp_line)
            self._temp_line = None

        if self._current_tool == ToolType.PANEL:
            self._create_divider(self._start_pos, end_pos)
        elif self._current_tool == ToolType.SPEECH_BUBBLE:
            self._create_bubble(self._start_pos, end_pos)

        self.page_modified.emit()

    def _create_divider(self, start: QPointF, end: QPointF):
        """分割線を作成（斜め線も可能）"""
        # 短すぎる線は無視
        if (end - start).manhattanLength() < MIN_DIVIDER_LENGTH:
            return

        # ページ境界にスナップ
        start = self._snap_to_boundary(start)
        end = self._snap_to_boundary(end)

        divider = DividerLine(
            x1=start.x(), y1=start.y(),
            x2=end.x(), y2=end.y()
        )

        item = DividerLineItem(divider)
        item.setZValue(ZVALUE_DIVIDER)

        # Undoコマンドを使用
        if self._undo_stack is not None:
            cmd = AddDividerCommand(self, divider, item)
            self._undo_stack.push(cmd)
        else:
            self._page.divider_lines.append(divider)
            self.addItem(item)
            self._update_panels()

    def _snap_to_boundary(self, pos: QPointF) -> QPointF:
        """マージン境界にスナップ"""
        x, y = pos.x(), pos.y()
        snap = DIVIDER_SNAP_RANGE
        margin = self._page.margin

        # マージン境界
        left = margin
        top = margin
        right = self._page.width - margin
        bottom = self._page.height - margin

        # 左端にスナップ
        if x < left + snap:
            x = left
        # 右端にスナップ
        elif x > right - snap:
            x = right

        # 上端にスナップ
        if y < top + snap:
            y = top
        # 下端にスナップ
        elif y > bottom - snap:
            y = bottom

        # マージン内に制限
        x = max(left, min(right, x))
        y = max(top, min(bottom, y))

        return QPointF(x, y)

    def _create_bubble(self, start, end):
        x = min(start.x(), end.x())
        y = min(start.y(), end.y())
        settings = SettingsService.get_instance()

        w = abs(end.x() - start.x())
        h = abs(end.y() - start.y())

        if w < MIN_BUBBLE_DRAG_SIZE:
            w = settings.bubble_width
        if h < MIN_BUBBLE_DRAG_SIZE:
            h = settings.bubble_height

        bubble = SpeechBubble(
            x=x, y=y, width=w, height=h,
            bubble_type=self._current_bubble_type,
            tail_x=w / 2, tail_y=h + BUBBLE_TAIL_OFFSET,
            font_family=settings.font_family,
            font_size=settings.font_size,
            vertical=settings.bubble_vertical
        )

        item = SpeechBubbleGraphicsItem(bubble)
        item.setZValue(ZVALUE_BUBBLE)

        # Undoコマンドを使用
        if self._undo_stack is not None:
            cmd = AddBubbleCommand(self, bubble, item)
            self._undo_stack.push(cmd)
        else:
            self._page.speech_bubbles.append(bubble)
            self.addItem(item)

    def delete_selected(self):
        for item in self.selectedItems():
            if isinstance(item, DividerLineItem):
                if self._undo_stack is not None:
                    cmd = DeleteDividerCommand(self, item.divider, item)
                    self._undo_stack.push(cmd)
                else:
                    if item.divider in self._page.divider_lines:
                        self._page.divider_lines.remove(item.divider)
                    self.removeItem(item)
                    self._update_panels()
                    self.page_modified.emit()
            elif isinstance(item, SpeechBubbleGraphicsItem):
                if self._undo_stack is not None:
                    cmd = DeleteBubbleCommand(self, item.bubble, item)
                    self._undo_stack.push(cmd)
                else:
                    if item.bubble in self._page.speech_bubbles:
                        self._page.speech_bubbles.remove(item.bubble)
                    self.removeItem(item)
                    self.page_modified.emit()
