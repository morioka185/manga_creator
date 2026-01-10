from PyQt6.QtWidgets import QGraphicsView
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter

from src.utils.constants import DEFAULT_ZOOM, MIN_ZOOM, MAX_ZOOM, ZOOM_FACTOR


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

        self._zoom = DEFAULT_ZOOM
        self._first_show = True

    def showEvent(self, event):
        super().showEvent(event)
        if self._first_show:
            self._first_show = False
            # 初回表示時に画面にフィット
            self.fit_to_view()

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
        if self._zoom < MAX_ZOOM:
            self._zoom *= ZOOM_FACTOR
            self.setTransform(self.transform().scale(ZOOM_FACTOR, ZOOM_FACTOR))

    def zoom_out(self):
        if self._zoom > MIN_ZOOM:
            self._zoom /= ZOOM_FACTOR
            self.setTransform(self.transform().scale(1/ZOOM_FACTOR, 1/ZOOM_FACTOR))

    def reset_zoom(self):
        self._zoom = DEFAULT_ZOOM
        self.resetTransform()

    def fit_to_view(self):
        self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom = self.transform().m11()
