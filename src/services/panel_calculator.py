from typing import List, Tuple, Optional
from PyQt6.QtCore import QPointF, QLineF, QRectF, Qt
from PyQt6.QtGui import QPolygonF

from src.models.divider_line import DividerLine


class PanelCalculator:
    """分割線からコマ領域（ポリゴン）を計算する - ポリゴン分割方式"""

    EPSILON = 1e-10
    POINT_TOLERANCE = 0.5
    MIN_AREA = 1.0

    @staticmethod
    def calculate_panels(width: float, height: float,
                         dividers: List[DividerLine],
                         margin: int = 0) -> List[QPolygonF]:
        """
        ページを分割線で区切り、各コマ領域をポリゴンとして返す
        """
        left = margin
        top = margin
        right = width - margin
        bottom = height - margin
        rect_w = right - left
        rect_h = bottom - top

        if rect_w <= 0 or rect_h <= 0:
            return []

        # 初期ポリゴン（マージン内の矩形）
        initial_poly = [
            {'x': left, 'y': top},
            {'x': right, 'y': top},
            {'x': right, 'y': bottom},
            {'x': left, 'y': bottom}
        ]
        polygons = [initial_poly]

        if not dividers:
            return [PanelCalculator._dict_poly_to_qpolygon(initial_poly)]

        # 既存の延長済み線を保持
        extended_lines = []

        for divider in dividers:
            p1 = {'x': divider.x1, 'y': divider.y1}
            p2 = {'x': divider.x2, 'y': divider.y2}

            # 線を境界・既存線まで延長
            extended = PanelCalculator._extend_line(
                p1, p2, left, top, rect_w, rect_h, extended_lines
            )

            if not extended:
                continue

            extended_lines.append(extended)

            # すべてのポリゴンを分割
            new_polygons = []
            for poly in polygons:
                split_result = PanelCalculator._split_polygon(
                    poly, extended['start'], extended['end']
                )
                new_polygons.extend(split_result)

            polygons = new_polygons

        # 面積でフィルタリングしてQPolygonFに変換
        result = []
        for poly in polygons:
            area = PanelCalculator._calc_area(poly)
            if area > PanelCalculator.MIN_AREA:
                result.append(PanelCalculator._dict_poly_to_qpolygon(poly))

        # 余白を適用
        if dividers and extended_lines:
            result = PanelCalculator._apply_gutters(
                result, extended_lines, dividers, QRectF(left, top, rect_w, rect_h)
            )

        # 日本のマンガ読み順（逆Z型：右から左、上から下）でソート
        result = PanelCalculator._sort_panels_manga_order(result)

        return result

    @staticmethod
    def _segment_intersection(p1: dict, p2: dict, p3: dict, p4: dict) -> Optional[dict]:
        """2つの線分の交点を計算"""
        x1, y1 = p1['x'], p1['y']
        x2, y2 = p2['x'], p2['y']
        x3, y3 = p3['x'], p3['y']
        x4, y4 = p4['x'], p4['y']

        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < PanelCalculator.EPSILON:
            return None

        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

        eps = PanelCalculator.EPSILON
        if -eps <= t <= 1 + eps and -eps <= u <= 1 + eps:
            return {
                'x': x1 + t * (x2 - x1),
                'y': y1 + t * (y2 - y1),
                't': t
            }
        return None

    @staticmethod
    def _ray_segment_intersection(origin: dict, direction: dict,
                                   p3: dict, p4: dict) -> Optional[dict]:
        """レイと線分の交点を計算"""
        ray_length = 10000
        x1, y1 = origin['x'], origin['y']
        x2 = origin['x'] + direction['x'] * ray_length
        y2 = origin['y'] + direction['y'] * ray_length
        x3, y3 = p3['x'], p3['y']
        x4, y4 = p4['x'], p4['y']

        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < PanelCalculator.EPSILON:
            return None

        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

        eps = PanelCalculator.EPSILON
        # t > 0 (前方), u は 0~1 (線分上)
        if t > 1e-6 and -eps <= u <= 1 + eps:
            return {
                'x': origin['x'] + direction['x'] * ray_length * t,
                'y': origin['y'] + direction['y'] * ray_length * t,
                'dist': t
            }
        return None

    @staticmethod
    def _point_on_segment(point: dict, seg_start: dict, seg_end: dict, tolerance: float = 5.0) -> bool:
        """点が線分上にあるかチェック"""
        # 線分の範囲内かチェック
        min_x = min(seg_start['x'], seg_end['x']) - tolerance
        max_x = max(seg_start['x'], seg_end['x']) + tolerance
        min_y = min(seg_start['y'], seg_end['y']) - tolerance
        max_y = max(seg_start['y'], seg_end['y']) + tolerance

        if not (min_x <= point['x'] <= max_x and min_y <= point['y'] <= max_y):
            return False

        # 点と線分の距離を計算
        dx = seg_end['x'] - seg_start['x']
        dy = seg_end['y'] - seg_start['y']
        length_sq = dx * dx + dy * dy

        if length_sq < 1:
            return False

        t = max(0, min(1, ((point['x'] - seg_start['x']) * dx + (point['y'] - seg_start['y']) * dy) / length_sq))
        proj_x = seg_start['x'] + t * dx
        proj_y = seg_start['y'] + t * dy
        dist = ((point['x'] - proj_x) ** 2 + (point['y'] - proj_y) ** 2) ** 0.5

        return dist < tolerance

    @staticmethod
    def _extend_line(p1: dict, p2: dict, left: float, top: float,
                     rect_w: float, rect_h: float,
                     existing_lines: List[dict]) -> Optional[dict]:
        """2点を通る直線を境界・既存線まで延長"""
        dx = p2['x'] - p1['x']
        dy = p2['y'] - p1['y']
        length = (dx * dx + dy * dy) ** 0.5

        if length < 1:
            return None

        dir_x = dx / length
        dir_y = dy / length

        right = left + rect_w
        bottom = top + rect_h

        # 境界の4辺
        boundaries = [
            ({'x': left, 'y': top}, {'x': right, 'y': top}),        # 上
            ({'x': right, 'y': top}, {'x': right, 'y': bottom}),    # 右
            ({'x': right, 'y': bottom}, {'x': left, 'y': bottom}),  # 下
            ({'x': left, 'y': bottom}, {'x': left, 'y': top})       # 左
        ]

        # p1が既に既存線上にあるかチェック
        p1_on_existing = False
        for line in existing_lines:
            if PanelCalculator._point_on_segment(p1, line['start'], line['end']):
                p1_on_existing = True
                break

        # p2が既に既存線上にあるかチェック
        p2_on_existing = False
        for line in existing_lines:
            if PanelCalculator._point_on_segment(p2, line['start'], line['end']):
                p2_on_existing = True
                break

        # 既存線も含める
        all_segments = list(boundaries)
        for line in existing_lines:
            all_segments.append((line['start'], line['end']))

        # p1から逆方向に延長（既存線上なら延長しない）
        start_point = {'x': p1['x'], 'y': p1['y']}
        if not p1_on_existing:
            min_dist_back = float('inf')
            for a, b in all_segments:
                hit = PanelCalculator._ray_segment_intersection(
                    p1, {'x': -dir_x, 'y': -dir_y}, a, b
                )
                if hit and hit['dist'] < min_dist_back:
                    min_dist_back = hit['dist']
                    start_point = {'x': hit['x'], 'y': hit['y']}

        # p2から順方向に延長（既存線上なら延長しない）
        end_point = {'x': p2['x'], 'y': p2['y']}
        if not p2_on_existing:
            min_dist_fwd = float('inf')
            for a, b in all_segments:
                hit = PanelCalculator._ray_segment_intersection(
                    p2, {'x': dir_x, 'y': dir_y}, a, b
                )
                if hit and hit['dist'] < min_dist_fwd:
                    min_dist_fwd = hit['dist']
                    end_point = {'x': hit['x'], 'y': hit['y']}

        return {'start': start_point, 'end': end_point}

    @staticmethod
    def _split_polygon(vertices: List[dict], line_start: dict,
                       line_end: dict) -> List[List[dict]]:
        """ポリゴンを線で2分割"""
        n = len(vertices)
        intersections = []

        for i in range(n):
            a = vertices[i]
            b = vertices[(i + 1) % n]
            hit = PanelCalculator._segment_intersection(a, b, line_start, line_end)

            if hit:
                # 重複チェック
                is_dup = any(
                    abs(inter['point']['x'] - hit['x']) < PanelCalculator.POINT_TOLERANCE and
                    abs(inter['point']['y'] - hit['y']) < PanelCalculator.POINT_TOLERANCE
                    for inter in intersections
                )
                if not is_dup:
                    intersections.append({
                        'point': {'x': hit['x'], 'y': hit['y']},
                        'edge': i,
                        't': hit['t']
                    })

        if len(intersections) < 2:
            return [vertices]

        # エッジ順でソート
        intersections.sort(key=lambda x: (x['edge'], x['t']))

        int1, int2 = intersections[0], intersections[1]

        # 2つのポリゴンを作成
        poly1 = []
        poly2 = []

        current = poly1
        for i in range(n):
            current.append({'x': vertices[i]['x'], 'y': vertices[i]['y']})

            if i == int1['edge']:
                current.append({'x': int1['point']['x'], 'y': int1['point']['y']})
                current = poly2
                poly2.append({'x': int1['point']['x'], 'y': int1['point']['y']})

            if i == int2['edge'] and current is poly2:
                current.append({'x': int2['point']['x'], 'y': int2['point']['y']})
                current = poly1
                poly1.append({'x': int2['point']['x'], 'y': int2['point']['y']})

        result = []
        if len(poly1) >= 3:
            result.append(poly1)
        if len(poly2) >= 3:
            result.append(poly2)

        return result if result else [vertices]

    @staticmethod
    def _calc_area(poly: List[dict]) -> float:
        """ポリゴンの面積を計算"""
        area = 0
        n = len(poly)
        for i in range(n):
            j = (i + 1) % n
            area += poly[i]['x'] * poly[j]['y'] - poly[j]['x'] * poly[i]['y']
        return abs(area / 2)

    @staticmethod
    def _dict_poly_to_qpolygon(poly: List[dict]) -> QPolygonF:
        """dict形式のポリゴンをQPolygonFに変換"""
        points = [QPointF(p['x'], p['y']) for p in poly]
        return QPolygonF(points)

    @staticmethod
    def _apply_gutters(panels: List[QPolygonF], extended_lines: List[dict],
                       dividers: List[DividerLine], page_rect: QRectF) -> List[QPolygonF]:
        """各コマに余白を適用（斜め線対応）- 辺をオフセットして再構築"""
        result = []
        line_tolerance = 5.0

        for panel in panels:
            # ポリゴンの頂点リストを取得
            vertices = []
            for i in range(panel.count()):
                pt = panel.at(i)
                vertices.append({'x': pt.x(), 'y': pt.y()})

            if len(vertices) < 3:
                result.append(panel)
                continue

            # 各辺のオフセット量を計算
            n = len(vertices)
            edge_offsets = [0.0] * n  # 各辺のオフセット量

            for i, ext_line in enumerate(extended_lines):
                if i >= len(dividers):
                    break

                gutter = dividers[i].gutter_width
                half_gutter = gutter / 2

                if half_gutter <= 0:
                    continue

                line_start = ext_line['start']
                line_end = ext_line['end']

                # 各辺が分割線上にあるかチェック
                for edge_idx in range(n):
                    v1 = vertices[edge_idx]
                    v2 = vertices[(edge_idx + 1) % n]

                    dist1 = PanelCalculator._point_to_line_distance(v1, line_start, line_end)
                    dist2 = PanelCalculator._point_to_line_distance(v2, line_start, line_end)

                    if dist1 < line_tolerance and dist2 < line_tolerance:
                        # この辺は分割線上にある
                        edge_offsets[edge_idx] = max(edge_offsets[edge_idx], half_gutter)

            # 辺をオフセットして新しいポリゴンを構築
            new_vertices = PanelCalculator._offset_polygon_edges(
                vertices, edge_offsets, page_rect, line_tolerance
            )

            # QPolygonFに変換
            new_polygon = QPolygonF([QPointF(v['x'], v['y']) for v in new_vertices])
            result.append(new_polygon)

        return result

    @staticmethod
    def _offset_polygon_edges(vertices: List[dict], edge_offsets: List[float],
                              page_rect: QRectF, tolerance: float) -> List[dict]:
        """各辺を指定量だけ内側にオフセットしてポリゴンを再構築"""
        n = len(vertices)
        if n < 3:
            return vertices

        # ページ境界
        page_left = page_rect.left()
        page_top = page_rect.top()
        page_right = page_rect.right()
        page_bottom = page_rect.bottom()

        # 各辺のオフセット後の直線を計算
        offset_lines = []
        for i in range(n):
            v1 = vertices[i]
            v2 = vertices[(i + 1) % n]
            offset = edge_offsets[i]

            # 辺の方向ベクトル
            dx = v2['x'] - v1['x']
            dy = v2['y'] - v1['y']
            length = (dx * dx + dy * dy) ** 0.5

            if length < 0.001:
                offset_lines.append((v1, v2))
                continue

            # 内向き法線（反時計回りのポリゴンを仮定）
            nx = -dy / length
            ny = dx / length

            # ポリゴンの重心を計算
            cx, cy = 0, 0
            for v in vertices:
                cx += v['x']
                cy += v['y']
            cx /= n
            cy /= n

            # 法線が内側を向くように調整
            mid_x = (v1['x'] + v2['x']) / 2
            mid_y = (v1['y'] + v2['y']) / 2
            to_center_x = cx - mid_x
            to_center_y = cy - mid_y
            dot = nx * to_center_x + ny * to_center_y
            if dot < 0:
                nx = -nx
                ny = -ny

            # 辺がページ境界上にあるかチェック
            on_boundary = PanelCalculator._edge_on_boundary(
                v1, v2, page_left, page_top, page_right, page_bottom, tolerance
            )

            if on_boundary:
                # 境界上の辺はオフセットしない
                offset_lines.append((v1, v2))
            else:
                # 辺をオフセット
                new_v1 = {'x': v1['x'] + nx * offset, 'y': v1['y'] + ny * offset}
                new_v2 = {'x': v2['x'] + nx * offset, 'y': v2['y'] + ny * offset}
                offset_lines.append((new_v1, new_v2))

        # オフセットされた辺の交点から新しい頂点を計算
        new_vertices = []
        for i in range(n):
            prev_line = offset_lines[(i - 1 + n) % n]
            curr_line = offset_lines[i]

            # 前の辺と現在の辺の交点を計算
            intersection = PanelCalculator._line_intersection(
                prev_line[0], prev_line[1], curr_line[0], curr_line[1]
            )

            if intersection:
                new_vertices.append(intersection)
            else:
                # 交点が見つからない場合は元の頂点を使用
                new_vertices.append({'x': vertices[i]['x'], 'y': vertices[i]['y']})

        return new_vertices

    @staticmethod
    def _edge_on_boundary(v1: dict, v2: dict, left: float, top: float,
                          right: float, bottom: float, tolerance: float) -> bool:
        """辺がページ境界上にあるかチェック"""
        # 両端点が同じ境界上にあるかチェック
        if abs(v1['x'] - left) < tolerance and abs(v2['x'] - left) < tolerance:
            return True
        if abs(v1['x'] - right) < tolerance and abs(v2['x'] - right) < tolerance:
            return True
        if abs(v1['y'] - top) < tolerance and abs(v2['y'] - top) < tolerance:
            return True
        if abs(v1['y'] - bottom) < tolerance and abs(v2['y'] - bottom) < tolerance:
            return True
        return False

    @staticmethod
    def _line_intersection(p1: dict, p2: dict, p3: dict, p4: dict) -> Optional[dict]:
        """2つの直線（無限延長）の交点を計算"""
        x1, y1 = p1['x'], p1['y']
        x2, y2 = p2['x'], p2['y']
        x3, y3 = p3['x'], p3['y']
        x4, y4 = p4['x'], p4['y']

        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 1e-10:
            return None

        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom

        return {
            'x': x1 + t * (x2 - x1),
            'y': y1 + t * (y2 - y1)
        }

    @staticmethod
    def _point_to_line_distance(point: dict, line_start: dict, line_end: dict) -> float:
        """点と線分の距離を計算"""
        px, py = point['x'], point['y']
        x1, y1 = line_start['x'], line_start['y']
        x2, y2 = line_end['x'], line_end['y']

        dx = x2 - x1
        dy = y2 - y1
        length_sq = dx * dx + dy * dy

        if length_sq < 1:
            return ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5

        # 線分上の最近点のパラメータ
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / length_sq))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy

        return ((px - proj_x) ** 2 + (py - proj_y) ** 2) ** 0.5

    @staticmethod
    def get_panel_at_point(panels: List[QPolygonF], point: QPointF) -> int:
        """指定した点を含むパネルのインデックスを返す"""
        for i, panel in enumerate(panels):
            if panel.containsPoint(point, Qt.FillRule.OddEvenFill):
                return i
        return -1

    @staticmethod
    def _sort_panels_manga_order(panels: List[QPolygonF]) -> List[QPolygonF]:
        """
        日本のマンガ読み順（逆Z型）でパネルをソート
        - 右上から開始
        - 同じ行では右から左へ
        - 行が終わったら下の行へ
        """
        if len(panels) <= 1:
            return panels

        # 各パネルの中心座標とバウンディングボックスを取得
        panel_data = []
        for i, panel in enumerate(panels):
            rect = panel.boundingRect()
            panel_data.append({
                'index': i,
                'panel': panel,
                'cx': rect.center().x(),
                'cy': rect.center().y(),
                'top': rect.top(),
                'bottom': rect.bottom()
            })

        # Y座標でグループ化（同じ「行」を識別）
        # パネルの高さの30%を許容誤差として使用
        rows = []
        used = [False] * len(panel_data)

        # 上から順にパネルをグループ化
        sorted_by_top = sorted(panel_data, key=lambda p: p['top'])

        for p in sorted_by_top:
            if used[p['index']]:
                continue

            # 新しい行を開始
            row = [p]
            used[p['index']] = True
            row_center_y = p['cy']

            # このパネルと同じ行にある他のパネルを探す
            for other in sorted_by_top:
                if used[other['index']]:
                    continue

                # Y座標の中心が近いものを同じ行とみなす
                # 許容誤差: パネル高さの40%
                height = p['bottom'] - p['top']
                tolerance = height * 0.4

                if abs(other['cy'] - row_center_y) < tolerance:
                    row.append(other)
                    used[other['index']] = True

            rows.append(row)

        # 各行内でX座標の降順（右から左）でソート
        sorted_panels = []
        for row in rows:
            row_sorted = sorted(row, key=lambda p: -p['cx'])  # 降順（右から左）
            for p in row_sorted:
                sorted_panels.append(p['panel'])

        return sorted_panels
