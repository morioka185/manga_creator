"""キャラクター一括生成ダイアログ"""
import base64
import tempfile
import uuid
import shutil
from pathlib import Path
from typing import Optional, List, Dict

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QGroupBox, QFormLayout,
    QSpinBox, QDoubleSpinBox, QComboBox, QProgressBar,
    QPlainTextEdit, QSplitter, QWidget, QMessageBox,
    QScrollArea, QFrame, QGridLayout
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QIcon, QFont

from src.services.story_import_service import StorySpec, StoryCharacter
from src.services.settings_service import SettingsService
from src.services.character_service import CharacterService
from src.services.forge_service import ForgeService
from src.models.character import Character
from src.workers.generation_worker import GenerationWorker


class CharacterGenerationDialog(QDialog):
    """キャラクター一括生成ダイアログ"""

    def __init__(
        self,
        story_spec: StorySpec,
        characters_base_folder: Optional[str] = None,
        parent=None
    ):
        super().__init__(parent)
        self._story_spec = story_spec
        self._settings = SettingsService.get_instance()
        self._character_service = CharacterService.get_instance()
        self._characters_base_folder = characters_base_folder  # キャラクター画像ベースフォルダ

        # 生成状態管理
        self._current_worker: Optional[GenerationWorker] = None
        self._generated_images: Dict[str, List[str]] = {}  # char_id -> [image_paths]
        self._confirmed_images: Dict[str, str] = {}  # char_id -> confirmed_image_path
        self._current_char_index = 0
        self._current_image_index: Dict[str, int] = {}  # 各キャラクターの選択中画像インデックス
        self._batch_generation_mode = False  # 全キャラ生成モードフラグ

        self.setWindowTitle("キャラクター画像生成")
        self.setMinimumSize(1000, 700)
        self._setup_ui()
        self._refresh_character_list()

    def _setup_ui(self):
        """UI構築"""
        layout = QVBoxLayout(self)

        # スプリッター
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左パネル: キャラクター一覧
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        char_group = QGroupBox("キャラクター一覧")
        char_layout = QVBoxLayout(char_group)

        self._char_list = QListWidget()
        self._char_list.setIconSize(QSize(64, 64))
        self._char_list.itemClicked.connect(self._on_char_selected)
        char_layout.addWidget(self._char_list)

        # 一括生成ボタン
        self._generate_all_btn = QPushButton("全キャラ生成")
        self._generate_all_btn.clicked.connect(self._on_generate_all)
        char_layout.addWidget(self._generate_all_btn)

        left_layout.addWidget(char_group)
        splitter.addWidget(left_widget)

        # 中央パネル: キャラクター詳細と生成
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)

        # キャラクター情報
        info_group = QGroupBox("キャラクター情報")
        info_layout = QVBoxLayout(info_group)

        self._char_name_label = QLabel("")
        self._char_name_label.setFont(QFont("", 12, QFont.Weight.Bold))
        info_layout.addWidget(self._char_name_label)

        self._char_appearance_text = QPlainTextEdit()
        self._char_appearance_text.setReadOnly(True)
        self._char_appearance_text.setMaximumHeight(80)
        info_layout.addWidget(QLabel("外見:"))
        info_layout.addWidget(self._char_appearance_text)

        center_layout.addWidget(info_group)

        # プロンプト編集
        prompt_group = QGroupBox("生成プロンプト")
        prompt_layout = QVBoxLayout(prompt_group)

        self._prompt_edit = QPlainTextEdit()
        self._prompt_edit.setMaximumHeight(80)
        self._prompt_edit.setPlaceholderText("キャラクターの外見プロンプト...")
        prompt_layout.addWidget(self._prompt_edit)

        center_layout.addWidget(prompt_group)

        # 生成設定
        settings_group = QGroupBox("生成設定")
        settings_layout = QFormLayout(settings_group)

        # Steps
        self._steps_spin = QSpinBox()
        self._steps_spin.setRange(1, 150)
        self._steps_spin.setValue(self._settings.default_steps)
        settings_layout.addRow("Steps:", self._steps_spin)

        # CFG Scale
        self._cfg_spin = QDoubleSpinBox()
        self._cfg_spin.setRange(1.0, 30.0)
        self._cfg_spin.setValue(self._settings.default_cfg_scale)
        self._cfg_spin.setSingleStep(0.5)
        settings_layout.addRow("CFG Scale:", self._cfg_spin)

        # Sampler
        self._sampler_combo = QComboBox()
        self._sampler_combo.addItems([
            "Euler a", "Euler", "DPM++ 2M", "DPM++ 2M Karras",
            "DPM++ SDE", "DPM++ SDE Karras", "DDIM"
        ])
        self._sampler_combo.setCurrentText(self._settings.default_sampler)
        settings_layout.addRow("Sampler:", self._sampler_combo)

        center_layout.addWidget(settings_group)

        # 生成ボタン
        gen_btn_layout = QHBoxLayout()
        self._generate_btn = QPushButton("このキャラを生成")
        self._generate_btn.clicked.connect(self._on_generate_current)
        self._generate_btn.setEnabled(False)
        gen_btn_layout.addWidget(self._generate_btn)

        self._regenerate_btn = QPushButton("再生成")
        self._regenerate_btn.clicked.connect(self._on_regenerate)
        self._regenerate_btn.setEnabled(False)
        gen_btn_layout.addWidget(self._regenerate_btn)

        center_layout.addLayout(gen_btn_layout)

        # プログレスバー
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        center_layout.addWidget(self._progress_bar)

        self._status_label = QLabel("")
        center_layout.addWidget(self._status_label)

        center_layout.addStretch()
        splitter.addWidget(center_widget)

        # 右パネル: 画像プレビュー
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        preview_group = QGroupBox("生成画像")
        preview_layout = QVBoxLayout(preview_group)

        # サムネイル一覧（横スクロール）
        thumb_scroll = QScrollArea()
        thumb_scroll.setWidgetResizable(True)
        thumb_scroll.setFixedHeight(130)
        thumb_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        thumb_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._thumbnail_container = QWidget()
        self._thumbnail_layout = QHBoxLayout(self._thumbnail_container)
        self._thumbnail_layout.setContentsMargins(4, 4, 4, 4)
        self._thumbnail_layout.setSpacing(8)
        self._thumbnail_layout.addStretch()
        thumb_scroll.setWidget(self._thumbnail_container)
        preview_layout.addWidget(thumb_scroll)

        # メインプレビュー
        self._preview_label = QLabel()
        self._preview_label.setMinimumSize(300, 400)
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setStyleSheet("border: 1px solid #ccc; background: #222;")
        self._preview_label.setText("生成画像がここに表示されます")
        preview_layout.addWidget(self._preview_label, 1)

        # 確定ボタン
        self._confirm_btn = QPushButton("この画像で確定")
        self._confirm_btn.clicked.connect(self._on_confirm_image)
        self._confirm_btn.setEnabled(False)
        self._confirm_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        preview_layout.addWidget(self._confirm_btn)

        right_layout.addWidget(preview_group)
        splitter.addWidget(right_widget)

        splitter.setSizes([200, 350, 350])
        layout.addWidget(splitter)

        # 下部ボタン
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._progress_label = QLabel("")
        btn_layout.addWidget(self._progress_label)

        self._finish_btn = QPushButton("完了してコマ生成へ")
        self._finish_btn.clicked.connect(self._on_finish)
        self._finish_btn.setEnabled(False)
        btn_layout.addWidget(self._finish_btn)

        self._cancel_btn = QPushButton("キャンセル")
        self._cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._cancel_btn)

        layout.addLayout(btn_layout)

    def _refresh_character_list(self):
        """キャラクター一覧を更新"""
        self._char_list.clear()

        for char in self._story_spec.characters:
            item = QListWidgetItem()

            # 確定済みの場合はアイコン表示
            if char.id in self._confirmed_images:
                pixmap = QPixmap(self._confirmed_images[char.id])
                if not pixmap.isNull():
                    scaled = pixmap.scaled(
                        64, 64,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    item.setIcon(QIcon(scaled))
                item.setText(f"{char.name} [確定]")
                item.setForeground(Qt.GlobalColor.green)
            else:
                item.setText(char.name)

            item.setData(Qt.ItemDataRole.UserRole, char)
            self._char_list.addItem(item)

        self._update_progress_label()

    def _update_progress_label(self):
        """進捗ラベルを更新"""
        confirmed = len(self._confirmed_images)
        total = len(self._story_spec.characters)
        self._progress_label.setText(f"確定: {confirmed}/{total}")

        # 全て確定したら完了ボタンを有効化
        self._finish_btn.setEnabled(confirmed == total)

    def _on_char_selected(self, item: QListWidgetItem):
        """キャラクター選択時"""
        char = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(char, StoryCharacter):
            return

        self._current_char_index = self._char_list.row(item)
        self._char_name_label.setText(char.name)
        self._char_appearance_text.setPlainText(char.appearance or "(未設定)")

        # プロンプトを設定（promptがあればそれを、なければappearanceから）
        prompt = char.prompt or char.appearance or ""
        self._prompt_edit.setPlainText(prompt)

        self._generate_btn.setEnabled(True)

        # 既存の生成画像があれば表示
        self._refresh_thumbnails(char.id)

        # 確定済み画像があれば表示
        if char.id in self._confirmed_images:
            self._show_preview(self._confirmed_images[char.id])
            self._regenerate_btn.setEnabled(True)
        elif char.id in self._generated_images and self._generated_images[char.id]:
            idx = self._current_image_index.get(char.id, 0)
            self._show_preview(self._generated_images[char.id][idx])
            self._regenerate_btn.setEnabled(True)
            self._confirm_btn.setEnabled(True)
        else:
            self._preview_label.clear()
            self._preview_label.setText("生成画像がここに表示されます")
            self._regenerate_btn.setEnabled(False)
            self._confirm_btn.setEnabled(False)

    def _refresh_thumbnails(self, char_id: str):
        """サムネイル一覧を更新"""
        # 既存のサムネイルをクリア
        while self._thumbnail_layout.count() > 1:  # stretchを残す
            item = self._thumbnail_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if char_id not in self._generated_images:
            return

        images = self._generated_images[char_id]
        selected_idx = self._current_image_index.get(char_id, 0)

        for i, img_path in enumerate(images):
            btn = QPushButton()
            btn.setFixedSize(110, 110)
            btn.setCheckable(True)
            btn.setChecked(i == selected_idx)

            is_confirmed = (char_id in self._confirmed_images and
                          self._confirmed_images[char_id] == img_path)

            if is_confirmed:
                btn.setStyleSheet("""
                    QPushButton { border: 3px solid #4CAF50; background: #333; }
                    QPushButton:hover { border: 3px solid #66BB6A; }
                    QPushButton:checked { border: 4px solid #4CAF50; }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton { border: 2px solid #555; background: #333; }
                    QPushButton:hover { border: 2px solid #888; }
                    QPushButton:checked { border: 3px solid #2196F3; }
                """)

            pixmap = QPixmap(img_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    100, 100,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                btn.setIcon(QIcon(scaled))
                btn.setIconSize(QSize(100, 100))

            btn.clicked.connect(lambda checked, idx=i, cid=char_id: self._on_thumbnail_clicked(cid, idx))
            self._thumbnail_layout.insertWidget(i, btn)

    def _on_thumbnail_clicked(self, char_id: str, index: int):
        """サムネイルクリック時"""
        if char_id not in self._generated_images:
            return

        images = self._generated_images[char_id]
        if index >= len(images):
            return

        self._current_image_index[char_id] = index
        self._show_preview(images[index])
        self._refresh_thumbnails(char_id)
        self._confirm_btn.setEnabled(True)

    def _show_preview(self, image_path: str):
        """プレビュー表示"""
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                self._preview_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self._preview_label.setPixmap(scaled)

    def _on_generate_current(self):
        """現在のキャラクターを生成"""
        item = self._char_list.currentItem()
        if not item:
            return

        char = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(char, StoryCharacter):
            self._generate_character(char)

    def _on_regenerate(self):
        """再生成"""
        self._on_generate_current()

    def _on_generate_all(self):
        """全キャラクター生成"""
        self._batch_generation_mode = True
        self._generate_next_ungenerated()

    def _generate_next_ungenerated(self):
        """次の未生成キャラクターを生成（確定状態は関係なく、画像がないキャラクター）"""
        # まだ画像が生成されていないキャラクターを探して生成
        for i, char in enumerate(self._story_spec.characters):
            if char.id not in self._generated_images or not self._generated_images[char.id]:
                self._char_list.setCurrentRow(i)
                self._on_char_selected(self._char_list.item(i))
                self._generate_character(char)
                return True  # 生成開始

        # 全員分の画像生成完了
        self._batch_generation_mode = False
        QMessageBox.information(
            self, "生成完了",
            "全キャラクターの画像生成が完了しました。\n"
            "各キャラクターを選択して画像を確認し、「この画像で確定」を押してください。"
        )
        # 最初のキャラクターを選択
        if self._char_list.count() > 0:
            self._char_list.setCurrentRow(0)
            self._on_char_selected(self._char_list.item(0))
        return False

    def _get_character_save_folder(self, char_name: str) -> Optional[str]:
        """キャラクター用の保存先フォルダを取得"""
        if not self._characters_base_folder:
            return None
        import re
        # ファイル名に使えない文字を置換
        invalid_chars = r'[<>:"/\\|?*]'
        safe_name = re.sub(invalid_chars, '_', char_name).strip(' .')
        if not safe_name:
            safe_name = "unnamed"
        char_folder = Path(self._characters_base_folder) / safe_name
        char_folder.mkdir(parents=True, exist_ok=True)
        return str(char_folder)

    # キャラクター参照画像用の固定タグ（正面、無表情、全身、白背景）
    CHARACTER_REFERENCE_TAGS = (
        "expressionless, front view, looking at viewer, "
        "standing, full body, simple background, white background"
    )

    def _generate_character(self, char: StoryCharacter):
        """キャラクター画像を生成"""
        if self._current_worker and self._current_worker.isRunning():
            return

        prompt = self._prompt_edit.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "エラー", "プロンプトを入力してください")
            return

        # キャラクター参照画像用の固定タグを自動付与
        prompt = f"{prompt}, {self.CHARACTER_REFERENCE_TAGS}"

        # 共通プロンプトを追加
        common_prompt = self._settings.default_prompt
        if common_prompt:
            prompt = f"{prompt}, {common_prompt}"

        # UI更新
        self._generate_btn.setEnabled(False)
        self._regenerate_btn.setEnabled(False)
        self._confirm_btn.setEnabled(False)
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 0)
        self._status_label.setText("生成中...")

        # キャラクター用保存先フォルダを取得
        save_folder = self._get_character_save_folder(char.name)

        # ワーカー作成
        self._current_worker = GenerationWorker(
            prompt=prompt,
            negative_prompt=self._settings.default_negative_prompt,
            width=768,  # キャラクター用は正方形に近いサイズ
            height=1024,
            steps=self._steps_spin.value(),
            cfg_scale=self._cfg_spin.value(),
            seed=-1,
            sampler_name=self._sampler_combo.currentText(),
            save_folder=save_folder,
            parent=self
        )

        self._current_worker.progress.connect(self._on_progress)
        self._current_worker.finished.connect(
            lambda success, result, seed: self._on_generation_finished(char.id, success, result, seed)
        )
        self._current_worker.start()

    def _on_progress(self, message: str):
        """進捗更新"""
        self._status_label.setText(message)

    def _on_generation_finished(self, char_id: str, success: bool, result: str, seed: str):
        """生成完了"""
        self._progress_bar.setVisible(False)
        self._generate_btn.setEnabled(True)
        self._regenerate_btn.setEnabled(True)

        if success:
            # 画像リストに追加
            if char_id not in self._generated_images:
                self._generated_images[char_id] = []
            self._generated_images[char_id].append(result)

            # 最新の画像を選択
            idx = len(self._generated_images[char_id]) - 1
            self._current_image_index[char_id] = idx

            self._refresh_thumbnails(char_id)
            self._show_preview(result)
            self._confirm_btn.setEnabled(True)
            self._status_label.setText(f"生成完了 - Seed: {seed}")

            # 全キャラ生成モードの場合、確定せずに次へ進む
            if self._batch_generation_mode:
                # 次の未生成キャラクターを生成
                self._generate_next_ungenerated()
        else:
            self._status_label.setText(f"エラー: {result}")
            self._batch_generation_mode = False  # エラー時はバッチモード解除
            QMessageBox.warning(self, "生成エラー", result)

    def _on_confirm_image(self):
        """画像を確定"""
        item = self._char_list.currentItem()
        if not item:
            return

        char = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(char, StoryCharacter):
            return

        char_id = char.id

        if char_id not in self._generated_images:
            return

        idx = self._current_image_index.get(char_id, 0)
        images = self._generated_images[char_id]
        if idx >= len(images):
            return

        # 確定画像を保存
        source_path = images[idx]
        self._confirmed_images[char_id] = source_path

        # リストを更新
        self._refresh_character_list()
        self._refresh_thumbnails(char_id)

        self._status_label.setText(f"「{char.name}」の画像を確定しました")

        # 次の未確定キャラクターへ移動
        self._move_to_next_unconfirmed()

    def _move_to_next_unconfirmed(self):
        """次の未確定キャラクターへ移動"""
        for i, char in enumerate(self._story_spec.characters):
            if char.id not in self._confirmed_images:
                self._char_list.setCurrentRow(i)
                self._on_char_selected(self._char_list.item(i))
                return

    def _on_finish(self):
        """完了してキャラクターを登録"""
        # 確定した画像をキャラクターサービスに登録
        saved_count = 0

        for char in self._story_spec.characters:
            if char.id in self._confirmed_images:
                source_path = self._confirmed_images[char.id]

                # 保存先を決定
                if self._characters_base_folder:
                    # プロジェクトフォルダが指定されている場合
                    # 画像はすでにキャラクターフォルダに保存されているのでそのまま使用
                    dest_path = Path(source_path)
                else:
                    # 従来の動作：APPDATAにコピー
                    import os
                    app_data = os.environ.get('APPDATA', os.path.expanduser('~'))
                    char_dir = Path(app_data) / 'MangaCreator' / 'characters'
                    char_dir.mkdir(parents=True, exist_ok=True)
                    dest_path = char_dir / f"{char.id}.png"
                    shutil.copy2(source_path, dest_path)

                # キャラクターを登録/更新
                existing = self._character_service.get_by_name(char.name)
                if existing:
                    existing.reference_image_path = str(dest_path)
                    existing.default_prompt = char.prompt or char.appearance or ""
                    self._character_service.update(existing.id, existing)
                else:
                    new_char = Character(
                        id=char.id,
                        name=char.name,
                        reference_image_path=str(dest_path),
                        default_prompt=char.prompt or char.appearance or "",
                        ip_adapter_weight=0.8
                    )
                    self._character_service.add(new_char)

                saved_count += 1

        QMessageBox.information(
            self, "完了",
            f"{saved_count}人のキャラクターを登録しました。\n"
            "コマ生成時にIP-Adapterで使用されます。"
        )
        self.accept()

    def get_confirmed_images(self) -> Dict[str, str]:
        """確定した画像を取得"""
        return self._confirmed_images.copy()

    def closeEvent(self, event):
        """ダイアログ閉じる時"""
        if self._current_worker and self._current_worker.isRunning():
            self._current_worker.cancel()
            self._current_worker.wait()
        super().closeEvent(event)
