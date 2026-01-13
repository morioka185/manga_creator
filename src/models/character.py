"""キャラクターモデル（AI画像生成用）"""
from dataclasses import dataclass, asdict, field
from typing import Optional
import uuid


@dataclass
class Character:
    """キャラクター参照画像データ"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    reference_image_path: str = ""
    default_prompt: str = ""
    ip_adapter_weight: float = 0.8

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'Character':
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', ''),
            reference_image_path=data.get('reference_image_path', ''),
            default_prompt=data.get('default_prompt', ''),
            ip_adapter_weight=data.get('ip_adapter_weight', 0.8)
        )
