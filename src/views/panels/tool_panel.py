from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QButtonGroup,
                               QLabel, QFrame)
from PyQt6.QtCore import pyqtSignal

from src.utils.enums import ToolType
from src.services.template_service import TemplateService, Template


class ToolPanel(QWidget):
    tool_changed = pyqtSignal(ToolType)
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
            ("選択 (V)", ToolType.SELECT),
            ("分割線 (P)", ToolType.PANEL),
            ("吹き出し (B)", ToolType.SPEECH_BUBBLE),
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

    def _on_template_clicked(self):
        btn = self.sender()
        template = btn.property("template")
        if template:
            self.template_selected.emit(template)

    def set_tool(self, tool_type: ToolType):
        """外部からツールを設定"""
        for btn in self._btn_group.buttons():
            if btn.property("tool_type") == tool_type:
                btn.setChecked(True)
                self.tool_changed.emit(tool_type)
                break
