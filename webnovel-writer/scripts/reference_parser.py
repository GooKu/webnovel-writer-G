"""Reference parser: parses ```change / ```entity fenced blocks.

Default parser used when `novel.config.json -> storage.parser` is unset.
Block format (YAML-like key:value, one per line):

    ```change
    章節: 42
    變動: 林凡 境界突破 練氣三層 → 練氣四層
    實體: linfan        # optional
    類型: realm_change  # optional
    ```

    ```entity
    id: linfan
    type: 角色
    canonical_name: 林凡
    aliases: [林師弟, 廢柴]
    tier: 核心
    short_desc: 主角，青雲宗外門弟子
    ```
"""
from __future__ import annotations

import re
from pathlib import Path

from parser_protocol import ChangeRecord, EntityRecord


BLOCK_RE = re.compile(r"^```(change|entity)\s*$(.*?)^```\s*$", re.MULTILINE | re.DOTALL)


def _parse_kv(body: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        k, _, v = line.partition(":")
        out[k.strip()] = v.strip().lstrip("#").strip()
    return out


def _parse_list(value: str) -> list[str]:
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    return [x.strip() for x in value.split(",") if x.strip()]


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


class ReferenceParser:
    def parse_entities(self, md_path: Path) -> list[EntityRecord]:
        text = md_path.read_text(encoding="utf-8")
        out: list[EntityRecord] = []
        for m in BLOCK_RE.finditer(text):
            if m.group(1) != "entity":
                continue
            kv = _parse_kv(m.group(2))
            if not kv.get("id") or not kv.get("canonical_name"):
                continue
            out.append(EntityRecord(
                id=kv["id"],
                type=kv.get("type", "未分类"),
                canonical_name=kv["canonical_name"],
                short_desc=kv.get("short_desc", ""),
                tier=kv.get("tier", "装饰"),
                aliases=_parse_list(kv.get("aliases", "")),
                source_md=str(md_path),
                source_line=_line_of(text, m.start()),
            ))
        return out

    def parse_changes(self, md_path: Path) -> list[ChangeRecord]:
        text = md_path.read_text(encoding="utf-8")
        out: list[ChangeRecord] = []
        for m in BLOCK_RE.finditer(text):
            if m.group(1) != "change":
                continue
            kv = _parse_kv(m.group(2))
            chap_raw = kv.get("章節") or kv.get("chapter")
            summary = kv.get("變動") or kv.get("summary")
            if not chap_raw or not summary:
                continue
            try:
                chap = int(re.search(r"\d+", chap_raw).group())
            except (AttributeError, ValueError):
                continue
            out.append(ChangeRecord(
                chapter=chap,
                summary=summary,
                entity_id=kv.get("實體") or kv.get("entity"),
                category=kv.get("類型") or kv.get("category"),
                source_md=str(md_path),
                source_line=_line_of(text, m.start()),
            ))
        return out


def get_parser() -> ReferenceParser:
    return ReferenceParser()
