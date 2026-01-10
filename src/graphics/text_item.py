from PyQt6.QtWidgets import QGraphicsTextItem, QGraphicsItem
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

from src.models.text_element import TextElement


class TextGraphicsItem(QGraphicsTextItem):
    def __init__(self, text_element: TextElement, parent=None):
        super().__init__(text_element.text, parent)
        self.text_element = text_element
        self.setPos(text_element.x, text_element.y)

        font = QFont(text_element.font_family, text_element.font_size)
        self.setFont(font)
        self.setDefaultTextColor(QColor(text_element.color))

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)

        self.setRotation(text_element.rotation)

    def mouseDoubleClickEvent(self, event):
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        self.setFocus()
        super().mouseDoubleClickEvent(event)

    def focusOutEvent(self, event):
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.text_element.text = self.toPlainText()
        super().focusOutEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self._sync_to_model()
        return super().itemChange(change, value)

    def _sync_to_model(self):
        pos = self.pos()
        self.text_element.x = pos.x()
        self.text_element.y = pos.y()
