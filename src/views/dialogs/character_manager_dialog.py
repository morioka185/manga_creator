"""キャラクター管理ダイアログ"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QLineEdit, QPlainTextEdit, QDoubleSpinBox,
    QPushButton, QListWidget, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from src.services.character_service import CharacterService
from src.models.character import Character
from typing import Optional


class CharacterManagerDialog(QDialog):
    """キャラクター管理ダイアログ"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._service = CharacterService.get_instance()
        self._current_character: Optional[Character] = None
        self._reference_image_path: Optional[str] = None

        self.setWindowTitle("キャラクター管理")
        self.setMinimumSize(600, 450)
        self._setup_ui()
        self._refresh_list()

    def _setup_ui(self):
        layout = QHBoxLayout(self)

        # 左側: キャラクターリスト
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("キャラクター一覧:"))

        self._char_list = QListWidget()
        self._char_list.currentRowChanged.connect(self._on_char_selected)
        left_layout.addWidget(self._char_list)

        # ボタン
        btn_layout = QHBoxLayout()
        self._add_btn = QPushButton("追加")
        self._add_btn.clicked.connect(self._on_add)
        btn_layout.addWidget(self._add_btn)

        self._delete_btn = QPushButton("削除")
        self._delete_btn.clicked.connect(self._on_delete)
        btn_layout.addWidget(self._delete_btn)

        left_layout.addLayout(btn_layout)
        layout.addLayout(left_layout)

        # 右側: 編集エリア
        right_layout = QVBoxLayout()

        edit_group = QGroupBox("キャラクター編集")
        edit_layout = QVBoxLayout(edit_group)

        # 名前
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("名前:"))
        self._name_edit = QLineEdit()
        name_row.addWidget(self._name_edit)
        edit_layout.addLayout(name_row)

        # 参照画像
        img_row = QHBoxLayout()
        img_row.addWidget(QLabel("参照画像:"))
        self._img_path_label = QLabel("未選択")
        self._img_path_label.setStyleSheet("color: gray;")
        img_row.addWidget(self._img_path_label, 1)
        self._img_select_btn = QPushButton("選択...")
        self._img_select_btn.clicked.connect(self._on_select_image)
        img_row.addWidget(self._img_select_btn)
        edit_layout.addLayout(img_row)

        # 画像プレビュー
        self._img_preview = QLabel()
        self._img_preview.setFixedSize(150, 150)
        self._img_preview.setStyleSheet("border: 1px solid #ccc; background: #f0f0f0;")
        self._img_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        edit_layout.addWidget(self._img_preview)

        # デフォルトプロンプト
        edit_layout.addWidget(QLabel("デフォルトプロンプト（任意）:"))
        self._prompt_edit = QPlainTextEdit()
        self._prompt_edit.setMaximumHeight(60)
        self._prompt_edit.setPlaceholderText("例: 1girl, black hair, blue eyes")
        edit_layout.addWidget(self._prompt_edit)

        # IP-Adapter強度
        weight_row = QHBoxLayout()
        weight_row.addWidget(QLabel("IP-Adapter強度:"))
        self._weight_spin = QDoubleSpinBox()
        self._weight_spin.setRange(0.0, 1.0)
        self._weight_spin.setSingleStep(0.1)
        self._weight_spin.setValue(0.8)
        weight_row.addWidget(self._weight_spin)
        weight_row.addStretch()
        edit_layout.addLayout(weight_row)

        # 保存ボタン
        self._save_btn = QPushButton("変更を保存")
        self._save_btn.clicked.connect(self._on_save)
        edit_layout.addWidget(self._save_btn)

        right_layout.addWidget(edit_group)
        right_layout.addStretch()
        layout.addLayout(right_layout)

    def _refresh_list(self):
        """リストを更新"""
        self._char_list.clear()
        for char in self._service.get_all():
            self._char_list.addItem(char.name)

        if self._char_list.count() > 0:
            self._char_list.setCurrentRow(0)
        else:
            self._clear_form()

    def _clear_form(self):
        """フォームをクリア"""
        self._current_character = None
        self._reference_image_path = None
        self._name_edit.clear()
        self._img_path_label.setText("未選択")
        self._img_path_label.setStyleSheet("color: gray;")
        self._img_preview.clear()
        self._prompt_edit.clear()
        self._weight_spin.setValue(0.8)

    def _on_char_selected(self, row: int):
        """キャラクター選択時"""
        if row < 0:
            self._clear_form()
            return

        characters = self._service.get_all()
        if row < len(characters):
            char = characters[row]
            self._current_character = char
            self._name_edit.setText(char.name)
            self._prompt_edit.setPlainText(char.default_prompt)
            self._weight_spin.setValue(char.ip_adapter_weight)

            if char.reference_image_path:
                self._reference_image_path = char.reference_image_path
                filename = char.reference_image_path.split('/')[-1].split('\\')[-1]
                self._img_path_label.setText(filename)
                self._img_path_label.setStyleSheet("")

                pixmap = QPixmap(char.reference_image_path)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(
                        150, 150,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self._img_preview.setPixmap(scaled)
                else:
                    self._img_preview.clear()
            else:
                self._reference_image_path = None
                self._img_path_label.setText("未選択")
                self._img_path_label.setStyleSheet("color: gray;")
                self._img_preview.clear()

    def _on_select_image(self):
        """参照画像選択"""
        path, _ = QFileDialog.getOpenFileName(
            self, "参照画像を選択",
            "",
            "画像ファイル (*.png *.jpg *.jpeg *.bmp)"
        )
        if path:
            self._reference_image_path = path
            filename = path.split('/')[-1].split('\\')[-1]
            self._img_path_label.setText(filename)
            self._img_path_label.setStyleSheet("")

            pixmap = QPixmap(path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    150, 150,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self._img_preview.setPixmap(scaled)

    def _on_add(self):
        """キャラクター追加"""
        # 新しいキャラクターを作成
        char = Character(
            name="新しいキャラクター",
            reference_image_path="",
            default_prompt="",
            ip_adapter_weight=0.8
        )
        self._service.add(char)
        self._refresh_list()

        # 新しいキャラクターを選択
        self._char_list.setCurrentRow(self._char_list.count() - 1)

    def _on_delete(self):
        """キャラクター削除"""
        if not self._current_character:
            return

        reply = QMessageBox.question(
            self, "確認",
            f"キャラクター「{self._current_character.name}」を削除しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._service.delete(self._current_character.id)
            self._refresh_list()

    def _on_save(self):
        """変更を保存"""
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "エラー", "名前を入力してください")
            return

        if self._current_character:
            # 既存キャラクターを更新
            updated = Character(
                id=self._current_character.id,
                name=name,
                reference_image_path=self._reference_image_path or "",
                default_prompt=self._prompt_edit.toPlainText(),
                ip_adapter_weight=self._weight_spin.value()
            )
            self._service.update(self._current_character.id, updated)
        else:
            # 新規作成
            new_char = Character(
                name=name,
                reference_image_path=self._reference_image_path or "",
                default_prompt=self._prompt_edit.toPlainText(),
                ip_adapter_weight=self._weight_spin.value()
            )
            self._service.add(new_char)

        self._refresh_list()
        QMessageBox.information(self, "保存完了", "キャラクターを保存しました")
