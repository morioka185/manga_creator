from typing import List, Tuple
from PyQt6.QtCore import QPointF, QLineF, QRectF, Qt
from PyQt6.QtGui import QPolygonF

from src.models.divider_line import DividerLine


class PanelCalculator:
    """分割線からコマ領域（ポリゴン）を計算する"""

    @staticmethod
    def calculate_panels(width: float, height: float,
                         dividers: List[DividerLine]) -> List[QPolygonF]:
        """
        ページを分割線で区切り、各コマ領域をポリゴンとして返す
        """
        if not dividers:
            # 分割線がない場合はページ全体が1つのコマ
            return [QPolygonF([
                QPointF(0, 0),
                QPointF(width, 0),
                QPointF(width, height),
                QPointF(0, height)
            ])]

        # ページの境界
        page_rect = QRectF(0, 0, width, height)

        # 線分のリストを作成し、境界まで延長
        lines = []
        gutter_widths = []
        for d in dividers:
            line = QLineF(d.x1, d.y1, d.x2, d.y2)
            lines.append(line)
            gutter_widths.append(d.gutter_width)

        # 各線を境界または他の線まで延長
        extended_lines = PanelCalculator._extend_lines(lines, page_rect)

        # すべての交点を計算
        points = PanelCalculator._collect_all_points(extended_lines, page_rect)

        # 領域を計算（シンプルな実装）
        panels = PanelCalculator._find_regions(extended_lines, page_rect, points)

        # 余白を適用（延長された線を使用）
        panels = PanelCalculator._apply_gutters(panels, extended_lines, gutter_widths, page_rect)

        return panels

    @staticmethod
    def _extend_lines(lines: List[QLineF], rect: QRectF) -> List[QLineF]:
        """各線を境界または他の線まで延長"""
        extended = []

        # ページ境界の4辺
        boundaries = [
            QLineF(rect.topLeft(), rect.topRight()),      # 上
            QLineF(rect.topRight(), rect.bottomRight()),  # 右
            QLineF(rect.bottomRight(), rect.bottomLeft()), # 下
            QLineF(rect.bottomLeft(), rect.topLeft())     # 左
        ]

        for i, line in enumerate(lines):
            # 他の線（自分以外）
            other_lines = [l for j, l in enumerate(lines) if j != i]

            # 両端を延長
            p1 = PanelCalculator._extend_point(line.p1(), line.p2(), line.p1(),
                                                boundaries + other_lines, rect)
            p2 = PanelCalculator._extend_point(line.p2(), line.p1(), line.p2(),
                                                boundaries + other_lines, rect)

            extended.append(QLineF(p1, p2))

        return extended

    @staticmethod
    def _extend_point(point: QPointF, other_point: QPointF, original: QPointF,
                      obstacles: List[QLineF], rect: QRectF) -> QPointF:
        """点を延長方向に、障害物にぶつかるまで延長"""
        # 端点が既に境界上にある場合は延長しない
        margin = 5.0
        on_boundary = (
            abs(point.x() - rect.left()) < margin or
            abs(point.x() - rect.right()) < margin or
            abs(point.y() - rect.top()) < margin or
            abs(point.y() - rect.bottom()) < margin
        )
        if on_boundary:
            return point

        # 延長方向ベクトル
        dx = point.x() - other_point.x()
        dy = point.y() - other_point.y()
        length = (dx * dx + dy * dy) ** 0.5

        if length < 0.001:
            return point

        # 単位ベクトル
        dx /= length
        dy /= length

        # 非常に長い線を作成（延長方向に）
        far_point = QPointF(point.x() + dx * 10000, point.y() + dy * 10000)
        extend_line = QLineF(point, far_point)

        # 最も近い交点を見つける
        closest_point = far_point
        closest_dist = float('inf')

        for obstacle in obstacles:
            intersection_type, intersect_point = extend_line.intersects(obstacle)
            if intersection_type == QLineF.IntersectionType.BoundedIntersection:
                dist = (intersect_point.x() - point.x()) ** 2 + (intersect_point.y() - point.y()) ** 2
                if dist > 0.1 and dist < closest_dist:  # 自分自身との交点を除く
                    closest_dist = dist
                    closest_point = intersect_point
            elif intersection_type == QLineF.IntersectionType.UnboundedIntersection:
                # 線の延長上に交点がある場合もチェック
                # 交点が延長方向にあるかチェック
                to_intersect_x = intersect_point.x() - point.x()
                to_intersect_y = intersect_point.y() - point.y()
                dot = to_intersect_x * dx + to_intersect_y * dy
                if dot > 0.1:  # 延長方向にある
                    dist = to_intersect_x ** 2 + to_intersect_y ** 2
                    if dist < closest_dist:
                        # 障害物の線分上にあるかチェック
                        if PanelCalculator._point_on_segment(intersect_point, obstacle):
                            closest_dist = dist
                            closest_point = intersect_point

        # ページ境界内に収める
        result_x = max(rect.left(), min(rect.right(), closest_point.x()))
        result_y = max(rect.top(), min(rect.bottom(), closest_point.y()))

        return QPointF(result_x, result_y)

    @staticmethod
    def _point_on_segment(point: QPointF, segment: QLineF) -> bool:
        """点が線分上にあるかチェック"""
        margin = 1.0
        min_x = min(segment.p1().x(), segment.p2().x()) - margin
        max_x = max(segment.p1().x(), segment.p2().x()) + margin
        min_y = min(segment.p1().y(), segment.p2().y()) - margin
        max_y = max(segment.p1().y(), segment.p2().y()) + margin

        return min_x <= point.x() <= max_x and min_y <= point.y() <= max_y

    @staticmethod
    def _collect_all_points(lines: List[QLineF], rect: QRectF) -> List[QPointF]:
        """すべての端点と交点を収集"""
        points = []

        # ページの4隅
        points.extend([
            QPointF(rect.left(), rect.top()),
            QPointF(rect.right(), rect.top()),
            QPointF(rect.right(), rect.bottom()),
            QPointF(rect.left(), rect.bottom())
        ])

        # 各線の端点
        for line in lines:
            points.append(line.p1())
            points.append(line.p2())

        # 線同士の交点
        for i, line1 in enumerate(lines):
            for line2 in lines[i + 1:]:
                intersection_type, point = line1.intersects(line2)
                if intersection_type == QLineF.IntersectionType.BoundedIntersection:
                    points.append(point)

        return points

    @staticmethod
    def _find_regions(lines: List[QLineF], rect: QRectF,
                      points: List[QPointF]) -> List[QPolygonF]:
        """
        分割線による領域を見つける
        シンプルな実装：グリッドベースのアプローチ
        """
        # 各線がページをどう分割するかを解析
        # X座標とY座標で分割点を収集
        x_coords = sorted(set([rect.left(), rect.right()] +
                              [p.x() for p in points
                               if rect.left() <= p.x() <= rect.right()]))
        y_coords = sorted(set([rect.top(), rect.bottom()] +
                              [p.y() for p in points
                               if rect.top() <= p.y() <= rect.bottom()]))

        panels = []

        # グリッドセルをチェック
        for i in range(len(x_coords) - 1):
            for j in range(len(y_coords) - 1):
                cell = QRectF(
                    x_coords[i], y_coords[j],
                    x_coords[i + 1] - x_coords[i],
                    y_coords[j + 1] - y_coords[j]
                )

                # このセルが分割線で切断されていないかチェック
                if not PanelCalculator._is_cell_cut(cell, lines):
                    polygon = QPolygonF([
                        cell.topLeft(),
                        cell.topRight(),
                        cell.bottomRight(),
                        cell.bottomLeft()
                    ])
                    panels.append(polygon)

        # セルを結合して大きな領域を作成
        merged = PanelCalculator._merge_adjacent_cells(panels, lines)

        return merged if merged else panels

    @staticmethod
    def _is_cell_cut(cell: QRectF, lines: List[QLineF]) -> bool:
        """セルが分割線で切断されているかチェック"""
        for line in lines:
            # 線がセルの内部を通過するかチェック
            if PanelCalculator._line_crosses_rect(line, cell):
                return True
        return False

    @staticmethod
    def _line_crosses_rect(line: QLineF, rect: QRectF) -> bool:
        """線が矩形の内部を横切るかチェック（境界上は除く）"""
        # セルを少し縮小して内部のみをチェック
        margin = 0.5
        inner_rect = QRectF(
            rect.left() + margin, rect.top() + margin,
            rect.width() - margin * 2, rect.height() - margin * 2
        )

        if inner_rect.width() <= 0 or inner_rect.height() <= 0:
            return False

        # 内側の矩形の4辺との交差をチェック
        edges = [
            QLineF(inner_rect.topLeft(), inner_rect.topRight()),
            QLineF(inner_rect.topRight(), inner_rect.bottomRight()),
            QLineF(inner_rect.bottomRight(), inner_rect.bottomLeft()),
            QLineF(inner_rect.bottomLeft(), inner_rect.topLeft())
        ]

        intersections = 0
        for edge in edges:
            intersection_type, _ = line.intersects(edge)
            if intersection_type == QLineF.IntersectionType.BoundedIntersection:
                intersections += 1

        # 2つ以上の辺と交差していれば、矩形を横切っている
        return intersections >= 2

    @staticmethod
    def _merge_adjacent_cells(cells: List[QPolygonF],
                               lines: List[QLineF]) -> List[QPolygonF]:
        """隣接するセルを結合（分割線がない境界で）"""
        if not cells or len(cells) <= 1:
            return cells

        # セルを矩形として扱う
        rects = [p.boundingRect() for p in cells]
        merged = [True] * len(cells)  # マージ対象かどうか

        # 結合を繰り返す
        changed = True
        while changed:
            changed = False
            for i in range(len(rects)):
                if not merged[i]:
                    continue
                for j in range(i + 1, len(rects)):
                    if not merged[j]:
                        continue

                    # 隣接チェックと結合
                    new_rect = PanelCalculator._try_merge_rects(
                        rects[i], rects[j], lines
                    )
                    if new_rect:
                        rects[i] = new_rect
                        merged[j] = False
                        changed = True
                        break
                if changed:
                    break

        # 結果を返す
        result = []
        for i, rect in enumerate(rects):
            if merged[i]:
                result.append(QPolygonF([
                    rect.topLeft(),
                    rect.topRight(),
                    rect.bottomRight(),
                    rect.bottomLeft()
                ]))

        return result

    @staticmethod
    def _try_merge_rects(rect1: QRectF, rect2: QRectF,
                          lines: List[QLineF]) -> QRectF:
        """2つの矩形を結合できる場合は結合して返す"""
        margin = 1.0

        # 水平方向に隣接（上下に並ぶ）
        if (abs(rect1.left() - rect2.left()) < margin and
            abs(rect1.right() - rect2.right()) < margin):

            # rect1が上、rect2が下
            if abs(rect1.bottom() - rect2.top()) < margin:
                edge = QLineF(rect1.bottomLeft(), rect1.bottomRight())
                if not PanelCalculator._edge_has_divider(edge, lines):
                    return QRectF(rect1.left(), rect1.top(),
                                  rect1.width(), rect1.height() + rect2.height())

            # rect2が上、rect1が下
            if abs(rect2.bottom() - rect1.top()) < margin:
                edge = QLineF(rect2.bottomLeft(), rect2.bottomRight())
                if not PanelCalculator._edge_has_divider(edge, lines):
                    return QRectF(rect2.left(), rect2.top(),
                                  rect2.width(), rect1.height() + rect2.height())

        # 垂直方向に隣接（左右に並ぶ）
        if (abs(rect1.top() - rect2.top()) < margin and
            abs(rect1.bottom() - rect2.bottom()) < margin):

            # rect1が左、rect2が右
            if abs(rect1.right() - rect2.left()) < margin:
                edge = QLineF(rect1.topRight(), rect1.bottomRight())
                if not PanelCalculator._edge_has_divider(edge, lines):
                    return QRectF(rect1.left(), rect1.top(),
                                  rect1.width() + rect2.width(), rect1.height())

            # rect2が左、rect1が右
            if abs(rect2.right() - rect1.left()) < margin:
                edge = QLineF(rect2.topRight(), rect2.bottomRight())
                if not PanelCalculator._edge_has_divider(edge, lines):
                    return QRectF(rect2.left(), rect2.top(),
                                  rect1.width() + rect2.width(), rect2.height())

        return None

    @staticmethod
    def _edge_has_divider(edge: QLineF, lines: List[QLineF]) -> bool:
        """辺上に分割線があるかチェック"""
        edge_margin = 2.0

        for line in lines:
            # 線が辺と重なっているかチェック
            # 線の両端点が辺の近くにあるか
            p1_on_edge = PanelCalculator._point_near_segment(line.p1(), edge, edge_margin)
            p2_on_edge = PanelCalculator._point_near_segment(line.p2(), edge, edge_margin)

            if p1_on_edge and p2_on_edge:
                return True

            # 辺の中点が線上にあるか
            mid = QPointF((edge.p1().x() + edge.p2().x()) / 2,
                         (edge.p1().y() + edge.p2().y()) / 2)
            if PanelCalculator._point_near_segment(mid, line, edge_margin):
                return True

        return False

    @staticmethod
    def _point_near_segment(point: QPointF, segment: QLineF, margin: float) -> bool:
        """点が線分の近くにあるかチェック"""
        dist = PanelCalculator._point_to_line_distance(point, segment)
        return dist < margin

    @staticmethod
    def _apply_gutters(panels: List[QPolygonF], lines: List[QLineF],
                       gutter_widths: List[float], page_rect: QRectF) -> List[QPolygonF]:
        """各コマに余白を適用"""
        result = []

        for panel in panels:
            rect = panel.boundingRect()

            # 各辺について、分割線に隣接しているかチェック
            left = rect.left()
            top = rect.top()
            right = rect.right()
            bottom = rect.bottom()

            for line, gutter in zip(lines, gutter_widths):
                half_gutter = gutter / 2

                # 水平線（Y座標で分割）
                if abs(line.p1().y() - line.p2().y()) < 1:  # ほぼ水平
                    line_y = (line.p1().y() + line.p2().y()) / 2
                    # コマの上辺がこの線に接している
                    if abs(top - line_y) < 1:
                        top += half_gutter
                    # コマの下辺がこの線に接している
                    if abs(bottom - line_y) < 1:
                        bottom -= half_gutter

                # 垂直線（X座標で分割）
                elif abs(line.p1().x() - line.p2().x()) < 1:  # ほぼ垂直
                    line_x = (line.p1().x() + line.p2().x()) / 2
                    # コマの左辺がこの線に接している
                    if abs(left - line_x) < 1:
                        left += half_gutter
                    # コマの右辺がこの線に接している
                    if abs(right - line_x) < 1:
                        right -= half_gutter

                # 斜め線の場合
                else:
                    # 簡易的に：コマの各頂点が線上にあるかチェック
                    for i in range(4):
                        corner = [
                            QPointF(rect.left(), rect.top()),
                            QPointF(rect.right(), rect.top()),
                            QPointF(rect.right(), rect.bottom()),
                            QPointF(rect.left(), rect.bottom())
                        ][i]

                        # 点と線の距離を計算
                        dist = PanelCalculator._point_to_line_distance(corner, line)
                        if dist < 1:
                            # この頂点は線上にある - 余白を適用
                            # 線に垂直な方向に移動
                            normal = PanelCalculator._line_normal(line)
                            if i == 0:  # 左上
                                left += half_gutter * abs(normal.x())
                                top += half_gutter * abs(normal.y())
                            elif i == 1:  # 右上
                                right -= half_gutter * abs(normal.x())
                                top += half_gutter * abs(normal.y())
                            elif i == 2:  # 右下
                                right -= half_gutter * abs(normal.x())
                                bottom -= half_gutter * abs(normal.y())
                            elif i == 3:  # 左下
                                left += half_gutter * abs(normal.x())
                                bottom -= half_gutter * abs(normal.y())

            # 新しいポリゴンを作成
            new_polygon = QPolygonF([
                QPointF(left, top),
                QPointF(right, top),
                QPointF(right, bottom),
                QPointF(left, bottom)
            ])
            result.append(new_polygon)

        return result

    @staticmethod
    def _point_to_line_distance(point: QPointF, line: QLineF) -> float:
        """点と線分の距離を計算"""
        x0, y0 = point.x(), point.y()
        x1, y1 = line.p1().x(), line.p1().y()
        x2, y2 = line.p2().x(), line.p2().y()

        dx = x2 - x1
        dy = y2 - y1
        length_sq = dx * dx + dy * dy

        if length_sq == 0:
            return ((x0 - x1) ** 2 + (y0 - y1) ** 2) ** 0.5

        t = max(0, min(1, ((x0 - x1) * dx + (y0 - y1) * dy) / length_sq))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy

        return ((x0 - proj_x) ** 2 + (y0 - proj_y) ** 2) ** 0.5

    @staticmethod
    def _line_normal(line: QLineF) -> QPointF:
        """線に垂直な単位ベクトルを返す"""
        dx = line.p2().x() - line.p1().x()
        dy = line.p2().y() - line.p1().y()
        length = (dx * dx + dy * dy) ** 0.5
        if length == 0:
            return QPointF(0, 0)
        return QPointF(-dy / length, dx / length)

    @staticmethod
    def get_panel_at_point(panels: List[QPolygonF], point: QPointF) -> int:
        """指定した点を含むパネルのインデックスを返す"""
        for i, panel in enumerate(panels):
            if panel.containsPoint(point, Qt.FillRule.OddEvenFill):
                return i
        return -1
