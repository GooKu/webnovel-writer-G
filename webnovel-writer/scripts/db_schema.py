"""SQLite schema & upsert helpers for the derived index.db (MD-first model)."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from parser_protocol import ChangeRecord, EntityRecord, SHORT_DESC_LIMIT


SCHEMA = """
CREATE TABLE IF NOT EXISTS entities (
    id              TEXT PRIMARY KEY,
    type            TEXT NOT NULL,
    canonical_name  TEXT NOT NULL,
    short_desc      TEXT,
    tier            TEXT,
    source_md       TEXT,
    source_line     INTEGER,
    extra_json      TEXT,
    updated_at      TEXT
);
CREATE TABLE IF NOT EXISTS aliases (
    alias       TEXT NOT NULL,
    entity_id   TEXT NOT NULL,
    PRIMARY KEY (alias, entity_id)
);
CREATE TABLE IF NOT EXISTS changes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    chapter      INTEGER NOT NULL,
    summary      TEXT NOT NULL,
    entity_id    TEXT,
    category     TEXT,
    source_md    TEXT NOT NULL,
    source_line  INTEGER,
    extra_json   TEXT,
    created_at   TEXT,
    UNIQUE(source_md, source_line, summary)
);
CREATE TABLE IF NOT EXISTS sync_files (
    path         TEXT PRIMARY KEY,
    last_synced  TEXT NOT NULL,
    mtime        REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS sync_meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
CREATE INDEX IF NOT EXISTS idx_changes_chapter ON changes(chapter);
CREATE INDEX IF NOT EXISTS idx_changes_entity ON changes(entity_id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _truncate(text: str, limit: int = SHORT_DESC_LIMIT) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def open_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    return conn


def upsert_entity(conn: sqlite3.Connection, e: EntityRecord) -> None:
    conn.execute(
        """INSERT INTO entities(id,type,canonical_name,short_desc,tier,source_md,source_line,extra_json,updated_at)
           VALUES(?,?,?,?,?,?,?,?,?)
           ON CONFLICT(id) DO UPDATE SET
             type=excluded.type, canonical_name=excluded.canonical_name,
             short_desc=excluded.short_desc, tier=excluded.tier,
             source_md=excluded.source_md, source_line=excluded.source_line,
             extra_json=excluded.extra_json, updated_at=excluded.updated_at""",
        (e.id, e.type, e.canonical_name, _truncate(e.short_desc), e.tier,
         e.source_md, e.source_line, json.dumps(e.extra, ensure_ascii=False), _now()),
    )
    conn.execute("DELETE FROM aliases WHERE entity_id=?", (e.id,))
    conn.executemany(
        "INSERT OR IGNORE INTO aliases(alias,entity_id) VALUES(?,?)",
        [(a, e.id) for a in e.aliases],
    )


def insert_change(conn: sqlite3.Connection, c: ChangeRecord) -> None:
    conn.execute(
        """INSERT OR IGNORE INTO changes(chapter,summary,entity_id,category,source_md,source_line,extra_json,created_at)
           VALUES(?,?,?,?,?,?,?,?)""",
        (c.chapter, _truncate(c.summary), c.entity_id, c.category,
         c.source_md, c.source_line, json.dumps(c.extra, ensure_ascii=False), _now()),
    )


def purge_source(conn: sqlite3.Connection, source_md: str) -> None:
    """Remove all rows derived from a given MD path (used before re-sync)."""
    conn.execute("DELETE FROM changes WHERE source_md=?", (source_md,))
    rows = conn.execute("SELECT id FROM entities WHERE source_md=?", (source_md,)).fetchall()
    for (eid,) in rows:
        conn.execute("DELETE FROM aliases WHERE entity_id=?", (eid,))
    conn.execute("DELETE FROM entities WHERE source_md=?", (source_md,))


def record_file_sync(conn: sqlite3.Connection, path: str, mtime: float) -> None:
    conn.execute(
        """INSERT INTO sync_files(path,last_synced,mtime) VALUES(?,?,?)
           ON CONFLICT(path) DO UPDATE SET last_synced=excluded.last_synced, mtime=excluded.mtime""",
        (path, _now(), mtime),
    )


def get_file_mtimes(conn: sqlite3.Connection) -> dict[str, float]:
    return {row[0]: row[1] for row in conn.execute("SELECT path, mtime FROM sync_files")}
