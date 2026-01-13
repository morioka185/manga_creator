"""ストーリー仕様書（JSON）のインポートサービス"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from pathlib import Path


@dataclass
class StoryCharacter:
    """ストーリー内のキャラクター情報"""
    id: str
    name: str
    appearance: str = ""
    personality: str = ""
    prompt: str = ""


@dataclass
class StoryDialogue:
    """セリフ情報"""
    speaker: Optional[str]
    text: str
    bubble_type: str = "SPEECH"  # SPEECH, CLOUD, EXPLOSION, RECTANGLE, OVAL, TEXT_ONLY
    rotation: float = 0  # 回転角度（TEXT_ONLY用）
    color: str = "#000000"  # 文字色（TEXT_ONLY用）
    vertical: bool = True  # 縦書き


@dataclass
class StoryPanel:
    """コマ情報"""
    panel_index: int
    scene_description: str = ""
    characters: List[str] = field(default_factory=list)
    composition: str = "medium_shot"
    prompt: str = ""
    negative_prompt: str = ""
    dialogues: List[StoryDialogue] = field(default_factory=list)


@dataclass
class StoryPage:
    """ページ情報"""
    page_number: int
    template: str = "4panel_2x2"
    panels: List[StoryPanel] = field(default_factory=list)


@dataclass
class StorySpec:
    """ストーリー仕様書全体"""
    title: str = ""
    characters: List[StoryCharacter] = field(default_factory=list)
    pages: List[StoryPage] = field(default_factory=list)

    def get_character_by_id(self, char_id: str) -> Optional[StoryCharacter]:
        """IDでキャラクターを取得"""
        for char in self.characters:
            if char.id == char_id:
                return char
        return None

    def get_character_by_name(self, name: str) -> Optional[StoryCharacter]:
        """名前でキャラクターを取得"""
        for char in self.characters:
            if char.name == name:
                return char
        return None


class StoryImportService:
    """ストーリー仕様書のインポートサービス"""

    @staticmethod
    def load_from_file(filepath: str) -> Optional[StorySpec]:
        """JSONファイルからストーリー仕様書を読み込み"""
        try:
            path = Path(filepath)
            if not path.exists():
                print(f"ファイルが見つかりません: {filepath}")
                return None

            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return StoryImportService.parse_json(data)

        except json.JSONDecodeError as e:
            print(f"JSON解析エラー: {e}")
            return None
        except Exception as e:
            print(f"読み込みエラー: {e}")
            return None

    @staticmethod
    def parse_json(data: dict) -> StorySpec:
        """辞書データからStorySpecを生成"""
        spec = StorySpec(title=data.get("title", ""))

        # キャラクター読み込み
        for char_data in data.get("characters", []):
            char = StoryCharacter(
                id=char_data.get("id", ""),
                name=char_data.get("name", ""),
                appearance=char_data.get("appearance", ""),
                personality=char_data.get("personality", ""),
                prompt=char_data.get("prompt", "")
            )
            spec.characters.append(char)

        # ページ読み込み
        for page_data in data.get("pages", []):
            page = StoryPage(
                page_number=page_data.get("page_number", 1),
                template=page_data.get("template", "4panel_2x2")
            )

            # パネル読み込み
            for panel_data in page_data.get("panels", []):
                dialogues = []
                for dial_data in panel_data.get("dialogues", []):
                    dialogues.append(StoryDialogue(
                        speaker=dial_data.get("speaker"),
                        text=dial_data.get("text", ""),
                        bubble_type=dial_data.get("bubble_type", "SPEECH"),
                        rotation=dial_data.get("rotation", 0),
                        color=dial_data.get("color", "#000000"),
                        vertical=dial_data.get("vertical", True)
                    ))

                panel = StoryPanel(
                    panel_index=panel_data.get("panel_index", 0),
                    scene_description=panel_data.get("scene_description", ""),
                    characters=panel_data.get("characters", []),
                    composition=panel_data.get("composition", "medium_shot"),
                    prompt=panel_data.get("prompt", ""),
                    negative_prompt=panel_data.get("negative_prompt", ""),
                    dialogues=dialogues
                )
                page.panels.append(panel)

            spec.pages.append(page)

        return spec

    @staticmethod
    def validate_spec(spec: StorySpec) -> List[str]:
        """仕様書のバリデーション、エラーリストを返す"""
        errors = []

        if not spec.pages:
            errors.append("ページが定義されていません")

        for page in spec.pages:
            if not page.panels:
                errors.append(f"ページ{page.page_number}: コマが定義されていません")

            for panel in page.panels:
                if not panel.prompt:
                    errors.append(
                        f"ページ{page.page_number} コマ{panel.panel_index}: "
                        "プロンプトが空です"
                    )

                # キャラクターIDの検証
                for char_id in panel.characters:
                    if not spec.get_character_by_id(char_id):
                        errors.append(
                            f"ページ{page.page_number} コマ{panel.panel_index}: "
                            f"キャラクター '{char_id}' が未定義です"
                        )

        return errors

    @staticmethod
    def get_template_panel_count(template_name: str) -> int:
        """テンプレート名からコマ数を取得"""
        template_panels = {
            "3panel_vertical": 3,
            "4panel_vertical": 4,
            "4panel_2x2": 4,
            "5panel_mixed": 5,
            "6panel_2x3": 6,
            "6panel_3x2": 6,
        }
        return template_panels.get(template_name, 4)
