"""AI画像生成ダイアログ"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QLineEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox,
    QPushButton, QComboBox, QCheckBox, QFileDialog,
    QProgressBar, QMessageBox, QSlider, QSizePolicy,
    QScrollArea, QWidget, QFrame, QButtonGroup, QRadioButton
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QImage, QIcon, QPixmapCache

from src.services.settings_service import SettingsService
from src.services.forge_service import ForgeService
from src.services.character_service import CharacterService
from src.workers.generation_worker import GenerationWorker
from src.models.character import Character
from typing import Optional, Tuple, List


class ImageGenDialog(QDialog):
    """AI画像生成ダイアログ"""

    def __init__(
        self,
        panel_size: Optional[Tuple[int, int]] = None,
        save_folder: Optional[str] = None,
        default_browse_path: Optional[str] = None,
        parent=None
    ):
        super().__init__(parent)
        self._settings = SettingsService.get_instance()
        self._character_service = CharacterService.get_instance()
        self._workers: list = []
        self._pending_count = 0
        self._current_worker_index = 0
        self._generated_image_path: Optional[str] = None
        self._generated_images: list = []
        self._thumbnail_buttons: list = []
        self._panel_size = panel_size  # コマのサイズ (width, height)
        self._pose_image_path: Optional[str] = None
        self._save_folder = save_folder  # 画像保存先フォルダ
        self._default_browse_path = default_browse_path or ""  # ファイル選択のデフォルトパス
        # 一括生成モード（再生成時に同じロジックを使うため）
        self._batch_mode = False
        self._batch_final_prompt: Optional[str] = None
        self._batch_final_negative_prompt: Optional[str] = None
        self._batch_character_ids: List[str] = []

        self.setWindowTitle("AI画像生成")
        self.setMinimumSize(600, 650)
        self.resize(700, 750)
        self._setup_ui()
        self._load_defaults()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # スクロールエリアを追加
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(6)

        # プロンプト入力（コンパクト化）
        prompt_group = QGroupBox("プロンプト")
        prompt_layout = QVBoxLayout(prompt_group)
        prompt_layout.setSpacing(4)

        # ポジティブプロンプト（共通 + コマ別を横に並べる）
        pos_row = QHBoxLayout()
        pos_row.setSpacing(8)

        pos_left = QVBoxLayout()
        pos_left.addWidget(QLabel("共通 (常に適用):"))
        self._common_prompt_edit = QPlainTextEdit()
        self._common_prompt_edit.setFixedHeight(45)
        self._common_prompt_edit.setPlaceholderText("masterpiece, best quality...")
        pos_left.addWidget(self._common_prompt_edit)
        pos_row.addLayout(pos_left, 1)

        pos_right = QVBoxLayout()
        pos_right.addWidget(QLabel("コマ別:"))
        self._prompt_edit = QPlainTextEdit()
        self._prompt_edit.setFixedHeight(45)
        self._prompt_edit.setPlaceholderText("1girl, smile...")
        pos_right.addWidget(self._prompt_edit)
        pos_row.addLayout(pos_right, 1)

        prompt_layout.addLayout(pos_row)

        # ネガティブプロンプト（共通 + コマ別を横に並べる）
        neg_row = QHBoxLayout()
        neg_row.setSpacing(8)

        neg_left = QVBoxLayout()
        neg_left.addWidget(QLabel("ネガティブ (共通):"))
        self._common_neg_prompt_edit = QPlainTextEdit()
        self._common_neg_prompt_edit.setFixedHeight(35)
        self._common_neg_prompt_edit.setPlaceholderText("lowres, bad anatomy...")
        neg_left.addWidget(self._common_neg_prompt_edit)
        neg_row.addLayout(neg_left, 1)

        neg_right = QVBoxLayout()
        neg_right.addWidget(QLabel("ネガティブ (コマ別):"))
        self._neg_prompt_edit = QPlainTextEdit()
        self._neg_prompt_edit.setFixedHeight(35)
        self._neg_prompt_edit.setPlaceholderText("text, watermark...")
        neg_right.addWidget(self._neg_prompt_edit)
        neg_row.addLayout(neg_right, 1)

        prompt_layout.addLayout(neg_row)
        layout.addWidget(prompt_group)

        # キャラクター設定とポーズ設定を横に並べる
        char_pose_row = QHBoxLayout()
        char_pose_row.setSpacing(8)

        # キャラクター設定
        char_group = QGroupBox("キャラクター")
        char_layout = QVBoxLayout(char_group)
        char_layout.setSpacing(4)

        # モード切り替え
        mode_row = QHBoxLayout()
        self._multi_char_check = QCheckBox("複数キャラクター")
        self._multi_char_check.toggled.connect(self._on_multi_char_toggled)
        mode_row.addWidget(self._multi_char_check)
        self._manage_char_btn = QPushButton("管理")
        self._manage_char_btn.setFixedWidth(50)
        self._manage_char_btn.clicked.connect(self._on_manage_characters)
        mode_row.addWidget(self._manage_char_btn)
        char_layout.addLayout(mode_row)

        # 単一キャラクター用コンテナ
        self._single_char_widget = QWidget()
        single_char_layout = QVBoxLayout(self._single_char_widget)
        single_char_layout.setContentsMargins(0, 0, 0, 0)
        single_char_layout.setSpacing(4)

        char_row = QHBoxLayout()
        self._character_combo = QComboBox()
        self._character_combo.currentIndexChanged.connect(self._on_character_changed)
        char_row.addWidget(self._character_combo, 1)
        single_char_layout.addLayout(char_row)

        weight_row = QHBoxLayout()
        weight_row.addWidget(QLabel("強度:"))
        self._ip_weight_slider = QSlider(Qt.Orientation.Horizontal)
        self._ip_weight_slider.setRange(0, 100)
        self._ip_weight_slider.setValue(80)
        self._ip_weight_slider.valueChanged.connect(self._on_ip_weight_changed)
        weight_row.addWidget(self._ip_weight_slider)
        self._ip_weight_label = QLabel("0.80")
        self._ip_weight_label.setFixedWidth(35)
        weight_row.addWidget(self._ip_weight_label)
        single_char_layout.addLayout(weight_row)
        char_layout.addWidget(self._single_char_widget)

        # 複数キャラクター用コンテナ
        self._multi_char_widget = QWidget()
        multi_char_layout = QVBoxLayout(self._multi_char_widget)
        multi_char_layout.setContentsMargins(0, 0, 0, 0)
        multi_char_layout.setSpacing(2)

        # 複数キャラクター選択（最大4人）
        self._multi_char_combos: List[QComboBox] = []
        self._multi_char_prompt_edits: List[QLineEdit] = []
        for i in range(4):
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{i+1}:"))
            combo = QComboBox()
            combo.setMinimumWidth(100)
            row.addWidget(combo, 1)
            prompt_edit = QLineEdit()
            prompt_edit.setPlaceholderText(f"キャラ{i+1}の特徴...")
            prompt_edit.setMaximumWidth(150)
            row.addWidget(prompt_edit)
            multi_char_layout.addLayout(row)
            self._multi_char_combos.append(combo)
            self._multi_char_prompt_edits.append(prompt_edit)

        # 分割方向とADetailer設定
        options_row = QHBoxLayout()
        options_row.addWidget(QLabel("分割:"))
        self._split_direction_combo = QComboBox()
        self._split_direction_combo.addItems(["横 (Columns)", "縦 (Rows)"])
        options_row.addWidget(self._split_direction_combo)
        self._adetailer_check = QCheckBox("顔補正")
        self._adetailer_check.setChecked(True)
        self._adetailer_check.setToolTip("ADetailerで顔を自動補正")
        options_row.addWidget(self._adetailer_check)
        options_row.addStretch()
        multi_char_layout.addLayout(options_row)

        char_layout.addWidget(self._multi_char_widget)
        self._multi_char_widget.hide()  # 初期は非表示

        char_pose_row.addWidget(char_group, 1)

        # ポーズ設定
        pose_group = QGroupBox("ポーズ (ControlNet)")
        pose_layout = QVBoxLayout(pose_group)
        pose_layout.setSpacing(4)

        pose_btn_row = QHBoxLayout()
        self._pose_path_label = QLabel("未選択")
        self._pose_path_label.setStyleSheet("color: gray;")
        pose_btn_row.addWidget(self._pose_path_label, 1)
        self._pose_select_btn = QPushButton("選択")
        self._pose_select_btn.setFixedWidth(50)
        self._pose_select_btn.clicked.connect(self._on_select_pose_image)
        pose_btn_row.addWidget(self._pose_select_btn)
        self._pose_clear_btn = QPushButton("×")
        self._pose_clear_btn.setFixedWidth(25)
        self._pose_clear_btn.clicked.connect(self._on_clear_pose_image)
        pose_btn_row.addWidget(self._pose_clear_btn)
        pose_layout.addLayout(pose_btn_row)

        # ポーズプレビュー（小さく）
        self._pose_preview = QLabel()
        self._pose_preview.setFixedSize(60, 60)
        self._pose_preview.setStyleSheet("border: 1px solid #ccc; background: #f0f0f0;")
        self._pose_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)

        cn_row = QHBoxLayout()
        cn_row.addWidget(self._pose_preview)
        cn_inner = QVBoxLayout()
        cn_weight_row = QHBoxLayout()
        cn_weight_row.addWidget(QLabel("強度:"))
        self._cn_weight_slider = QSlider(Qt.Orientation.Horizontal)
        self._cn_weight_slider.setRange(0, 100)
        self._cn_weight_slider.setValue(100)
        self._cn_weight_slider.valueChanged.connect(self._on_cn_weight_changed)
        cn_weight_row.addWidget(self._cn_weight_slider)
        self._cn_weight_label = QLabel("1.00")
        self._cn_weight_label.setFixedWidth(35)
        cn_weight_row.addWidget(self._cn_weight_label)
        cn_inner.addLayout(cn_weight_row)
        cn_inner.addStretch()
        cn_row.addLayout(cn_inner, 1)
        pose_layout.addLayout(cn_row)

        char_pose_row.addWidget(pose_group, 1)
        layout.addLayout(char_pose_row)

        # サイズ設定と詳細設定を横に並べる
        settings_row = QHBoxLayout()
        settings_row.setSpacing(8)

        # サイズ設定
        size_group = QGroupBox("生成サイズ")
        size_layout = QVBoxLayout(size_group)
        size_layout.setSpacing(4)

        self._size_preset_combo = QComboBox()
        self._size_presets = [
            ("832x1216 (縦・推奨)", 832, 1216),
            ("1216x832 (横・推奨)", 1216, 832),
            ("768x1344 (縦)", 768, 1344),
            ("1344x768 (横)", 1344, 768),
            ("1024x1024 (正方形)", 1024, 1024),
            ("896x1152 (縦)", 896, 1152),
            ("512x768 (小・縦)", 512, 768),
            ("カスタム", 0, 0),
        ]
        for name, w, h in self._size_presets:
            self._size_preset_combo.addItem(name)
        self._size_preset_combo.currentIndexChanged.connect(self._on_size_preset_changed)
        size_layout.addWidget(self._size_preset_combo)

        size_inner = QHBoxLayout()
        size_inner.addWidget(QLabel("W:"))
        self._width_spin = QSpinBox()
        self._width_spin.setRange(256, 2048)
        self._width_spin.setSingleStep(64)
        self._width_spin.valueChanged.connect(self._on_size_manually_changed)
        size_inner.addWidget(self._width_spin)
        size_inner.addWidget(QLabel("H:"))
        self._height_spin = QSpinBox()
        self._height_spin.setRange(256, 2048)
        self._height_spin.setSingleStep(64)
        self._height_spin.valueChanged.connect(self._on_size_manually_changed)
        size_inner.addWidget(self._height_spin)
        size_layout.addLayout(size_inner)

        self._match_panel_check = QCheckBox("コマサイズに合わせる")
        self._match_panel_check.toggled.connect(self._on_match_panel_toggled)
        size_layout.addWidget(self._match_panel_check)

        settings_row.addWidget(size_group, 1)

        # 詳細設定
        detail_group = QGroupBox("詳細設定")
        detail_layout = QVBoxLayout(detail_group)
        detail_layout.setSpacing(4)

        steps_row = QHBoxLayout()
        steps_row.addWidget(QLabel("Steps:"))
        self._steps_spin = QSpinBox()
        self._steps_spin.setRange(1, 150)
        steps_row.addWidget(self._steps_spin)
        steps_row.addWidget(QLabel("CFG:"))
        self._cfg_spin = QDoubleSpinBox()
        self._cfg_spin.setRange(1.0, 30.0)
        self._cfg_spin.setSingleStep(0.5)
        steps_row.addWidget(self._cfg_spin)
        detail_layout.addLayout(steps_row)

        seed_row = QHBoxLayout()
        seed_row.addWidget(QLabel("Seed:"))
        self._seed_spin = QSpinBox()
        self._seed_spin.setRange(-1, 2147483647)
        self._seed_spin.setValue(-1)
        self._seed_spin.setSpecialValueText("ランダム")
        seed_row.addWidget(self._seed_spin, 1)
        detail_layout.addLayout(seed_row)

        batch_row = QHBoxLayout()
        batch_row.addWidget(QLabel("枚数:"))
        self._batch_spin = QSpinBox()
        self._batch_spin.setRange(1, 4)
        self._batch_spin.setValue(1)
        batch_row.addWidget(self._batch_spin, 1)
        detail_layout.addLayout(batch_row)

        settings_row.addWidget(detail_group, 1)
        layout.addLayout(settings_row)

        # プレビュー
        preview_group = QGroupBox("プレビュー")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setSpacing(4)

        # サムネイルグリッド（横に並べる）
        self._thumbnail_container = QWidget()
        self._thumbnail_layout = QHBoxLayout(self._thumbnail_container)
        self._thumbnail_layout.setContentsMargins(0, 0, 0, 0)
        self._thumbnail_layout.setSpacing(8)

        thumb_scroll = QScrollArea()
        thumb_scroll.setWidgetResizable(True)
        thumb_scroll.setWidget(self._thumbnail_container)
        thumb_scroll.setFixedHeight(130)
        thumb_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        thumb_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        preview_layout.addWidget(thumb_scroll)

        # 選択中の画像表示
        self._selected_preview = QLabel()
        self._selected_preview.setMinimumSize(200, 180)
        self._selected_preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._selected_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._selected_preview.setStyleSheet("border: 1px solid #ccc; background: #222;")
        self._selected_preview.setText("生成画像がここに表示されます")
        preview_layout.addWidget(self._selected_preview, 1)

        # 進捗表示
        self._progress_bar = QProgressBar()
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFormat("")
        self._progress_bar.setRange(0, 0)
        self._progress_bar.hide()
        preview_layout.addWidget(self._progress_bar)

        self._status_label = QLabel("")
        preview_layout.addWidget(self._status_label)

        layout.addWidget(preview_group, 1)

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area, 1)

        # ボタン（スクロール外に固定）
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 4, 0, 0)
        self._generate_btn = QPushButton("生成")
        self._generate_btn.clicked.connect(self._on_generate)
        btn_layout.addWidget(self._generate_btn)

        self._apply_btn = QPushButton("コマに配置")
        self._apply_btn.clicked.connect(self._on_apply)
        self._apply_btn.setEnabled(False)
        btn_layout.addWidget(self._apply_btn)

        self._cancel_btn = QPushButton("キャンセル")
        self._cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self._cancel_btn)

        main_layout.addLayout(btn_layout)

    def _load_defaults(self):
        """デフォルト値を読み込み"""
        # 共通プロンプトは設定から読み込み
        self._common_prompt_edit.setPlainText(self._settings.default_prompt)
        self._common_neg_prompt_edit.setPlainText(self._settings.default_negative_prompt)
        # コマ別プロンプトは空で開始
        self._prompt_edit.clear()
        self._neg_prompt_edit.clear()
        self._steps_spin.setValue(self._settings.default_steps)
        self._cfg_spin.setValue(self._settings.default_cfg_scale)

        # サイズ設定：設定から推奨プリセットを読み込み
        default_preset = self._settings.default_gen_size_preset
        if default_preset < 0 or default_preset >= len(self._size_presets) - 1:
            default_preset = 0  # 無効な値の場合は推奨（832x1216）に

        if self._panel_size:
            self._match_panel_check.setEnabled(True)
        else:
            self._match_panel_check.setEnabled(False)

        # デフォルトは推奨サイズを設定
        self._size_preset_combo.setCurrentIndex(default_preset)
        _, w, h = self._size_presets[default_preset]
        self._width_spin.setValue(w)
        self._height_spin.setValue(h)

        # キャラクターリスト更新
        self._refresh_character_list()

    def _refresh_character_list(self):
        """キャラクターリストを更新"""
        # 単一キャラクター用
        self._character_combo.clear()
        self._character_combo.addItem("なし", None)

        characters = self._character_service.get_all()
        for char in characters:
            self._character_combo.addItem(char.name, char)

        # 複数キャラクター用
        for combo in self._multi_char_combos:
            combo.clear()
            combo.addItem("なし", None)
            for char in characters:
                combo.addItem(char.name, char)

    def _on_multi_char_toggled(self, checked: bool):
        """複数キャラクターモード切り替え"""
        self._single_char_widget.setVisible(not checked)
        self._multi_char_widget.setVisible(checked)

        # 複数キャラクターモードでは解像度を推奨値に変更
        if checked:
            # 複数人向け推奨解像度（小さめで安定）
            self._width_spin.setValue(768)
            self._height_spin.setValue(512)
            # プリセットを「カスタム」に
            self._size_preset_combo.setCurrentIndex(len(self._size_presets) - 1)

    def _get_selected_characters(self) -> List[Tuple[Optional[Character], str]]:
        """選択されたキャラクターと個別プロンプトを取得"""
        result = []
        for i, combo in enumerate(self._multi_char_combos):
            char = combo.currentData()
            prompt = self._multi_char_prompt_edits[i].text().strip()
            if char is not None or prompt:
                result.append((char if isinstance(char, Character) else None, prompt))
        return result

    def _on_character_changed(self, index):
        """キャラクター選択変更"""
        char = self._character_combo.itemData(index)
        if char and isinstance(char, Character):
            self._ip_weight_slider.setValue(int(char.ip_adapter_weight * 100))

    def _on_ip_weight_changed(self, value):
        """IP-Adapter強度変更"""
        self._ip_weight_label.setText(f"{value / 100:.2f}")

    def _on_cn_weight_changed(self, value):
        """ControlNet強度変更"""
        self._cn_weight_label.setText(f"{value / 100:.2f}")

    def _on_size_preset_changed(self, index):
        """サイズプリセット変更"""
        if index < 0 or index >= len(self._size_presets):
            return
        name, w, h = self._size_presets[index]
        if w > 0 and h > 0:
            self._width_spin.blockSignals(True)
            self._height_spin.blockSignals(True)
            self._width_spin.setValue(w)
            self._height_spin.setValue(h)
            self._width_spin.blockSignals(False)
            self._height_spin.blockSignals(False)

    def _on_size_manually_changed(self):
        """サイズ手動変更時にプリセットを「カスタム」に"""
        w = self._width_spin.value()
        h = self._height_spin.value()
        # 現在のプリセットと一致するか確認
        for i, (name, pw, ph) in enumerate(self._size_presets):
            if pw == w and ph == h:
                self._size_preset_combo.blockSignals(True)
                self._size_preset_combo.setCurrentIndex(i)
                self._size_preset_combo.blockSignals(False)
                return
        # 一致しない場合は「カスタム」に
        self._size_preset_combo.blockSignals(True)
        self._size_preset_combo.setCurrentIndex(len(self._size_presets) - 1)
        self._size_preset_combo.blockSignals(False)

    def _on_select_pose_image(self):
        """ポーズ画像選択"""
        path, _ = QFileDialog.getOpenFileName(
            self, "ポーズ画像を選択",
            self._default_browse_path,
            "画像ファイル (*.png *.jpg *.jpeg *.bmp)"
        )
        if path:
            self._pose_image_path = path
            self._pose_path_label.setText(path.split('/')[-1].split('\\')[-1])
            self._pose_path_label.setStyleSheet("")

            # プレビュー表示
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    100, 100,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self._pose_preview.setPixmap(scaled)

    def _on_clear_pose_image(self):
        """ポーズ画像クリア"""
        self._pose_image_path = None
        self._pose_path_label.setText("未選択")
        self._pose_path_label.setStyleSheet("color: gray;")
        self._pose_preview.clear()

    def _on_match_panel_toggled(self, checked):
        """コマサイズに合わせるトグル"""
        if checked and self._panel_size:
            w, h = self._panel_size
            w = ((w + 31) // 64) * 64
            h = ((h + 31) // 64) * 64
            w = max(256, min(2048, w))
            h = max(256, min(2048, h))
            self._width_spin.setValue(w)
            self._height_spin.setValue(h)

    def _on_manage_characters(self):
        """キャラクター管理ダイアログを開く"""
        from src.views.dialogs.character_manager_dialog import CharacterManagerDialog
        dialog = CharacterManagerDialog(self)
        if dialog.exec():
            self._refresh_character_list()

    def _on_generate(self):
        """生成開始"""
        if hasattr(self, '_workers') and any(w.isRunning() for w in self._workers):
            return

        # 古いワーカーをクリーンアップ
        if hasattr(self, '_workers'):
            for worker in self._workers:
                try:
                    worker.progress.disconnect()
                    worker.finished.disconnect()
                except (TypeError, RuntimeError):
                    pass  # 既に切断されている場合
                worker.deleteLater()
            self._workers = []

        # プロンプトを結合（コマ別 + 共通）※主題を先に、品質タグを後に
        common_prompt = self._common_prompt_edit.toPlainText().strip()
        panel_prompt = self._prompt_edit.toPlainText().strip()

        # 最終プロンプトを構築（コマ別が先、共通が後）
        prompt_parts = [p for p in [panel_prompt, common_prompt] if p]
        prompt = ", ".join(prompt_parts)

        # バリデーション（共通またはコマ別どちらかは必要）
        if not prompt:
            QMessageBox.warning(self, "エラー", "プロンプトを入力してください")
            return

        # ネガティブプロンプトも結合
        common_neg = self._common_neg_prompt_edit.toPlainText().strip()
        panel_neg = self._neg_prompt_edit.toPlainText().strip()
        neg_prompt_parts = [p for p in [common_neg, panel_neg] if p]
        negative_prompt = ", ".join(neg_prompt_parts)

        # 共通プロンプトを設定に保存（次回以降も使用）
        if common_prompt != self._settings.default_prompt:
            self._settings.default_prompt = common_prompt
        if common_neg != self._settings.default_negative_prompt:
            self._settings.default_negative_prompt = common_neg

        # 既存のサムネイルをクリア
        self._clear_thumbnails()

        # 複数キャラクターモードか判定
        # batch_modeの場合は強制的に無効化（一括生成と同じロジックを使う）
        is_multi_char = self._multi_char_check.isChecked() and not self._batch_mode

        # キャラクター取得
        char = None
        characters = []
        if self._batch_mode:
            # 一括生成モード：キャラクター外見は既にプロンプトに含まれている
            # IP-Adapter用に参照画像のみ取得
            char = None  # 外見タグ追加をスキップ
        elif is_multi_char:
            # 複数キャラクターモード
            characters = self._get_selected_characters()
            if not characters:
                QMessageBox.warning(self, "エラー", "少なくとも1つのキャラクターまたはプロンプトを指定してください")
                return
        else:
            # 単一キャラクターモード
            char = self._character_combo.currentData()

        # ControlNetモデル（ポーズ画像がある場合）
        controlnet_model = ""
        if self._pose_image_path:
            controlnet_model = "control_v11p_sd15_openpose [cab727d4]"

        # 分割方向を取得
        split_direction = "Columns" if self._split_direction_combo.currentIndex() == 0 else "Rows"

        # batch_mode時のIP-Adapter参照画像パスを取得
        batch_ip_adapter_path = None
        batch_ip_adapter_weight = self._ip_weight_slider.value() / 100
        if self._batch_mode and self._batch_character_ids:
            # キャラクターIDから参照画像を取得（最初のキャラクター）
            for char_id in self._batch_character_ids:
                char = self._character_service.get_by_id(char_id)
                if char and char.reference_image_path:
                    import os
                    if os.path.exists(char.reference_image_path):
                        batch_ip_adapter_path = char.reference_image_path
                        batch_ip_adapter_weight = char.ip_adapter_weight
                        print(f"[ImageGenDialog] batch_mode IP-Adapter: {char.name}")
                        break

        # 生成枚数
        batch_count = self._batch_spin.value()
        self._pending_count = batch_count
        self._workers = []

        # UI更新
        self._generate_btn.setEnabled(False)
        self._apply_btn.setEnabled(False)
        self._progress_bar.show()
        mode_text = "複数キャラクター" if is_multi_char else "通常"
        self._status_label.setText(f"生成を開始しています ({mode_text})... (0/{batch_count})")

        # 複数ワーカーを作成して順次実行
        base_seed = self._seed_spin.value()
        for i in range(batch_count):
            # シードを変える（-1以外の場合）
            seed = base_seed if base_seed == -1 else base_seed + i

            worker = GenerationWorker(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=self._width_spin.value(),
                height=self._height_spin.value(),
                steps=self._steps_spin.value(),
                cfg_scale=self._cfg_spin.value(),
                seed=seed,
                sampler_name=self._settings.default_sampler,
                character=char if isinstance(char, Character) else None,
                pose_image_path=self._pose_image_path,
                controlnet_model=controlnet_model,
                controlnet_weight=self._cn_weight_slider.value() / 100,
                # 複数キャラクターモード用パラメータ
                multi_char_mode=is_multi_char,
                characters=characters,
                split_direction=split_direction,
                use_adetailer=self._adetailer_check.isChecked() if is_multi_char else False,
                # 保存先フォルダ
                save_folder=self._save_folder,
                # 一括生成モード
                batch_mode=self._batch_mode,
                ip_adapter_image_path=batch_ip_adapter_path,
                ip_adapter_weight=batch_ip_adapter_weight,
                parent=self
            )

            worker.progress.connect(self._on_progress)
            worker.finished.connect(self._on_generation_finished)
            self._workers.append(worker)

        # 最初のワーカーを開始（1つずつ順次実行）
        self._current_worker_index = 0
        self._start_next_worker()

    def _start_next_worker(self):
        """次のワーカーを開始"""
        if self._current_worker_index < len(self._workers):
            batch_count = len(self._workers)
            self._status_label.setText(f"生成中... ({self._current_worker_index + 1}/{batch_count})")
            self._workers[self._current_worker_index].finished.connect(self._on_worker_finished)
            self._workers[self._current_worker_index].start()

    def _on_worker_finished(self):
        """1つのワーカーが完了"""
        self._current_worker_index += 1
        if self._current_worker_index < len(self._workers):
            self._start_next_worker()

    def _on_progress(self, message: str):
        """進捗更新"""
        self._status_label.setText(message)

    def _on_generation_finished(self, success: bool, result: str, seed: str):
        """生成完了"""
        self._pending_count -= 1

        if success:
            # 画像をリストに追加
            self._generated_images.append(result)
            self._add_thumbnail(result, seed)

            # 最初の画像なら選択状態にする
            if len(self._generated_images) == 1:
                self._select_image(0)

            self._status_label.setText(f"生成完了 ({len(self._generated_images)}枚) - Seed: {seed}")
            self._apply_btn.setEnabled(True)

            # シード値を更新（32bit整数の範囲内のみ）
            if seed:
                try:
                    seed_int = int(seed)
                    if -1 <= seed_int <= 2147483647:
                        self._seed_spin.setValue(seed_int)
                except (ValueError, OverflowError):
                    pass
        else:
            self._status_label.setText(f"エラー: {result}")

        # 全て完了したら
        if self._pending_count <= 0:
            self._generate_btn.setEnabled(True)
            self._progress_bar.hide()
            if not self._generated_images:
                QMessageBox.warning(self, "生成エラー", result)

    def _add_thumbnail(self, image_path: str, seed: str):
        """サムネイルを追加"""
        btn = QPushButton()
        btn.setFixedSize(110, 110)
        btn.setStyleSheet("""
            QPushButton { border: 2px solid #555; background: #333; }
            QPushButton:hover { border: 2px solid #888; }
            QPushButton:checked { border: 3px solid #4CAF50; }
        """)
        btn.setCheckable(True)

        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                100, 100,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            btn.setIcon(QIcon(scaled))
            btn.setIconSize(QSize(100, 100))

        index = len(self._thumbnail_buttons)
        btn.clicked.connect(lambda checked, idx=index: self._select_image(idx))
        self._thumbnail_buttons.append(btn)
        self._thumbnail_layout.addWidget(btn)

    def _select_image(self, index: int):
        """画像を選択"""
        if index < 0 or index >= len(self._generated_images):
            return

        # 選択状態を更新
        for i, btn in enumerate(self._thumbnail_buttons):
            btn.setChecked(i == index)

        # 選択画像を保存
        self._generated_image_path = self._generated_images[index]

        # 大きいプレビューを更新
        pixmap = QPixmap(self._generated_image_path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                self._selected_preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self._selected_preview.setPixmap(scaled)

    def _clear_thumbnails(self):
        """サムネイルをクリア"""
        for btn in self._thumbnail_buttons:
            self._thumbnail_layout.removeWidget(btn)
            btn.deleteLater()
        self._thumbnail_buttons.clear()
        self._generated_images.clear()
        self._generated_image_path = None
        self._selected_preview.clear()
        self._selected_preview.setText("生成された画像がここに表示されます")
        # 再生成時に古いキャッシュ画像が表示されないようにクリア
        QPixmapCache.clear()

    def _on_apply(self):
        """コマに配置"""
        if self._generated_image_path:
            self.accept()

    def _on_cancel(self):
        """キャンセル"""
        if hasattr(self, '_workers'):
            for worker in self._workers:
                if worker.isRunning():
                    worker.cancel()
                    worker.wait()
        self.reject()

    def get_generated_image_path(self) -> Optional[str]:
        """生成された画像のパスを取得"""
        return self._generated_image_path

    def get_generation_settings(self) -> dict:
        """生成時に使用した設定を取得（再生成用）"""
        # プロンプトを結合（コマ別 + 共通）
        common_prompt = self._common_prompt_edit.toPlainText().strip()
        panel_prompt = self._prompt_edit.toPlainText().strip()
        prompt_parts = [p for p in [panel_prompt, common_prompt] if p]
        prompt = ", ".join(prompt_parts)

        common_neg = self._common_neg_prompt_edit.toPlainText().strip()
        panel_neg = self._neg_prompt_edit.toPlainText().strip()
        neg_prompt_parts = [p for p in [common_neg, panel_neg] if p]
        negative_prompt = ", ".join(neg_prompt_parts)

        # 複数キャラクターモードか判定
        is_multi_char = self._multi_char_check.isChecked()

        # キャラクター情報取得
        character_ids = []
        multi_char_data = []

        if is_multi_char:
            # 複数キャラクターモード: 各キャラクターのIDと個別プロンプトを保存
            for i, combo in enumerate(self._multi_char_combos):
                char = combo.currentData()
                individual_prompt = self._multi_char_prompt_edits[i].text().strip()
                char_id = char.id if char and isinstance(char, Character) else None
                multi_char_data.append({
                    'character_id': char_id,
                    'individual_prompt': individual_prompt
                })
        else:
            # 単一キャラクターモード
            char = self._character_combo.currentData()
            if char and isinstance(char, Character):
                character_ids = [char.id]

        # batch_mode時は、最終プロンプトを保存
        final_prompt = ""
        final_negative_prompt = ""
        if self._batch_mode:
            # batch_modeの場合、promptは既にfinal_prompt（UIで編集されている可能性あり）
            final_prompt = prompt
            final_negative_prompt = negative_prompt
            # character_idsは元の設定から引き継ぐ
            if not character_ids and self._batch_character_ids:
                character_ids = self._batch_character_ids

        return {
            'prompt': prompt,
            'negative_prompt': negative_prompt,
            'seed': self._seed_spin.value(),
            'character_ids': character_ids,
            'steps': self._steps_spin.value(),
            'cfg_scale': self._cfg_spin.value(),
            'width': self._width_spin.value(),
            'height': self._height_spin.value(),
            'ip_adapter_weight': self._ip_weight_slider.value() / 100,
            # 複数キャラクターモード設定
            'multi_char_mode': is_multi_char,
            'multi_char_data': multi_char_data,
            'split_direction': self._split_direction_combo.currentIndex(),
            'use_adetailer': self._adetailer_check.isChecked(),
            # 一括生成モード設定
            'batch_mode': self._batch_mode,
            'final_prompt': final_prompt,
            'final_negative_prompt': final_negative_prompt
        }

    def set_initial_settings(self, settings: dict):
        """既存の設定で初期化（再生成用）"""
        if not settings:
            return

        # 一括生成モードの設定を取得
        self._batch_mode = settings.get('batch_mode', False)
        self._batch_final_prompt = settings.get('final_prompt', '')
        self._batch_final_negative_prompt = settings.get('final_negative_prompt', '')
        self._batch_character_ids = settings.get('character_ids', [])

        # プロンプトを設定
        if self._batch_mode and self._batch_final_prompt:
            # 一括生成モードの場合、最終プロンプトをコマ別に設定
            # 共通プロンプトは空にする（final_promptに既に含まれている）
            self._prompt_edit.setPlainText(self._batch_final_prompt)
            self._common_prompt_edit.setPlainText("")
            if self._batch_final_negative_prompt:
                self._neg_prompt_edit.setPlainText(self._batch_final_negative_prompt)
                self._common_neg_prompt_edit.setPlainText("")
        else:
            # 通常モードの場合
            if settings.get('prompt'):
                self._prompt_edit.setPlainText(settings['prompt'])
            if settings.get('negative_prompt'):
                self._neg_prompt_edit.setPlainText(settings['negative_prompt'])

        # シード設定（QSpinBoxの範囲外の値は-1にフォールバック）
        if 'seed' in settings:
            seed_val = settings['seed']
            if seed_val < -1 or seed_val > 2147483647:
                seed_val = -1
            self._seed_spin.setValue(seed_val)

        # 複数キャラクターモード判定
        is_multi_char = settings.get('multi_char_mode', False)
        self._multi_char_check.setChecked(is_multi_char)

        if is_multi_char:
            # 複数キャラクターモードの設定を復元
            multi_char_data = settings.get('multi_char_data', [])
            for i, data in enumerate(multi_char_data):
                if i >= len(self._multi_char_combos):
                    break
                # キャラクター選択
                char_id = data.get('character_id')
                if char_id:
                    for j in range(self._multi_char_combos[i].count()):
                        char = self._multi_char_combos[i].itemData(j)
                        if char and isinstance(char, Character) and char.id == char_id:
                            self._multi_char_combos[i].setCurrentIndex(j)
                            break
                # 個別プロンプト
                individual_prompt = data.get('individual_prompt', '')
                self._multi_char_prompt_edits[i].setText(individual_prompt)

            # 分割方向
            split_direction = settings.get('split_direction', 0)
            self._split_direction_combo.setCurrentIndex(split_direction)

            # ADetailer設定
            use_adetailer = settings.get('use_adetailer', True)
            self._adetailer_check.setChecked(use_adetailer)
        else:
            # 単一キャラクターモードの設定を復元
            if settings.get('character_ids'):
                char_id = settings['character_ids'][0]
                for i in range(self._character_combo.count()):
                    char = self._character_combo.itemData(i)
                    if char and isinstance(char, Character) and char.id == char_id:
                        self._character_combo.setCurrentIndex(i)
                        break

        # 詳細設定
        if 'steps' in settings:
            self._steps_spin.setValue(settings['steps'])
        if 'cfg_scale' in settings:
            self._cfg_spin.setValue(settings['cfg_scale'])
        if 'ip_adapter_weight' in settings:
            self._ip_weight_slider.setValue(int(settings['ip_adapter_weight'] * 100))

        # サイズ設定を復元
        if 'width' in settings:
            self._width_spin.setValue(settings['width'])
        if 'height' in settings:
            self._height_spin.setValue(settings['height'])
