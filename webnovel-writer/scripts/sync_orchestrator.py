"""Sync orchestrator: MD → index.db.

Reads novel.config.json from --project-root, dynamically loads the project
parser (or reference_parser by default), scans configured paths, and upserts
the derived index.db.

Subcommands:
  status   : list MDs whose mtime > last_sync, plus orphan DB sources
  sync     : incremental sync (only changed MDs)
  rebuild  : drop & recreate DB from all MDs (with backup)
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Ensure sibling imports work when run as a script
sys.path.insert(0, str(Path(__file__).resolve().parent))
from db_schema import (
    get_file_mtimes, insert_change, open_db, purge_source,
    record_file_sync, upsert_entity,
)
from parser_protocol import NovelParser


def load_config(project_root: Path) -> dict:
    cfg_path = project_root / "novel.config.json"
    if not cfg_path.exists():
        sys.exit(f"[ERR] novel.config.json not found at {cfg_path}")
    return json.loads(cfg_path.read_text(encoding="utf-8"))


def load_parser(project_root: Path, parser_path: str | None) -> NovelParser:
    if not parser_path:
        from reference_parser import get_parser
        return get_parser()
    abs_path = (project_root / parser_path).resolve()
    if not abs_path.exists():
        sys.exit(f"[ERR] parser module not found: {abs_path}")
    spec = importlib.util.spec_from_file_location("project_parser", abs_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    if not hasattr(mod, "get_parser"):
        sys.exit(f"[ERR] parser module {abs_path} missing get_parser()")
    return mod.get_parser()


def collect_files(project_root: Path, scan_paths: list[str]) -> list[Path]:
    out: list[Path] = []
    seen: set[Path] = set()
    for pat in scan_paths:
        for p in project_root.glob(pat):
            if p.is_file() and p.suffix == ".md" and p not in seen:
                seen.add(p)
                out.append(p)
    return sorted(out)


def cmd_status(project_root: Path, cfg: dict) -> int:
    storage = cfg.get("storage", {})
    db_path = project_root / storage.get("db_path", ".webnovel/index.db")
    scan = storage.get("scan_paths", [])
    files = collect_files(project_root, scan)

    if not db_path.exists():
        print(f"[INFO] DB not yet created: {db_path}")
        print(f"[INFO] {len(files)} MD file(s) will be ingested on first sync.")
        return 0

    conn = open_db(db_path)
    known = get_file_mtimes(conn)
    current = {str(p): p.stat().st_mtime for p in files}

    changed = [p for p, m in current.items() if known.get(p, 0.0) < m]
    orphans = [p for p in known if p not in current]
    new = [p for p in current if p not in known]

    print(f"== sync status ({datetime.now().isoformat(timespec='seconds')}) ==")
    print(f"DB: {db_path}")
    print(f"sync_mode: {storage.get('sync_mode', 'active')}")
    print(f"\n[NEW] {len(new)} file(s) never synced:")
    for p in new: print(f"  + {Path(p).relative_to(project_root)}")
    print(f"\n[CHANGED] {len(changed) - len(new)} file(s) modified since last sync:")
    for p in changed:
        if p not in new:
            print(f"  ~ {Path(p).relative_to(project_root)}")
    print(f"\n[ORPHAN] {len(orphans)} DB source(s) no longer on disk:")
    for p in orphans: print(f"  - {p}")
    return 0


def _sync_file(conn, parser: NovelParser, md: Path) -> tuple[int, int]:
    src = str(md)
    purge_source(conn, src)
    ents = parser.parse_entities(md)
    chgs = parser.parse_changes(md)
    for e in ents:
        e.source_md = src
        upsert_entity(conn, e)
    for c in chgs:
        c.source_md = src
        insert_change(conn, c)
    record_file_sync(conn, src, md.stat().st_mtime)
    return len(ents), len(chgs)


def cmd_sync(project_root: Path, cfg: dict, full: bool = False) -> int:
    storage = cfg.get("storage", {})
    db_path = project_root / storage.get("db_path", ".webnovel/index.db")
    parser = load_parser(project_root, storage.get("parser"))
    files = collect_files(project_root, storage.get("scan_paths", []))

    conn = open_db(db_path)
    known = {} if full else get_file_mtimes(conn)
    targets = [p for p in files if known.get(str(p), 0.0) < p.stat().st_mtime]

    if not targets:
        print("[OK] nothing to sync.")
        return 0

    total_e = total_c = 0
    for md in targets:
        e, c = _sync_file(conn, parser, md)
        total_e += e; total_c += c
        print(f"  sync {md.relative_to(project_root)}  entities={e}  changes={c}")
    conn.commit()

    if full:
        # remove orphans
        current = {str(p) for p in files}
        for orphan in [p for p in get_file_mtimes(conn) if p not in current]:
            purge_source(conn, orphan)
            conn.execute("DELETE FROM sync_files WHERE path=?", (orphan,))
        conn.commit()

    print(f"\n[DONE] files={len(targets)}  entities={total_e}  changes={total_c}")
    return 0


def cmd_rebuild(project_root: Path, cfg: dict) -> int:
    db_path = project_root / cfg.get("storage", {}).get("db_path", ".webnovel/index.db")
    if db_path.exists():
        bak = db_path.with_suffix(f".db.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        shutil.copy2(db_path, bak)
        print(f"[BACKUP] {bak}")
        db_path.unlink()
    return cmd_sync(project_root, cfg, full=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", required=True)
    ap.add_argument("subcommand", choices=["status", "sync", "rebuild"])
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    cfg = load_config(root)

    if args.subcommand == "status":  return cmd_status(root, cfg)
    if args.subcommand == "sync":    return cmd_sync(root, cfg)
    if args.subcommand == "rebuild": return cmd_rebuild(root, cfg)
    return 1


if __name__ == "__main__":
    sys.exit(main())
