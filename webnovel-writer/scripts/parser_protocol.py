"""Parser protocol & data records for MD-first sync.

Project parsers must implement `NovelParser` and expose a module-level
`get_parser()` factory. Framework imports the module path declared in
`novel.config.json -> storage.parser`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


SHORT_DESC_LIMIT = 30


@dataclass
class EntityRecord:
    id: str
    type: str
    canonical_name: str
    short_desc: str = ""
    tier: str = "装饰"
    aliases: list[str] = field(default_factory=list)
    source_md: str = ""
    source_line: int = 0
    extra: dict = field(default_factory=dict)


@dataclass
class ChangeRecord:
    chapter: int                    # required
    summary: str                    # required, ≤30 chars (truncated by writer)
    entity_id: str | None = None
    category: str | None = None
    source_md: str = ""
    source_line: int = 0
    extra: dict = field(default_factory=dict)


class NovelParser(Protocol):
    def parse_entities(self, md_path: Path) -> list[EntityRecord]: ...
    def parse_changes(self, md_path: Path) -> list[ChangeRecord]: ...
