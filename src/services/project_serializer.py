import json
from typing import Optional

from src.models.project import Project
from src.models.page import Page
from src.models.divider_line import DividerLine
from src.models.speech_bubble import SpeechBubble
from src.models.text_element import TextElement
from src.models.panel_image_data import PanelImageData
from src.utils.enums import BubbleType
from src.utils.constants import DEFAULT_MARGIN


class ProjectSerializer:
    """プロジェクトのシリアライズ/デシリアライズを行うサービス"""

    FILE_VERSION = "1.0"

    @staticmethod
    def serialize(project: Project) -> str:
        """プロジェクトをJSON文字列に変換"""
        data = {
            "version": ProjectSerializer.FILE_VERSION,
            "name": project.name,
            "pages": [ProjectSerializer._serialize_page(page) for page in project.pages]
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def _serialize_page(page: Page) -> dict:
        """ページをdict形式に変換"""
        return {
            "id": page.id,
            "width": page.width,
            "height": page.height,
            "margin": page.margin,
            "divider_lines": [ProjectSerializer._serialize_divider(d) for d in page.divider_lines],
            "panel_images": {
                panel_id: ProjectSerializer._serialize_panel_image(img_data)
                for panel_id, img_data in page.panel_images.items()
            },
            "speech_bubbles": [ProjectSerializer._serialize_bubble(b) for b in page.speech_bubbles],
            "text_elements": [ProjectSerializer._serialize_text(t) for t in page.text_elements]
        }

    @staticmethod
    def _serialize_divider(divider: DividerLine) -> dict:
        return {
            "id": divider.id,
            "x1": divider.x1,
            "y1": divider.y1,
            "x2": divider.x2,
            "y2": divider.y2,
            "gutter_width": divider.gutter_width
        }

    @staticmethod
    def _serialize_panel_image(img_data: PanelImageData) -> dict:
        return {
            "image_path": img_data.image_path,
            "scale": img_data.scale,
            "offset_x": img_data.offset_x,
            "offset_y": img_data.offset_y
        }

    @staticmethod
    def _serialize_bubble(bubble: SpeechBubble) -> dict:
        return {
            "id": bubble.id,
            "x": bubble.x,
            "y": bubble.y,
            "width": bubble.width,
            "height": bubble.height,
            "text": bubble.text,
            "bubble_type": bubble.bubble_type.name,
            "font_family": bubble.font_family,
            "font_size": bubble.font_size,
            "tail_x": bubble.tail_x,
            "tail_y": bubble.tail_y,
            "vertical": bubble.vertical
        }

    @staticmethod
    def _serialize_text(text: TextElement) -> dict:
        return {
            "id": text.id,
            "x": text.x,
            "y": text.y,
            "text": text.text,
            "font_family": text.font_family,
            "font_size": text.font_size,
            "color": text.color,
            "rotation": text.rotation
        }

    @staticmethod
    def deserialize(json_str: str) -> Optional[Project]:
        """JSON文字列からプロジェクトを復元"""
        try:
            data = json.loads(json_str)
            project = Project(name=data.get("name", "Untitled"), pages=[])

            for page_data in data.get("pages", []):
                page = ProjectSerializer._deserialize_page(page_data)
                project.pages.append(page)

            # ページが空なら1ページ追加
            if not project.pages:
                project.pages.append(Page())

            return project
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"プロジェクト読み込みエラー: {e}")
            return None

    @staticmethod
    def _deserialize_page(data: dict) -> Page:
        """dictからページを復元"""
        page = Page(
            id=data.get("id"),
            width=data.get("width", 1600),
            height=data.get("height", 2560),
            margin=data.get("margin", DEFAULT_MARGIN),
            divider_lines=[],
            panel_images={},
            speech_bubbles=[],
            text_elements=[]
        )

        # 分割線
        for d_data in data.get("divider_lines", []):
            page.divider_lines.append(ProjectSerializer._deserialize_divider(d_data))

        # パネル画像
        for panel_id, img_data in data.get("panel_images", {}).items():
            page.panel_images[panel_id] = ProjectSerializer._deserialize_panel_image(img_data)

        # 吹き出し
        for b_data in data.get("speech_bubbles", []):
            page.speech_bubbles.append(ProjectSerializer._deserialize_bubble(b_data))

        # テキスト
        for t_data in data.get("text_elements", []):
            page.text_elements.append(ProjectSerializer._deserialize_text(t_data))

        return page

    @staticmethod
    def _deserialize_divider(data: dict) -> DividerLine:
        return DividerLine(
            id=data.get("id"),
            x1=data.get("x1", 0),
            y1=data.get("y1", 0),
            x2=data.get("x2", 100),
            y2=data.get("y2", 100),
            gutter_width=data.get("gutter_width", DEFAULT_MARGIN)
        )

    @staticmethod
    def _deserialize_panel_image(data: dict) -> PanelImageData:
        return PanelImageData(
            image_path=data.get("image_path", ""),
            scale=data.get("scale", 1.0),
            offset_x=data.get("offset_x", 0.0),
            offset_y=data.get("offset_y", 0.0)
        )

    @staticmethod
    def _deserialize_bubble(data: dict) -> SpeechBubble:
        bubble_type = BubbleType.OVAL
        type_name = data.get("bubble_type", "OVAL")
        try:
            bubble_type = BubbleType[type_name]
        except KeyError:
            pass

        return SpeechBubble(
            id=data.get("id"),
            x=data.get("x", 0),
            y=data.get("y", 0),
            width=data.get("width", 150),
            height=data.get("height", 100),
            text=data.get("text", ""),
            bubble_type=bubble_type,
            font_family=data.get("font_family", "Yu Gothic"),
            font_size=data.get("font_size", 14),
            tail_x=data.get("tail_x", 0),
            tail_y=data.get("tail_y", 0),
            vertical=data.get("vertical", True)
        )

    @staticmethod
    def _deserialize_text(data: dict) -> TextElement:
        return TextElement(
            id=data.get("id"),
            x=data.get("x", 0),
            y=data.get("y", 0),
            text=data.get("text", ""),
            font_family=data.get("font_family", "Yu Gothic"),
            font_size=data.get("font_size", 14),
            color=data.get("color", "#000000"),
            rotation=data.get("rotation", 0)
        )

    @staticmethod
    def save_to_file(project: Project, filepath: str) -> bool:
        """プロジェクトをファイルに保存"""
        try:
            json_str = ProjectSerializer.serialize(project)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(json_str)
            return True
        except IOError as e:
            print(f"ファイル保存エラー: {e}")
            return False

    @staticmethod
    def load_from_file(filepath: str) -> Optional[Project]:
        """ファイルからプロジェクトを読み込み"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                json_str = f.read()
            return ProjectSerializer.deserialize(json_str)
        except IOError as e:
            print(f"ファイル読み込みエラー: {e}")
            return None
