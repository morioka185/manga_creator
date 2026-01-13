"""画像パス管理サービス

プロジェクトと同じ階層に画像フォルダを作成し、
ページごと・キャラクターごとにサブフォルダを管理する。
"""
import os
import re
from pathlib import Path
from typing import Optional


class ImagePathService:
    """画像パス管理サービス（シングルトン）"""

    _instance: Optional['ImagePathService'] = None
    _project_path: Optional[Path] = None

    @classmethod
    def get_instance(cls) -> 'ImagePathService':
        """シングルトンインスタンス取得"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_project_path(self, project_path: Optional[str]):
        """プロジェクトパスを設定

        Args:
            project_path: プロジェクトファイル（.manga）のパス
        """
        if project_path:
            self._project_path = Path(project_path)
        else:
            self._project_path = None

    def get_project_path(self) -> Optional[Path]:
        """現在のプロジェクトパスを取得"""
        return self._project_path

    def is_project_saved(self) -> bool:
        """プロジェクトが保存されているかどうか"""
        return self._project_path is not None and self._project_path.exists()

    def get_images_base_folder(self) -> Optional[Path]:
        """画像ベースフォルダを取得

        プロジェクトフォルダと同じ階層に {プロジェクト名}_images フォルダを作成

        Returns:
            画像ベースフォルダのパス。プロジェクト未保存の場合はNone
        """
        if not self._project_path:
            return None

        # プロジェクトファイルのディレクトリとベース名を取得
        project_dir = self._project_path.parent
        project_name = self._project_path.stem  # 拡張子を除いたファイル名

        # 画像フォルダパス
        images_folder = project_dir / f"{project_name}_images"
        return images_folder

    def get_page_images_folder(self, page_number: int) -> Optional[Path]:
        """ページ画像フォルダを取得

        Args:
            page_number: ページ番号（1始まり）

        Returns:
            ページ画像フォルダのパス。プロジェクト未保存の場合はNone
        """
        base = self.get_images_base_folder()
        if not base:
            return None

        return base / "pages" / f"page_{page_number}"

    def get_character_images_folder(self, character_name: str) -> Optional[Path]:
        """キャラクター画像フォルダを取得

        Args:
            character_name: キャラクター名

        Returns:
            キャラクター画像フォルダのパス。プロジェクト未保存の場合はNone
        """
        base = self.get_images_base_folder()
        if not base:
            return None

        # ファイル名に使えない文字を置換
        safe_name = self._sanitize_filename(character_name)
        return base / "characters" / safe_name

    def get_misc_images_folder(self) -> Optional[Path]:
        """その他の画像フォルダを取得（ベースフォルダ直下）

        Returns:
            その他画像フォルダのパス。プロジェクト未保存の場合はNone
        """
        return self.get_images_base_folder()

    def ensure_page_folder(self, page_number: int) -> Optional[Path]:
        """ページフォルダを作成して返す

        Args:
            page_number: ページ番号（1始まり）

        Returns:
            作成されたフォルダのパス。プロジェクト未保存の場合はNone
        """
        folder = self.get_page_images_folder(page_number)
        if folder:
            folder.mkdir(parents=True, exist_ok=True)
        return folder

    def ensure_character_folder(self, character_name: str) -> Optional[Path]:
        """キャラクターフォルダを作成して返す

        Args:
            character_name: キャラクター名

        Returns:
            作成されたフォルダのパス。プロジェクト未保存の場合はNone
        """
        folder = self.get_character_images_folder(character_name)
        if folder:
            folder.mkdir(parents=True, exist_ok=True)
        return folder

    def ensure_misc_folder(self) -> Optional[Path]:
        """その他フォルダを作成して返す

        Returns:
            作成されたフォルダのパス。プロジェクト未保存の場合はNone
        """
        folder = self.get_misc_images_folder()
        if folder:
            folder.mkdir(parents=True, exist_ok=True)
        return folder

    def get_default_browse_folder(self) -> str:
        """画像選択ダイアログのデフォルトフォルダを取得

        Returns:
            デフォルトフォルダのパス。プロジェクト未保存の場合は空文字列
        """
        base = self.get_images_base_folder()
        if base and base.exists():
            return str(base)
        return ""

    def get_page_browse_folder(self, page_number: int) -> str:
        """ページ画像選択ダイアログのデフォルトフォルダを取得

        Args:
            page_number: ページ番号（1始まり）

        Returns:
            デフォルトフォルダのパス。存在しない場合はベースフォルダまたは空文字列
        """
        folder = self.get_page_images_folder(page_number)
        if folder and folder.exists():
            return str(folder)
        return self.get_default_browse_folder()

    def get_character_browse_folder(self, character_name: str) -> str:
        """キャラクター画像選択ダイアログのデフォルトフォルダを取得

        Args:
            character_name: キャラクター名

        Returns:
            デフォルトフォルダのパス。存在しない場合はベースフォルダまたは空文字列
        """
        folder = self.get_character_images_folder(character_name)
        if folder and folder.exists():
            return str(folder)
        return self.get_default_browse_folder()

    def _sanitize_filename(self, name: str) -> str:
        """ファイル名に使えない文字を置換

        Args:
            name: 元の名前

        Returns:
            サニタイズされた名前
        """
        # Windowsで使用不可の文字を置換
        invalid_chars = r'[<>:"/\\|?*]'
        sanitized = re.sub(invalid_chars, '_', name)
        # 先頭・末尾の空白とドットを除去
        sanitized = sanitized.strip(' .')
        # 空になった場合はデフォルト名
        if not sanitized:
            sanitized = "unnamed"
        return sanitized
