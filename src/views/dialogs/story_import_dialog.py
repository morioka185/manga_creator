"""ストーリー仕様書インポートダイアログ"""
from typing import Optional, List, Dict

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QGroupBox, QFormLayout,
    QSpinBox, QDoubleSpinBox, QComboBox, QProgressBar, QCheckBox,
    QTextEdit, QSplitter, QWidget, QFileDialog, QMessageBox,
    QScrollArea, QFrame, QPlainTextEdit, QSlider
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap, QIcon
from PyQt6.QtCore import QSize

from src.services.story_import_service import (
    StoryImportService, StorySpec, StoryCharacter, StoryPage, StoryPanel
)
from src.services.settings_service import SettingsService
from src.services.character_service import CharacterService
from src.services.image_path_service import ImagePathService
from src.workers.batch_generation_worker import BatchGenerationWorker, GeneratedPanel


class StoryImportDialog(QDialog):
    """ストーリー仕様書インポートダイアログ"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._story_spec: Optional[StorySpec] = None
        self._worker: Optional[BatchGenerationWorker] = None
        self._generated_panels: List[GeneratedPanel] = []
        self._settings = SettingsService.get_instance()
        self._character_service = CharacterService.get_instance()
        self._character_images: Dict[str, str] = {}  # char_id -> reference_image_path

        self.setWindowTitle("ストーリー仕様書を読み込み")
        self.setMinimumSize(900, 700)
        self._setup_ui()

    def _setup_ui(self):
        """UI構築"""
        layout = QVBoxLayout(self)

        # ファイル選択部分
        file_layout = QHBoxLayout()
        self._file_label = QLabel("ファイル: (未選択)")
        self._file_label.setStyleSheet("color: gray;")
        file_layout.addWidget(self._file_label, 1)

        self._browse_btn = QPushButton("JSONを選択...")
        self._browse_btn.clicked.connect(self._on_browse)
        file_layout.addWidget(self._browse_btn)
        layout.addLayout(file_layout)

        # スプリッター（左: キャラクター/ページ一覧、右: 詳細）
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左パネル
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # キャラクター一覧
        char_group = QGroupBox("キャラクター")
        char_layout = QVBoxLayout(char_group)
        self._char_list = QListWidget()
        self._char_list.setIconSize(QSize(48, 48))
        self._char_list.itemClicked.connect(self._on_char_selected)
        char_layout.addWidget(self._char_list)

        # キャラクター画像生成ボタン
        self._gen_char_btn = QPushButton("キャラクター画像を生成...")
        self._gen_char_btn.setEnabled(False)
        self._gen_char_btn.clicked.connect(self._on_generate_characters)
        self._gen_char_btn.setStyleSheet("background-color: #2196F3; color: white;")
        char_layout.addWidget(self._gen_char_btn)

        left_layout.addWidget(char_group)

        # ページ/コマ一覧
        page_group = QGroupBox("ページ/コマ")
        page_layout = QVBoxLayout(page_group)
        self._page_list = QListWidget()
        self._page_list.itemClicked.connect(self._on_panel_selected)
        page_layout.addWidget(self._page_list)
        left_layout.addWidget(page_group)

        splitter.addWidget(left_widget)

        # 右パネル（詳細表示）
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 詳細グループ
        detail_group = QGroupBox("詳細")
        detail_layout = QVBoxLayout(detail_group)

        self._detail_text = QTextEdit()
        self._detail_text.setReadOnly(True)
        self._detail_text.setFont(QFont("Consolas", 10))
        detail_layout.addWidget(self._detail_text)

        right_layout.addWidget(detail_group)
        splitter.addWidget(right_widget)

        splitter.setSizes([300, 600])
        layout.addWidget(splitter)

        # 生成設定
        settings_group = QGroupBox("生成設定")
        settings_layout = QFormLayout(settings_group)

        # 共通プロンプト（品質タグなど）
        prompt_layout = QVBoxLayout()
        self._common_prompt_edit = QPlainTextEdit()
        self._common_prompt_edit.setFixedHeight(40)
        self._common_prompt_edit.setPlaceholderText("masterpiece, best quality, anime style...")
        self._common_prompt_edit.setPlainText(self._settings.default_prompt)
        prompt_layout.addWidget(self._common_prompt_edit)
        settings_layout.addRow("共通プロンプト:", prompt_layout)

        # 共通ネガティブプロンプト
        neg_prompt_layout = QVBoxLayout()
        self._common_neg_prompt_edit = QPlainTextEdit()
        self._common_neg_prompt_edit.setFixedHeight(40)
        self._common_neg_prompt_edit.setPlaceholderText("lowres, bad anatomy, worst quality...")
        self._common_neg_prompt_edit.setPlainText(self._settings.default_negative_prompt)
        neg_prompt_layout.addWidget(self._common_neg_prompt_edit)
        settings_layout.addRow("共通ネガティブ:", neg_prompt_layout)

        # IP-Adapter設定
        ip_layout = QHBoxLayout()
        self._use_ip_adapter_check = QCheckBox("IP-Adapter使用")
        self._use_ip_adapter_check.setChecked(True)
        self._use_ip_adapter_check.toggled.connect(self._on_ip_adapter_toggled)
        ip_layout.addWidget(self._use_ip_adapter_check)
        ip_layout.addWidget(QLabel("強度:"))
        self._ip_weight_slider = QSlider(Qt.Orientation.Horizontal)
        self._ip_weight_slider.setRange(0, 100)
        self._ip_weight_slider.setValue(80)
        self._ip_weight_slider.valueChanged.connect(self._on_ip_weight_changed)
        self._ip_weight_slider.setFixedWidth(100)
        ip_layout.addWidget(self._ip_weight_slider)
        self._ip_weight_label = QLabel("0.80")
        self._ip_weight_label.setFixedWidth(35)
        ip_layout.addWidget(self._ip_weight_label)
        ip_layout.addStretch()
        settings_layout.addRow("キャラクター参照:", ip_layout)

        # コマ形状に応じた自動サイズ調整
        self._auto_size_check = QCheckBox("コマ形状に応じてサイズを自動調整")
        self._auto_size_check.setChecked(True)
        self._auto_size_check.toggled.connect(self._on_auto_size_toggled)
        settings_layout.addRow("", self._auto_size_check)

        # 縦長コマ用サイズ
        portrait_layout = QHBoxLayout()
        self._portrait_width_spin = QSpinBox()
        self._portrait_width_spin.setRange(256, 2048)
        self._portrait_width_spin.setValue(832)
        self._portrait_width_spin.setSingleStep(64)
        portrait_layout.addWidget(self._portrait_width_spin)
        portrait_layout.addWidget(QLabel("x"))
        self._portrait_height_spin = QSpinBox()
        self._portrait_height_spin.setRange(256, 2048)
        self._portrait_height_spin.setValue(1216)
        self._portrait_height_spin.setSingleStep(64)
        portrait_layout.addWidget(self._portrait_height_spin)
        portrait_layout.addStretch()
        settings_layout.addRow("縦長コマ:", portrait_layout)

        # 横長コマ用サイズ
        landscape_layout = QHBoxLayout()
        self._landscape_width_spin = QSpinBox()
        self._landscape_width_spin.setRange(256, 2048)
        self._landscape_width_spin.setValue(1216)
        self._landscape_width_spin.setSingleStep(64)
        landscape_layout.addWidget(self._landscape_width_spin)
        landscape_layout.addWidget(QLabel("x"))
        self._landscape_height_spin = QSpinBox()
        self._landscape_height_spin.setRange(256, 2048)
        self._landscape_height_spin.setValue(832)
        self._landscape_height_spin.setSingleStep(64)
        landscape_layout.addWidget(self._landscape_height_spin)
        landscape_layout.addStretch()
        settings_layout.addRow("横長コマ:", landscape_layout)

        # 固定サイズ（自動調整OFF時に使用）
        size_layout = QHBoxLayout()
        self._width_spin = QSpinBox()
        self._width_spin.setRange(256, 2048)
        self._width_spin.setValue(832)
        self._width_spin.setSingleStep(64)
        self._width_spin.setEnabled(False)
        size_layout.addWidget(self._width_spin)
        size_layout.addWidget(QLabel("x"))
        self._height_spin = QSpinBox()
        self._height_spin.setRange(256, 2048)
        self._height_spin.setValue(1216)
        self._height_spin.setSingleStep(64)
        self._height_spin.setEnabled(False)
        size_layout.addWidget(self._height_spin)
        size_layout.addStretch()
        settings_layout.addRow("固定サイズ:", size_layout)

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

        layout.addWidget(settings_group)

        # プログレスバー
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        self._status_label = QLabel("")
        layout.addWidget(self._status_label)

        # ボタン
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._generate_btn = QPushButton("一括生成")
        self._generate_btn.setEnabled(False)
        self._generate_btn.clicked.connect(self._on_generate)
        btn_layout.addWidget(self._generate_btn)

        self._test_btn = QPushButton("テスト（画像なし）")
        self._test_btn.setEnabled(False)
        self._test_btn.clicked.connect(self._on_test_without_images)
        self._test_btn.setStyleSheet("background-color: #FF9800; color: white;")
        btn_layout.addWidget(self._test_btn)

        self._cancel_btn = QPushButton("キャンセル")
        self._cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self._cancel_btn)

        self._apply_btn = QPushButton("プロジェクトに反映")
        self._apply_btn.setEnabled(False)
        self._apply_btn.clicked.connect(self.accept)
        self._apply_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        btn_layout.addWidget(self._apply_btn)

        self._close_btn = QPushButton("閉じる")
        self._close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._close_btn)

        layout.addLayout(btn_layout)

    def _on_ip_adapter_toggled(self, checked: bool):
        """IP-Adapter使用のトグル"""
        self._ip_weight_slider.setEnabled(checked)
        self._ip_weight_label.setEnabled(checked)

    def _on_ip_weight_changed(self, value: int):
        """IP-Adapter強度変更"""
        self._ip_weight_label.setText(f"{value / 100:.2f}")

    def _on_auto_size_toggled(self, checked: bool):
        """自動サイズ調整のトグル"""
        # 縦長/横長サイズは常に有効
        self._portrait_width_spin.setEnabled(checked)
        self._portrait_height_spin.setEnabled(checked)
        self._landscape_width_spin.setEnabled(checked)
        self._landscape_height_spin.setEnabled(checked)
        # 固定サイズは自動調整OFF時のみ有効
        self._width_spin.setEnabled(not checked)
        self._height_spin.setEnabled(not checked)

    def _on_browse(self):
        """JSONファイル選択"""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "ストーリー仕様書を選択",
            "",
            "JSON Files (*.json);;All Files (*)"
        )

        if filepath:
            self._load_json(filepath)

    def _load_json(self, filepath: str):
        """JSONファイルを読み込み"""
        spec = StoryImportService.load_from_file(filepath)

        if not spec:
            QMessageBox.critical(
                self, "エラー",
                "JSONファイルの読み込みに失敗しました。\n形式を確認してください。"
            )
            return

        # バリデーション
        errors = StoryImportService.validate_spec(spec)
        if errors:
            error_text = "\n".join(errors[:10])
            if len(errors) > 10:
                error_text += f"\n... 他{len(errors) - 10}件のエラー"

            QMessageBox.warning(
                self, "警告",
                f"仕様書に問題があります:\n\n{error_text}"
            )

        self._story_spec = spec
        self._file_label.setText(f"ファイル: {filepath}")
        self._file_label.setStyleSheet("")
        self._generate_btn.setEnabled(True)
        self._test_btn.setEnabled(True)
        self._gen_char_btn.setEnabled(len(spec.characters) > 0)

        # 既存のキャラクター参照画像を確認
        self._load_existing_character_images()

        self._refresh_lists()
        self._status_label.setText(
            f"読み込み完了: {len(spec.characters)}キャラクター, "
            f"{len(spec.pages)}ページ"
        )

    def _load_existing_character_images(self):
        """既存のキャラクター参照画像を読み込み"""
        if not self._story_spec:
            return

        self._character_images.clear()
        for char in self._story_spec.characters:
            # 名前でCharacterServiceから検索
            existing = self._character_service.get_by_name(char.name)
            if existing and existing.reference_image_path:
                import os
                if os.path.exists(existing.reference_image_path):
                    self._character_images[char.id] = existing.reference_image_path

    def _on_generate_characters(self):
        """キャラクター画像生成ダイアログを開く"""
        if not self._story_spec:
            return

        # プロジェクト保存チェック
        image_path_service = ImagePathService.get_instance()
        characters_base_folder = None
        if image_path_service.get_images_base_folder():
            # プロジェクトが保存されている場合
            base = image_path_service.get_images_base_folder()
            if base:
                characters_base_folder = str(base / "characters")
        else:
            # プロジェクト未保存の場合は警告
            reply = QMessageBox.question(
                self, "プロジェクト未保存",
                "キャラクター画像をプロジェクトフォルダに保存するには、\n"
                "先にプロジェクトを保存する必要があります。\n\n"
                "プロジェクト保存後に再度お試しください。\n"
                "（一時フォルダに保存して続行することもできます）\n\n"
                "一時フォルダに保存して続行しますか？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            # 一時フォルダに保存する場合はcharacters_base_folderはNoneのまま

        from src.views.dialogs.character_generation_dialog import CharacterGenerationDialog
        dialog = CharacterGenerationDialog(
            self._story_spec,
            characters_base_folder=characters_base_folder,
            parent=self
        )

        if dialog.exec():
            # 生成された画像を保存
            self._character_images.update(dialog.get_confirmed_images())
            self._load_existing_character_images()  # サービスから再読み込み
            self._refresh_lists()
            self._status_label.setText("キャラクター画像を登録しました")

    def _refresh_lists(self):
        """リストを更新"""
        if not self._story_spec:
            return

        # キャラクター一覧
        self._char_list.clear()
        for char in self._story_spec.characters:
            item = QListWidgetItem()

            # 参照画像がある場合はアイコン表示
            if char.id in self._character_images:
                pixmap = QPixmap(self._character_images[char.id])
                if not pixmap.isNull():
                    scaled = pixmap.scaled(
                        48, 48,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    item.setIcon(QIcon(scaled))
                item.setText(f"{char.name} [参照画像あり]")
                item.setForeground(Qt.GlobalColor.green)
            else:
                item.setText(f"{char.name} ({char.id})")

            item.setData(Qt.ItemDataRole.UserRole, char)
            self._char_list.addItem(item)

        # ページ/コマ一覧
        self._page_list.clear()
        for page in self._story_spec.pages:
            # ページヘッダー
            page_item = QListWidgetItem(f"📄 ページ {page.page_number}")
            page_item.setData(Qt.ItemDataRole.UserRole, page)
            font = page_item.font()
            font.setBold(True)
            page_item.setFont(font)
            self._page_list.addItem(page_item)

            # コマ
            for panel in page.panels:
                desc = panel.scene_description[:30] if panel.scene_description else "(説明なし)"
                if len(panel.scene_description) > 30:
                    desc += "..."
                panel_item = QListWidgetItem(f"    コマ{panel.panel_index + 1}: {desc}")
                panel_item.setData(Qt.ItemDataRole.UserRole, (page, panel))
                self._page_list.addItem(panel_item)

    def _on_char_selected(self, item: QListWidgetItem):
        """キャラクター選択時"""
        char = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(char, StoryCharacter):
            text = f"""【キャラクター情報】

ID: {char.id}
名前: {char.name}

外見:
{char.appearance}

性格:
{char.personality}

プロンプト:
{char.prompt}
"""
            self._detail_text.setText(text)

    def _on_panel_selected(self, item: QListWidgetItem):
        """コマ選択時"""
        data = item.data(Qt.ItemDataRole.UserRole)

        if isinstance(data, StoryPage):
            # ページ選択
            text = f"""【ページ情報】

ページ番号: {data.page_number}
テンプレート: {data.template}
コマ数: {len(data.panels)}
"""
            self._detail_text.setText(text)

        elif isinstance(data, tuple):
            page, panel = data
            # コマ選択
            dialogues_text = ""
            if panel.dialogues:
                for d in panel.dialogues:
                    speaker = d.speaker if d.speaker else "(ナレーション)"
                    bubble_info = f"[{d.bubble_type}]" if d.bubble_type != "SPEECH" else ""
                    dialogues_text += f"  {speaker}: 「{d.text}」{bubble_info}\n"

            text = f"""【コマ情報】

ページ: {page.page_number}
コマ: {panel.panel_index + 1}
構図: {panel.composition}

シーン説明:
{panel.scene_description}

登場キャラクター:
{", ".join(panel.characters) if panel.characters else "(なし)"}

セリフ:
{dialogues_text if dialogues_text else "(なし)"}

プロンプト:
{panel.prompt}

ネガティブプロンプト:
{panel.negative_prompt}
"""
            self._detail_text.setText(text)

    def _on_generate(self):
        """一括生成開始"""
        if not self._story_spec:
            return

        if self._worker and self._worker.isRunning():
            return

        # プロジェクト保存チェック
        image_path_service = ImagePathService.get_instance()
        save_base_folder = None
        if image_path_service.get_images_base_folder():
            # プロジェクトが保存されている場合
            save_base_folder = str(image_path_service.get_images_base_folder())
        else:
            # プロジェクト未保存の場合は警告
            reply = QMessageBox.question(
                self, "プロジェクト未保存",
                "画像をプロジェクトフォルダに保存するには、\n"
                "先にプロジェクトを保存する必要があります。\n\n"
                "一時フォルダに保存して続行しますか？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            # 一時フォルダに保存する場合はsave_base_folderはNoneのまま

        # UI更新
        self._generate_btn.setEnabled(False)
        self._browse_btn.setEnabled(False)
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(0)

        # ワーカー作成
        auto_size = self._auto_size_check.isChecked()
        self._worker = BatchGenerationWorker(
            story_spec=self._story_spec,
            width=self._width_spin.value(),
            height=self._height_spin.value(),
            steps=self._steps_spin.value(),
            cfg_scale=self._cfg_spin.value(),
            sampler_name=self._sampler_combo.currentText(),
            use_ip_adapter=self._use_ip_adapter_check.isChecked(),
            ip_adapter_weight=self._ip_weight_slider.value() / 100,
            common_prompt=self._common_prompt_edit.toPlainText().strip(),
            common_negative_prompt=self._common_neg_prompt_edit.toPlainText().strip(),
            portrait_size=(
                self._portrait_width_spin.value(),
                self._portrait_height_spin.value()
            ),
            landscape_size=(
                self._landscape_width_spin.value(),
                self._landscape_height_spin.value()
            ),
            auto_size=auto_size,
            save_base_folder=save_base_folder,
            use_adetailer=True,  # 複数キャラ時は顔補正を有効化
            split_direction="Columns",  # 複数キャラ時の分割方向（横並び）
            parent=self
        )

        self._worker.progress.connect(self._on_progress)
        self._worker.panel_generated.connect(self._on_panel_generated)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_progress(self, current: int, total: int, message: str):
        """進捗更新"""
        self._progress_bar.setMaximum(total)
        self._progress_bar.setValue(current)
        self._status_label.setText(message)

    def _on_panel_generated(self, panel: GeneratedPanel):
        """コマ生成完了"""
        self._generated_panels.append(panel)

    def _on_finished(self, success: bool, message: str, panels: list):
        """生成完了"""
        self._progress_bar.setVisible(False)
        self._generate_btn.setEnabled(True)
        self._browse_btn.setEnabled(True)
        self._status_label.setText(message)

        if success and panels:
            self._generated_panels = panels
            self._apply_btn.setEnabled(True)
            QMessageBox.information(
                self, "完了",
                f"{len(panels)}枚の画像を生成しました。\n"
                "「プロジェクトに反映」ボタンを押してプロジェクトに適用してください。"
            )

    def _on_test_without_images(self):
        """画像生成なしでテスト（デバッグ用）"""
        if not self._story_spec:
            return

        # ページをpage_numberでソート（BatchGenerationWorkerと同じ順序）
        sorted_pages = sorted(self._story_spec.pages, key=lambda p: p.page_number)

        # デバッグ出力
        print(f"[Test] Total pages: {len(sorted_pages)}")
        for i, p in enumerate(sorted_pages):
            print(f"[Test]   sorted_pages[{i}]: page_number={p.page_number}, panels={len(p.panels)}")

        # ダミーのGeneratedPanelリストを作成
        self._generated_panels = []
        for page_idx, page in enumerate(sorted_pages):
            sorted_panels = sorted(page.panels, key=lambda p: p.panel_index)
            for panel_idx, panel in enumerate(sorted_panels):
                print(f"[Test] Creating dummy panel: page_idx={page_idx}, panel_idx={panel_idx}")
                dummy_panel = GeneratedPanel(
                    page_index=page_idx,
                    panel_index=panel_idx,
                    image_path="",  # 空のパス（画像なし）
                    prompt=panel.prompt,
                    negative_prompt=panel.negative_prompt,
                    seed="-1",
                    character_ids=panel.characters
                )
                self._generated_panels.append(dummy_panel)

        self._apply_btn.setEnabled(True)
        self._status_label.setText(
            f"テストモード: {len(self._generated_panels)}コマ分のダミーデータを作成しました"
        )
        print(f"[Test] Created {len(self._generated_panels)} dummy panels")

    def _on_cancel(self):
        """キャンセル"""
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._status_label.setText("キャンセル中...")
        else:
            self.reject()

    def get_story_spec(self) -> Optional[StorySpec]:
        """ストーリー仕様書を取得"""
        return self._story_spec

    def get_generated_panels(self) -> List[GeneratedPanel]:
        """生成されたコマ一覧を取得"""
        return self._generated_panels

    def closeEvent(self, event):
        """ダイアログ閉じる時"""
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait()
        super().closeEvent(event)
