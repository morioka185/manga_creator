from dataclasses import dataclass, field
from typing import List

from src.utils.constants import MIN_IMAGE_SCALE


@dataclass
class PanelImageData:
    """コマ内の画像データを管理するクラス"""
    image_path: str           # 画像ファイルパス
    scale: float = MIN_IMAGE_SCALE  # 拡大率（1.0 = 最小フィット）
    offset_x: float = 0.0     # X方向オフセット（ピクセル）
    offset_y: float = 0.0     # Y方向オフセット（ピクセル）
    flip_horizontal: bool = False   # 左右反転
    generation_prompt: str = ""      # 生成時のプロンプト（再生成用）
    negative_prompt: str = ""        # ネガティブプロンプト（再生成用）
    generation_seed: int = -1        # 生成時のシード（再生成用）
    character_ids: List[str] = field(default_factory=list)  # 使用キャラクターID
    # 一括生成モードフラグ（再生成時に同じロジックを使用するため）
    batch_mode: bool = False         # 一括生成で生成されたか
    final_prompt: str = ""           # 一括生成時の最終プロンプト（キャラ外見+共通を含む）
    final_negative_prompt: str = ""  # 一括生成時の最終ネガティブプロンプト

    def to_dict(self) -> dict:
        """辞書形式に変換（保存用）"""
        return {
            'image_path': self.image_path,
            'scale': self.scale,
            'offset_x': self.offset_x,
            'offset_y': self.offset_y,
            'flip_horizontal': self.flip_horizontal,
            'generation_prompt': self.generation_prompt,
            'negative_prompt': self.negative_prompt,
            'generation_seed': self.generation_seed,
            'character_ids': self.character_ids,
            'batch_mode': self.batch_mode,
            'final_prompt': self.final_prompt,
            'final_negative_prompt': self.final_negative_prompt
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'PanelImageData':
        """辞書から復元"""
        return cls(
            image_path=data['image_path'],
            scale=data.get('scale', MIN_IMAGE_SCALE),
            offset_x=data.get('offset_x', 0.0),
            offset_y=data.get('offset_y', 0.0),
            flip_horizontal=data.get('flip_horizontal', False),
            generation_prompt=data.get('generation_prompt', ''),
            negative_prompt=data.get('negative_prompt', ''),
            generation_seed=data.get('generation_seed', -1),
            character_ids=data.get('character_ids', []),
            batch_mode=data.get('batch_mode', False),
            final_prompt=data.get('final_prompt', ''),
            final_negative_prompt=data.get('final_negative_prompt', '')
        )
