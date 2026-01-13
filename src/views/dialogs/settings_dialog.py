from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QGroupBox, QLabel, QSpinBox, QCheckBox, QFontComboBox,
    QPushButton, QListWidget, QListWidgetItem, QLineEdit,
    QDialogButtonBox, QMessageBox, QInputDialog, QFileDialog,
    QDoubleSpinBox, QPlainTextEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from src.services.settings_service import SettingsService, FontStyle
from src.services.forge_service import ForgeService
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

        # AI画像生成タブ
        self._forge_tab = QWidget()
        self._setup_forge_tab()
        self._tabs.addTab(self._forge_tab, "AI画像生成")

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

    def _setup_forge_tab(self):
        """AI画像生成（Forge）タブを設定"""
        layout = QVBoxLayout(self._forge_tab)

        # Forge接続設定
        connection_group = QGroupBox("Forge接続設定")
        connection_layout = QVBoxLayout(connection_group)

        # パス設定
        path_row = QHBoxLayout()
        path_row.addWidget(QLabel("Forgeパス:"))
        self._forge_path_edit = QLineEdit()
        self._forge_path_edit.setPlaceholderText("例: C:\\StabilityMatrix\\Data\\Packages\\stable-diffusion-webui-forge")
        path_row.addWidget(self._forge_path_edit)
        self._forge_browse_btn = QPushButton("参照...")
        self._forge_browse_btn.clicked.connect(self._on_browse_forge_path)
        path_row.addWidget(self._forge_browse_btn)
        connection_layout.addLayout(path_row)

        # API URL設定
        url_row = QHBoxLayout()
        url_row.addWidget(QLabel("API URL:"))
        self._forge_url_edit = QLineEdit()
        self._forge_url_edit.setPlaceholderText("例: http://127.0.0.1:7860")
        url_row.addWidget(self._forge_url_edit)
        self._forge_test_btn = QPushButton("接続テスト")
        self._forge_test_btn.clicked.connect(self._on_test_forge_connection)
        url_row.addWidget(self._forge_test_btn)
        self._forge_ext_btn = QPushButton("拡張機能確認")
        self._forge_ext_btn.clicked.connect(self._on_check_extensions)
        url_row.addWidget(self._forge_ext_btn)
        connection_layout.addLayout(url_row)

        # 自動起動設定
        self._forge_auto_launch_check = QCheckBox("AI生成時にForgeを自動起動")
        connection_layout.addWidget(self._forge_auto_launch_check)

        # API-onlyモード設定
        self._forge_api_only_check = QCheckBox("API-onlyモードで起動（UIなし、高速）")
        self._forge_api_only_check.setToolTip("チェックを外すとForge UIも表示されます。エラーが発生する場合はオフにしてください。")
        connection_layout.addWidget(self._forge_api_only_check)

        # タイムアウト設定
        timeout_row = QHBoxLayout()
        timeout_row.addWidget(QLabel("起動タイムアウト:"))
        self._forge_timeout_spin = QSpinBox()
        self._forge_timeout_spin.setRange(30, 300)
        self._forge_timeout_spin.setSuffix(" 秒")
        timeout_row.addWidget(self._forge_timeout_spin)
        timeout_row.addStretch()
        connection_layout.addLayout(timeout_row)

        layout.addWidget(connection_group)

        # デフォルト生成設定
        gen_group = QGroupBox("デフォルト生成設定")
        gen_layout = QVBoxLayout(gen_group)

        # デフォルトプロンプト
        gen_layout.addWidget(QLabel("デフォルトプロンプト:"))
        self._default_prompt_edit = QPlainTextEdit()
        self._default_prompt_edit.setMaximumHeight(60)
        gen_layout.addWidget(self._default_prompt_edit)

        # デフォルトネガティブプロンプト
        gen_layout.addWidget(QLabel("デフォルトネガティブプロンプト:"))
        self._default_neg_prompt_edit = QPlainTextEdit()
        self._default_neg_prompt_edit.setMaximumHeight(60)
        gen_layout.addWidget(self._default_neg_prompt_edit)

        # Steps, CFG Scale, Sampler
        params_row = QHBoxLayout()
        params_row.addWidget(QLabel("Steps:"))
        self._default_steps_spin = QSpinBox()
        self._default_steps_spin.setRange(1, 150)
        params_row.addWidget(self._default_steps_spin)

        params_row.addWidget(QLabel("CFG Scale:"))
        self._default_cfg_spin = QDoubleSpinBox()
        self._default_cfg_spin.setRange(1.0, 30.0)
        self._default_cfg_spin.setSingleStep(0.5)
        params_row.addWidget(self._default_cfg_spin)

        params_row.addWidget(QLabel("サンプラー:"))
        self._default_sampler_edit = QLineEdit()
        self._default_sampler_edit.setMaximumWidth(120)
        params_row.addWidget(self._default_sampler_edit)

        params_row.addStretch()
        gen_layout.addLayout(params_row)

        layout.addWidget(gen_group)
        layout.addStretch()

    def _on_browse_forge_path(self):
        """Forgeパス参照"""
        path = QFileDialog.getExistingDirectory(
            self, "Forgeフォルダを選択",
            self._forge_path_edit.text()
        )
        if path:
            self._forge_path_edit.setText(path)

    def _on_test_forge_connection(self):
        """Forge接続テスト"""
        url = self._forge_url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "エラー", "API URLを入力してください")
            return

        if ForgeService.check_connection(url):
            # 詳細情報を取得
            ready, status = ForgeService.check_ready(url)
            options = ForgeService.get_options(url)
            model = options.get('sd_model_checkpoint', '不明')
            sampler = options.get('samples_save', '不明')

            msg = f"Forgeに接続できました\n\n"
            msg += f"モデル: {model}\n"

            if ready:
                QMessageBox.information(self, "成功", msg)
            else:
                msg += f"\n警告: {status}"
                QMessageBox.warning(self, "接続成功（警告あり）", msg)
        else:
            QMessageBox.warning(
                self, "失敗",
                "Forgeに接続できませんでした\n\n"
                "・Forgeが起動しているか確認してください\n"
                "・--api オプションで起動しているか確認してください"
            )

    def _on_check_extensions(self):
        """拡張機能の確認"""
        url = self._forge_url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "エラー", "API URLを入力してください")
            return

        if not ForgeService.check_connection(url):
            QMessageBox.warning(self, "エラー", "Forgeに接続できません。先に接続テストを行ってください。")
            return

        # 拡張機能状態を取得
        ext_status = ForgeService.check_extension_status(url)

        # 結果メッセージ作成
        msg = "【複数キャラクター生成に必要な拡張機能】\n\n"

        # Regional Prompter
        rp = ext_status["regional_prompter"]
        if rp["enabled"]:
            msg += f"Regional Prompter: OK\n   名前: {rp['name']}\n\n"
        elif rp["installed"]:
            msg += "Regional Prompter: インストール済（無効）\n   Forgeで有効化してください\n\n"
        else:
            msg += "Regional Prompter: 未インストール\n   推奨: sd-forge-regional-prompter\n\n"

        # ADetailer
        ad = ext_status["adetailer"]
        if ad["enabled"]:
            msg += f"ADetailer: OK\n   名前: {ad['name']}\n\n"
        elif ad["installed"]:
            msg += "ADetailer: インストール済（無効）\n   Forgeで有効化してください\n\n"
        else:
            msg += "ADetailer: 未インストール\n   推奨: adetailer\n\n"

        # ControlNet
        cn = ext_status["controlnet"]
        if cn["enabled"]:
            msg += f"ControlNet: OK\n   名前: {cn['name']}\n\n"
        elif cn["installed"]:
            msg += "ControlNet: インストール済（無効）\n   Forgeで有効化してください\n\n"
        else:
            msg += "ControlNet: 未インストール\n   IP-Adapterに必要です\n\n"

        # IP-Adapterモデル確認
        ip_models = ForgeService.get_ip_adapter_models(url)
        if ip_models:
            msg += f"IP-Adapterモデル: {len(ip_models)}個検出\n"
            for m in ip_models[:3]:  # 最大3つ表示
                msg += f"   - {m}\n"
            if len(ip_models) > 3:
                msg += f"   ... 他{len(ip_models)-3}個\n"
        else:
            msg += "IP-Adapterモデル: 未検出\n   キャラクター参照画像機能に必要です\n"

        # 全てOKかチェック
        all_ok = rp["enabled"] and ad["enabled"] and cn["enabled"]
        if all_ok:
            QMessageBox.information(self, "拡張機能確認", msg + "\n全ての拡張機能が利用可能です")
        else:
            QMessageBox.warning(self, "拡張機能確認", msg + "\n一部の拡張機能が不足しています")

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

        # Forge設定
        self._forge_path_edit.setText(self._settings.forge_path)
        self._forge_url_edit.setText(self._settings.forge_api_url)
        self._forge_auto_launch_check.setChecked(self._settings.forge_auto_launch)
        self._forge_api_only_check.setChecked(self._settings.forge_api_only)
        self._forge_timeout_spin.setValue(self._settings.forge_startup_timeout)
        self._default_prompt_edit.setPlainText(self._settings.default_prompt)
        self._default_neg_prompt_edit.setPlainText(self._settings.default_negative_prompt)
        self._default_steps_spin.setValue(self._settings.default_steps)
        self._default_cfg_spin.setValue(self._settings.default_cfg_scale)
        self._default_sampler_edit.setText(self._settings.default_sampler)

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

        # Forge設定を保存
        self._settings.forge_path = self._forge_path_edit.text()
        self._settings.forge_api_url = self._forge_url_edit.text()
        self._settings.forge_auto_launch = self._forge_auto_launch_check.isChecked()
        self._settings.forge_api_only = self._forge_api_only_check.isChecked()
        self._settings.forge_startup_timeout = self._forge_timeout_spin.value()
        self._settings.default_prompt = self._default_prompt_edit.toPlainText()
        self._settings.default_negative_prompt = self._default_neg_prompt_edit.toPlainText()
        self._settings.default_steps = self._default_steps_spin.value()
        self._settings.default_cfg_scale = self._default_cfg_spin.value()
        self._settings.default_sampler = self._default_sampler_edit.text()

        self.accept()
