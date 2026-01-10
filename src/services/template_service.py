from dataclasses import dataclass
from typing import List

from src.models.page import Page
from src.models.divider_line import DividerLine


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
            Template("6コマ（2x3）", [
                LineTemplate(0.5, 0, 0.5, 1),
                LineTemplate(0, 0.333, 1, 0.333),
                LineTemplate(0, 0.666, 1, 0.666),
            ]),
            Template("6コマ（3x2）", [
                LineTemplate(0, 0.5, 1, 0.5),
                LineTemplate(0.333, 0, 0.333, 1),
                LineTemplate(0.666, 0, 0.666, 1),
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
