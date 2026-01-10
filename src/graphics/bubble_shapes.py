import math
from PyQt6.QtGui import QPainterPath, QPolygonF
from PyQt6.QtCore import QPointF, QRectF

from src.utils.enums import BubbleType
from src.utils.constants import (
    ROUNDED_RECT_RADIUS, CLOUD_BUMP_COUNT, EXPLOSION_SPIKE_COUNT
)


class BubbleShapes:
    @staticmethod
    def create_path(bubble_type: BubbleType, rect: QRectF, tail_pos: QPointF) -> QPainterPath:
        if bubble_type == BubbleType.OVAL:
            return BubbleShapes.create_oval(rect, tail_pos)
        elif bubble_type == BubbleType.ROUNDED_RECT:
            return BubbleShapes.create_rounded_rect(rect, tail_pos)
        elif bubble_type == BubbleType.CLOUD:
            return BubbleShapes.create_cloud(rect, tail_pos)
        elif bubble_type == BubbleType.EXPLOSION:
            return BubbleShapes.create_explosion(rect)
        return QPainterPath()

    @staticmethod
    def create_oval(rect: QRectF, tail_pos: QPointF) -> QPainterPath:
        path = QPainterPath()
        path.addEllipse(rect)
        path = BubbleShapes._add_tail(path, rect, tail_pos)
        return path

    @staticmethod
    def create_rounded_rect(rect: QRectF, tail_pos: QPointF, radius: float = ROUNDED_RECT_RADIUS) -> QPainterPath:
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        path = BubbleShapes._add_tail(path, rect, tail_pos)
        return path

    @staticmethod
    def create_cloud(rect: QRectF, tail_pos: QPointF) -> QPainterPath:
        path = QPainterPath()
        cx, cy = rect.center().x(), rect.center().y()
        rx, ry = rect.width() / 2.5, rect.height() / 2.5

        num_bumps = CLOUD_BUMP_COUNT
        for i in range(num_bumps):
            angle = 2 * math.pi * i / num_bumps
            bump_x = cx + rx * math.cos(angle)
            bump_y = cy + ry * math.sin(angle)
            bump_radius = min(rect.width(), rect.height()) * 0.2
            ellipse_path = QPainterPath()
            ellipse_path.addEllipse(QPointF(bump_x, bump_y), bump_radius, bump_radius)
            path = path.united(ellipse_path)

        center_path = QPainterPath()
        center_path.addEllipse(rect.adjusted(rect.width()*0.15, rect.height()*0.15,
                                              -rect.width()*0.15, -rect.height()*0.15))
        path = path.united(center_path)

        if tail_pos and not tail_pos.isNull():
            small_bubble1 = QPainterPath()
            small_bubble2 = QPainterPath()
            small_bubble3 = QPainterPath()

            dx = tail_pos.x() - cx
            dy = tail_pos.y() - cy

            small_bubble1.addEllipse(QPointF(cx + dx * 0.5, cy + dy * 0.5), 12, 12)
            small_bubble2.addEllipse(QPointF(cx + dx * 0.7, cy + dy * 0.7), 8, 8)
            small_bubble3.addEllipse(QPointF(cx + dx * 0.85, cy + dy * 0.85), 5, 5)

            path = path.united(small_bubble1)
            path = path.united(small_bubble2)
            path = path.united(small_bubble3)

        return path

    @staticmethod
    def create_explosion(rect: QRectF) -> QPainterPath:
        path = QPainterPath()
        cx, cy = rect.center().x(), rect.center().y()
        rx, ry = rect.width() / 2, rect.height() / 2

        num_spikes = EXPLOSION_SPIKE_COUNT
        points = []
        for i in range(num_spikes * 2):
            angle = math.pi * i / num_spikes - math.pi / 2
            r = 1.0 if i % 2 == 0 else 0.6
            x = cx + rx * r * math.cos(angle)
            y = cy + ry * r * math.sin(angle)
            points.append(QPointF(x, y))

        polygon = QPolygonF(points)
        path.addPolygon(polygon)
        path.closeSubpath()
        return path

    @staticmethod
    def _add_tail(path: QPainterPath, rect: QRectF, tail_pos: QPointF) -> QPainterPath:
        if tail_pos is None or tail_pos.isNull():
            return path

        cx, cy = rect.center().x(), rect.center().y()

        angle = math.atan2(tail_pos.y() - cy, tail_pos.x() - cx)

        offset = 15
        base1 = QPointF(
            cx + rect.width() * 0.3 * math.cos(angle - 0.3),
            cy + rect.height() * 0.3 * math.sin(angle - 0.3)
        )
        base2 = QPointF(
            cx + rect.width() * 0.3 * math.cos(angle + 0.3),
            cy + rect.height() * 0.3 * math.sin(angle + 0.3)
        )

        tail_path = QPainterPath()
        tail_path.moveTo(base1)
        tail_path.lineTo(tail_pos)
        tail_path.lineTo(base2)
        tail_path.closeSubpath()

        return path.united(tail_path)
