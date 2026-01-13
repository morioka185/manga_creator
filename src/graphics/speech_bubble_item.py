import math

from PyQt6.QtWidgets import QGraphicsItem, QGraphicsTextItem, QInputDialog, QMenu
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPen, QBrush, QColor, QPainter, QFont, QFontMetrics, QTextDocument, QTextOption

from src.models.speech_bubble import SpeechBubble
from src.graphics.bubble_shapes import BubbleShapes
from src.utils.enums import BubbleType
from src.utils.constants import (
    HANDLE_SIZE, MIN_PANEL_SIZE, TAIL_HANDLE_SIZE, ROTATION_HANDLE_OFFSET,
    BUBBLE_BOUNDING_MARGIN, BUBBLE_TEXT_PADDING, BUBBLE_BORDER_WIDTH,
    COLOR_WHITE, COLOR_BLACK, COLOR_HANDLE, COLOR_HANDLE_BORDER, COLOR_ROTATION_HANDLE
)

ROTATION_HANDLE_SIZE = 8


class SpeechBubbleGraphicsItem(QGraphicsItem):
    # 縦書き時に回転させる文字（括弧など）
    ROTATE_CHARS = '（）「」『』【】〈〉《》｛｝［］(){}[]<>'
    # 縦書き時に位置調整する句読点
    PUNCT_CHARS = '、。，．・：；'

    def __init__(self, bubble: SpeechBubble, parent=None):
        super().__init__(parent)
        self.bubble = bubble
        self.setPos(bubble.x, bubble.y)

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton)

        # 回転の原点を中心に設定
        self.setTransformOriginPoint(bubble.width / 2, bubble.height / 2)
        self.setRotation(bubble.rotation)

        self._resizing = False
        self._resize_handle = None
        self._start_rect = None
        self._start_scene_pos = None
        self._start_item_pos = None
        self._dragging_tail = False
        self._rotating = False
        self._rotation_start_angle = 0

    def _has_tail(self) -> bool:
        """尻尾を持つタイプかどうか"""
        return self.bubble.bubble_type in (BubbleType.SPEECH, BubbleType.CLOUD)

    def boundingRect(self) -> QRectF:
        margin = BUBBLE_BOUNDING_MARGIN
        # 基本の吹き出し領域
        rect = QRectF(-margin, -margin,
                      self.bubble.width + margin * 2,
                      self.bubble.height + margin * 2)

        # 回転ハンドルの領域を含める
        rotation_handle_rect = QRectF(
            self.bubble.width / 2 - ROTATION_HANDLE_SIZE,
            -ROTATION_HANDLE_OFFSET - ROTATION_HANDLE_SIZE,
            ROTATION_HANDLE_SIZE * 2,
            ROTATION_HANDLE_SIZE * 2
        )
        rect = rect.united(rotation_handle_rect)

        # 尻尾の位置も含める（残像防止）
        if self._has_tail():
            tail_rect = QRectF(
                self.bubble.tail_x - TAIL_HANDLE_SIZE,
                self.bubble.tail_y - TAIL_HANDLE_SIZE,
                TAIL_HANDLE_SIZE * 2,
                TAIL_HANDLE_SIZE * 2
            )
            rect = rect.united(tail_rect)
        return rect

    def _get_text_rect(self, rect: QRectF) -> QRectF:
        """バブルタイプに応じたテキスト描画領域を計算

        楕円形の場合、内接矩形を計算してテキストがカーブにかからないようにする
        """
        bubble_type = self.bubble.bubble_type

        if bubble_type == BubbleType.TEXT_ONLY:
            # 文字のみの場合はパディングなし
            return rect

        if bubble_type in (BubbleType.OVAL, BubbleType.SPEECH):
            # 楕円に内接する最大の長方形は 1/√2 倍
            inscribed_factor = 1.0 / math.sqrt(2)  # ≈ 0.707

            margin_x = rect.width() * (1 - inscribed_factor) / 2
            margin_y = rect.height() * (1 - inscribed_factor) / 2
            # 最小パディングも確保
            margin_x = max(margin_x, BUBBLE_TEXT_PADDING)
            margin_y = max(margin_y, BUBBLE_TEXT_PADDING)
            return rect.adjusted(margin_x, margin_y, -margin_x, -margin_y)

        elif bubble_type == BubbleType.CLOUD:
            # 雲形は中央部分が rect.adjusted(15%, 15%, -15%, -15%) で描画されている
            cloud_margin = 0.18  # 雲のバンプを考慮してやや大きめ
            margin_x = rect.width() * cloud_margin + BUBBLE_TEXT_PADDING
            margin_y = rect.height() * cloud_margin + BUBBLE_TEXT_PADDING
            return rect.adjusted(margin_x, margin_y, -margin_x, -margin_y)

        elif bubble_type == BubbleType.EXPLOSION:
            # 爆発形は内側の60%部分に収める (スパイクの内側)
            inner_ratio = 0.35  # (1 - 0.6) / 2 + padding
            margin_x = rect.width() * inner_ratio
            margin_y = rect.height() * inner_ratio
            return rect.adjusted(margin_x, margin_y, -margin_x, -margin_y)

        else:  # RECTANGLE
            # 通常のパディング
            padding = BUBBLE_TEXT_PADDING
            return rect.adjusted(padding, padding, -padding, -padding)

    def paint(self, painter: QPainter, option, widget=None):
        rect = QRectF(0, 0, self.bubble.width, self.bubble.height)
        tail_pos = QPointF(self.bubble.tail_x, self.bubble.tail_y) if self._has_tail() else QPointF()

        # TEXT_ONLY以外は形状を描画
        if self.bubble.bubble_type != BubbleType.TEXT_ONLY:
            path = BubbleShapes.create_path(
                self.bubble.bubble_type, rect, tail_pos, self.bubble.corner_radius
            )
            painter.setBrush(QBrush(QColor(*COLOR_WHITE)))
            painter.setPen(QPen(QColor(*COLOR_BLACK), BUBBLE_BORDER_WIDTH))
            painter.drawPath(path)

        # テキストを描画
        font = QFont(self.bubble.font_family, self.bubble.font_size)
        painter.setFont(font)

        # TEXT_ONLYの場合はcolor属性を使用、それ以外は黒
        if self.bubble.bubble_type == BubbleType.TEXT_ONLY:
            text_color = QColor(self.bubble.color)
        else:
            text_color = QColor(*COLOR_BLACK)
        painter.setPen(QPen(text_color))

        # バブルタイプに応じたテキスト領域を計算
        text_rect = self._get_text_rect(rect)

        if self.bubble.vertical:
            self._draw_vertical_text(painter, text_rect, self.bubble.text, font)
        else:
            self._draw_horizontal_text(painter, text_rect, self.bubble.text, font)

        if self.isSelected():
            self._draw_handles(painter, rect)

    def _draw_vertical_text(self, painter: QPainter, rect: QRectF, text: str, font: QFont):
        """縦書きテキストを描画（自動フォントサイズ調整）"""
        if not text:
            return

        # auto_font_size がONの場合のみフォントサイズを自動調整
        if self.bubble.auto_font_size:
            fitting_size = self._calculate_fitting_font_size(text, rect, font, vertical=True)
            adjusted_font = QFont(font.family(), fitting_size)
        else:
            adjusted_font = QFont(font.family(), font.pointSize())

        fm = QFontMetrics(adjusted_font)
        char_height = fm.height()
        # 日本語文字は全角（正方形）なので、高さと同じ幅を使用
        char_width = fm.height()
        line_spacing = char_width * 1.2  # 行間（縦書きでは横方向）

        # 改行で分割
        lines = text.split('\n')

        # 全体の幅を計算（右から左に配置）
        total_width = len(lines) * line_spacing
        start_x = rect.center().x() + total_width / 2 - line_spacing / 2

        painter.setFont(adjusted_font)

        for line_idx, line in enumerate(lines):
            # 各行のX位置（右から左）
            x = start_x - line_idx * line_spacing

            # 行の高さを計算して中央揃え
            line_height = len(line) * char_height
            start_y = rect.center().y() - line_height / 2 + char_height / 2

            for char_idx, char in enumerate(line):
                y = start_y + char_idx * char_height

                # 括弧類は90度回転
                if char in self.ROTATE_CHARS:
                    painter.save()
                    painter.translate(x, y)
                    painter.rotate(90)
                    painter.drawText(QPointF(-char_width/2, char_height/4), char)
                    painter.restore()
                # 句読点は右上に配置
                elif char in self.PUNCT_CHARS:
                    painter.drawText(QPointF(x + char_width/3, y - char_height/3), char)
                else:
                    # 通常の文字は中央に配置
                    char_rect = QRectF(x - char_width/2, y - char_height/2, char_width, char_height)
                    painter.drawText(char_rect, Qt.AlignmentFlag.AlignCenter, char)

    def _calculate_fitting_font_size(self, text: str, rect: QRectF, base_font: QFont, vertical: bool = False) -> int:
        """テキストが領域に収まるフォントサイズを計算"""
        font_size = base_font.pointSize()
        min_font_size = 6  # 最小フォントサイズ

        while font_size >= min_font_size:
            test_font = QFont(base_font.family(), font_size)

            if vertical:
                # 縦書きの場合
                fm = QFontMetrics(test_font)
                char_height = fm.height()
                char_width = fm.height()
                line_spacing = char_width * 1.2

                lines = text.split('\n')
                total_width = len(lines) * line_spacing
                max_line_height = max(len(line) * char_height for line in lines) if lines else 0

                if total_width <= rect.width() and max_line_height <= rect.height():
                    return font_size
            else:
                # 横書きの場合
                doc = QTextDocument()
                doc.setDefaultFont(test_font)
                doc.setPlainText(text)
                doc.setTextWidth(rect.width())

                text_option = QTextOption(Qt.AlignmentFlag.AlignCenter)
                text_option.setWrapMode(QTextOption.WrapMode.WordWrap)
                doc.setDefaultTextOption(text_option)

                doc_size = doc.size()
                if doc_size.height() <= rect.height():
                    return font_size

            font_size -= 1

        return min_font_size

    def _draw_horizontal_text(self, painter: QPainter, rect: QRectF, text: str, font: QFont):
        """横書きテキストを描画（自動フォントサイズ調整）"""
        if not text:
            return

        # auto_font_size がONの場合のみフォントサイズを自動調整
        if self.bubble.auto_font_size:
            fitting_size = self._calculate_fitting_font_size(text, rect, font, vertical=False)
            adjusted_font = QFont(font.family(), fitting_size)
        else:
            adjusted_font = QFont(font.family(), font.pointSize())

        doc = QTextDocument()
        doc.setDefaultFont(adjusted_font)
        doc.setPlainText(text)
        doc.setTextWidth(rect.width())

        # テキストを中央揃えに設定
        text_option = QTextOption(Qt.AlignmentFlag.AlignCenter)
        text_option.setWrapMode(QTextOption.WrapMode.WordWrap)
        doc.setDefaultTextOption(text_option)

        # テキストのサイズを取得
        doc_size = doc.size()

        # 中央配置のための位置計算
        x = rect.left() + (rect.width() - doc_size.width()) / 2
        y = rect.top() + (rect.height() - doc_size.height()) / 2

        painter.save()
        painter.translate(x, y)
        doc.drawContents(painter)
        painter.restore()

    def _draw_handles(self, painter: QPainter, rect: QRectF):
        # リサイズハンドル
        handles = self._get_handles(rect)
        painter.setBrush(QBrush(QColor(*COLOR_HANDLE)))
        painter.setPen(QPen(QColor(*COLOR_HANDLE_BORDER)))
        for handle_rect in handles.values():
            painter.drawRect(handle_rect)

        # 尻尾ハンドル（尻尾を持つタイプのみ）
        if self._has_tail():
            tail_pos = QPointF(self.bubble.tail_x, self.bubble.tail_y)
            if not tail_pos.isNull():
                painter.setBrush(QBrush(QColor(*COLOR_ROTATION_HANDLE)))
                painter.drawEllipse(tail_pos, TAIL_HANDLE_SIZE, TAIL_HANDLE_SIZE)

        # 回転ハンドル
        rot_pos = self._get_rotation_handle_pos(rect)
        painter.setBrush(QBrush(QColor(*COLOR_ROTATION_HANDLE)))
        painter.setPen(QPen(QColor(*COLOR_HANDLE_BORDER)))
        painter.drawEllipse(rot_pos, ROTATION_HANDLE_SIZE, ROTATION_HANDLE_SIZE)
        # 中心と回転ハンドルを結ぶ線
        painter.drawLine(QPointF(rect.center().x(), rect.top()), rot_pos)

    def _get_rotation_handle_pos(self, rect: QRectF) -> QPointF:
        """回転ハンドルの位置を取得"""
        return QPointF(rect.center().x(), -ROTATION_HANDLE_OFFSET)

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
        if not self._has_tail():
            return False
        tail_pos = QPointF(self.bubble.tail_x, self.bubble.tail_y)
        return (pos - tail_pos).manhattanLength() < TAIL_HANDLE_SIZE * 2

    def _is_near_rotation_handle(self, pos) -> bool:
        rect = QRectF(0, 0, self.bubble.width, self.bubble.height)
        rot_pos = self._get_rotation_handle_pos(rect)
        return (pos - rot_pos).manhattanLength() < ROTATION_HANDLE_SIZE * 2

    def hoverMoveEvent(self, event):
        handle = self._handle_at(event.pos())
        if handle:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif self.isSelected() and self._is_near_tail(event.pos()):
            self.setCursor(Qt.CursorShape.CrossCursor)
        elif self.isSelected() and self._is_near_rotation_handle(event.pos()):
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event)
            return
        if event.button() == Qt.MouseButton.LeftButton:
            # 回転ハンドル
            if self.isSelected() and self._is_near_rotation_handle(event.pos()):
                self._rotating = True
                center = QPointF(self.bubble.width / 2, self.bubble.height / 2)
                self._rotation_start_angle = math.degrees(
                    math.atan2(event.pos().y() - center.y(), event.pos().x() - center.x())
                )
                return
            # 尻尾ハンドル
            if self.isSelected() and self._is_near_tail(event.pos()):
                self._dragging_tail = True
                return
            # リサイズハンドル
            handle = self._handle_at(event.pos())
            if handle:
                self._resizing = True
                self._resize_handle = handle
                self._start_rect = QRectF(0, 0, self.bubble.width, self.bubble.height)
                self._start_scene_pos = event.scenePos()
                self._start_item_pos = self.pos()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._rotating:
            center = QPointF(self.bubble.width / 2, self.bubble.height / 2)
            current_angle = math.degrees(
                math.atan2(event.pos().y() - center.y(), event.pos().x() - center.x())
            )
            delta_angle = current_angle - self._rotation_start_angle
            new_rotation = self.bubble.rotation + delta_angle
            # -180〜180の範囲に正規化
            while new_rotation > 180:
                new_rotation -= 360
            while new_rotation < -180:
                new_rotation += 360
            self.bubble.rotation = new_rotation
            self.setRotation(new_rotation)
            self._rotation_start_angle = current_angle
            return
        if self._dragging_tail:
            # 残像防止: 形状変更前に呼び出す
            self.prepareGeometryChange()
            self.bubble.tail_x = event.pos().x()
            self.bubble.tail_y = event.pos().y()
            self.update()
            return
        if self._resizing:
            delta = event.scenePos() - self._start_scene_pos
            rect = QRectF(self._start_rect)

            if 'right' in self._resize_handle:
                new_w = rect.width() + delta.x()
                if new_w >= MIN_PANEL_SIZE:
                    self.bubble.width = new_w
            if 'left' in self._resize_handle:
                new_w = rect.width() - delta.x()
                if new_w >= MIN_PANEL_SIZE:
                    self.bubble.width = new_w
                    self.setX(self._start_item_pos.x() + delta.x())
            if 'bottom' in self._resize_handle:
                new_h = rect.height() + delta.y()
                if new_h >= MIN_PANEL_SIZE:
                    self.bubble.height = new_h
            if 'top' in self._resize_handle:
                new_h = rect.height() - delta.y()
                if new_h >= MIN_PANEL_SIZE:
                    self.bubble.height = new_h
                    self.setY(self._start_item_pos.y() + delta.y())

            # 回転の原点を更新
            self.setTransformOriginPoint(self.bubble.width / 2, self.bubble.height / 2)
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
        if self._rotating:
            self._rotating = False
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

    def _show_context_menu(self, event):
        """右クリックメニューを表示"""
        menu = QMenu()

        # 吹き出しの種類サブメニュー
        type_menu = menu.addMenu("吹き出しの種類")

        type_names = {
            BubbleType.TEXT_ONLY: "文字のみ",
            BubbleType.OVAL: "楕円",
            BubbleType.SPEECH: "吹き出し",
            BubbleType.RECTANGLE: "長方形",
            BubbleType.CLOUD: "もくもく",
            BubbleType.EXPLOSION: "爆発",
        }

        type_actions = {}
        for bubble_type, name in type_names.items():
            action = type_menu.addAction(name)
            action.setCheckable(True)
            action.setChecked(self.bubble.bubble_type == bubble_type)
            type_actions[action] = bubble_type

        menu.addSeparator()

        # 縦書き/横書き
        vertical_action = menu.addAction("縦書き")
        vertical_action.setCheckable(True)
        vertical_action.setChecked(self.bubble.vertical)

        # サイズ追従
        auto_size_action = menu.addAction("サイズに追従")
        auto_size_action.setCheckable(True)
        auto_size_action.setChecked(self.bubble.auto_font_size)

        menu.addSeparator()

        # セリフ編集
        edit_action = menu.addAction("セリフを編集...")

        action = menu.exec(event.screenPos())

        if action in type_actions:
            new_type = type_actions[action]
            if self.bubble.bubble_type != new_type:
                self.bubble.bubble_type = new_type
                self.prepareGeometryChange()
                self.update()
        elif action == vertical_action:
            self.bubble.vertical = not self.bubble.vertical
            self.update()
        elif action == auto_size_action:
            self.bubble.auto_font_size = not self.bubble.auto_font_size
            self.update()
        elif action == edit_action:
            text, ok = QInputDialog.getMultiLineText(
                None, "セリフ入力", "テキストを入力:", self.bubble.text
            )
            if ok:
                self.bubble.text = text
                self.update()
