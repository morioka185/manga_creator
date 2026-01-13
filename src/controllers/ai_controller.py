import uuid

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QMessageBox

from src.models.project import Project
from src.models.page import Page
from src.models.speech_bubble import SpeechBubble
from src.models.panel_image_data import PanelImageData
from src.services.image_path_service import ImagePathService
from src.services.template_service import TemplateService
from src.services.story_import_service import StoryDialogue
from src.utils.enums import BubbleType
from src.utils.constants import (
    STATUSBAR_MESSAGE_TIMEOUT_LONG, DEFAULT_FONT_SIZE, BUBBLE_TEXT_PADDING,
    ROUNDED_RECT_RADIUS
)


class AIController(QObject):
    """AI画像生成関連の機能を管理"""

    # シグナル
    page_modified = pyqtSignal()
    status_message = pyqtSignal(str, int)
    title_update_requested = pyqtSignal()

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
    def _scene(self):
        return self._main_window._scene

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
    def _current_page_index(self):
        return self._main_window._current_page_index

    def _check_project_saved_for_image_gen(self) -> bool:
        """画像生成前にプロジェクトが保存されているかチェック"""
        if not self._current_file_path:
            reply = QMessageBox.question(
                self._main_window, "プロジェクト未保存",
                "画像をプロジェクトフォルダに保存するには、\n"
                "先にプロジェクトを保存する必要があります。\n\n"
                "今すぐプロジェクトを保存しますか？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._main_window._file_controller.on_save_as()
                return self._current_file_path is not None
            return False
        return True

    def _get_page_save_folder(self) -> str:
        """現在のページ用の画像保存フォルダを取得"""
        image_path_service = ImagePathService.get_instance()
        folder = image_path_service.ensure_page_folder(self._current_page_index + 1)
        return str(folder) if folder else ""

    def _get_default_browse_path(self) -> str:
        """画像選択のデフォルトパスを取得"""
        image_path_service = ImagePathService.get_instance()
        return image_path_service.get_page_browse_folder(self._current_page_index + 1)

    def on_ai_generate(self):
        """AI画像生成ダイアログを開く"""
        if not self._check_project_saved_for_image_gen():
            return

        from src.graphics.panel_polygon_item import PanelPolygonItem

        panel_size = None
        items = self._scene.selectedItems()
        for item in items:
            if isinstance(item, PanelPolygonItem):
                rect = item.boundingRect()
                panel_size = (int(rect.width()), int(rect.height()))
                break

        from src.views.dialogs.image_gen_dialog import ImageGenDialog
        dialog = ImageGenDialog(
            panel_size=panel_size,
            save_folder=self._get_page_save_folder(),
            default_browse_path=self._get_default_browse_path(),
            parent=self._main_window
        )

        if dialog.exec():
            image_path = dialog.get_generated_image_path()
            if image_path:
                for item in items:
                    if isinstance(item, PanelPolygonItem):
                        item.set_image(image_path)
                        self._scene._save_panel_image(item.panel_id, item.get_image_data())
                        self.page_modified.emit()
                        self.status_message.emit(
                            "AI生成画像をコマに配置しました",
                            STATUSBAR_MESSAGE_TIMEOUT_LONG
                        )
                        return

                self.status_message.emit(
                    f"画像を保存しました: {image_path}",
                    STATUSBAR_MESSAGE_TIMEOUT_LONG
                )

    def on_ai_generate_for_panel(self, panel_id: str, width: int, height: int):
        """特定のコマに対してAI画像生成ダイアログを開く"""
        if not self._check_project_saved_for_image_gen():
            return

        from src.graphics.panel_polygon_item import PanelPolygonItem
        from src.views.dialogs.image_gen_dialog import ImageGenDialog

        dialog = ImageGenDialog(
            panel_size=(width, height),
            save_folder=self._get_page_save_folder(),
            default_browse_path=self._get_default_browse_path(),
            parent=self._main_window
        )

        if dialog.exec():
            image_path = dialog.get_generated_image_path()
            if image_path:
                settings = dialog.get_generation_settings()
                for item in self._scene.items():
                    if isinstance(item, PanelPolygonItem) and item.panel_id == panel_id:
                        item.set_image_with_generation_data(
                            image_path,
                            settings.get('prompt', ''),
                            settings.get('negative_prompt', ''),
                            settings.get('seed', -1),
                            settings.get('character_ids', []),
                            batch_mode=settings.get('batch_mode', False),
                            final_prompt=settings.get('final_prompt', ''),
                            final_negative_prompt=settings.get('final_negative_prompt', '')
                        )
                        self._scene._save_panel_image(item.panel_id, item.get_image_data())
                        self.page_modified.emit()
                        self.status_message.emit(
                            "AI生成画像をコマに配置しました",
                            STATUSBAR_MESSAGE_TIMEOUT_LONG
                        )
                        return

    def on_ai_regenerate_for_panel(self, panel_id: str, width: int, height: int, settings: dict):
        """同じ設定で再生成ダイアログを開く"""
        if not self._check_project_saved_for_image_gen():
            return

        from src.graphics.panel_polygon_item import PanelPolygonItem
        from src.views.dialogs.image_gen_dialog import ImageGenDialog

        dialog = ImageGenDialog(
            panel_size=(width, height),
            save_folder=self._get_page_save_folder(),
            default_browse_path=self._get_default_browse_path(),
            parent=self._main_window
        )
        dialog.set_initial_settings(settings)

        if dialog.exec():
            image_path = dialog.get_generated_image_path()
            if image_path:
                new_settings = dialog.get_generation_settings()
                for item in self._scene.items():
                    if isinstance(item, PanelPolygonItem) and item.panel_id == panel_id:
                        item.set_image_with_generation_data(
                            image_path,
                            new_settings.get('prompt', ''),
                            new_settings.get('negative_prompt', ''),
                            new_settings.get('seed', -1),
                            new_settings.get('character_ids', []),
                            batch_mode=new_settings.get('batch_mode', False),
                            final_prompt=new_settings.get('final_prompt', ''),
                            final_negative_prompt=new_settings.get('final_negative_prompt', '')
                        )
                        self._scene._save_panel_image(item.panel_id, item.get_image_data())
                        self.page_modified.emit()
                        self.status_message.emit(
                            "AI再生成画像をコマに配置しました",
                            STATUSBAR_MESSAGE_TIMEOUT_LONG
                        )
                        return

    def on_ai_character_manager(self):
        """キャラクター管理ダイアログを開く"""
        from src.views.dialogs.character_manager_dialog import CharacterManagerDialog
        dialog = CharacterManagerDialog(self._main_window)
        dialog.exec()

    def on_story_import(self):
        """ストーリー仕様書インポートダイアログを開く"""
        from src.views.dialogs.story_import_dialog import StoryImportDialog

        dialog = StoryImportDialog(self._main_window)

        if dialog.exec():
            story_spec = dialog.get_story_spec()
            generated_panels = dialog.get_generated_panels()

            if not story_spec or not generated_panels:
                return

            # 既存ページ数を保存（新規ページはこの後ろに追加される）
            base_page_index = len(self._project.pages) if self._project else 0

            self._create_project_from_story(story_spec)
            sorted_pages = self._apply_templates_to_pages(story_spec)
            self._place_generated_images(sorted_pages, generated_panels, base_page_index)
            self._create_speech_bubbles(sorted_pages, generated_panels, base_page_index)
            self._finalize_import(story_spec, base_page_index)

    def _create_project_from_story(self, story_spec):
        """ストーリーから既存プロジェクトにページを追加（プロジェクトがない場合は新規作成）"""
        if not self._project:
            # プロジェクトがない場合のみ新規作成
            self._project = Project(
                name=story_spec.title or "ストーリープロジェクト",
                pages=[]
            )
        # 既存プロジェクトのシーンキャッシュから追加予定のページ分はクリアしない
        # （既存ページは維持される）
        self._is_modified = True

    def _apply_templates_to_pages(self, story_spec) -> list:
        """各ページにテンプレート適用"""
        template_mapping = {
            "3panel_vertical": "3段",
            "4panel_vertical": "4コマ（縦）",
            "4panel_2x2": "4コマ（2x2）",
            "5panel_mixed": "5コマ（大+4）",
            "6panel_2x3": "6コマ（2x3）",
            "6panel_3x2": "6コマ（3x2）",
        }
        templates = {t.name: t for t in TemplateService.get_templates()}

        sorted_pages = sorted(story_spec.pages, key=lambda p: p.page_number)

        for story_page in sorted_pages:
            page = Page()
            self._project.pages.append(page)

            template_name = template_mapping.get(story_page.template)
            if template_name and template_name in templates:
                TemplateService.apply_template(page, templates[template_name])

        return sorted_pages

    def _place_generated_images(self, sorted_pages, generated_panels, base_page_index: int = 0):
        """生成画像をコマに配置"""
        for gen_panel in generated_panels:
            actual_page_index = base_page_index + gen_panel.page_index
            if actual_page_index < len(self._project.pages):
                page = self._project.pages[actual_page_index]

                panel_id = f"panel_{gen_panel.panel_index}"
                image_data = PanelImageData(
                    image_path=gen_panel.image_path,
                    generation_prompt=gen_panel.prompt,
                    negative_prompt=gen_panel.negative_prompt,
                    generation_seed=int(gen_panel.seed) if gen_panel.seed.isdigit() else -1,
                    character_ids=gen_panel.character_ids,
                    batch_mode=True,  # 一括生成フラグをON
                    final_prompt=gen_panel.final_prompt,  # 一括生成時の最終プロンプト
                    final_negative_prompt=gen_panel.final_negative_prompt
                )
                page.panel_images[panel_id] = image_data

    def _create_speech_bubbles(self, sorted_pages, generated_panels, base_page_index: int = 0):
        """セリフを吹き出しとして配置"""
        from src.services.panel_calculator import PanelCalculator

        for gen_panel in generated_panels:
            actual_page_index = base_page_index + gen_panel.page_index
            if actual_page_index >= len(self._project.pages):
                continue

            page = self._project.pages[actual_page_index]
            story_page = sorted_pages[gen_panel.page_index]
            sorted_panels = sorted(story_page.panels, key=lambda p: p.panel_index)

            if gen_panel.panel_index >= len(sorted_panels):
                continue

            # コマ領域を計算
            panel_polygons = PanelCalculator.calculate_panels(
                page.width, page.height, page.divider_lines, page.margin
            )

            # 対応するコマのバウンディングボックスを取得
            panel_rect = None
            if gen_panel.panel_index < len(panel_polygons):
                panel_rect = panel_polygons[gen_panel.panel_index].boundingRect()

            panel_data = sorted_panels[gen_panel.panel_index]
            for i, dialogue in enumerate(panel_data.dialogues):
                bubble = self._create_bubble_for_dialogue(
                    dialogue, gen_panel.panel_index, i, panel_rect
                )
                page.speech_bubbles.append(bubble)

    def _create_bubble_for_dialogue(
        self, dialogue: StoryDialogue, panel_index: int, dialogue_index: int,
        panel_rect=None
    ) -> SpeechBubble:
        """セリフ用の吹き出しを作成

        Args:
            dialogue: セリフ情報
            panel_index: コマのインデックス
            dialogue_index: セリフのインデックス（コマ内）
            panel_rect: コマのバウンディングボックス（QRectF）
        """
        text = dialogue.text
        font_size = DEFAULT_FONT_SIZE
        padding = BUBBLE_TEXT_PADDING * 2

        lines = text.split('\n') if '\n' in text else [text]
        max_chars = max(len(line) for line in lines)
        num_lines = len(lines)

        char_height = font_size
        line_spacing = font_size * 1.2
        ellipse_factor = 1.5

        bubble_height = (max_chars * char_height + padding) * ellipse_factor
        bubble_width = (num_lines * line_spacing + padding) * ellipse_factor

        bubble_width = max(bubble_width, 80)
        bubble_height = max(bubble_height, 100)

        # BubbleTypeを文字列から変換
        try:
            bubble_type = BubbleType[dialogue.bubble_type]
        except KeyError:
            bubble_type = BubbleType.SPEECH

        # コマ領域内に吹き出しを配置
        if panel_rect:
            # コマ内の右上寄りに配置し、複数セリフは下にずらす
            margin = 20
            x = panel_rect.right() - bubble_width - margin - (dialogue_index * 30)
            y = panel_rect.top() + margin + (dialogue_index * (bubble_height + 20))

            # コマ内に収まるように調整
            x = max(panel_rect.left() + margin, min(x, panel_rect.right() - bubble_width - margin))
            y = max(panel_rect.top() + margin, min(y, panel_rect.bottom() - bubble_height - margin))
        else:
            # コマ領域が取得できない場合はデフォルト位置
            x = 100 + (panel_index * 200)
            y = 100 + (dialogue_index * 150)

        return SpeechBubble(
            id=str(uuid.uuid4()),
            x=x,
            y=y,
            width=bubble_width,
            height=bubble_height,
            text=text,
            bubble_type=bubble_type,
            vertical=dialogue.vertical,
            rotation=dialogue.rotation,
            color=dialogue.color,
            corner_radius=ROUNDED_RECT_RADIUS
        )

    def _finalize_import(self, story_spec, base_page_index: int = 0):
        """インポート完了処理"""
        self._main_window._page_list.set_project(self._project)
        # 追加されたページの最初に移動
        self._main_window._load_page(base_page_index)
        self.title_update_requested.emit()

        added_pages = len(story_spec.pages)
        self.status_message.emit(
            f"ストーリーから{added_pages}ページを追加しました（合計{len(self._project.pages)}ページ）",
            STATUSBAR_MESSAGE_TIMEOUT_LONG
        )
