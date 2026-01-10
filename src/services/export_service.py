from PyQt6.QtWidgets import QGraphicsScene
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QImage, QPainter, QColor

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.utils import ImageReader
from PIL import Image
import io
import os

from src.models.project import Project
from src.graphics.divider_line_item import DividerLineItem


class ExportService:
    @staticmethod
    def _hide_dividers(scene: QGraphicsScene) -> list:
        """分割線を非表示にし、元の状態を返す"""
        states = []
        for item in scene.items():
            if isinstance(item, DividerLineItem):
                states.append((item, item.isVisible()))
                item.setVisible(False)
        return states

    @staticmethod
    def _restore_dividers(states: list):
        """分割線の表示状態を復元"""
        for item, visible in states:
            item.setVisible(visible)

    @staticmethod
    def export_page_to_image(scene: QGraphicsScene, filepath: str,
                              format: str = "PNG", quality: int = 95, dpi: int = 300):
        # 分割線を一時的に非表示
        divider_states = ExportService._hide_dividers(scene)

        rect = scene.sceneRect()
        scale = dpi / 72.0

        image = QImage(
            int(rect.width() * scale),
            int(rect.height() * scale),
            QImage.Format.Format_ARGB32
        )
        image.fill(QColor(255, 255, 255))

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.scale(scale, scale)
        scene.render(painter)
        painter.end()

        # 分割線を復元
        ExportService._restore_dividers(divider_states)

        if format.upper() == "JPG":
            image.save(filepath, "JPEG", quality)
        else:
            image.save(filepath, format.upper())

    @staticmethod
    def export_project_to_pdf(project: Project, scenes: list, filepath: str, dpi: int = 150):
        if not scenes:
            return

        first_page = project.pages[0]
        page_width = first_page.width
        page_height = first_page.height

        c = pdf_canvas.Canvas(filepath, pagesize=(page_width, page_height))

        for i, scene in enumerate(scenes):
            if i > 0:
                c.showPage()
                c.setPageSize((project.pages[i].width, project.pages[i].height))

            # 分割線を一時的に非表示
            divider_states = ExportService._hide_dividers(scene)

            rect = scene.sceneRect()
            scale = dpi / 72.0

            image = QImage(
                int(rect.width() * scale),
                int(rect.height() * scale),
                QImage.Format.Format_RGB32
            )
            image.fill(QColor(255, 255, 255))

            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.scale(scale, scale)
            scene.render(painter)
            painter.end()

            # 分割線を復元
            ExportService._restore_dividers(divider_states)

            buffer = io.BytesIO()
            image.save(buffer, "PNG")
            buffer.seek(0)

            pil_img = Image.open(buffer)
            img_reader = ImageReader(pil_img)

            c.drawImage(img_reader, 0, 0,
                       width=project.pages[i].width,
                       height=project.pages[i].height)

        c.save()

    @staticmethod
    def scene_to_qimage(scene: QGraphicsScene, dpi: int = 150) -> QImage:
        rect = scene.sceneRect()
        scale = dpi / 72.0

        image = QImage(
            int(rect.width() * scale),
            int(rect.height() * scale),
            QImage.Format.Format_ARGB32
        )
        image.fill(QColor(255, 255, 255))

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.scale(scale, scale)
        scene.render(painter)
        painter.end()

        return image
