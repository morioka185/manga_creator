"""キャラクター管理サービス（プロジェクトベース）"""
from typing import List, Optional, TYPE_CHECKING

from src.models.character import Character

if TYPE_CHECKING:
    from src.models.project import Project


class CharacterService:
    """キャラクター管理サービス（シングルトン、プロジェクト連携）"""

    _instance: Optional['CharacterService'] = None
    _project: Optional['Project'] = None

    @classmethod
    def get_instance(cls) -> 'CharacterService':
        """シングルトンインスタンス取得"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._project = None

    def set_project(self, project: 'Project'):
        """現在のプロジェクトを設定"""
        self._project = project

    def get_project(self) -> Optional['Project']:
        """現在のプロジェクトを取得"""
        return self._project

    def get_all(self) -> List[Character]:
        """全キャラクター取得"""
        if self._project is None:
            return []
        return self._project.characters.copy()

    def get_by_id(self, character_id: str) -> Optional[Character]:
        """IDでキャラクター取得"""
        if self._project is None:
            return None
        for char in self._project.characters:
            if char.id == character_id:
                return char
        return None

    def get_by_name(self, name: str) -> Optional[Character]:
        """名前でキャラクター取得"""
        if self._project is None:
            return None
        for char in self._project.characters:
            if char.name == name:
                return char
        return None

    def add(self, character: Character):
        """キャラクター追加"""
        if self._project is None:
            return

        # 同名チェック
        existing = self.get_by_name(character.name)
        if existing:
            # 既存を更新
            self.update(existing.id, character)
            return

        self._project.characters.append(character)

    def update(self, character_id: str, character: Character):
        """キャラクター更新"""
        if self._project is None:
            return

        for i, char in enumerate(self._project.characters):
            if char.id == character_id:
                # IDを維持
                character.id = character_id
                self._project.characters[i] = character
                return

    def delete(self, character_id: str):
        """キャラクター削除"""
        if self._project is None:
            return

        self._project.characters = [
            c for c in self._project.characters if c.id != character_id
        ]
