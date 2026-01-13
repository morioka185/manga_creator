from dataclasses import dataclass, field
from typing import List

from src.models.page import Page
from src.models.character import Character
from src.services.settings_service import SettingsService


@dataclass
class Project:
    name: str = "Untitled"
    pages: List[Page] = field(default_factory=list)
    characters: List[Character] = field(default_factory=list)

    def __post_init__(self):
        if not self.pages:
            settings = SettingsService.get_instance()
            self.pages.append(Page(
                width=settings.page_width,
                height=settings.page_height,
                margin=settings.page_margin
            ))
