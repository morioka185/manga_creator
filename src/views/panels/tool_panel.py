from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QButtonGroup,
                               QLabel, QComboBox, QFrame)
from PyQt6.QtCore import pyqtSignal

from src.utils.enums import ToolType, BubbleType
from src.services.template_service import TemplateService, Template


class ToolPanel(QWidget):
    tool_changed = pyqtSignal(ToolType)
    bubble_type_changed = pyqtSignal(BubbleType)
    template_selected = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        tool_label = QLabel("ツール")
        tool_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(tool_label)

        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)

        tools = [
            ("選択", ToolType.SELECT),
            ("分割線", ToolType.PANEL),
            ("吹き出し", ToolType.SPEECH_BUBBLE),
            ("テキスト", ToolType.TEXT),
        ]

        for name, tool_type in tools:
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setProperty("tool_type", tool_type)
            self._btn_group.addButton(btn)
            layout.addWidget(btn)
            if tool_type == ToolType.SELECT:
                btn.setChecked(True)

        self._btn_group.buttonClicked.connect(self._on_tool_clicked)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(separator)

        bubble_label = QLabel("吹き出し種類")
        bubble_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(bubble_label)

        self._bubble_combo = QComboBox()
        self._bubble_combo.addItem("楕円", BubbleType.OVAL)
        self._bubble_combo.addItem("角丸", BubbleType.ROUNDED_RECT)
        self._bubble_combo.addItem("雲形", BubbleType.CLOUD)
        self._bubble_combo.addItem("爆発", BubbleType.EXPLOSION)
        self._bubble_combo.currentIndexChanged.connect(self._on_bubble_changed)
        layout.addWidget(self._bubble_combo)

        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(separator2)

        template_label = QLabel("テンプレート")
        template_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(template_label)

        self._templates = TemplateService.get_templates()
        for template in self._templates:
            btn = QPushButton(template.name)
            btn.setProperty("template", template)
            btn.clicked.connect(self._on_template_clicked)
            layout.addWidget(btn)

        layout.addStretch()

    def _on_tool_clicked(self, btn):
        tool_type = btn.property("tool_type")
        self.tool_changed.emit(tool_type)

    def _on_bubble_changed(self, index):
        bubble_type = self._bubble_combo.itemData(index)
        self.bubble_type_changed.emit(bubble_type)

    def _on_template_clicked(self):
        btn = self.sender()
        template = btn.property("template")
        if template:
            self.template_selected.emit(template)
