#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
novel.config.json resolver

讀取使用端專案根的 novel.config.json，提供：
- Python API：load_config / resolve_path / resolve_arc_path
- CLI：python config_resolver.py <project_root> get <dotted.key> [--default X]

若 config 不存在或欄位缺失，回退到呼叫者提供的 default 值。
使用端框架內部狀態（.webnovel/state.json 等）不由本模組管理。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

CONFIG_FILENAME = "novel.config.json"


def find_config(project_root: Path) -> Optional[Path]:
    candidate = project_root / CONFIG_FILENAME
    return candidate if candidate.is_file() else None


def load_config(project_root: Path) -> dict:
    path = find_config(project_root)
    if path is None:
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _get_by_dotted(data: Any, key: str) -> Any:
    cur: Any = data
    for part in key.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def resolve_path(
    project_root: Path,
    dotted_key: str,
    default: Optional[str] = None,
) -> Optional[str]:
    """
    依點分路徑取 config 欄位。

    範例：
        resolve_path(root, "settings.worldview", "设定集/世界观.md")
        resolve_path(root, "arcs.正篇卷一.chapters_dir")
    """
    cfg = load_config(project_root)
    value = _get_by_dotted(cfg, dotted_key)
    if isinstance(value, str) and value:
        return value
    return default


def resolve_arc_path(
    project_root: Path,
    arc_key: Optional[str],
    sub_key: str,
    default: Optional[str] = None,
) -> Optional[str]:
    """
    解析 arcs[arc_key].<sub_key>。若 arc_key 為 None，使用 project.current_arc。
    """
    cfg = load_config(project_root)
    if arc_key is None:
        arc_key = _get_by_dotted(cfg, "project.current_arc")
        if not isinstance(arc_key, str) or not arc_key:
            return default
    value = _get_by_dotted(cfg, f"arcs.{arc_key}.{sub_key}")
    if isinstance(value, str) and value:
        return value
    return default


def format_chapter_filename(pattern: str, num: int, title: str = "") -> str:
    """
    依 chapter_pattern 生成檔名。僅支援 {NNN}（3 位補零）與 {title}。
    """
    return pattern.replace("{NNN}", f"{num:03d}").replace("{title}", title)


def _cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="novel.config.json resolver")
    parser.add_argument("project_root", help="使用端專案根目錄絕對路徑")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_get = sub.add_parser("get", help="取得 dotted key 對應值")
    p_get.add_argument("key", help="dotted key，例：settings.worldview")
    p_get.add_argument("--default", default="", help="找不到時回退值")

    p_has = sub.add_parser("has-config", help="檢查 novel.config.json 是否存在")

    p_dump = sub.add_parser("dump", help="輸出完整 config JSON")

    args = parser.parse_args(argv)
    root = Path(args.project_root).expanduser().resolve()

    if args.cmd == "has-config":
        print("1" if find_config(root) else "0")
        return 0

    if args.cmd == "dump":
        cfg = load_config(root)
        print(json.dumps(cfg, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "get":
        value = resolve_path(root, args.key, args.default or None)
        print(value if value is not None else "")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
