from dataclasses import dataclass


@dataclass
class PanelImageData:
    """コマ内の画像データを管理するクラス"""
    image_path: str           # 画像ファイルパス
    scale: float = 1.0        # 拡大率（1.0 = 最小フィット）
    offset_x: float = 0.0     # X方向オフセット（ピクセル）
    offset_y: float = 0.0     # Y方向オフセット（ピクセル）

    def to_dict(self) -> dict:
        """辞書形式に変換（保存用）"""
        return {
            'image_path': self.image_path,
            'scale': self.scale,
            'offset_x': self.offset_x,
            'offset_y': self.offset_y
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'PanelImageData':
        """辞書から復元"""
        return cls(
            image_path=data['image_path'],
            scale=data.get('scale', 1.0),
            offset_x=data.get('offset_x', 0.0),
            offset_y=data.get('offset_y', 0.0)
        )
