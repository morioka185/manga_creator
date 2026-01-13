import math
from PyQt6.QtGui import QPainterPath, QPolygonF
from PyQt6.QtCore import QPointF, QRectF

from src.utils.enums import BubbleType
from src.utils.constants import (
    ROUNDED_RECT_RADIUS, CLOUD_BUMP_COUNT, EXPLOSION_SPIKE_COUNT
)


class BubbleShapes:
    @staticmethod
    def create_path(bubble_type: BubbleType, rect: QRectF, tail_pos: QPointF, corner_radius: float = ROUNDED_RECT_RADIUS) -> QPainterPath:
        if bubble_type == BubbleType.TEXT_ONLY:
            return QPainterPath()  # 形状なし
        elif bubble_type == BubbleType.OVAL:
            return BubbleShapes.create_oval(rect)  # 尻尾なし
        elif bubble_type == BubbleType.SPEECH:
            return BubbleShapes.create_speech(rect, tail_pos)  # 楕円＋尻尾
        elif bubble_type == BubbleType.RECTANGLE:
            return BubbleShapes.create_rectangle(rect, corner_radius)  # 角丸度調整可能
        elif bubble_type == BubbleType.CLOUD:
            return BubbleShapes.create_cloud(rect, tail_pos)
        elif bubble_type == BubbleType.EXPLOSION:
            return BubbleShapes.create_explosion(rect)
        return QPainterPath()

    @staticmethod
    def create_oval(rect: QRectF) -> QPainterPath:
        """楕円（尻尾なし）"""
        path = QPainterPath()
        path.addEllipse(rect)
        return path

    @staticmethod
    def create_speech(rect: QRectF, tail_pos: QPointF) -> QPainterPath:
        """吹き出し（楕円＋尻尾）"""
        path = QPainterPath()
        path.addEllipse(rect)
        path = BubbleShapes._add_tail(path, rect, tail_pos)
        return path

    @staticmethod
    def create_rectangle(rect: QRectF, corner_radius: float = 0) -> QPainterPath:
        """長方形（角丸度調整可能）"""
        path = QPainterPath()
        if corner_radius > 0:
            path.addRoundedRect(rect, corner_radius, corner_radius)
        else:
            path.addRect(rect)
        return path

    @staticmethod
    def create_cloud(rect: QRectF, tail_pos: QPointF) -> QPainterPath:
        """雲形（もくもく）吹き出し"""
        path = QPainterPath()
        cx, cy = rect.center().x(), rect.center().y()
        w, h = rect.width(), rect.height()

        # 内側の基本楕円（少し小さめ）
        inner_rect = rect.adjusted(w * 0.1, h * 0.1, -w * 0.1, -h * 0.1)
        path.addEllipse(inner_rect)

        # 周囲にバンプを配置（大きめの楕円を重ねる）
        num_bumps = CLOUD_BUMP_COUNT
        for i in range(num_bumps):
            angle = 2 * math.pi * i / num_bumps - math.pi / 2  # 上から開始
            # 楕円の縁に沿った位置
            edge_x = cx + (w * 0.35) * math.cos(angle)
            edge_y = cy + (h * 0.35) * math.sin(angle)

            # バンプのサイズを変化させる（より自然に）
            size_variation = 0.9 + 0.2 * math.sin(i * 1.5)
            bump_rx = w * 0.22 * size_variation
            bump_ry = h * 0.22 * size_variation

            bump_path = QPainterPath()
            bump_path.addEllipse(QPointF(edge_x, edge_y), bump_rx, bump_ry)
            path = path.united(bump_path)

        # 尻尾（小さな丸が連なる形）
        if tail_pos and not tail_pos.isNull():
            dx = tail_pos.x() - cx
            dy = tail_pos.y() - cy
            dist = math.sqrt(dx * dx + dy * dy)

            if dist > 0:
                # 3つの小さな丸を配置
                base_size = min(w, h) * 0.12
                positions = [0.55, 0.72, 0.88]
                sizes = [base_size, base_size * 0.65, base_size * 0.4]

                for pos, size in zip(positions, sizes):
                    bubble = QPainterPath()
                    bubble.addEllipse(QPointF(cx + dx * pos, cy + dy * pos), size, size)
                    path = path.united(bubble)

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
