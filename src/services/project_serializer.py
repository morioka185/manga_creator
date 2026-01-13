import json
from typing import Optional

from src.models.project import Project
from src.models.page import Page
from src.models.divider_line import DividerLine
from src.models.speech_bubble import SpeechBubble
from src.models.panel_image_data import PanelImageData
from src.models.character import Character
from src.utils.enums import BubbleType
from src.utils.constants import DEFAULT_MARGIN, ROUNDED_RECT_RADIUS, DEFAULT_BUBBLE_WIDTH, DEFAULT_BUBBLE_HEIGHT


class ProjectSerializer:
    """プロジェクトのシリアライズ/デシリアライズを行うサービス"""

    FILE_VERSION = "1.1"

    @staticmethod
    def serialize(project: Project) -> str:
        """プロジェクトをJSON文字列に変換"""
        data = {
            "version": ProjectSerializer.FILE_VERSION,
            "name": project.name,
            "pages": [ProjectSerializer._serialize_page(page) for page in project.pages],
            "characters": [char.to_dict() for char in project.characters]
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
            "speech_bubbles": [ProjectSerializer._serialize_bubble(b) for b in page.speech_bubbles]
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
        return img_data.to_dict()

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
            "vertical": bubble.vertical,
            "auto_font_size": bubble.auto_font_size,
            "rotation": bubble.rotation,
            "color": bubble.color,
            "corner_radius": bubble.corner_radius
        }

    @staticmethod
    def deserialize(json_str: str) -> Optional[Project]:
        """JSON文字列からプロジェクトを復元"""
        try:
            data = json.loads(json_str)
            project = Project(name=data.get("name", "Untitled"), pages=[], characters=[])

            for page_data in data.get("pages", []):
                page = ProjectSerializer._deserialize_page(page_data)
                project.pages.append(page)

            # キャラクター復元
            for char_data in data.get("characters", []):
                project.characters.append(Character.from_dict(char_data))

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
            speech_bubbles=[]
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

        # 後方互換性: 旧text_elementsをTEXT_ONLYタイプのspeech_bubblesに変換
        for t_data in data.get("text_elements", []):
            page.speech_bubbles.append(ProjectSerializer._migrate_text_to_bubble(t_data))

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
        return PanelImageData.from_dict(data)

    @staticmethod
    def _deserialize_bubble(data: dict) -> SpeechBubble:
        bubble_type = BubbleType.SPEECH
        type_name = data.get("bubble_type", "SPEECH")

        # 後方互換性: 旧タイプ名をマッピング
        type_mapping = {
            "ROUNDED_RECT": "RECTANGLE",  # 角丸四角形は長方形に統合
            "OVAL": "OVAL",  # 旧OVALはそのまま（尻尾なしに変更）
        }
        type_name = type_mapping.get(type_name, type_name)

        try:
            bubble_type = BubbleType[type_name]
        except KeyError:
            bubble_type = BubbleType.SPEECH

        return SpeechBubble(
            id=data.get("id"),
            x=data.get("x", 0),
            y=data.get("y", 0),
            width=data.get("width", DEFAULT_BUBBLE_WIDTH),
            height=data.get("height", DEFAULT_BUBBLE_HEIGHT),
            text=data.get("text", ""),
            bubble_type=bubble_type,
            font_family=data.get("font_family", "Yu Gothic"),
            font_size=data.get("font_size", 48),
            tail_x=data.get("tail_x", 0),
            tail_y=data.get("tail_y", 0),
            vertical=data.get("vertical", True),
            auto_font_size=data.get("auto_font_size", True),
            rotation=data.get("rotation", 0),
            color=data.get("color", "#000000"),
            corner_radius=data.get("corner_radius", ROUNDED_RECT_RADIUS)
        )

    @staticmethod
    def _migrate_text_to_bubble(data: dict) -> SpeechBubble:
        """旧TextElementデータをTEXT_ONLYタイプのSpeechBubbleに変換"""
        return SpeechBubble(
            id=data.get("id"),
            x=data.get("x", 0),
            y=data.get("y", 0),
            width=DEFAULT_BUBBLE_WIDTH,
            height=DEFAULT_BUBBLE_HEIGHT,
            text=data.get("text", ""),
            bubble_type=BubbleType.TEXT_ONLY,
            font_family=data.get("font_family", "Yu Gothic"),
            font_size=data.get("font_size", 48),
            tail_x=0,
            tail_y=0,
            vertical=False,  # 旧テキストは横書き
            auto_font_size=False,
            rotation=data.get("rotation", 0),
            color=data.get("color", "#000000"),
            corner_radius=0
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
