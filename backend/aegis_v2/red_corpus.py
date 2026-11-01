"""Disk-backed, provenance-aware corpus; public resources are not target facts."""
from __future__ import annotations

import hashlib
from contextlib import contextmanager
import json
from pathlib import Path
import re
import sqlite3


class AttackCorpus:
    def __init__(self, path):
        self.path = Path(path).resolve()

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True, timeout=20)
        db.row_factory = sqlite3.Row
        try:
            yield db
        finally:
            db.close()

    def summary(self):
        with self.connect() as db:
            return json.loads(db.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()[0])

    @staticmethod
    def _where(query, framework, kind):
        parameters, clauses = [], []
        if query.strip():
            # Quote tokens before FTS parsing; SQL parameters bind the expression.
            words = re.findall(r"[^\W_]+", query, flags=re.UNICODE)
            expression = " AND ".join('"' + word.replace('"', '""') + '"' for word in words)
            if not expression:
                return " WHERE 0", []
            clauses.append("r.rowid IN (SELECT rowid FROM search WHERE search MATCH ?)")
            parameters.append(expression)
        if framework:
            clauses.append("EXISTS (SELECT 1 FROM provenance p WHERE p.resource_id=r.id AND p.source=?)")
            parameters.append(framework)
        if kind:
            clauses.append("r.kind=?")
            parameters.append(kind)
        return (" WHERE " + " AND ".join(clauses) if clauses else ""), parameters

    def search(self, query="", framework=None, kind=None, offset=0, limit=10, *, full=False):
        where, params = self._where(query, framework, kind)
        with self.connect() as db:
            total = db.execute("SELECT count(*) FROM resources r" + where, params).fetchone()[0]
            if full:
                columns = "r.record"
            else:
                columns = "r.id,r.framework,r.version,r.license,r.path,r.title,r.sha256,r.kind"
            rows = db.execute("SELECT " + columns + " FROM resources r" + where +
                              " ORDER BY r.rowid LIMIT ? OFFSET ?", params + [limit, offset]).fetchall()
            return {"total": total, "results": [json.loads(row[0]) if full else dict(row) for row in rows],
                    "next_offset": offset + len(rows) if offset + len(rows) < total else None}

    def get(self, identifier):
        with self.connect() as db:
            row = db.execute("SELECT record FROM resources WHERE id=?", (identifier,)).fetchone()
            if row is None:
                row = db.execute("SELECT r.record FROM resources r JOIN provenance p ON p.resource_id=r.id WHERE p.alias_id=? LIMIT 1", (identifier,)).fetchone()
            if row is None:
                return None
            resource = json.loads(row[0])
            resource["provenance"] = [dict(p) for p in db.execute(
                "SELECT source,path,source_row,alias_id FROM provenance WHERE resource_id=?", (resource["id"],))]
            return resource

    def bundle(self, *, query="", framework=None, kind=None, key="", count=3):
        total = self.search(query, framework, kind, limit=1)["total"]
        if not total:
            return []
        # Sample independent positions rather than an adjacent block of mined
        # records, which can cluster around similar mechanisms.
        selected, positions = [], set()
        for index in range(min(count, total)):
            offset = int(hashlib.sha256((key + ":" + str(index)).encode()).hexdigest(), 16) % total
            while offset in positions:
                offset = (offset + 1) % total
            positions.add(offset)
            selected.extend(self.search(query, framework, kind, offset, 1, full=True)["results"])
        return selected


def initialize_corpus(path):
    db = sqlite3.connect(path)
    db.execute("PRAGMA journal_mode=OFF")
    db.execute("PRAGMA synchronous=OFF")
    db.executescript("""
        CREATE TABLE resources(id TEXT PRIMARY KEY, sha256 TEXT UNIQUE NOT NULL,
            framework TEXT NOT NULL, version TEXT, license TEXT, path TEXT, title TEXT,
            kind TEXT NOT NULL, record TEXT NOT NULL);
        CREATE INDEX source_kind ON resources(framework,kind);
        CREATE TABLE provenance(resource_id TEXT, source TEXT, path TEXT, source_row TEXT, alias_id TEXT,
            UNIQUE(resource_id,source,path,source_row));
        CREATE INDEX provenance_source ON provenance(source,resource_id);
        CREATE INDEX provenance_alias ON provenance(alias_id);
        CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT);
        CREATE VIRTUAL TABLE search USING fts5(title,text,description,content='');
    """)
    return db


def add_resource(db, row):
    text = row.get("text")
    if not isinstance(text, str) or not text.strip():
        return False
    # Upstream Python literals can contain escaped surrogate pairs. Convert
    # pairs to scalar Unicode and replace lone invalid surrogates consistently.
    text = text.encode("utf-16", "surrogatepass").decode("utf-16", "replace")
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    row = dict(row, text=text, sha256=sha)
    row.setdefault("id", row["framework"] + ":" + sha[:24])
    row.setdefault("kind", "seed")
    row.setdefault("description", "")
    row.setdefault("license", "not-specified")
    row.setdefault("version", "snapshot")
    row.setdefault("title", row["framework"])
    row.setdefault("path", "")
    record = json.dumps(row, ensure_ascii=True)
    result = db.execute("INSERT OR IGNORE INTO resources VALUES(?,?,?,?,?,?,?,?,?)", (
        row["id"],sha,row["framework"],row["version"],row["license"],row["path"],row["title"],row["kind"],record))
    inserted = result.rowcount == 1
    if inserted:
        db.execute("INSERT INTO search(rowid,title,text,description) VALUES(?,?,?,?)", (
            result.lastrowid,row["title"],text,row["description"]))
        identifier = row["id"]
    else:
        identifier = db.execute("SELECT id FROM resources WHERE sha256=?", (sha,)).fetchone()[0]
    db.execute("INSERT OR IGNORE INTO provenance VALUES(?,?,?,?,?)", (
        identifier,row["framework"],row["path"],str(row.get("location", "")),row["id"]))
    return inserted
