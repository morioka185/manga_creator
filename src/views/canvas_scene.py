from PyQt6.QtWidgets import QGraphicsScene, QGraphicsPolygonItem, QGraphicsLineItem, QFileDialog, QMenu
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF, QLineF
from PyQt6.QtGui import QPen, QColor, QBrush, QPolygonF, QPixmap, QPainter

from src.models.page import Page
from src.models.divider_line import DividerLine
from src.models.speech_bubble import SpeechBubble
from src.models.text_element import TextElement
from src.models.panel_image_data import PanelImageData
from src.graphics.divider_line_item import DividerLineItem
from src.graphics.speech_bubble_item import SpeechBubbleGraphicsItem
from src.graphics.text_item import TextGraphicsItem
from src.services.panel_calculator import PanelCalculator
from src.utils.enums import ToolType, BubbleType


class PanelPolygonItem(QGraphicsPolygonItem):
    """コマ領域（ポリゴン）を表示するアイテム"""

    MIN_SCALE = 1.0   # 最小スケール（コマを完全に覆う）
    MAX_SCALE = 4.0   # 最大スケール（400%）
    SCALE_STEP = 0.1  # スケール変更ステップ

    def __init__(self, polygon: QPolygonF, panel_id: str, parent=None):
        super().__init__(polygon, parent)
        self.panel_id = panel_id
        self._pixmap = None
        self._image_data = None  # PanelImageData

        # ドラッグ操作用
        self._dragging = False
        self._drag_start_pos = None
        self._drag_start_offset = None

        self.setPen(QPen(QColor(0, 0, 0), 2))
        self.setBrush(QBrush(QColor(255, 255, 255)))
        self.setFlag(QGraphicsPolygonItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton)

    def set_image_data(self, image_data: PanelImageData):
        """画像データを設定"""
        self._image_data = image_data
        self._pixmap = QPixmap(image_data.image_path)
        if self._pixmap.isNull():
            self._pixmap = None
            self._image_data = None
        self.update()

    def set_image(self, path: str):
        """新しい画像を設定（スケール・オフセットはリセット）"""
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            self._pixmap = pixmap
            self._image_data = PanelImageData(
                image_path=path,
                scale=1.0,
                offset_x=0.0,
                offset_y=0.0
            )
        else:
            self._pixmap = None
            self._image_data = None
        self.update()

    def clear_image(self):
        """画像をクリア"""
        self._pixmap = None
        self._image_data = None
        self.update()
        # シーンに通知
        if self.scene():
            self.scene()._clear_panel_image(self.panel_id)

    def get_image_data(self) -> PanelImageData:
        """画像データを取得"""
        return self._image_data

    def get_image_path(self) -> str:
        """画像パスを取得（後方互換性）"""
        return self._image_data.image_path if self._image_data else None

    def _get_base_scale(self) -> float:
        """コマを完全に覆うための基本スケールを計算"""
        if not self._pixmap or self._pixmap.isNull():
            return 1.0

        rect = self.polygon().boundingRect()
        img_w = self._pixmap.width()
        img_h = self._pixmap.height()

        if img_w == 0 or img_h == 0:
            return 1.0

        # アスペクト比を維持しながらコマを覆う最小スケール
        scale_w = rect.width() / img_w
        scale_h = rect.height() / img_h
        return max(scale_w, scale_h)

    def _get_scaled_pixmap_size(self) -> tuple:
        """現在のスケールでの画像サイズを取得"""
        if not self._pixmap or not self._image_data:
            return (0, 0)

        base_scale = self._get_base_scale()
        actual_scale = base_scale * self._image_data.scale

        return (
            self._pixmap.width() * actual_scale,
            self._pixmap.height() * actual_scale
        )

    def _clamp_offset(self):
        """オフセットを制限（画像がコマ外にはみ出さないように）"""
        if not self._image_data or not self._pixmap:
            return

        rect = self.polygon().boundingRect()
        scaled_w, scaled_h = self._get_scaled_pixmap_size()

        # 画像がコマより大きい場合のみオフセット可能
        max_offset_x = max(0, (scaled_w - rect.width()) / 2)
        max_offset_y = max(0, (scaled_h - rect.height()) / 2)

        self._image_data.offset_x = max(-max_offset_x, min(max_offset_x, self._image_data.offset_x))
        self._image_data.offset_y = max(-max_offset_y, min(max_offset_y, self._image_data.offset_y))

    def paint(self, painter: QPainter, option, widget=None):
        # 背景を描画
        painter.setBrush(self.brush())
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(self.polygon())

        # 画像があれば描画
        if self._pixmap and not self._pixmap.isNull() and self._image_data:
            rect = self.polygon().boundingRect()

            # スケール計算
            base_scale = self._get_base_scale()
            actual_scale = base_scale * self._image_data.scale

            scaled_w = int(self._pixmap.width() * actual_scale)
            scaled_h = int(self._pixmap.height() * actual_scale)

            scaled = self._pixmap.scaled(
                scaled_w, scaled_h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            # クリップしてポリゴン内に描画
            painter.setClipPath(self.shape())

            # 中央配置 + オフセット
            x = rect.x() + (rect.width() - scaled.width()) / 2 + self._image_data.offset_x
            y = rect.y() + (rect.height() - scaled.height()) / 2 + self._image_data.offset_y
            painter.drawPixmap(int(x), int(y), scaled)
            painter.setClipping(False)

        # 枠線を描画
        painter.setPen(self.pen())
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolygon(self.polygon())

        # 選択時は編集可能であることを示す
        if self.isSelected() and self._image_data:
            # 選択枠を描画
            painter.setPen(QPen(QColor(0, 120, 215), 2, Qt.PenStyle.DashLine))
            painter.drawPolygon(self.polygon())

    def wheelEvent(self, event):
        """マウスホイールで拡大縮小"""
        if not self._image_data:
            return

        # ホイールの回転量を取得
        delta = event.delta() if hasattr(event, 'delta') else event.angleDelta().y()

        if delta > 0:
            # 拡大
            new_scale = min(self.MAX_SCALE, self._image_data.scale + self.SCALE_STEP)
        else:
            # 縮小
            new_scale = max(self.MIN_SCALE, self._image_data.scale - self.SCALE_STEP)

        self._image_data.scale = new_scale
        self._clamp_offset()
        self.update()

        # シーンに変更を通知
        if self.scene():
            self.scene()._save_panel_image(self.panel_id, self._image_data)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event)
            return

        if event.button() == Qt.MouseButton.LeftButton and self._image_data:
            # ドラッグ開始
            self._dragging = True
            self._drag_start_pos = event.pos()
            self._drag_start_offset = (self._image_data.offset_x, self._image_data.offset_y)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging and self._image_data:
            # オフセットを更新
            delta = event.pos() - self._drag_start_pos
            self._image_data.offset_x = self._drag_start_offset[0] + delta.x()
            self._image_data.offset_y = self._drag_start_offset[1] + delta.y()
            self._clamp_offset()
            self.update()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._dragging:
            self._dragging = False
            self.setCursor(Qt.CursorShape.OpenHandCursor if self._image_data else Qt.CursorShape.ArrowCursor)

            # シーンに変更を通知
            if self.scene() and self._image_data:
                self.scene()._save_panel_image(self.panel_id, self._image_data)
            return

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """ダブルクリックで画像を選択"""
        path, _ = QFileDialog.getOpenFileName(
            None, "画像を選択", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if path:
            self.set_image(path)
            # シーンに通知
            if self.scene() and self._image_data:
                self.scene()._save_panel_image(self.panel_id, self._image_data)

    def hoverEnterEvent(self, event):
        if self._image_data:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverLeaveEvent(event)

    def _show_context_menu(self, event):
        """右クリックメニューを表示"""
        menu = QMenu()

        if self._image_data:
            # 画像がある場合
            change_action = menu.addAction("画像を変更")
            clear_action = menu.addAction("画像をクリア")
            menu.addSeparator()
            reset_action = menu.addAction("位置・サイズをリセット")

            action = menu.exec(event.screenPos())

            if action == change_action:
                self._select_new_image()
            elif action == clear_action:
                self.clear_image()
            elif action == reset_action:
                self._image_data.scale = 1.0
                self._image_data.offset_x = 0.0
                self._image_data.offset_y = 0.0
                self.update()
                if self.scene():
                    self.scene()._save_panel_image(self.panel_id, self._image_data)
        else:
            # 画像がない場合
            add_action = menu.addAction("画像を追加")
            action = menu.exec(event.screenPos())

            if action == add_action:
                self._select_new_image()

    def _select_new_image(self):
        """新しい画像を選択"""
        path, _ = QFileDialog.getOpenFileName(
            None, "画像を選択", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if path:
            self.set_image(path)
            if self.scene() and self._image_data:
                self.scene()._save_panel_image(self.panel_id, self._image_data)


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
