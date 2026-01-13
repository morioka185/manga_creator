from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
                               QPushButton, QHBoxLayout, QMenu)
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QIcon

from src.models.project import Project
from src.models.page import Page
from src.services.settings_service import SettingsService
from src.utils.constants import (
    PANEL_MARGIN, THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT, THUMBNAIL_SPACING,
    COLOR_WHITE, COLOR_GRAY, COLOR_BLACK,
    DEFAULT_PAGE_WIDTH, DEFAULT_PAGE_HEIGHT
)


class PageListWidget(QWidget):
    page_selected = pyqtSignal(int)
    page_added = pyqtSignal()
    page_deleted = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._project = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(PANEL_MARGIN, PANEL_MARGIN, PANEL_MARGIN, PANEL_MARGIN)

        self._list = QListWidget()
        self._list.setIconSize(QSize(THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT))
        self._list.setSpacing(THUMBNAIL_SPACING)
        self._list.currentRowChanged.connect(self._on_row_changed)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self._list)

        btn_layout = QHBoxLayout()
        self._add_btn = QPushButton("+ ページ追加")
        self._add_btn.clicked.connect(self._on_add_clicked)
        btn_layout.addWidget(self._add_btn)
        layout.addLayout(btn_layout)

    def set_project(self, project: Project):
        self._project = project
        self._refresh_list()

    def _refresh_list(self):
        self._list.clear()
        if not self._project:
            return

        for i, page in enumerate(self._project.pages):
            item = QListWidgetItem(f"P{i + 1}")
            thumbnail = self._create_thumbnail(page)
            item.setIcon(QIcon(thumbnail))
            self._list.addItem(item)

        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    def _create_thumbnail(self, page: Page) -> QPixmap:
        thumb_w, thumb_h = THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT
        img = QImage(thumb_w, thumb_h, QImage.Format.Format_RGB32)
        img.fill(QColor(*COLOR_WHITE))

        painter = QPainter(img)
        painter.setPen(QColor(*COLOR_GRAY))
        painter.drawRect(0, 0, thumb_w - 1, thumb_h - 1)

        scale_x = thumb_w / page.width
        scale_y = thumb_h / page.height

        painter.setPen(QColor(*COLOR_BLACK))
        # 分割線を描画
        for divider in page.divider_lines:
            x1 = int(divider.x1 * scale_x)
            y1 = int(divider.y1 * scale_y)
            x2 = int(divider.x2 * scale_x)
            y2 = int(divider.y2 * scale_y)
            painter.drawLine(x1, y1, x2, y2)

        painter.end()
        return QPixmap.fromImage(img)

    def _on_row_changed(self, row):
        if row >= 0:
            self.page_selected.emit(row)

    def _on_add_clicked(self):
        if self._project:
            settings = SettingsService.get_instance()
            self._project.pages.append(Page(
                width=settings.page_width,
                height=settings.page_height,
                margin=settings.page_margin
            ))
            self._refresh_list()
            self._list.setCurrentRow(len(self._project.pages) - 1)
            self.page_added.emit()

    def _show_context_menu(self, pos):
        item = self._list.itemAt(pos)
        if not item:
            return

        row = self._list.row(item)
        menu = QMenu(self)

        delete_action = menu.addAction("削除")
        duplicate_action = menu.addAction("複製")

        action = menu.exec(self._list.mapToGlobal(pos))

        if action == delete_action:
            if len(self._project.pages) > 1:
                self._project.pages.pop(row)
                # 削除されたページのインデックスを先に通知
                self.page_deleted.emit(row)
                # リストを更新（setCurrentRowはせず手動で選択）
                self._list.clear()
                for i, page in enumerate(self._project.pages):
                    item = QListWidgetItem(f"P{i + 1}")
                    thumbnail = self._create_thumbnail(page)
                    item.setIcon(QIcon(thumbnail))
                    self._list.addItem(item)
                # 適切なページを選択
                new_row = min(row, len(self._project.pages) - 1)
                self._list.setCurrentRow(new_row)
        elif action == duplicate_action:
            original = self._project.pages[row]
            new_page = Page(width=original.width, height=original.height)
            self._project.pages.insert(row + 1, new_page)
            self._refresh_list()

    def update_thumbnail(self, page_index: int):
        if self._project and 0 <= page_index < len(self._project.pages):
            page = self._project.pages[page_index]
            thumbnail = self._create_thumbnail(page)
            self._list.item(page_index).setIcon(QIcon(thumbnail))

    def select_page(self, index: int):
        if 0 <= index < self._list.count():
            self._list.setCurrentRow(index)
