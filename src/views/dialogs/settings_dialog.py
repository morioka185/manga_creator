from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QGroupBox, QLabel, QSpinBox, QCheckBox, QFontComboBox,
    QPushButton, QListWidget, QListWidgetItem, QLineEdit,
    QDialogButtonBox, QMessageBox, QInputDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from src.services.settings_service import SettingsService, FontStyle
from src.utils.constants import (
    MIN_FONT_SIZE, MAX_FONT_SIZE,
    SPINBOX_SIZE_MIN, SPINBOX_SIZE_MAX,
    PAGE_SIZE_MIN, PAGE_SIZE_MAX,
    SPINBOX_MARGIN_MAX
)


class SettingsDialog(QDialog):
    """設定ダイアログ"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = SettingsService.get_instance()
        self.setWindowTitle("設定")
        self.setMinimumSize(500, 450)
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # タブウィジェット
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        # デフォルト設定タブ
        self._defaults_tab = QWidget()
        self._setup_defaults_tab()
        self._tabs.addTab(self._defaults_tab, "デフォルト設定")

        # スタイルプリセットタブ
        self._styles_tab = QWidget()
        self._setup_styles_tab()
        self._tabs.addTab(self._styles_tab, "スタイルプリセット")

        # ボタン
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _setup_defaults_tab(self):
        layout = QVBoxLayout(self._defaults_tab)

        # フォント設定
        font_group = QGroupBox("フォント")
        font_layout = QVBoxLayout(font_group)

        font_row = QHBoxLayout()
        font_row.addWidget(QLabel("フォント:"))
        self._font_combo = QFontComboBox()
        font_row.addWidget(self._font_combo)
        font_layout.addLayout(font_row)

        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("サイズ:"))
        self._font_size_spin = QSpinBox()
        self._font_size_spin.setRange(MIN_FONT_SIZE, MAX_FONT_SIZE)
        size_row.addWidget(self._font_size_spin)
        font_layout.addLayout(size_row)

        layout.addWidget(font_group)

        # 吹き出し設定
        bubble_group = QGroupBox("吹き出し")
        bubble_layout = QVBoxLayout(bubble_group)

        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("幅:"))
        self._bubble_w_spin = QSpinBox()
        self._bubble_w_spin.setRange(SPINBOX_SIZE_MIN, SPINBOX_SIZE_MAX)
        size_row.addWidget(self._bubble_w_spin)
        size_row.addWidget(QLabel("高さ:"))
        self._bubble_h_spin = QSpinBox()
        self._bubble_h_spin.setRange(SPINBOX_SIZE_MIN, SPINBOX_SIZE_MAX)
        size_row.addWidget(self._bubble_h_spin)
        bubble_layout.addLayout(size_row)

        self._vertical_check = QCheckBox("縦書き")
        bubble_layout.addWidget(self._vertical_check)

        layout.addWidget(bubble_group)

        # ページ設定
        page_group = QGroupBox("ページ")
        page_layout = QVBoxLayout(page_group)

        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("幅:"))
        self._page_w_spin = QSpinBox()
        self._page_w_spin.setRange(PAGE_SIZE_MIN, PAGE_SIZE_MAX)
        size_row.addWidget(self._page_w_spin)
        size_row.addWidget(QLabel("高さ:"))
        self._page_h_spin = QSpinBox()
        self._page_h_spin.setRange(PAGE_SIZE_MIN, PAGE_SIZE_MAX)
        size_row.addWidget(self._page_h_spin)
        page_layout.addLayout(size_row)

        margin_row = QHBoxLayout()
        margin_row.addWidget(QLabel("外枠幅:"))
        self._margin_spin = QSpinBox()
        self._margin_spin.setRange(0, SPINBOX_MARGIN_MAX)
        self._margin_spin.setSuffix(" px")
        margin_row.addWidget(self._margin_spin)
        page_layout.addLayout(margin_row)

        layout.addWidget(page_group)
        layout.addStretch()

    def _setup_styles_tab(self):
        layout = QHBoxLayout(self._styles_tab)

        # 左側：スタイルリスト
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("スタイル一覧:"))

        self._style_list = QListWidget()
        self._style_list.currentRowChanged.connect(self._on_style_selected)
        left_layout.addWidget(self._style_list)

        # ボタン
        btn_layout = QHBoxLayout()
        self._add_btn = QPushButton("追加")
        self._add_btn.clicked.connect(self._on_add_style)
        btn_layout.addWidget(self._add_btn)

        self._delete_btn = QPushButton("削除")
        self._delete_btn.clicked.connect(self._on_delete_style)
        btn_layout.addWidget(self._delete_btn)

        self._reset_btn = QPushButton("リセット")
        self._reset_btn.clicked.connect(self._on_reset_styles)
        btn_layout.addWidget(self._reset_btn)

        left_layout.addLayout(btn_layout)
        layout.addLayout(left_layout)

        # 右側：スタイル編集
        right_layout = QVBoxLayout()
        edit_group = QGroupBox("スタイル編集")
        edit_layout = QVBoxLayout(edit_group)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("名前:"))
        self._style_name_edit = QLineEdit()
        name_row.addWidget(self._style_name_edit)
        edit_layout.addLayout(name_row)

        font_row = QHBoxLayout()
        font_row.addWidget(QLabel("フォント:"))
        self._style_font_combo = QFontComboBox()
        font_row.addWidget(self._style_font_combo)
        edit_layout.addLayout(font_row)

        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("サイズ:"))
        self._style_size_spin = QSpinBox()
        self._style_size_spin.setRange(MIN_FONT_SIZE, MAX_FONT_SIZE)
        size_row.addWidget(self._style_size_spin)
        edit_layout.addLayout(size_row)

        self._style_bold_check = QCheckBox("太字")
        edit_layout.addWidget(self._style_bold_check)

        self._apply_style_btn = QPushButton("変更を保存")
        self._apply_style_btn.clicked.connect(self._on_apply_style)
        edit_layout.addWidget(self._apply_style_btn)

        right_layout.addWidget(edit_group)
        right_layout.addStretch()
        layout.addLayout(right_layout)

    def _load_settings(self):
        """設定を読み込み"""
        # デフォルト設定
        self._font_combo.setCurrentFont(QFont(self._settings.font_family))
        self._font_size_spin.setValue(self._settings.font_size)
        self._bubble_w_spin.setValue(self._settings.bubble_width)
        self._bubble_h_spin.setValue(self._settings.bubble_height)
        self._vertical_check.setChecked(self._settings.bubble_vertical)
        self._page_w_spin.setValue(self._settings.page_width)
        self._page_h_spin.setValue(self._settings.page_height)
        self._margin_spin.setValue(self._settings.page_margin)

        # スタイルリスト
        self._refresh_style_list()

    def _refresh_style_list(self):
        """スタイルリストを更新"""
        self._style_list.clear()
        for style in self._settings.get_font_styles():
            self._style_list.addItem(style.name)
        if self._style_list.count() > 0:
            self._style_list.setCurrentRow(0)

    def _on_style_selected(self, row):
        """スタイル選択時"""
        if row < 0:
            return
        styles = self._settings.get_font_styles()
        if row < len(styles):
            style = styles[row]
            self._style_name_edit.setText(style.name)
            self._style_font_combo.setCurrentFont(QFont(style.font_family))
            self._style_size_spin.setValue(style.font_size)
            self._style_bold_check.setChecked(style.bold)

    def _on_add_style(self):
        """スタイル追加"""
        name, ok = QInputDialog.getText(self, "スタイル追加", "スタイル名:")
        if ok and name:
            style = FontStyle(
                name=name,
                font_family=self._settings.font_family,
                font_size=self._settings.font_size,
                bold=False
            )
            self._settings.add_font_style(style)
            self._refresh_style_list()
            # 新しいスタイルを選択
            for i in range(self._style_list.count()):
                if self._style_list.item(i).text() == name:
                    self._style_list.setCurrentRow(i)
                    break

    def _on_delete_style(self):
        """スタイル削除"""
        row = self._style_list.currentRow()
        if row < 0:
            return
        name = self._style_list.item(row).text()
        reply = QMessageBox.question(
            self, "確認", f"スタイル「{name}」を削除しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._settings.delete_font_style(name)
            self._refresh_style_list()

    def _on_reset_styles(self):
        """スタイルをリセット"""
        reply = QMessageBox.question(
            self, "確認", "スタイルをデフォルトにリセットしますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._settings.reset_font_styles()
            self._refresh_style_list()

    def _on_apply_style(self):
        """スタイル変更を保存"""
        row = self._style_list.currentRow()
        if row < 0:
            return

        old_name = self._style_list.item(row).text()
        new_style = FontStyle(
            name=self._style_name_edit.text(),
            font_family=self._style_font_combo.currentFont().family(),
            font_size=self._style_size_spin.value(),
            bold=self._style_bold_check.isChecked()
        )
        self._settings.update_font_style(old_name, new_style)
        self._refresh_style_list()

        # 更新したスタイルを選択
        for i in range(self._style_list.count()):
            if self._style_list.item(i).text() == new_style.name:
                self._style_list.setCurrentRow(i)
                break

    def _on_accept(self):
        """OK押下時"""
        # デフォルト設定を保存
        self._settings.font_family = self._font_combo.currentFont().family()
        self._settings.font_size = self._font_size_spin.value()
        self._settings.bubble_width = self._bubble_w_spin.value()
        self._settings.bubble_height = self._bubble_h_spin.value()
        self._settings.bubble_vertical = self._vertical_check.isChecked()
        self._settings.page_width = self._page_w_spin.value()
        self._settings.page_height = self._page_h_spin.value()
        self._settings.page_margin = self._margin_spin.value()
        self.accept()
