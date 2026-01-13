from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                               QMenuBar, QMenu, QToolBar, QFileDialog,
                               QMessageBox, QSplitter, QStatusBar, QInputDialog,
                               QApplication)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence, QUndoStack, QFont
import copy

from src.models.project import Project
from src.models.page import Page
from src.models.speech_bubble import SpeechBubble
from src.views.canvas_scene import CanvasScene
from src.graphics.panel_polygon_item import PanelPolygonItem
from src.views.canvas_view import CanvasView
from src.views.page_list_widget import PageListWidget
from src.views.panels.tool_panel import ToolPanel
from src.views.panels.property_panel import PropertyPanel
from src.services.template_service import TemplateService
from src.utils.enums import ToolType
from src.utils.constants import (
    WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT, LEFT_PANEL_WIDTH, RIGHT_PANEL_WIDTH,
    PANEL_MARGIN, PASTE_OFFSET,
    ZVALUE_BUBBLE, ZVALUE_DIVIDER,
    STATUSBAR_MESSAGE_TIMEOUT, STATUSBAR_MESSAGE_TIMEOUT_LONG,
    PAGE_SIZE_MIN, PAGE_SIZE_MAX
)
from src.graphics.speech_bubble_item import SpeechBubbleGraphicsItem
from src.graphics.divider_line_item import DividerLineItem
from src.views.dialogs.settings_dialog import SettingsDialog
from src.services.settings_service import SettingsService
from src.services.character_service import CharacterService

from src.controllers.file_controller import FileController
from src.controllers.ai_controller import AIController
from src.controllers.menu_controller import MenuController


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("漫画コマ割りエディタ")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        self._project = Project()
        self._current_page_index = 0
        self._scenes = {}
        self._current_file_path = None
        self._is_modified = False
        self._clipboard = None
        self._undo_stack = QUndoStack(self)

        # キャラクターサービスにプロジェクトを設定
        CharacterService.get_instance().set_project(self._project)

        # コントローラー初期化
        self._file_controller = FileController(self)
        self._ai_controller = AIController(self)
        self._menu_controller = MenuController(self)

        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()
        self._connect_signals()

        self._load_page(0)
        self._update_title()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(PANEL_MARGIN, PANEL_MARGIN, PANEL_MARGIN, PANEL_MARGIN)

        self._page_list = PageListWidget()
        self._page_list.set_project(self._project)
        left_layout.addWidget(self._page_list, 1)

        self._tool_panel = ToolPanel()
        left_layout.addWidget(self._tool_panel)

        left_panel.setFixedWidth(LEFT_PANEL_WIDTH)
        splitter.addWidget(left_panel)

        self._scene = CanvasScene()
        self._scene.set_undo_stack(self._undo_stack)
        self._scene.ai_generate_requested.connect(self._ai_controller.on_ai_generate_for_panel)
        self._scene.ai_regenerate_requested.connect(self._ai_controller.on_ai_regenerate_for_panel)
        self._canvas_view = CanvasView(self._scene)
        splitter.addWidget(self._canvas_view)

        self._property_panel = PropertyPanel()
        self._property_panel.setFixedWidth(RIGHT_PANEL_WIDTH)
        splitter.addWidget(self._property_panel)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)

        main_layout.addWidget(splitter)

    def _setup_menu(self):
        menubar = self.menuBar()

        # ファイルメニュー
        file_menu = menubar.addMenu("ファイル(&F)")

        new_action = QAction("新規(&N)", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._file_controller.on_new)
        file_menu.addAction(new_action)

        open_action = QAction("開く(&O)...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._file_controller.on_open)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        save_action = QAction("保存(&S)", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._file_controller.on_save)
        file_menu.addAction(save_action)

        save_as_action = QAction("名前を付けて保存(&A)...", self)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_action.triggered.connect(self._file_controller.on_save_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        export_menu = file_menu.addMenu("エクスポート")

        export_png = QAction("PNG出力...", self)
        export_png.setShortcut(QKeySequence("Ctrl+Shift+E"))
        export_png.triggered.connect(self._file_controller.on_export_png)
        export_menu.addAction(export_png)

        export_jpg = QAction("JPG出力...", self)
        export_jpg.setShortcut(QKeySequence("Ctrl+Shift+J"))
        export_jpg.triggered.connect(self._file_controller.on_export_jpg)
        export_menu.addAction(export_jpg)

        export_pdf = QAction("PDF出力（全ページ）...", self)
        export_pdf.setShortcut(QKeySequence("Ctrl+Shift+P"))
        export_pdf.triggered.connect(self._file_controller.on_export_pdf)
        export_menu.addAction(export_pdf)

        file_menu.addSeparator()

        exit_action = QAction("終了(&X)", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 編集メニュー
        edit_menu = menubar.addMenu("編集(&E)")

        self._undo_action = self._undo_stack.createUndoAction(self, "元に戻す(&U)")
        self._undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        edit_menu.addAction(self._undo_action)

        self._redo_action = self._undo_stack.createRedoAction(self, "やり直し(&R)")
        self._redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        edit_menu.addAction(self._redo_action)

        edit_menu.addSeparator()

        copy_action = QAction("コピー(&C)", self)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.triggered.connect(self._on_copy)
        edit_menu.addAction(copy_action)

        paste_action = QAction("ペースト(&P)", self)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        paste_action.triggered.connect(self._on_paste)
        edit_menu.addAction(paste_action)

        edit_menu.addSeparator()

        delete_action = QAction("削除(&D)", self)
        delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        delete_action.triggered.connect(self._on_delete)
        edit_menu.addAction(delete_action)

        # 表示メニュー
        view_menu = menubar.addMenu("表示(&V)")

        zoom_in = QAction("拡大", self)
        zoom_in.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in.triggered.connect(self._canvas_view.zoom_in)
        view_menu.addAction(zoom_in)

        zoom_out = QAction("縮小", self)
        zoom_out.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out.triggered.connect(self._canvas_view.zoom_out)
        view_menu.addAction(zoom_out)

        reset_zoom = QAction("ズームリセット", self)
        reset_zoom.triggered.connect(self._canvas_view.reset_zoom)
        view_menu.addAction(reset_zoom)

        fit_view = QAction("画面にフィット", self)
        fit_view.triggered.connect(self._canvas_view.fit_to_view)
        view_menu.addAction(fit_view)

        # ツールメニュー
        tool_menu = menubar.addMenu("ツール(&T)")

        select_tool_action = QAction("選択ツール(&S)", self)
        select_tool_action.setShortcut(QKeySequence("V"))
        select_tool_action.triggered.connect(lambda: self._tool_panel.set_tool(ToolType.SELECT))
        tool_menu.addAction(select_tool_action)

        panel_tool_action = QAction("分割線ツール(&P)", self)
        panel_tool_action.setShortcut(QKeySequence("P"))
        panel_tool_action.triggered.connect(lambda: self._tool_panel.set_tool(ToolType.PANEL))
        tool_menu.addAction(panel_tool_action)

        bubble_tool_action = QAction("吹き出しツール(&B)", self)
        bubble_tool_action.setShortcut(QKeySequence("B"))
        bubble_tool_action.triggered.connect(lambda: self._tool_panel.set_tool(ToolType.SPEECH_BUBBLE))
        tool_menu.addAction(bubble_tool_action)

        # ページメニュー
        page_menu = menubar.addMenu("ページ(&G)")

        add_page = QAction("ページ追加(&A)", self)
        add_page.setShortcut(QKeySequence("Ctrl+Shift+N"))
        add_page.triggered.connect(self._on_add_page)
        page_menu.addAction(add_page)

        page_settings = QAction("ページ設定...", self)
        page_settings.triggered.connect(self._on_page_settings)
        page_menu.addAction(page_settings)

        # スタイルメニュー
        self._style_menu = menubar.addMenu("スタイル(&S)")
        self._menu_controller.set_style_menu(self._style_menu)
        self._menu_controller.update_style_menu()

        # AIメニュー
        ai_menu = menubar.addMenu("AI(&A)")

        ai_generate_action = QAction("画像を生成...", self)
        ai_generate_action.setShortcut(QKeySequence("Ctrl+G"))
        ai_generate_action.triggered.connect(self._ai_controller.on_ai_generate)
        ai_menu.addAction(ai_generate_action)

        ai_menu.addSeparator()

        ai_char_action = QAction("キャラクター管理...", self)
        ai_char_action.triggered.connect(self._ai_controller.on_ai_character_manager)
        ai_menu.addAction(ai_char_action)

        ai_menu.addSeparator()

        ai_story_action = QAction("ストーリー仕様書を読み込み...", self)
        ai_story_action.triggered.connect(self._ai_controller.on_story_import)
        ai_menu.addAction(ai_story_action)

        # 設定メニュー
        settings_menu = menubar.addMenu("設定(&O)")

        settings_action = QAction("設定...", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._on_settings)
        settings_menu.addAction(settings_action)

    def _on_settings(self):
        """設定ダイアログを開く"""
        dialog = SettingsDialog(self)
        if dialog.exec():
            self._menu_controller.update_style_menu()

    def _setup_toolbar(self):
        pass

    def _setup_statusbar(self):
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._update_statusbar()

    def _connect_signals(self):
        self._page_list.page_selected.connect(self._on_page_selected)
        self._page_list.page_added.connect(self._on_page_added)
        self._page_list.page_deleted.connect(self._on_page_deleted)

        self._tool_panel.tool_changed.connect(self._scene.set_tool)
        self._tool_panel.template_selected.connect(self._on_template_selected)

        self._scene.selectionChanged.connect(self._on_selection_changed)
        self._scene.page_modified.connect(self._on_page_modified)

        self._property_panel.property_changed.connect(self._on_page_modified)
        self._property_panel.page_margin_changed.connect(self._on_margin_changed)

        # コントローラーのシグナル接続
        self._file_controller.title_update_requested.connect(self._update_title)
        self._file_controller.status_message.connect(self._show_status_message)

        self._ai_controller.page_modified.connect(self._on_page_modified)
        self._ai_controller.status_message.connect(self._show_status_message)
        self._ai_controller.title_update_requested.connect(self._update_title)

        self._menu_controller.page_modified.connect(self._on_page_modified)
        self._menu_controller.status_message.connect(self._show_status_message)

    def _show_status_message(self, message: str, timeout: int):
        """ステータスバーにメッセージを表示"""
        self._statusbar.showMessage(message, timeout)

    def _load_page(self, index: int):
        if index < 0 or index >= len(self._project.pages):
            return

        self._current_page_index = index
        page = self._project.pages[index]

        if index not in self._scenes:
            scene = CanvasScene()
            scene.set_undo_stack(self._undo_stack)
            scene.set_page(page)
            scene.selectionChanged.connect(self._on_selection_changed)
            scene.page_modified.connect(self._on_page_modified)
            scene.ai_generate_requested.connect(self._ai_controller.on_ai_generate_for_panel)
            scene.ai_regenerate_requested.connect(self._ai_controller.on_ai_regenerate_for_panel)
            self._tool_panel.tool_changed.connect(scene.set_tool)
            self._scenes[index] = scene

        self._scene = self._scenes[index]
        self._canvas_view.setScene(self._scene)
        self._property_panel.set_page(page)
        self._update_statusbar()

    def _on_page_selected(self, index: int):
        self._load_page(index)

    def _on_page_added(self):
        pass

    def _on_page_deleted(self, deleted_index: int):
        """ページ削除時の処理"""
        # 削除されたページのシーンを削除
        if deleted_index in self._scenes:
            del self._scenes[deleted_index]

        # 削除されたインデックスより後のシーンのインデックスを更新
        new_scenes = {}
        for idx, scene in self._scenes.items():
            if idx > deleted_index:
                new_scenes[idx - 1] = scene
            else:
                new_scenes[idx] = scene
        self._scenes = new_scenes

        # 現在のページインデックスを調整
        if self._current_page_index >= len(self._project.pages):
            self._current_page_index = len(self._project.pages) - 1
        elif self._current_page_index > deleted_index:
            self._current_page_index -= 1

        # ページを再読み込み
        self._load_page(self._current_page_index)
        self._is_modified = True
        self._update_title()
        self._update_statusbar()

    def _on_selection_changed(self):
        items = self._scene.selectedItems()
        if items:
            self._property_panel.set_selected_item(items[0])
        else:
            self._property_panel.set_selected_item(None)

    def _on_page_modified(self):
        self._page_list.update_thumbnail(self._current_page_index)
        self._is_modified = True
        self._update_title()

    def _on_margin_changed(self, margin):
        """外枠幅変更時にシーンを再描画"""
        page = self._project.pages[self._current_page_index]
        self._scene.set_page(page)

    def _update_title(self):
        """ウィンドウタイトルを更新"""
        title = "漫画コマ割りエディタ"
        if self._current_file_path:
            import os
            title = f"{os.path.basename(self._current_file_path)} - {title}"
        else:
            title = f"新規プロジェクト - {title}"
        if self._is_modified:
            title = f"* {title}"
        self.setWindowTitle(title)

    def _on_copy(self):
        """選択アイテムをコピー"""
        items = self._scene.selectedItems()
        if not items:
            return

        item = items[0]
        if isinstance(item, SpeechBubbleGraphicsItem):
            self._clipboard = ('bubble', copy.deepcopy(item.bubble))
        elif isinstance(item, DividerLineItem):
            self._clipboard = ('divider', copy.deepcopy(item.divider))

        self._statusbar.showMessage("コピーしました", STATUSBAR_MESSAGE_TIMEOUT)

    def _on_paste(self):
        """ペースト"""
        if not self._clipboard:
            return

        import uuid
        item_type, data = self._clipboard
        page = self._project.pages[self._current_page_index]

        if item_type == 'bubble':
            new_bubble = copy.deepcopy(data)
            new_bubble.x += PASTE_OFFSET
            new_bubble.y += PASTE_OFFSET
            new_bubble.id = str(uuid.uuid4())
            page.speech_bubbles.append(new_bubble)

            item = SpeechBubbleGraphicsItem(new_bubble)
            item.setZValue(ZVALUE_BUBBLE)
            self._scene.addItem(item)

        elif item_type == 'divider':
            new_divider = copy.deepcopy(data)
            new_divider.x1 += PASTE_OFFSET
            new_divider.y1 += PASTE_OFFSET
            new_divider.x2 += PASTE_OFFSET
            new_divider.y2 += PASTE_OFFSET
            new_divider.id = str(uuid.uuid4())
            page.divider_lines.append(new_divider)

            item = DividerLineItem(new_divider)
            item.setZValue(ZVALUE_DIVIDER)
            self._scene.addItem(item)
            self._scene.divider_changed.emit()

        self._on_page_modified()
        self._statusbar.showMessage("ペーストしました", STATUSBAR_MESSAGE_TIMEOUT)

    def closeEvent(self, event):
        """ウィンドウを閉じる前の確認"""
        if self._file_controller.check_unsaved_changes():
            event.accept()
        else:
            event.ignore()

    def _on_add_page(self):
        self._page_list._on_add_clicked()

    def _on_page_settings(self):
        page = self._project.pages[self._current_page_index]

        width, ok = QInputDialog.getInt(self, "ページ設定", "幅:", page.width, PAGE_SIZE_MIN, PAGE_SIZE_MAX)
        if not ok:
            return

        height, ok = QInputDialog.getInt(self, "ページ設定", "高さ:", page.height, PAGE_SIZE_MIN, PAGE_SIZE_MAX)
        if not ok:
            return

        page.width = width
        page.height = height

        if self._current_page_index in self._scenes:
            del self._scenes[self._current_page_index]
        self._load_page(self._current_page_index)

    def _on_delete(self):
        self._scene.delete_selected()

    def _on_template_selected(self, template):
        reply = QMessageBox.question(
            self, "テンプレート適用",
            f"テンプレート「{template.name}」を適用しますか？\n現在のコマは削除されます。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            page = self._project.pages[self._current_page_index]
            TemplateService.apply_template(page, template)

            if self._current_page_index in self._scenes:
                del self._scenes[self._current_page_index]
            self._load_page(self._current_page_index)
            self._page_list.update_thumbnail(self._current_page_index)

    def _update_statusbar(self):
        if self._project.pages:
            page = self._project.pages[self._current_page_index]
            self._statusbar.showMessage(
                f"ページ: {self._current_page_index + 1}/{len(self._project.pages)} | "
                f"サイズ: {page.width} x {page.height}"
            )
