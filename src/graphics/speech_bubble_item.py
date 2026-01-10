from PyQt6.QtWidgets import QGraphicsItem, QGraphicsTextItem, QInputDialog
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPen, QBrush, QColor, QPainter, QFont

from src.models.speech_bubble import SpeechBubble
from src.graphics.bubble_shapes import BubbleShapes
from src.utils.constants import HANDLE_SIZE, MIN_PANEL_SIZE


class SpeechBubbleGraphicsItem(QGraphicsItem):
    def __init__(self, bubble: SpeechBubble, parent=None):
        super().__init__(parent)
        self.bubble = bubble
        self.setPos(bubble.x, bubble.y)

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)

        self._resizing = False
        self._resize_handle = None
        self._start_rect = None
        self._start_pos = None
        self._dragging_tail = False

    def boundingRect(self) -> QRectF:
        margin = 20
        return QRectF(-margin, -margin,
                      self.bubble.width + margin * 2,
                      self.bubble.height + margin * 2)

    def paint(self, painter: QPainter, option, widget=None):
        rect = QRectF(0, 0, self.bubble.width, self.bubble.height)
        tail_pos = QPointF(self.bubble.tail_x, self.bubble.tail_y)

        path = BubbleShapes.create_path(self.bubble.bubble_type, rect, tail_pos)

        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.drawPath(path)

        font = QFont(self.bubble.font_family, self.bubble.font_size)
        painter.setFont(font)
        painter.setPen(QPen(QColor(0, 0, 0)))

        text_rect = rect.adjusted(10, 10, -10, -10)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                         self.bubble.text)

        if self.isSelected():
            self._draw_handles(painter, rect)

    def _draw_handles(self, painter: QPainter, rect: QRectF):
        handles = self._get_handles(rect)
        painter.setBrush(QBrush(QColor(100, 150, 255)))
        painter.setPen(QPen(QColor(50, 100, 200)))
        for handle_rect in handles.values():
            painter.drawRect(handle_rect)

        tail_pos = QPointF(self.bubble.tail_x, self.bubble.tail_y)
        if not tail_pos.isNull():
            painter.setBrush(QBrush(QColor(255, 150, 100)))
            painter.drawEllipse(tail_pos, 6, 6)

    def _get_handles(self, rect: QRectF) -> dict:
        s = HANDLE_SIZE
        return {
            'top_left': QRectF(rect.left() - s/2, rect.top() - s/2, s, s),
            'top_right': QRectF(rect.right() - s/2, rect.top() - s/2, s, s),
            'bottom_left': QRectF(rect.left() - s/2, rect.bottom() - s/2, s, s),
            'bottom_right': QRectF(rect.right() - s/2, rect.bottom() - s/2, s, s),
        }

    def _handle_at(self, pos) -> str:
        if not self.isSelected():
            return None
        rect = QRectF(0, 0, self.bubble.width, self.bubble.height)
        handles = self._get_handles(rect)
        for name, handle_rect in handles.items():
            if handle_rect.contains(pos):
                return name
        return None

    def _is_near_tail(self, pos) -> bool:
        tail_pos = QPointF(self.bubble.tail_x, self.bubble.tail_y)
        return (pos - tail_pos).manhattanLength() < 12

    def hoverMoveEvent(self, event):
        handle = self._handle_at(event.pos())
        if handle:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif self.isSelected() and self._is_near_tail(event.pos()):
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.isSelected() and self._is_near_tail(event.pos()):
                self._dragging_tail = True
                return
            handle = self._handle_at(event.pos())
            if handle:
                self._resizing = True
                self._resize_handle = handle
                self._start_rect = QRectF(0, 0, self.bubble.width, self.bubble.height)
                self._start_pos = event.pos()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging_tail:
            self.bubble.tail_x = event.pos().x()
            self.bubble.tail_y = event.pos().y()
            self.update()
            return
        if self._resizing:
            delta = event.pos() - self._start_pos
            rect = QRectF(self._start_rect)

            if 'right' in self._resize_handle:
                new_w = rect.width() + delta.x()
                if new_w >= MIN_PANEL_SIZE:
                    self.bubble.width = new_w
            if 'left' in self._resize_handle:
                new_w = rect.width() - delta.x()
                if new_w >= MIN_PANEL_SIZE:
                    self.bubble.width = new_w
                    self.setX(self.x() + delta.x())
            if 'bottom' in self._resize_handle:
                new_h = rect.height() + delta.y()
                if new_h >= MIN_PANEL_SIZE:
                    self.bubble.height = new_h
            if 'top' in self._resize_handle:
                new_h = rect.height() - delta.y()
                if new_h >= MIN_PANEL_SIZE:
                    self.bubble.height = new_h
                    self.setY(self.y() + delta.y())

            self.prepareGeometryChange()
            self.update()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resizing:
            self._resizing = False
            self._resize_handle = None
        if self._dragging_tail:
            self._dragging_tail = False
        self._sync_to_model()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        text, ok = QInputDialog.getMultiLineText(
            None, "セリフ入力", "テキストを入力:", self.bubble.text
        )
        if ok:
            self.bubble.text = text
            self.update()

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self._sync_to_model()
        return super().itemChange(change, value)

    def _sync_to_model(self):
        pos = self.pos()
        self.bubble.x = pos.x()
        self.bubble.y = pos.y()
