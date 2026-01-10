from PyQt6.QtWidgets import QGraphicsScene, QGraphicsPolygonItem, QGraphicsLineItem, QFileDialog
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF, QLineF
from PyQt6.QtGui import QPen, QColor, QBrush, QPolygonF, QPixmap, QPainter

from src.models.page import Page
from src.models.divider_line import DividerLine
from src.models.speech_bubble import SpeechBubble
from src.models.text_element import TextElement
from src.graphics.divider_line_item import DividerLineItem
from src.graphics.speech_bubble_item import SpeechBubbleGraphicsItem
from src.graphics.text_item import TextGraphicsItem
from src.services.panel_calculator import PanelCalculator
from src.utils.enums import ToolType, BubbleType


class PanelPolygonItem(QGraphicsPolygonItem):
    """コマ領域（ポリゴン）を表示するアイテム"""

    def __init__(self, polygon: QPolygonF, panel_id: str, parent=None):
        super().__init__(polygon, parent)
        self.panel_id = panel_id
        self._pixmap = None
        self._image_path = None

        self.setPen(QPen(QColor(0, 0, 0), 2))
        self.setBrush(QBrush(QColor(255, 255, 255)))
        self.setFlag(QGraphicsPolygonItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)

    def set_image(self, path: str):
        self._pixmap = QPixmap(path)
        self._image_path = path
        self.update()

    def clear_image(self):
        self._pixmap = None
        self._image_path = None
        self.update()

    def get_image_path(self) -> str:
        return self._image_path

    def paint(self, painter: QPainter, option, widget=None):
        # 背景を描画
        painter.setBrush(self.brush())
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(self.polygon())

        # 画像があれば描画
        if self._pixmap and not self._pixmap.isNull():
            rect = self.polygon().boundingRect()
            scaled = self._pixmap.scaled(
                int(rect.width()), int(rect.height()),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )

            # クリップしてポリゴン内に描画
            painter.setClipPath(self.shape())
            x = rect.x() + (rect.width() - scaled.width()) / 2
            y = rect.y() + (rect.height() - scaled.height()) / 2
            painter.drawPixmap(int(x), int(y), scaled)
            painter.setClipping(False)

        # 枠線を描画
        painter.setPen(self.pen())
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolygon(self.polygon())

    def mouseDoubleClickEvent(self, event):
        """ダブルクリックで画像を選択"""
        path, _ = QFileDialog.getOpenFileName(
            None, "画像を選択", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if path:
            self.set_image(path)
            # シーンに通知
            if self.scene():
                self.scene()._save_panel_image(self.panel_id, path)


class CanvasScene(QGraphicsScene):
    item_selected = pyqtSignal(object)
    page_modified = pyqtSignal()
    divider_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._page = None
        self._current_tool = ToolType.SELECT
        self._current_bubble_type = BubbleType.OVAL
        self._drawing = False
        self._start_pos = None
        self._temp_line = None
        self._panel_items = []

        self.divider_changed.connect(self._on_divider_changed)

    def set_page(self, page: Page):
        self.clear()
        self._page = page
        self._panel_items = []

        self.setSceneRect(0, 0, page.width, page.height)

        # 背景
        bg_rect = self.addRect(0, 0, page.width, page.height,
                               QPen(QColor(200, 200, 200)),
                               QBrush(QColor(245, 245, 245)))
        bg_rect.setZValue(-1000)

        # コマ領域を計算して描画
        self._update_panels()

        # 分割線を描画
        for divider in page.divider_lines:
            item = DividerLineItem(divider)
            item.setZValue(100)
            self.addItem(item)

        # 吹き出し
        for bubble in page.speech_bubbles:
            item = SpeechBubbleGraphicsItem(bubble)
            item.setZValue(200)
            self.addItem(item)

        # テキスト
        for text_elem in page.text_elements:
            item = TextGraphicsItem(text_elem)
            item.setZValue(200)
            self.addItem(item)

    def _update_panels(self):
        """分割線からコマ領域を再計算"""
        # 既存のパネルアイテムを削除
        for item in self._panel_items:
            self.removeItem(item)
        self._panel_items = []

        if not self._page:
            return

        # コマ領域を計算
        panels = PanelCalculator.calculate_panels(
            self._page.width, self._page.height,
            self._page.divider_lines
        )

        # 各コマを描画
        for i, polygon in enumerate(panels):
            panel_id = f"panel_{i}"
            item = PanelPolygonItem(polygon, panel_id)
            item.setZValue(0)

            # 保存された画像があれば適用
            if panel_id in self._page.panel_images:
                item.set_image(self._page.panel_images[panel_id])

            self.addItem(item)
            self._panel_items.append(item)

    def _save_panel_image(self, panel_id: str, path: str):
        """パネルの画像パスを保存"""
        if self._page:
            self._page.panel_images[panel_id] = path
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
                    QPen(QColor(100, 100, 255), 2, Qt.PenStyle.DashLine)
                )

    def mouseMoveEvent(self, event):
        if self._current_tool == ToolType.SELECT:
            super().mouseMoveEvent(event)
            return

        if self._drawing and self._temp_line:
            end_pos = event.scenePos()
            # 水平・垂直にスナップ
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

        # 一時線を削除
        if self._temp_line:
            self.removeItem(self._temp_line)
            self._temp_line = None

        if self._current_tool == ToolType.PANEL:
            self._create_divider(self._start_pos, end_pos)
        elif self._current_tool == ToolType.SPEECH_BUBBLE:
            self._create_bubble(self._start_pos, end_pos)
        elif self._current_tool == ToolType.TEXT:
            self._create_text(event.scenePos())

        self.page_modified.emit()

    def _create_divider(self, start: QPointF, end: QPointF):
        """分割線を作成（水平・垂直のみ）"""
        # 短すぎる線は無視
        if (end - start).manhattanLength() < 30:
            return

        # 水平・垂直にスナップ
        dx = abs(end.x() - start.x())
        dy = abs(end.y() - start.y())

        if dx > dy:
            # 水平線
            end = QPointF(end.x(), start.y())
        else:
            # 垂直線
            end = QPointF(start.x(), end.y())

        # ページ境界にスナップ
        start = self._snap_to_boundary(start)
        end = self._snap_to_boundary(end)

        divider = DividerLine(
            x1=start.x(), y1=start.y(),
            x2=end.x(), y2=end.y()
        )
        self._page.divider_lines.append(divider)

        item = DividerLineItem(divider)
        item.setZValue(100)
        self.addItem(item)

        # コマ領域を再計算
        self._update_panels()

    def _snap_to_boundary(self, pos: QPointF) -> QPointF:
        """ページ境界にスナップ"""
        x, y = pos.x(), pos.y()
        snap = 20

        if x < snap:
            x = 0
        elif x > self._page.width - snap:
            x = self._page.width

        if y < snap:
            y = 0
        elif y > self._page.height - snap:
            y = self._page.height

        return QPointF(x, y)

    def _create_bubble(self, start, end):
        x = min(start.x(), end.x())
        y = min(start.y(), end.y())
        w = abs(end.x() - start.x())
        h = abs(end.y() - start.y())

        if w < 20:
            w = 150
        if h < 20:
            h = 100

        bubble = SpeechBubble(
            x=x, y=y, width=w, height=h,
            bubble_type=self._current_bubble_type,
            tail_x=w / 2, tail_y=h + 30
        )
        self._page.speech_bubbles.append(bubble)

        item = SpeechBubbleGraphicsItem(bubble)
        item.setZValue(200)
        self.addItem(item)

    def _create_text(self, pos):
        text_elem = TextElement(x=pos.x(), y=pos.y(), text="テキスト")
        self._page.text_elements.append(text_elem)

        item = TextGraphicsItem(text_elem)
        item.setZValue(200)
        self.addItem(item)
        item.setSelected(True)

    def delete_selected(self):
        for item in self.selectedItems():
            if isinstance(item, DividerLineItem):
                if item.divider in self._page.divider_lines:
                    self._page.divider_lines.remove(item.divider)
                self.removeItem(item)
                self._update_panels()
            elif isinstance(item, SpeechBubbleGraphicsItem):
                if item.bubble in self._page.speech_bubbles:
                    self._page.speech_bubbles.remove(item.bubble)
                self.removeItem(item)
            elif isinstance(item, TextGraphicsItem):
                if item.text_element in self._page.text_elements:
                    self._page.text_elements.remove(item.text_element)
                self.removeItem(item)
        self.page_modified.emit()
