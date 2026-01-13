from PyQt6.QtGui import QUndoCommand
from copy import deepcopy


class AddDividerCommand(QUndoCommand):
    """分割線追加のUndoコマンド"""
    def __init__(self, scene, divider, item):
        super().__init__("分割線を追加")
        self._scene = scene
        self._divider = divider
        self._item = item

    def redo(self):
        if self._divider not in self._scene._page.divider_lines:
            self._scene._page.divider_lines.append(self._divider)
        if self._item.scene() != self._scene:
            self._scene.addItem(self._item)
        self._scene._update_panels()
        self._scene.page_modified.emit()

    def undo(self):
        if self._divider in self._scene._page.divider_lines:
            self._scene._page.divider_lines.remove(self._divider)
        if self._item.scene() == self._scene:
            self._scene.removeItem(self._item)
        self._scene._update_panels()
        self._scene.page_modified.emit()


class DeleteDividerCommand(QUndoCommand):
    """分割線削除のUndoコマンド"""
    def __init__(self, scene, divider, item):
        super().__init__("分割線を削除")
        self._scene = scene
        self._divider = divider
        self._item = item

    def redo(self):
        if self._divider in self._scene._page.divider_lines:
            self._scene._page.divider_lines.remove(self._divider)
        if self._item.scene() == self._scene:
            self._scene.removeItem(self._item)
        self._scene._update_panels()
        self._scene.page_modified.emit()

    def undo(self):
        if self._divider not in self._scene._page.divider_lines:
            self._scene._page.divider_lines.append(self._divider)
        if self._item.scene() != self._scene:
            self._scene.addItem(self._item)
        self._scene._update_panels()
        self._scene.page_modified.emit()


class AddBubbleCommand(QUndoCommand):
    """吹き出し追加のUndoコマンド"""
    def __init__(self, scene, bubble, item):
        super().__init__("吹き出しを追加")
        self._scene = scene
        self._bubble = bubble
        self._item = item

    def redo(self):
        if self._bubble not in self._scene._page.speech_bubbles:
            self._scene._page.speech_bubbles.append(self._bubble)
        if self._item.scene() != self._scene:
            self._scene.addItem(self._item)
        self._scene.page_modified.emit()

    def undo(self):
        if self._bubble in self._scene._page.speech_bubbles:
            self._scene._page.speech_bubbles.remove(self._bubble)
        if self._item.scene() == self._scene:
            self._scene.removeItem(self._item)
        self._scene.page_modified.emit()


class DeleteBubbleCommand(QUndoCommand):
    """吹き出し削除のUndoコマンド"""
    def __init__(self, scene, bubble, item):
        super().__init__("吹き出しを削除")
        self._scene = scene
        self._bubble = bubble
        self._item = item

    def redo(self):
        if self._bubble in self._scene._page.speech_bubbles:
            self._scene._page.speech_bubbles.remove(self._bubble)
        if self._item.scene() == self._scene:
            self._scene.removeItem(self._item)
        self._scene.page_modified.emit()

    def undo(self):
        if self._bubble not in self._scene._page.speech_bubbles:
            self._scene._page.speech_bubbles.append(self._bubble)
        if self._item.scene() != self._scene:
            self._scene.addItem(self._item)
        self._scene.page_modified.emit()


