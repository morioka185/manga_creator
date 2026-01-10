import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional

from src.utils.constants import (
    DEFAULT_FONT_SIZE, DEFAULT_FONT_FAMILY,
    DEFAULT_BUBBLE_WIDTH, DEFAULT_BUBBLE_HEIGHT,
    DEFAULT_PAGE_WIDTH, DEFAULT_PAGE_HEIGHT, DEFAULT_MARGIN
)


@dataclass
class FontStyle:
    """フォントスタイルプリセット"""
    name: str
    font_family: str
    font_size: int
    bold: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'FontStyle':
        return cls(**data)


class SettingsService:
    """アプリケーション設定を管理するサービス"""

    _instance = None
    _settings = None
    _settings_file = None

    # デフォルトスタイルプリセット
    DEFAULT_STYLES = [
        {'name': '通常', 'font_family': 'Yu Gothic', 'font_size': 48, 'bold': False},
        {'name': '喜', 'font_family': 'Yu Gothic', 'font_size': 52, 'bold': True},
        {'name': '怒', 'font_family': 'Yu Gothic', 'font_size': 56, 'bold': True},
        {'name': '哀', 'font_family': 'Yu Gothic', 'font_size': 44, 'bold': False},
        {'name': '楽', 'font_family': 'Yu Gothic', 'font_size': 50, 'bold': False},
    ]

    # デフォルト設定
    DEFAULTS = {
        'font_size': DEFAULT_FONT_SIZE,
        'font_family': DEFAULT_FONT_FAMILY,
        'bubble_width': DEFAULT_BUBBLE_WIDTH,
        'bubble_height': DEFAULT_BUBBLE_HEIGHT,
        'bubble_vertical': True,
        'page_width': DEFAULT_PAGE_WIDTH,
        'page_height': DEFAULT_PAGE_HEIGHT,
        'page_margin': DEFAULT_MARGIN,
        'font_styles': None,  # 初期化時にDEFAULT_STYLESからコピー
    }

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._settings_file = self._get_settings_path()
        self._settings = self._load_settings()

    def _get_settings_path(self) -> Path:
        """設定ファイルのパスを取得"""
        app_data = os.environ.get('APPDATA', os.path.expanduser('~'))
        settings_dir = Path(app_data) / 'MangaCreator'
        settings_dir.mkdir(parents=True, exist_ok=True)
        return settings_dir / 'settings.json'

    def _load_settings(self) -> dict:
        """設定を読み込み"""
        settings = self.DEFAULTS.copy()
        settings['font_styles'] = [s.copy() for s in self.DEFAULT_STYLES]

        if self._settings_file.exists():
            try:
                with open(self._settings_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # デフォルト値とマージ
                    for key, value in loaded.items():
                        if key == 'font_styles' and value:
                            settings['font_styles'] = value
                        else:
                            settings[key] = value
            except Exception:
                pass
        return settings

    def save_settings(self):
        """設定を保存"""
        try:
            with open(self._settings_file, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"設定の保存に失敗: {e}")

    def get(self, key: str, default=None):
        """設定値を取得"""
        return self._settings.get(key, default or self.DEFAULTS.get(key))

    def set(self, key: str, value):
        """設定値を設定"""
        self._settings[key] = value
        self.save_settings()

    # 便利なプロパティ
    @property
    def font_size(self) -> int:
        return self.get('font_size')

    @font_size.setter
    def font_size(self, value: int):
        self.set('font_size', value)

    @property
    def font_family(self) -> str:
        return self.get('font_family')

    @font_family.setter
    def font_family(self, value: str):
        self.set('font_family', value)

    @property
    def bubble_width(self) -> int:
        return self.get('bubble_width')

    @bubble_width.setter
    def bubble_width(self, value: int):
        self.set('bubble_width', value)

    @property
    def bubble_height(self) -> int:
        return self.get('bubble_height')

    @bubble_height.setter
    def bubble_height(self, value: int):
        self.set('bubble_height', value)

    @property
    def bubble_vertical(self) -> bool:
        return self.get('bubble_vertical')

    @bubble_vertical.setter
    def bubble_vertical(self, value: bool):
        self.set('bubble_vertical', value)

    @property
    def page_width(self) -> int:
        return self.get('page_width')

    @page_width.setter
    def page_width(self, value: int):
        self.set('page_width', value)

    @property
    def page_height(self) -> int:
        return self.get('page_height')

    @page_height.setter
    def page_height(self, value: int):
        self.set('page_height', value)

    @property
    def page_margin(self) -> int:
        return self.get('page_margin')

    @page_margin.setter
    def page_margin(self, value: int):
        self.set('page_margin', value)

    # フォントスタイル関連メソッド
    def get_font_styles(self) -> List[FontStyle]:
        """全フォントスタイルを取得"""
        styles_data = self._settings.get('font_styles', [])
        return [FontStyle.from_dict(s) for s in styles_data]

    def get_font_style(self, name: str) -> Optional[FontStyle]:
        """名前でフォントスタイルを取得"""
        for style in self.get_font_styles():
            if style.name == name:
                return style
        return None

    def add_font_style(self, style: FontStyle):
        """フォントスタイルを追加"""
        styles = self._settings.get('font_styles', [])
        # 同じ名前があれば更新
        for i, s in enumerate(styles):
            if s['name'] == style.name:
                styles[i] = style.to_dict()
                self.save_settings()
                return
        styles.append(style.to_dict())
        self._settings['font_styles'] = styles
        self.save_settings()

    def update_font_style(self, old_name: str, style: FontStyle):
        """フォントスタイルを更新"""
        styles = self._settings.get('font_styles', [])
        for i, s in enumerate(styles):
            if s['name'] == old_name:
                styles[i] = style.to_dict()
                self._settings['font_styles'] = styles
                self.save_settings()
                return

    def delete_font_style(self, name: str):
        """フォントスタイルを削除"""
        styles = self._settings.get('font_styles', [])
        self._settings['font_styles'] = [s for s in styles if s['name'] != name]
        self.save_settings()

    def reset_font_styles(self):
        """フォントスタイルをデフォルトにリセット"""
        self._settings['font_styles'] = [s.copy() for s in self.DEFAULT_STYLES]
        self.save_settings()
