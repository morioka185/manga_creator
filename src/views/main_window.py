from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                               QMenuBar, QMenu, QToolBar, QFileDialog,
                               QMessageBox, QSplitter, QStatusBar, QInputDialog,
                               QApplication)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence, QUndoStack, QUndoCommand
import copy

from src.models.project import Project
from src.models.page import Page
from src.models.speech_bubble import SpeechBubble
from src.models.text_element import TextElement
from src.views.canvas_scene import CanvasScene, PanelPolygonItem
from src.views.canvas_view import CanvasView
from src.views.page_list_widget import PageListWidget
from src.views.panels.tool_panel import ToolPanel
from src.views.panels.property_panel import PropertyPanel
from src.services.export_service import ExportService
from src.services.template_service import TemplateService
from src.services.project_serializer import ProjectSerializer
from src.utils.enums import ToolType
from src.utils.constants import (
    WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT, LEFT_PANEL_WIDTH, RIGHT_PANEL_WIDTH,
    PANEL_MARGIN, PASTE_OFFSET, EXPORT_JPG_QUALITY,
    ZVALUE_BUBBLE, ZVALUE_TEXT, ZVALUE_DIVIDER,
    STATUSBAR_MESSAGE_TIMEOUT, STATUSBAR_MESSAGE_TIMEOUT_LONG,
    PAGE_SIZE_MIN, PAGE_SIZE_MAX
)
from src.graphics.speech_bubble_item import SpeechBubbleGraphicsItem
from src.graphics.text_item import TextGraphicsItem
from src.graphics.divider_line_item import DividerLineItem
from src.views.dialogs.settings_dialog import SettingsDialog
from src.services.settings_service import SettingsService


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

        # クリップボード（コピー/ペースト用）
        self._clipboard = None

        # Undo/Redo スタック
        self._undo_stack = QUndoStack(self)

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

        # ===== ファイルメニュー =====
        file_menu = menubar.addMenu("ファイル(&F)")

        new_action = QAction("新規(&N)", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._on_new)
        file_menu.addAction(new_action)

        open_action = QAction("開く(&O)...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._on_open)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        save_action = QAction("保存(&S)", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._on_save)
        file_menu.addAction(save_action)

        save_as_action = QAction("名前を付けて保存(&A)...", self)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_action.triggered.connect(self._on_save_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        export_menu = file_menu.addMenu("エクスポート")

        export_png = QAction("PNG出力...", self)
        export_png.setShortcut(QKeySequence("Ctrl+Shift+E"))
        export_png.triggered.connect(self._on_export_png)
        export_menu.addAction(export_png)

        export_jpg = QAction("JPG出力...", self)
        export_jpg.setShortcut(QKeySequence("Ctrl+Shift+J"))
        export_jpg.triggered.connect(self._on_export_jpg)
        export_menu.addAction(export_jpg)

        export_pdf = QAction("PDF出力（全ページ）...", self)
        export_pdf.setShortcut(QKeySequence("Ctrl+Shift+P"))
        export_pdf.triggered.connect(self._on_export_pdf)
        export_menu.addAction(export_pdf)

        file_menu.addSeparator()

        exit_action = QAction("終了(&X)", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # ===== 編集メニュー =====
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

        # ===== ツールメニュー =====
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

        text_tool_action = QAction("テキストツール(&T)", self)
        text_tool_action.setShortcut(QKeySequence("T"))
        text_tool_action.triggered.connect(lambda: self._tool_panel.set_tool(ToolType.TEXT))
        tool_menu.addAction(text_tool_action)

        page_menu = menubar.addMenu("ページ(&G)")

        add_page = QAction("ページ追加(&A)", self)
        add_page.setShortcut(QKeySequence("Ctrl+Shift+N"))
        add_page.triggered.connect(self._on_add_page)
        page_menu.addAction(add_page)

        page_settings = QAction("ページ設定...", self)
        page_settings.triggered.connect(self._on_page_settings)
        page_menu.addAction(page_settings)

        # ===== スタイルメニュー =====
        self._style_menu = menubar.addMenu("スタイル(&S)")
        self._update_style_menu()

        # ===== 設定メニュー =====
        settings_menu = menubar.addMenu("設定(&O)")

        settings_action = QAction("設定...", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._on_settings)
        settings_menu.addAction(settings_action)

    def _update_style_menu(self):
        """スタイルメニューを更新"""
        self._style_menu.clear()
        settings = SettingsService.get_instance()

        for i, style in enumerate(settings.get_font_styles()):
            action = QAction(style.name, self)
            # 数字キーでショートカット (1-9)
            if i < 9:
                action.setShortcut(QKeySequence(str(i + 1)))
            action.triggered.connect(lambda checked, s=style: self._apply_style(s))
            self._style_menu.addAction(action)

        self._style_menu.addSeparator()
        edit_action = QAction("スタイルを編集...", self)
        edit_action.triggered.connect(self._on_settings)
        self._style_menu.addAction(edit_action)

    def _apply_style(self, style):
        """選択中のアイテムにスタイルを適用"""
        items = self._scene.selectedItems()
        if not items:
            self._statusbar.showMessage("アイテムを選択してください", STATUSBAR_MESSAGE_TIMEOUT)
            return

        for item in items:
            if isinstance(item, SpeechBubbleGraphicsItem):
                item.bubble.font_family = style.font_family
                item.bubble.font_size = style.font_size
                item.update()
            elif isinstance(item, TextGraphicsItem):
                from PyQt6.QtGui import QFont
                font = QFont(style.font_family, style.font_size)
                font.setBold(style.bold)
                item.setFont(font)
                item.text_element.font_family = style.font_family
                item.text_element.font_size = style.font_size

        # プロパティパネルのUIを更新
        if items:
            self._property_panel.set_selected_item(items[0])

        self._on_page_modified()
        self._statusbar.showMessage(f"スタイル「{style.name}」を適用しました", STATUSBAR_MESSAGE_TIMEOUT)

    def _on_settings(self):
        """設定ダイアログを開く"""
        dialog = SettingsDialog(self)
        if dialog.exec():
            self._update_style_menu()

    def _setup_toolbar(self):
        pass  # ツールバーは不要（メニューとショートカットで対応）

    def _setup_statusbar(self):
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._update_statusbar()

    def _connect_signals(self):
        self._page_list.page_selected.connect(self._on_page_selected)
        self._page_list.page_added.connect(self._on_page_added)

        self._tool_panel.tool_changed.connect(self._scene.set_tool)
        self._tool_panel.bubble_type_changed.connect(self._scene.set_bubble_type)
        self._tool_panel.template_selected.connect(self._on_template_selected)

        self._scene.selectionChanged.connect(self._on_selection_changed)
        self._scene.page_modified.connect(self._on_page_modified)

        self._property_panel.property_changed.connect(self._on_page_modified)
        self._property_panel.page_margin_changed.connect(self._on_margin_changed)

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
            self._tool_panel.tool_changed.connect(scene.set_tool)
            self._tool_panel.bubble_type_changed.connect(scene.set_bubble_type)
            self._scenes[index] = scene

        self._scene = self._scenes[index]
        self._canvas_view.setScene(self._scene)
        self._property_panel.set_page(page)
        self._update_statusbar()

    def _on_page_selected(self, index: int):
        self._load_page(index)

    def _on_page_added(self):
        pass

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

    def _on_new(self):
        if self._is_modified:
            reply = QMessageBox.question(
                self, "確認", "新規プロジェクトを作成しますか？\n保存されていない変更は失われます。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self._project = Project()
        self._scenes.clear()
        self._current_file_path = None
        self._is_modified = False
        self._undo_stack.clear()
        self._page_list.set_project(self._project)
        self._load_page(0)
        self._update_title()

    def _on_open(self):
        """プロジェクトを開く"""
        if self._is_modified:
            reply = QMessageBox.question(
                self, "確認", "プロジェクトを開きますか？\n保存されていない変更は失われます。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        filepath, _ = QFileDialog.getOpenFileName(
            self, "プロジェクトを開く", "",
            "Manga Project (*.manga);;JSON Files (*.json);;All Files (*)"
        )
        if filepath:
            project = ProjectSerializer.load_from_file(filepath)
            if project:
                self._project = project
                self._scenes.clear()
                self._current_file_path = filepath
                self._is_modified = False
                self._undo_stack.clear()
                self._page_list.set_project(self._project)
                self._load_page(0)
                self._update_title()
            else:
                QMessageBox.warning(self, "エラー", "プロジェクトの読み込みに失敗しました。")

    def _on_save(self):
        """プロジェクトを保存"""
        if self._current_file_path:
            self._save_to_file(self._current_file_path)
        else:
            self._on_save_as()

    def _on_save_as(self):
        """名前を付けて保存"""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "名前を付けて保存", "",
            "Manga Project (*.manga);;JSON Files (*.json)"
        )
        if filepath:
            # 拡張子がなければ追加
            if not filepath.endswith('.manga') and not filepath.endswith('.json'):
                filepath += '.manga'
            self._save_to_file(filepath)

    def _save_to_file(self, filepath: str):
        """ファイルに保存"""
        if ProjectSerializer.save_to_file(self._project, filepath):
            self._current_file_path = filepath
            self._is_modified = False
            self._update_title()
            self._statusbar.showMessage("保存しました", STATUSBAR_MESSAGE_TIMEOUT_LONG)
        else:
            QMessageBox.warning(self, "エラー", "保存に失敗しました。")

    def _on_copy(self):
        """選択アイテムをコピー"""
        items = self._scene.selectedItems()
        if not items:
            return

        item = items[0]
        if isinstance(item, SpeechBubbleGraphicsItem):
            # 吹き出しをコピー
            self._clipboard = ('bubble', copy.deepcopy(item.bubble))
        elif isinstance(item, TextGraphicsItem):
            # テキストをコピー
            self._clipboard = ('text', copy.deepcopy(item.text_element))
        elif isinstance(item, DividerLineItem):
            # 分割線をコピー
            self._clipboard = ('divider', copy.deepcopy(item.divider))

        self._statusbar.showMessage("コピーしました", STATUSBAR_MESSAGE_TIMEOUT)

    def _on_paste(self):
        """ペースト"""
        if not self._clipboard:
            return

        item_type, data = self._clipboard
        page = self._project.pages[self._current_page_index]

        if item_type == 'bubble':
            new_bubble = copy.deepcopy(data)
            new_bubble.x += PASTE_OFFSET
            new_bubble.y += PASTE_OFFSET
            import uuid
            new_bubble.id = str(uuid.uuid4())
            page.speech_bubbles.append(new_bubble)

            # シーンを更新
            from src.graphics.speech_bubble_item import SpeechBubbleGraphicsItem
            item = SpeechBubbleGraphicsItem(new_bubble)
            item.setZValue(ZVALUE_BUBBLE)
            self._scene.addItem(item)

        elif item_type == 'text':
            new_text = copy.deepcopy(data)
            new_text.x += PASTE_OFFSET
            new_text.y += PASTE_OFFSET
            import uuid
            new_text.id = str(uuid.uuid4())
            page.text_elements.append(new_text)

            from src.graphics.text_item import TextGraphicsItem
            item = TextGraphicsItem(new_text)
            item.setZValue(ZVALUE_TEXT)
            self._scene.addItem(item)

        elif item_type == 'divider':
            new_divider = copy.deepcopy(data)
            new_divider.x1 += PASTE_OFFSET
            new_divider.y1 += PASTE_OFFSET
            new_divider.x2 += PASTE_OFFSET
            new_divider.y2 += PASTE_OFFSET
            import uuid
            new_divider.id = str(uuid.uuid4())
            page.divider_lines.append(new_divider)

            from src.graphics.divider_line_item import DividerLineItem
            item = DividerLineItem(new_divider)
            item.setZValue(ZVALUE_DIVIDER)
            self._scene.addItem(item)
            self._scene.divider_changed.emit()

        self._on_page_modified()
        self._statusbar.showMessage("ペーストしました", STATUSBAR_MESSAGE_TIMEOUT)

    def closeEvent(self, event):
        """ウィンドウを閉じる前の確認"""
        if self._is_modified:
            reply = QMessageBox.question(
                self, "確認", "保存されていない変更があります。\n保存しますか？",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Save:
                self._on_save()
                if self._is_modified:  # 保存がキャンセルされた場合
                    event.ignore()
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
        event.accept()

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

    def _on_export_png(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "PNG出力", "", "PNG Files (*.png)"
        )
        if filepath:
            ExportService.export_page_to_image(self._scene, filepath, "PNG")
            QMessageBox.information(self, "完了", "PNGファイルを出力しました。")

    def _on_export_jpg(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "JPG出力", "", "JPEG Files (*.jpg)"
        )
        if filepath:
            ExportService.export_page_to_image(self._scene, filepath, "JPG", quality=EXPORT_JPG_QUALITY)
            QMessageBox.information(self, "完了", "JPGファイルを出力しました。")

    def _on_export_pdf(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "PDF出力", "", "PDF Files (*.pdf)"
        )
        if filepath:
            scenes = []
            for i in range(len(self._project.pages)):
                if i not in self._scenes:
                    scene = CanvasScene()
                    scene.set_page(self._project.pages[i])
                    self._scenes[i] = scene
                scenes.append(self._scenes[i])

            ExportService.export_project_to_pdf(self._project, scenes, filepath)
            QMessageBox.information(self, "完了", f"PDFファイルを出力しました。\n{len(scenes)}ページ")

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
