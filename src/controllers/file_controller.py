from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from src.models.project import Project
from src.services.project_serializer import ProjectSerializer
from src.services.export_service import ExportService
from src.services.image_path_service import ImagePathService
from src.services.character_service import CharacterService
from src.views.canvas_scene import CanvasScene
from src.utils.constants import EXPORT_JPG_QUALITY, STATUSBAR_MESSAGE_TIMEOUT_LONG


class FileController(QObject):
    """ファイル操作関連の機能を管理"""

    # シグナル
    project_changed = pyqtSignal()
    title_update_requested = pyqtSignal()
    status_message = pyqtSignal(str, int)

    def __init__(self, main_window):
        super().__init__(main_window)
        self._main_window = main_window

    @property
    def _project(self):
        return self._main_window._project

    @_project.setter
    def _project(self, value):
        self._main_window._project = value

    @property
    def _scenes(self):
        return self._main_window._scenes

    @property
    def _current_file_path(self):
        return self._main_window._current_file_path

    @_current_file_path.setter
    def _current_file_path(self, value):
        self._main_window._current_file_path = value

    @property
    def _is_modified(self):
        return self._main_window._is_modified

    @_is_modified.setter
    def _is_modified(self, value):
        self._main_window._is_modified = value

    @property
    def _undo_stack(self):
        return self._main_window._undo_stack

    @property
    def _scene(self):
        return self._main_window._scene

    def on_new(self):
        """新規プロジェクトを作成"""
        if self._is_modified:
            reply = QMessageBox.question(
                self._main_window, "確認",
                "新規プロジェクトを作成しますか？\n保存されていない変更は失われます。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self._project = Project()
        self._scenes.clear()
        self._current_file_path = None
        self._is_modified = False
        self._undo_stack.clear()
        ImagePathService.get_instance().set_project_path(None)
        CharacterService.get_instance().set_project(self._project)
        self._main_window._page_list.set_project(self._project)
        self._main_window._load_page(0)
        self.title_update_requested.emit()

    def on_open(self):
        """プロジェクトを開く"""
        if self._is_modified:
            reply = QMessageBox.question(
                self._main_window, "確認",
                "プロジェクトを開きますか？\n保存されていない変更は失われます。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        filepath, _ = QFileDialog.getOpenFileName(
            self._main_window, "プロジェクトを開く", "",
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
                ImagePathService.get_instance().set_project_path(filepath)
                CharacterService.get_instance().set_project(self._project)
                self._main_window._page_list.set_project(self._project)
                self._main_window._load_page(0)
                self.title_update_requested.emit()
            else:
                QMessageBox.warning(self._main_window, "エラー", "プロジェクトの読み込みに失敗しました。")

    def on_save(self):
        """プロジェクトを保存"""
        if self._current_file_path:
            self._save_to_file(self._current_file_path)
        else:
            self.on_save_as()

    def on_save_as(self):
        """名前を付けて保存"""
        filepath, _ = QFileDialog.getSaveFileName(
            self._main_window, "名前を付けて保存", "",
            "Manga Project (*.manga);;JSON Files (*.json)"
        )
        if filepath:
            if not filepath.endswith('.manga') and not filepath.endswith('.json'):
                filepath += '.manga'
            self._save_to_file(filepath)

    def _save_to_file(self, filepath: str):
        """ファイルに保存"""
        if ProjectSerializer.save_to_file(self._project, filepath):
            self._current_file_path = filepath
            self._is_modified = False
            ImagePathService.get_instance().set_project_path(filepath)
            self.title_update_requested.emit()
            self.status_message.emit("保存しました", STATUSBAR_MESSAGE_TIMEOUT_LONG)
        else:
            QMessageBox.warning(self._main_window, "エラー", "保存に失敗しました。")

    def on_export_png(self):
        """PNG形式でエクスポート"""
        filepath, _ = QFileDialog.getSaveFileName(
            self._main_window, "PNG出力", "", "PNG Files (*.png)"
        )
        if filepath:
            ExportService.export_page_to_image(self._scene, filepath, "PNG")
            QMessageBox.information(self._main_window, "完了", "PNGファイルを出力しました。")

    def on_export_jpg(self):
        """JPEG形式でエクスポート"""
        filepath, _ = QFileDialog.getSaveFileName(
            self._main_window, "JPG出力", "", "JPEG Files (*.jpg)"
        )
        if filepath:
            ExportService.export_page_to_image(
                self._scene, filepath, "JPG", quality=EXPORT_JPG_QUALITY
            )
            QMessageBox.information(self._main_window, "完了", "JPGファイルを出力しました。")

    def on_export_pdf(self):
        """PDF形式でエクスポート"""
        filepath, _ = QFileDialog.getSaveFileName(
            self._main_window, "PDF出力", "", "PDF Files (*.pdf)"
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
            QMessageBox.information(
                self._main_window, "完了",
                f"PDFファイルを出力しました。\n{len(scenes)}ページ"
            )

    def check_unsaved_changes(self) -> bool:
        """未保存の変更を確認（Trueで続行可能）"""
        if self._is_modified:
            reply = QMessageBox.question(
                self._main_window, "確認",
                "保存されていない変更があります。\n保存しますか？",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Save:
                self.on_save()
                return not self._is_modified
            elif reply == QMessageBox.StandardButton.Cancel:
                return False
        return True
