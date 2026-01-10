from PyQt6.QtWidgets import QGraphicsView
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter


class CanvasView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self._zoom = 1.0

    def wheelEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
        else:
            super().wheelEvent(event)

    def zoom_in(self):
        if self._zoom < 5.0:
            self._zoom *= 1.2
            self.setTransform(self.transform().scale(1.2, 1.2))

    def zoom_out(self):
        if self._zoom > 0.2:
            self._zoom /= 1.2
            self.setTransform(self.transform().scale(1/1.2, 1/1.2))

    def reset_zoom(self):
        self._zoom = 1.0
        self.resetTransform()

    def fit_to_view(self):
        self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom = self.transform().m11()
