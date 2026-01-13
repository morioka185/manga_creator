from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence

from src.services.settings_service import SettingsService
from src.graphics.speech_bubble_item import SpeechBubbleGraphicsItem
from src.utils.constants import STATUSBAR_MESSAGE_TIMEOUT


class MenuController(QObject):
    """メニュー関連の機能を管理（主にスタイル関連）"""

    # シグナル
    page_modified = pyqtSignal()
    status_message = pyqtSignal(str, int)

    def __init__(self, main_window):
        super().__init__(main_window)
        self._main_window = main_window
        self._style_menu = None

    def set_style_menu(self, menu):
        """スタイルメニューを設定"""
        self._style_menu = menu

    def update_style_menu(self):
        """スタイルメニューを更新"""
        if not self._style_menu:
            return

        self._style_menu.clear()
        settings = SettingsService.get_instance()

        for i, style in enumerate(settings.get_font_styles()):
            action = QAction(style.name, self._main_window)
            if i < 9:
                action.setShortcut(QKeySequence(str(i + 1)))
            action.triggered.connect(lambda checked, s=style: self.apply_style(s))
            self._style_menu.addAction(action)

        self._style_menu.addSeparator()
        edit_action = QAction("スタイルを編集...", self._main_window)
        edit_action.triggered.connect(self._main_window._on_settings)
        self._style_menu.addAction(edit_action)

    def apply_style(self, style):
        """選択中のアイテムにスタイルを適用"""
        items = self._main_window._scene.selectedItems()
        if not items:
            self.status_message.emit("アイテムを選択してください", STATUSBAR_MESSAGE_TIMEOUT)
            return

        for item in items:
            if isinstance(item, SpeechBubbleGraphicsItem):
                item.bubble.font_family = style.font_family
                item.bubble.font_size = style.font_size
                item.update()

        if items:
            self._main_window._property_panel.set_selected_item(items[0])

        self.page_modified.emit()
        self.status_message.emit(f"スタイル「{style.name}」を適用しました", STATUSBAR_MESSAGE_TIMEOUT)
