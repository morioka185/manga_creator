from PyQt6.QtWidgets import QGraphicsPolygonItem, QFileDialog, QMenu
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPen, QColor, QBrush, QPolygonF, QPixmap, QPainter, QTransform

from src.models.panel_image_data import PanelImageData
from src.utils.constants import (
    MIN_IMAGE_SCALE, MAX_IMAGE_SCALE, IMAGE_SCALE_STEP,
    COLOR_WHITE, COLOR_BLACK, DEFAULT_PANEL_BORDER_WIDTH
)


class PanelPolygonItem(QGraphicsPolygonItem):
    """コマ領域（ポリゴン）を表示するアイテム"""

    def __init__(self, polygon: QPolygonF, panel_id: str, parent=None):
        super().__init__(polygon, parent)
        self.panel_id = panel_id
        self._pixmap = None
        self._image_data = None  # PanelImageData

        # ドラッグ操作用
        self._dragging = False
        self._drag_start_pos = None
        self._drag_start_offset = None

        self.setPen(QPen(QColor(*COLOR_BLACK), DEFAULT_PANEL_BORDER_WIDTH))
        self.setBrush(QBrush(QColor(*COLOR_WHITE)))
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

    def set_image_with_generation_data(self, path: str, prompt: str, negative_prompt: str,
                                        seed: int, character_ids: list,
                                        batch_mode: bool = False,
                                        final_prompt: str = "",
                                        final_negative_prompt: str = ""):
        """生成情報付きで画像を設定（再生成用データを保持）"""
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            self._pixmap = pixmap
            self._image_data = PanelImageData(
                image_path=path,
                scale=1.0,
                offset_x=0.0,
                offset_y=0.0,
                generation_prompt=prompt,
                negative_prompt=negative_prompt,
                generation_seed=seed,
                character_ids=character_ids if character_ids else [],
                batch_mode=batch_mode,
                final_prompt=final_prompt,
                final_negative_prompt=final_negative_prompt
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

            # 左右反転
            if self._image_data.flip_horizontal:
                scaled = scaled.transformed(QTransform().scale(-1, 1))

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
            new_scale = min(MAX_IMAGE_SCALE, self._image_data.scale + IMAGE_SCALE_STEP)
        else:
            # 縮小
            new_scale = max(MIN_IMAGE_SCALE, self._image_data.scale - IMAGE_SCALE_STEP)

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

        # AI画像生成（常に表示）
        ai_generate_action = menu.addAction("AI画像生成...")

        # AI再生成（生成プロンプトがある場合のみ表示）
        ai_regenerate_action = None
        if self._image_data and self._image_data.generation_prompt:
            ai_regenerate_action = menu.addAction("同じ設定で再生成...")

        menu.addSeparator()

        if self._image_data:
            # 画像がある場合
            change_action = menu.addAction("画像を変更")
            clear_action = menu.addAction("画像をクリア")
            menu.addSeparator()
            flip_action = menu.addAction("左右反転")
            flip_action.setCheckable(True)
            flip_action.setChecked(self._image_data.flip_horizontal)
            reset_action = menu.addAction("位置・サイズをリセット")

            action = menu.exec(event.screenPos())

            if action == ai_generate_action:
                self._request_ai_generation()
            elif action == ai_regenerate_action:
                self._request_ai_regeneration()
            elif action == change_action:
                self._select_new_image()
            elif action == clear_action:
                self.clear_image()
            elif action == flip_action:
                self._image_data.flip_horizontal = not self._image_data.flip_horizontal
                self.update()
                if self.scene():
                    self.scene()._save_panel_image(self.panel_id, self._image_data)
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

            if action == ai_generate_action:
                self._request_ai_generation()
            elif action == add_action:
                self._select_new_image()

    def _request_ai_generation(self):
        """AI画像生成をリクエスト"""
        if self.scene():
            rect = self.polygon().boundingRect()
            width = int(rect.width())
            height = int(rect.height())
            self.scene().ai_generate_requested.emit(self.panel_id, width, height)

    def _request_ai_regeneration(self):
        """同じ設定でAI画像再生成をリクエスト"""
        if self.scene() and self._image_data:
            rect = self.polygon().boundingRect()
            width = int(rect.width())
            height = int(rect.height())
            settings = {
                'prompt': self._image_data.generation_prompt,
                'negative_prompt': self._image_data.negative_prompt,
                'seed': self._image_data.generation_seed,
                'character_ids': self._image_data.character_ids,
                # 一括生成モードの設定（再生成時に同じロジックを使う）
                'batch_mode': self._image_data.batch_mode,
                'final_prompt': self._image_data.final_prompt,
                'final_negative_prompt': self._image_data.final_negative_prompt
            }
            self.scene().ai_regenerate_requested.emit(self.panel_id, width, height, settings)

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
