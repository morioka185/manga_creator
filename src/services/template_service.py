from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from enum import Enum

from src.models.page import Page
from src.models.divider_line import DividerLine


class PanelOrientation(Enum):
    """コマの向き"""
    PORTRAIT = "portrait"    # 縦長
    LANDSCAPE = "landscape"  # 横長
    SQUARE = "square"        # 正方形


@dataclass
class LineTemplate:
    """分割線のテンプレート（比率で指定）"""
    x1_ratio: float
    y1_ratio: float
    x2_ratio: float
    y2_ratio: float


@dataclass
class Template:
    name: str
    lines: List[LineTemplate]


class TemplateService:
    @staticmethod
    def get_templates() -> List[Template]:
        return [
            Template("4コマ（縦）", [
                LineTemplate(0, 0.25, 1, 0.25),
                LineTemplate(0, 0.50, 1, 0.50),
                LineTemplate(0, 0.75, 1, 0.75),
            ]),
            Template("4コマ（2x2）", [
                LineTemplate(0.5, 0, 0.5, 1),
                LineTemplate(0, 0.5, 1, 0.5),
            ]),
            Template("5コマ（大+4）", [
                # 上に大きいコマ(40%) + 下に2x2(60%)
                LineTemplate(0, 0.4, 1, 0.4),      # 上下分割
                LineTemplate(0.5, 0.4, 0.5, 1),   # 下部の左右分割
                LineTemplate(0.25, 0.7, 0.75, 0.7),  # 下部の上下分割（中央の短い線）
            ]),
            Template("6コマ（2x3）", [
                LineTemplate(0.5, 0, 0.5, 1),
                LineTemplate(0, 0.333, 1, 0.333),
                LineTemplate(0, 0.666, 1, 0.666),
            ]),
            Template("見開き（大+2小）", [
                LineTemplate(0, 0.6, 1, 0.6),
                LineTemplate(0.5, 0.6, 0.5, 1),
            ]),
            Template("上大+下2分割", [
                LineTemplate(0, 0.5, 1, 0.5),
                LineTemplate(0.5, 0.5, 0.5, 1),
            ]),
            Template("3段", [
                LineTemplate(0, 0.333, 1, 0.333),
                LineTemplate(0, 0.666, 1, 0.666),
            ]),
            Template("2段", [
                LineTemplate(0, 0.5, 1, 0.5),
            ]),
        ]

    # ストーリー仕様書のテンプレート名とTemplateServiceのテンプレート名の対応
    TEMPLATE_NAME_MAP: Dict[str, str] = {
        "3panel_vertical": "3段",
        "4panel_vertical": "4コマ（縦）",
        "4panel_2x2": "4コマ（2x2）",
        "5panel_mixed": "5コマ（大+4）",
        "6panel_2x3": "6コマ（2x3）",
        "spread_large_2small": "見開き（大+2小）",
        "top_large_bottom_2": "上大+下2分割",
        "3段": "3段",
        "2段": "2段",
    }

    @staticmethod
    def get_template_by_name(name: str) -> Optional[Template]:
        """テンプレート名からTemplateを取得"""
        # ストーリー仕様書形式の名前を変換
        internal_name = TemplateService.TEMPLATE_NAME_MAP.get(name, name)

        for template in TemplateService.get_templates():
            if template.name == internal_name:
                return template
        return None

    @staticmethod
    def get_panel_orientations(
        template_name: str,
        page_width: float = 1000,
        page_height: float = 1400
    ) -> List[PanelOrientation]:
        """
        テンプレート内の各コマの向き（縦長/横長/正方形）を取得

        Args:
            template_name: テンプレート名（ストーリー仕様書形式または日本語形式）
            page_width: ページ幅（計算用）
            page_height: ページ高さ（計算用）

        Returns:
            各コマのPanelOrientationのリスト
        """
        template = TemplateService.get_template_by_name(template_name)
        if not template:
            # テンプレートが見つからない場合はデフォルト（縦長）を返す
            return [PanelOrientation.PORTRAIT]

        # 分割線からコマ領域を計算
        from src.services.panel_calculator import PanelCalculator

        dividers = []
        for lt in template.lines:
            dividers.append(DividerLine(
                x1=page_width * lt.x1_ratio,
                y1=page_height * lt.y1_ratio,
                x2=page_width * lt.x2_ratio,
                y2=page_height * lt.y2_ratio
            ))

        panels = PanelCalculator.calculate_panels(page_width, page_height, dividers)

        # 各コマの向きを判定
        orientations = []
        for panel in panels:
            rect = panel.boundingRect()
            width = rect.width()
            height = rect.height()

            # アスペクト比で判定（1.15以上の差があれば縦長/横長）
            aspect_ratio = width / height if height > 0 else 1.0

            if aspect_ratio > 1.15:
                orientations.append(PanelOrientation.LANDSCAPE)
            elif aspect_ratio < 0.87:  # 1/1.15 ≈ 0.87
                orientations.append(PanelOrientation.PORTRAIT)
            else:
                orientations.append(PanelOrientation.SQUARE)

        return orientations

    @staticmethod
    def get_recommended_size(
        orientation: PanelOrientation,
        portrait_size: Tuple[int, int] = (832, 1216),
        landscape_size: Tuple[int, int] = (1216, 832)
    ) -> Tuple[int, int]:
        """
        コマの向きに応じた推奨生成サイズを取得

        Args:
            orientation: コマの向き
            portrait_size: 縦長用サイズ (width, height)
            landscape_size: 横長用サイズ (width, height)

        Returns:
            推奨サイズ (width, height)
        """
        if orientation == PanelOrientation.LANDSCAPE:
            return landscape_size
        elif orientation == PanelOrientation.PORTRAIT:
            return portrait_size
        else:
            # 正方形の場合は大きい方のサイズで正方形にする
            size = max(portrait_size[0], portrait_size[1])
            # 64の倍数に丸める
            size = ((size + 31) // 64) * 64
            return (size, size)

    @staticmethod
    def apply_template(page: Page, template: Template):
        """テンプレートをページに適用"""
        page.divider_lines.clear()
        page.panel_images.clear()

        for lt in template.lines:
            divider = DividerLine(
                x1=page.width * lt.x1_ratio,
                y1=page.height * lt.y1_ratio,
                x2=page.width * lt.x2_ratio,
                y2=page.height * lt.y2_ratio
            )
            page.divider_lines.append(divider)
