from dataclasses import dataclass, field
from typing import List

from src.models.page import Page


@dataclass
class Project:
    name: str = "Untitled"
    pages: List[Page] = field(default_factory=list)

    def __post_init__(self):
        if not self.pages:
            self.pages.append(Page())
