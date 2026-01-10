import math
from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsItem, QFileDialog
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPen, QBrush, QColor, QPainter, QPixmap

from src.models.panel import Panel
from src.utils.constants import HANDLE_SIZE, MIN_PANEL_SIZE, SNAP_DISTANCE


class PanelGraphicsItem(QGraphicsRectItem):
    def __init__(self, panel: Panel, parent=None):
        super().__init__(0, 0, panel.width, panel.height, parent)
        self.panel = panel
        self.setPos(panel.x, panel.y)

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)

        self.setTransformOriginPoint(panel.width / 2, panel.height / 2)
        self.setRotation(panel.rotation)

        self._pixmap = None
        if panel.image_path:
            self.load_image(panel.image_path)

        self._resizing = False
        self._rotating = False
        self._resize_handle = None
        self._start_rect = None
        self._start_pos = None
        self._start_rotation = 0

        self._update_pen()

    def _update_pen(self):
        pen = QPen(QColor(0, 0, 0))
        pen.setWidthF(self.panel.border_width)
        self.setPen(pen)
        self.setBrush(QBrush(QColor(255, 255, 255)))

    def load_image(self, path: str):
        self._pixmap = QPixmap(path)
        if not self._pixmap.isNull():
            self.panel.image_path = path
        else:
            self._pixmap = None
        self.update()

    def clear_image(self):
        self._pixmap = None
        self.panel.image_path = None
        self.update()

    def paint(self, painter: QPainter, option, widget=None):
        super().paint(painter, option, widget)

        if self._pixmap and not self._pixmap.isNull():
            rect = self.rect()
            scaled = self._pixmap.scaled(
                int(rect.width()), int(rect.height()),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            x = rect.x() + (rect.width() - scaled.width()) / 2
            y = rect.y() + (rect.height() - scaled.height()) / 2
            painter.drawPixmap(int(x), int(y), scaled)

        if self.isSelected():
            self._draw_handles(painter)

    def _draw_handles(self, painter: QPainter):
        rect = self.rect()
        handles = self._get_handles(rect)
        painter.setBrush(QBrush(QColor(100, 150, 255)))
        painter.setPen(QPen(QColor(50, 100, 200)))
        for name, handle_rect in handles.items():
            if name == 'rotate':
                painter.setBrush(QBrush(QColor(255, 150, 100)))
                painter.drawEllipse(handle_rect)
                painter.setBrush(QBrush(QColor(100, 150, 255)))
            else:
                painter.drawRect(handle_rect)

    def _get_handles(self, rect: QRectF) -> dict:
        s = HANDLE_SIZE
        return {
            'top_left': QRectF(rect.left() - s/2, rect.top() - s/2, s, s),
            'top_right': QRectF(rect.right() - s/2, rect.top() - s/2, s, s),
            'bottom_left': QRectF(rect.left() - s/2, rect.bottom() - s/2, s, s),
            'bottom_right': QRectF(rect.right() - s/2, rect.bottom() - s/2, s, s),
            'top': QRectF(rect.center().x() - s/2, rect.top() - s/2, s, s),
            'bottom': QRectF(rect.center().x() - s/2, rect.bottom() - s/2, s, s),
            'left': QRectF(rect.left() - s/2, rect.center().y() - s/2, s, s),
            'right': QRectF(rect.right() - s/2, rect.center().y() - s/2, s, s),
            'rotate': QRectF(rect.center().x() - s/2, rect.top() - 25, s, s),
        }

    def _handle_at(self, pos) -> str:
        if not self.isSelected():
            return None
        handles = self._get_handles(self.rect())
        for name, handle_rect in handles.items():
            if handle_rect.contains(pos):
                return name
        return None

    def hoverMoveEvent(self, event):
        handle = self._handle_at(event.pos())
        if handle:
            if handle == 'rotate':
                self.setCursor(Qt.CursorShape.CrossCursor)
            elif handle in ('top_left', 'bottom_right'):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif handle in ('top_right', 'bottom_left'):
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif handle in ('top', 'bottom'):
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            elif handle in ('left', 'right'):
                self.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self._handle_at(event.pos())
            if handle == 'rotate':
                self._rotating = True
                self._start_rotation = self.rotation()
                self._start_pos = event.pos()
                return
            elif handle:
                self._resizing = True
                self._resize_handle = handle
                self._start_rect = self.rect()
                self._start_pos = event.pos()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._rotating:
            center = self.rect().center()
            start_vec = self._start_pos - center
            current_vec = event.pos() - center
            start_angle = math.atan2(start_vec.y(), start_vec.x())
            current_angle = math.atan2(current_vec.y(), current_vec.x())
            delta_angle = math.degrees(current_angle - start_angle)
            self.setRotation(self._start_rotation + delta_angle)
            self.update()
            return

        if self._resizing:
            delta = event.pos() - self._start_pos
            rect = QRectF(self._start_rect)

            if 'left' in self._resize_handle:
                new_left = rect.left() + delta.x()
                new_left = self._snap_edge(new_left, 'left')
                if rect.right() - new_left >= MIN_PANEL_SIZE:
                    rect.setLeft(new_left)
            if 'right' in self._resize_handle:
                new_right = rect.right() + delta.x()
                new_right = self._snap_edge(new_right, 'right')
                if new_right - rect.left() >= MIN_PANEL_SIZE:
                    rect.setRight(new_right)
            if 'top' in self._resize_handle:
                new_top = rect.top() + delta.y()
                new_top = self._snap_edge(new_top, 'top')
                if rect.bottom() - new_top >= MIN_PANEL_SIZE:
                    rect.setTop(new_top)
            if 'bottom' in self._resize_handle:
                new_bottom = rect.bottom() + delta.y()
                new_bottom = self._snap_edge(new_bottom, 'bottom')
                if new_bottom - rect.top() >= MIN_PANEL_SIZE:
                    rect.setBottom(new_bottom)

            self.setRect(rect.normalized())
            self.update()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._rotating:
            self._rotating = False
            self._sync_to_model()
        if self._resizing:
            self._resizing = False
            self._resize_handle = None
            self._sync_to_model()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        path, _ = QFileDialog.getOpenFileName(
            None, "画像を選択",
            "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if path:
            self.load_image(path)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            new_pos = QPointF(value)
            snapped_pos = self._snap_position(new_pos)
            self._sync_to_model()
            return snapped_pos
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self._sync_to_model()
        return super().itemChange(change, value)

    def _get_other_panels(self):
        if not self.scene():
            return []
        panels = []
        for item in self.scene().items():
            if isinstance(item, PanelGraphicsItem) and item != self:
                panels.append(item)
        return panels

    def _get_snap_lines(self):
        h_lines = []
        v_lines = []

        if self.scene():
            scene_rect = self.scene().sceneRect()
            h_lines.extend([scene_rect.top(), scene_rect.bottom()])
            v_lines.extend([scene_rect.left(), scene_rect.right()])

        for panel in self._get_other_panels():
            if abs(panel.rotation()) < 5:
                pos = panel.pos()
                rect = panel.rect()
                h_lines.extend([
                    pos.y() + rect.top(),
                    pos.y() + rect.bottom()
                ])
                v_lines.extend([
                    pos.x() + rect.left(),
                    pos.x() + rect.right()
                ])

        return h_lines, v_lines

    def _snap_edge(self, value: float, edge: str) -> float:
        if abs(self.rotation()) > 5:
            return value

        h_lines, v_lines = self._get_snap_lines()
        pos = self.pos()

        if edge in ('top', 'bottom'):
            world_value = pos.y() + value
            for line in h_lines:
                if abs(world_value - line) < SNAP_DISTANCE:
                    return line - pos.y()
        else:
            world_value = pos.x() + value
            for line in v_lines:
                if abs(world_value - line) < SNAP_DISTANCE:
                    return line - pos.x()

        return value

    def _snap_position(self, pos: QPointF) -> QPointF:
        if abs(self.rotation()) > 5:
            return pos

        h_lines, v_lines = self._get_snap_lines()
        rect = self.rect()

        my_top = pos.y() + rect.top()
        my_bottom = pos.y() + rect.bottom()
        my_left = pos.x() + rect.left()
        my_right = pos.x() + rect.right()

        new_x = pos.x()
        new_y = pos.y()

        for line in h_lines:
            if abs(my_top - line) < SNAP_DISTANCE:
                new_y = line - rect.top()
                break
            if abs(my_bottom - line) < SNAP_DISTANCE:
                new_y = line - rect.bottom()
                break

        for line in v_lines:
            if abs(my_left - line) < SNAP_DISTANCE:
                new_x = line - rect.left()
                break
            if abs(my_right - line) < SNAP_DISTANCE:
                new_x = line - rect.right()
                break

        return QPointF(new_x, new_y)

    def _sync_to_model(self):
        pos = self.pos()
        rect = self.rect()
        self.panel.x = pos.x() + rect.x()
        self.panel.y = pos.y() + rect.y()
        self.panel.width = rect.width()
        self.panel.height = rect.height()
        self.panel.rotation = self.rotation()
