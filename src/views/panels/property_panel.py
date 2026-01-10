from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QSpinBox,
                               QHBoxLayout, QGroupBox, QPushButton,
                               QFontComboBox, QColorDialog, QFrame,
                               QDoubleSpinBox, QFileDialog, QCheckBox,
                               QPlainTextEdit)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor

from src.graphics.speech_bubble_item import SpeechBubbleGraphicsItem
from src.graphics.text_item import TextGraphicsItem
from src.graphics.divider_line_item import DividerLineItem
from src.utils.constants import (
    DEFAULT_MARGIN, PANEL_MARGIN,
    SPINBOX_POSITION_MIN, SPINBOX_POSITION_MAX,
    SPINBOX_SIZE_MIN, SPINBOX_SIZE_MAX,
    SPINBOX_MARGIN_MAX, SPINBOX_GUTTER_MAX, SPINBOX_GUTTER_STEP,
    SPINBOX_ROTATION_MIN, SPINBOX_ROTATION_MAX,
    MIN_IMAGE_SCALE, MAX_IMAGE_SCALE, IMAGE_SCALE_STEP,
    MIN_FONT_SIZE, MAX_FONT_SIZE, DEFAULT_FONT_SIZE
)


class PropertyPanel(QWidget):
    property_changed = pyqtSignal()
    page_margin_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_item = None
        self._current_page = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(PANEL_MARGIN, PANEL_MARGIN, PANEL_MARGIN, PANEL_MARGIN)

        title = QLabel("プロパティ")
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)

        # ページ設定グループ
        self._page_group = QGroupBox("ページ設定")
        page_layout = QVBoxLayout(self._page_group)
        margin_row = QHBoxLayout()
        margin_row.addWidget(QLabel("外枠幅:"))
        self._margin_spin = QSpinBox()
        self._margin_spin.setRange(0, SPINBOX_MARGIN_MAX)
        self._margin_spin.setValue(DEFAULT_MARGIN)
        self._margin_spin.setSuffix(" px")
        self._margin_spin.valueChanged.connect(self._on_margin_changed)
        margin_row.addWidget(self._margin_spin)
        page_layout.addLayout(margin_row)
        layout.addWidget(self._page_group)

        pos_group = QGroupBox("位置")
        pos_layout = QHBoxLayout(pos_group)
        pos_layout.addWidget(QLabel("X:"))
        self._x_spin = QSpinBox()
        self._x_spin.setRange(SPINBOX_POSITION_MIN, SPINBOX_POSITION_MAX)
        self._x_spin.valueChanged.connect(self._on_position_changed)
        pos_layout.addWidget(self._x_spin)
        pos_layout.addWidget(QLabel("Y:"))
        self._y_spin = QSpinBox()
        self._y_spin.setRange(SPINBOX_POSITION_MIN, SPINBOX_POSITION_MAX)
        self._y_spin.valueChanged.connect(self._on_position_changed)
        pos_layout.addWidget(self._y_spin)
        layout.addWidget(pos_group)

        size_group = QGroupBox("サイズ")
        size_layout = QHBoxLayout(size_group)
        size_layout.addWidget(QLabel("W:"))
        self._w_spin = QSpinBox()
        self._w_spin.setRange(SPINBOX_SIZE_MIN, SPINBOX_SIZE_MAX)
        self._w_spin.valueChanged.connect(self._on_size_changed)
        size_layout.addWidget(self._w_spin)
        size_layout.addWidget(QLabel("H:"))
        self._h_spin = QSpinBox()
        self._h_spin.setRange(SPINBOX_SIZE_MIN, SPINBOX_SIZE_MAX)
        self._h_spin.valueChanged.connect(self._on_size_changed)
        size_layout.addWidget(self._h_spin)
        layout.addWidget(size_group)

        self._rotation_group = QGroupBox("回転")
        rot_layout = QHBoxLayout(self._rotation_group)
        rot_layout.addWidget(QLabel("角度:"))
        self._rotation_spin = QSpinBox()
        self._rotation_spin.setRange(SPINBOX_ROTATION_MIN, SPINBOX_ROTATION_MAX)
        self._rotation_spin.setSuffix("°")
        self._rotation_spin.valueChanged.connect(self._on_rotation_changed)
        rot_layout.addWidget(self._rotation_spin)
        layout.addWidget(self._rotation_group)
        self._rotation_group.hide()

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(separator)

        self._image_group = QGroupBox("コマ画像")
        image_layout = QVBoxLayout(self._image_group)
        self._image_btn = QPushButton("画像を選択...")
        self._image_btn.clicked.connect(self._on_select_image)
        image_layout.addWidget(self._image_btn)

        # スケール設定
        scale_row = QHBoxLayout()
        scale_row.addWidget(QLabel("拡大率:"))
        self._scale_spin = QDoubleSpinBox()
        self._scale_spin.setRange(MIN_IMAGE_SCALE, MAX_IMAGE_SCALE)
        self._scale_spin.setSingleStep(IMAGE_SCALE_STEP)
        self._scale_spin.setValue(MIN_IMAGE_SCALE)
        self._scale_spin.valueChanged.connect(self._on_scale_changed)
        scale_row.addWidget(self._scale_spin)
        image_layout.addLayout(scale_row)

        # リセットボタン
        self._reset_btn = QPushButton("位置・サイズをリセット")
        self._reset_btn.clicked.connect(self._on_reset_image)
        image_layout.addWidget(self._reset_btn)

        self._clear_btn = QPushButton("画像をクリア")
        self._clear_btn.clicked.connect(self._on_clear_image)
        image_layout.addWidget(self._clear_btn)
        layout.addWidget(self._image_group)
        self._image_group.hide()

        # 分割線の設定
        self._line_group = QGroupBox("分割線")
        line_layout = QVBoxLayout(self._line_group)
        width_row = QHBoxLayout()
        width_row.addWidget(QLabel("間白幅:"))
        self._gutter_spin = QDoubleSpinBox()
        self._gutter_spin.setRange(0, SPINBOX_GUTTER_MAX)
        self._gutter_spin.setSingleStep(SPINBOX_GUTTER_STEP)
        self._gutter_spin.setValue(DEFAULT_MARGIN)
        self._gutter_spin.setSuffix(" px")
        self._gutter_spin.valueChanged.connect(self._on_gutter_changed)
        width_row.addWidget(self._gutter_spin)
        line_layout.addLayout(width_row)
        layout.addWidget(self._line_group)
        self._line_group.hide()

        self._font_group = QGroupBox("フォント")
        font_layout = QVBoxLayout(self._font_group)
        self._font_combo = QFontComboBox()
        self._font_combo.currentFontChanged.connect(self._on_font_changed)
        font_layout.addWidget(self._font_combo)

        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("サイズ:"))
        self._font_size_spin = QSpinBox()
        self._font_size_spin.setRange(MIN_FONT_SIZE, MAX_FONT_SIZE)
        self._font_size_spin.setValue(DEFAULT_FONT_SIZE)
        self._font_size_spin.valueChanged.connect(self._on_font_size_changed)
        size_row.addWidget(self._font_size_spin)
        font_layout.addLayout(size_row)

        self._color_btn = QPushButton("文字色")
        self._color_btn.clicked.connect(self._on_color_clicked)
        font_layout.addWidget(self._color_btn)

        # 縦書きチェックボックス（吹き出し用）
        self._vertical_check = QCheckBox("縦書き")
        self._vertical_check.setChecked(True)
        self._vertical_check.stateChanged.connect(self._on_vertical_changed)
        font_layout.addWidget(self._vertical_check)

        layout.addWidget(self._font_group)
        self._font_group.hide()

        # テキスト内容グループ
        self._content_group = QGroupBox("テキスト内容")
        content_layout = QVBoxLayout(self._content_group)
        self._content_edit = QPlainTextEdit()
        self._content_edit.setMaximumHeight(100)
        self._content_edit.setPlaceholderText("テキストを入力...")
        self._content_edit.textChanged.connect(self._on_content_changed)
        content_layout.addWidget(self._content_edit)
        layout.addWidget(self._content_group)
        self._content_group.hide()

        layout.addStretch()

    def set_page(self, page):
        self._current_page = page
        if page:
            self._margin_spin.blockSignals(True)
            self._margin_spin.setValue(page.margin)
            self._margin_spin.blockSignals(False)

    def set_selected_item(self, item):
        self._current_item = item
        self._update_ui()

    def _update_ui(self):
        self._image_group.hide()
        self._font_group.hide()
        self._rotation_group.hide()
        self._line_group.hide()
        self._content_group.hide()

        if not self._current_item:
            return

        self._x_spin.blockSignals(True)
        self._y_spin.blockSignals(True)
        self._w_spin.blockSignals(True)
        self._h_spin.blockSignals(True)
        self._rotation_spin.blockSignals(True)
        self._gutter_spin.blockSignals(True)

        # PanelPolygonItem（コマ領域）
        if self._current_item.__class__.__name__ == 'PanelPolygonItem':
            rect = self._current_item.polygon().boundingRect()
            self._x_spin.setValue(int(rect.x()))
            self._y_spin.setValue(int(rect.y()))
            self._w_spin.setValue(int(rect.width()))
            self._h_spin.setValue(int(rect.height()))

            # スケール値を更新
            self._scale_spin.blockSignals(True)
            image_data = self._current_item.get_image_data()
            if image_data:
                self._scale_spin.setValue(image_data.scale)
                self._scale_spin.setEnabled(True)
                self._reset_btn.setEnabled(True)
                self._clear_btn.setEnabled(True)
            else:
                self._scale_spin.setValue(MIN_IMAGE_SCALE)
                self._scale_spin.setEnabled(False)
                self._reset_btn.setEnabled(False)
                self._clear_btn.setEnabled(False)
            self._scale_spin.blockSignals(False)

            self._image_group.show()

        # DividerLineItem（分割線）
        elif isinstance(self._current_item, DividerLineItem):
            line = self._current_item.line()
            self._x_spin.setValue(int(line.p1().x()))
            self._y_spin.setValue(int(line.p1().y()))
            self._gutter_spin.setValue(self._current_item.divider.gutter_width)
            self._line_group.show()

        elif isinstance(self._current_item, SpeechBubbleGraphicsItem):
            bubble = self._current_item.bubble
            self._x_spin.setValue(int(bubble.x))
            self._y_spin.setValue(int(bubble.y))
            self._w_spin.setValue(int(bubble.width))
            self._h_spin.setValue(int(bubble.height))
            # 縦書き設定
            self._vertical_check.blockSignals(True)
            self._vertical_check.setChecked(bubble.vertical)
            self._vertical_check.blockSignals(False)
            self._vertical_check.show()
            # テキスト内容
            self._content_edit.blockSignals(True)
            self._content_edit.setPlainText(bubble.text)
            self._content_edit.blockSignals(False)
            self._font_group.show()
            self._content_group.show()

        elif isinstance(self._current_item, TextGraphicsItem):
            text_elem = self._current_item.text_element
            self._x_spin.setValue(int(text_elem.x))
            self._y_spin.setValue(int(text_elem.y))
            self._vertical_check.hide()  # テキスト要素には縦書き設定なし
            # テキスト内容
            self._content_edit.blockSignals(True)
            self._content_edit.setPlainText(self._current_item.toPlainText())
            self._content_edit.blockSignals(False)
            self._font_group.show()
            self._content_group.show()

        self._x_spin.blockSignals(False)
        self._y_spin.blockSignals(False)
        self._w_spin.blockSignals(False)
        self._h_spin.blockSignals(False)
        self._rotation_spin.blockSignals(False)
        self._gutter_spin.blockSignals(False)

    def _on_position_changed(self):
        if not self._current_item:
            return
        self._current_item.setPos(self._x_spin.value(), self._y_spin.value())
        self.property_changed.emit()

    def _on_size_changed(self):
        if not self._current_item:
            return

        if isinstance(self._current_item, SpeechBubbleGraphicsItem):
            self._current_item.bubble.width = self._w_spin.value()
            self._current_item.bubble.height = self._h_spin.value()
            self._current_item.prepareGeometryChange()
            self._current_item.update()
            self.property_changed.emit()

    def _on_rotation_changed(self, angle):
        pass  # 現在は未使用

    def _on_select_image(self):
        # PanelPolygonItem（コマ領域）
        if self._current_item.__class__.__name__ == 'PanelPolygonItem':
            path, _ = QFileDialog.getOpenFileName(
                self, "画像を選択", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
            )
            if path:
                self._current_item.set_image(path)
                # シーンに保存
                image_data = self._current_item.get_image_data()
                if self._current_item.scene() and image_data:
                    self._current_item.scene()._save_panel_image(
                        self._current_item.panel_id, image_data
                    )
                self._update_ui()  # UIを更新してスケールを有効化
                self.property_changed.emit()

    def _on_clear_image(self):
        # PanelPolygonItem（コマ領域）
        if self._current_item.__class__.__name__ == 'PanelPolygonItem':
            self._current_item.clear_image()
            self._update_ui()  # UIを更新してスケールを無効化
            self.property_changed.emit()

    def _on_scale_changed(self, scale):
        # PanelPolygonItem（コマ領域）
        if self._current_item.__class__.__name__ == 'PanelPolygonItem':
            image_data = self._current_item.get_image_data()
            if image_data:
                image_data.scale = scale
                self._current_item._clamp_offset()
                self._current_item.update()
                # シーンに保存
                if self._current_item.scene():
                    self._current_item.scene()._save_panel_image(
                        self._current_item.panel_id, image_data
                    )
                self.property_changed.emit()

    def _on_reset_image(self):
        # PanelPolygonItem（コマ領域）
        if self._current_item.__class__.__name__ == 'PanelPolygonItem':
            image_data = self._current_item.get_image_data()
            if image_data:
                image_data.scale = MIN_IMAGE_SCALE
                image_data.offset_x = 0.0
                image_data.offset_y = 0.0
                self._current_item.update()
                # スケールスピンボックスを更新
                self._scale_spin.blockSignals(True)
                self._scale_spin.setValue(MIN_IMAGE_SCALE)
                self._scale_spin.blockSignals(False)
                # シーンに保存
                if self._current_item.scene():
                    self._current_item.scene()._save_panel_image(
                        self._current_item.panel_id, image_data
                    )
                self.property_changed.emit()

    def _on_gutter_changed(self, width):
        if isinstance(self._current_item, DividerLineItem):
            self._current_item.divider.gutter_width = width
            # シーンに変更を通知してコマ領域を再計算
            if self._current_item.scene():
                self._current_item.scene().divider_changed.emit()
            self.property_changed.emit()

    def _on_font_changed(self, font):
        if isinstance(self._current_item, SpeechBubbleGraphicsItem):
            self._current_item.bubble.font_family = font.family()
            self._current_item.update()
        elif isinstance(self._current_item, TextGraphicsItem):
            current_font = self._current_item.font()
            current_font.setFamily(font.family())
            self._current_item.setFont(current_font)
            self._current_item.text_element.font_family = font.family()
        self.property_changed.emit()

    def _on_font_size_changed(self, size):
        if isinstance(self._current_item, SpeechBubbleGraphicsItem):
            self._current_item.bubble.font_size = size
            self._current_item.update()
        elif isinstance(self._current_item, TextGraphicsItem):
            current_font = self._current_item.font()
            current_font.setPointSize(size)
            self._current_item.setFont(current_font)
            self._current_item.text_element.font_size = size
        self.property_changed.emit()

    def _on_color_clicked(self):
        color = QColorDialog.getColor()
        if color.isValid() and isinstance(self._current_item, TextGraphicsItem):
            self._current_item.setDefaultTextColor(color)
            self._current_item.text_element.color = color.name()
            self.property_changed.emit()

    def _on_vertical_changed(self, state):
        """縦書き/横書き切替"""
        if isinstance(self._current_item, SpeechBubbleGraphicsItem):
            self._current_item.bubble.vertical = (state == Qt.CheckState.Checked.value)
            self._current_item.update()
            self.property_changed.emit()

    def _on_margin_changed(self, margin):
        """外枠幅変更"""
        if self._current_page:
            self._current_page.margin = margin
            self.page_margin_changed.emit(margin)
            self.property_changed.emit()

    def _on_content_changed(self):
        """テキスト内容変更"""
        if not self._current_item:
            return
        text = self._content_edit.toPlainText()
        if isinstance(self._current_item, SpeechBubbleGraphicsItem):
            self._current_item.bubble.text = text
            self._current_item.update()
            self.property_changed.emit()
        elif isinstance(self._current_item, TextGraphicsItem):
            self._current_item.setPlainText(text)
            self._current_item.text_element.text = text
            self.property_changed.emit()
