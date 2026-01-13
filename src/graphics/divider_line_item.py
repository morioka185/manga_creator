from PyQt6.QtWidgets import QGraphicsLineItem, QGraphicsItem
from PyQt6.QtCore import Qt, QPointF, QLineF, QRectF
from PyQt6.QtGui import QPen, QBrush, QColor, QPainter

from src.models.divider_line import DividerLine
from src.utils.constants import (
    HANDLE_SIZE, SNAP_DISTANCE,
    COLOR_DIVIDER, COLOR_DIVIDER_SELECTED,
    COLOR_HANDLE, COLOR_HANDLE_BORDER,
    DIVIDER_LINE_WIDTH, DIVIDER_LINE_WIDTH_SELECTED,
    DIVIDER_SNAP_RANGE
)


class DividerLineItem(QGraphicsLineItem):
    def __init__(self, divider: DividerLine, parent=None):
        super().__init__(divider.x1, divider.y1, divider.x2, divider.y2, parent)
        self.divider = divider

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)

        self._dragging = None  # 'start', 'end', 'line'
        self._drag_offset = QPointF()

        self._update_pen()

    def _update_pen(self):
        pen = QPen(QColor(*COLOR_DIVIDER))
        pen.setWidthF(DIVIDER_LINE_WIDTH)
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        self.setPen(pen)

    def paint(self, painter: QPainter, option, widget=None):
        # 線を描画
        if self.isSelected():
            pen = QPen(QColor(*COLOR_DIVIDER_SELECTED))
            pen.setWidthF(DIVIDER_LINE_WIDTH_SELECTED)
            pen.setStyle(Qt.PenStyle.SolidLine)
            painter.setPen(pen)
        else:
            painter.setPen(self.pen())

        painter.drawLine(self.line())

        # 選択時はハンドルを描画
        if self.isSelected():
            self._draw_handles(painter)

    def _draw_handles(self, painter: QPainter):
        painter.setBrush(QBrush(QColor(*COLOR_HANDLE)))
        painter.setPen(QPen(QColor(*COLOR_HANDLE_BORDER)))

        s = HANDLE_SIZE
        line = self.line()

        # 始点ハンドル
        painter.drawEllipse(line.p1(), s, s)
        # 終点ハンドル
        painter.drawEllipse(line.p2(), s, s)

    def boundingRect(self) -> QRectF:
        extra = HANDLE_SIZE + 5
        return super().boundingRect().adjusted(-extra, -extra, extra, extra)

    def shape(self):
        from PyQt6.QtGui import QPainterPath, QPainterPathStroker
        path = QPainterPath()
        path.moveTo(self.line().p1())
        path.lineTo(self.line().p2())

        stroker = QPainterPathStroker()
        stroker.setWidth(DIVIDER_SNAP_RANGE)
        return stroker.createStroke(path)

    def _handle_at(self, pos: QPointF) -> str:
        line = self.line()
        s = HANDLE_SIZE + 5

        if (pos - line.p1()).manhattanLength() < s * 2:
            return 'start'
        if (pos - line.p2()).manhattanLength() < s * 2:
            return 'end'

        return None

    def hoverMoveEvent(self, event):
        if self.isSelected():
            handle = self._handle_at(event.pos())
            if handle:
                self.setCursor(Qt.CursorShape.CrossCursor)
            else:
                self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.isSelected():
            handle = self._handle_at(event.pos())
            if handle:
                self._dragging = handle
            else:
                self._dragging = 'line'
                self._drag_offset = event.pos()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging == 'start':
            new_pos = self._snap_to_edge(event.pos())
            self.setLine(QLineF(new_pos, self.line().p2()))
            self.update()
            return
        elif self._dragging == 'end':
            new_pos = self._snap_to_edge(event.pos())
            self.setLine(QLineF(self.line().p1(), new_pos))
            self.update()
            return
        elif self._dragging == 'line':
            delta = event.pos() - self._drag_offset
            line = self.line()
            new_line = QLineF(line.p1() + delta, line.p2() + delta)
            self.setLine(new_line)
            self._drag_offset = event.pos()
            self.update()
            return
        super().mouseMoveEvent(event)

    def _constrain_to_direction(self, new_pos: QPointF, fixed_pos: QPointF) -> QPointF:
        """水平または垂直方向に制約"""
        line = self.line()
        is_horizontal = abs(line.p1().y() - line.p2().y()) < abs(line.p1().x() - line.p2().x())

        if is_horizontal:
            # 水平線: Y座標を固定
            return QPointF(new_pos.x(), fixed_pos.y())
        else:
            # 垂直線: X座標を固定
            return QPointF(fixed_pos.x(), new_pos.y())

    def mouseReleaseEvent(self, event):
        if self._dragging:
            self._dragging = None
            self._sync_to_model()
        super().mouseReleaseEvent(event)

    def _snap_to_edge(self, pos: QPointF) -> QPointF:
        """ページの端にスナップ"""
        if not self.scene():
            return pos

        rect = self.scene().sceneRect()
        x, y = pos.x(), pos.y()

        # 左端
        if abs(x - rect.left()) < SNAP_DISTANCE:
            x = rect.left()
        # 右端
        if abs(x - rect.right()) < SNAP_DISTANCE:
            x = rect.right()
        # 上端
        if abs(y - rect.top()) < SNAP_DISTANCE:
            y = rect.top()
        # 下端
        if abs(y - rect.bottom()) < SNAP_DISTANCE:
            y = rect.bottom()

        return QPointF(x, y)

    def _sync_to_model(self):
        line = self.line()
        self.divider.x1 = line.p1().x()
        self.divider.y1 = line.p1().y()
        self.divider.x2 = line.p2().x()
        self.divider.y2 = line.p2().y()

        # シーンに変更を通知
        if self.scene():
            self.scene().divider_changed.emit()
