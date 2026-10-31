from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Callable

from cryptography.fernet import Fernet
from sqlalchemy import (JSON, Boolean, Column, Float, Integer, MetaData, String, Table, Text,
                        and_, create_engine, delete, event, insert, select, update)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool

from .contracts import digest, new_id, now

metadata = MetaData()
records = Table("records", metadata,
    Column("id", String(100), primary_key=True), Column("workspace", String(100), nullable=False, index=True),
    Column("kind", String(50), nullable=False, index=True), Column("version", Integer, nullable=False, default=1),
    Column("private", Boolean, nullable=False, default=False), Column("payload", Text, nullable=False),
    Column("created", Float, nullable=False), Column("updated", Float, nullable=False))
events = Table("events", metadata,
    Column("seq", Integer, primary_key=True, autoincrement=True), Column("workspace", String(100), nullable=False, index=True),
    Column("campaign", String(100), nullable=False, index=True), Column("kind", String(80), nullable=False),
    Column("payload", JSON, nullable=False), Column("created", Float, nullable=False))
idempotency = Table("idempotency", metadata,
    Column("id", String(300), primary_key=True), Column("request_hash", String(64), nullable=False),
    Column("result", JSON, nullable=False), Column("created", Float, nullable=False))


class NotFound(LookupError):
    pass


class Conflict(RuntimeError):
    pass


class PrivateAccess(PermissionError):
    pass


class Store:
    def __init__(self, database_url: str, vault_key: str = "", runtime_dir: Path | None = None):
        if database_url.startswith("sqlite:///") and database_url != "sqlite:///:memory:":
            Path(database_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        kwargs = {"pool_pre_ping": True}
        if database_url.startswith("sqlite:"):
            kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
            if database_url == "sqlite:///:memory:":
                kwargs["poolclass"] = StaticPool
        self.engine = create_engine(database_url, **kwargs)
        if database_url.startswith("sqlite:"):
            @event.listens_for(self.engine, "connect")
            def pragmas(conn, _):
                conn.execute("PRAGMA foreign_keys=ON")
                conn.execute("PRAGMA busy_timeout=30000")
                if database_url != "sqlite:///:memory:":
                    conn.execute("PRAGMA journal_mode=WAL")
        if not vault_key:
            if runtime_dir:
                runtime_dir.mkdir(parents=True, exist_ok=True)
                keyfile = runtime_dir / "vault.key"
                try:
                    fd = os.open(keyfile, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    with os.fdopen(fd, "wb") as f:
                        f.write(Fernet.generate_key())
                except FileExistsError:
                    pass
                vault_key = keyfile.read_text().strip()
            else:
                vault_key = Fernet.generate_key().decode()
        self.cipher = Fernet(vault_key.encode())
        metadata.create_all(self.engine)

    @contextmanager
    def transaction(self):
        with self.engine.connect() as conn:
            if self.engine.dialect.name == "sqlite":
                conn.exec_driver_sql("BEGIN IMMEDIATE")
            else:
                conn.begin()
            try:
                yield conn
                conn.commit()
            except BaseException:
                conn.rollback()
                raise

    def _encode(self, payload: dict, private: bool):
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
        return self.cipher.encrypt(raw).decode() if private else raw.decode()

    def _decode(self, row, private_access=False):
        if row["private"] and not private_access:
            raise PrivateAccess("This record belongs to the independent evaluator.")
        raw = row["payload"]
        if row["private"]:
            raw = self.cipher.decrypt(raw.encode()).decode()
        return json.loads(raw)

    def create(self, kind: str, workspace: str, payload: dict, *, id: str | None = None, private=False):
        identifier = id or new_id(kind)
        with self.transaction() as conn:
            conn.execute(insert(records).values(id=identifier, workspace=workspace, kind=kind, version=1,
                         private=private, payload=self._encode(payload, private), created=now(), updated=now()))
        return identifier

    def get(self, identifier: str, workspace: str, *, private_access=False) -> dict:
        with self.engine.connect() as conn:
            row = conn.execute(select(records).where(records.c.id == identifier, records.c.workspace == workspace)).mappings().first()
        if row is None:
            raise NotFound(identifier)
        return self._decode(row, private_access) | {"id": row["id"], "_version": row["version"], "_created": row["created"]}

    def list(self, kind: str, workspace: str, *, limit=100, offset=0, private_access=False) -> list[dict]:
        with self.engine.connect() as conn:
            rows = conn.execute(select(records).where(records.c.kind == kind, records.c.workspace == workspace)
                    .order_by(records.c.created.desc()).limit(min(limit, 1000)).offset(offset)).mappings().all()
        return [self._decode(row, private_access) | {"id": row["id"], "_version": row["version"], "_created": row["created"]} for row in rows]

    def mutate(self, identifier: str, workspace: str, fn: Callable[[dict], dict], *, private_access=False) -> dict:
        with self.transaction() as conn:
            stmt = select(records).where(records.c.id == identifier, records.c.workspace == workspace)
            if self.engine.dialect.name != "sqlite":
                stmt = stmt.with_for_update()
            row = conn.execute(stmt).mappings().first()
            if row is None:
                raise NotFound(identifier)
            old = self._decode(row, private_access)
            changed = fn(old)
            changed.pop("_version", None); changed.pop("_created", None); changed.pop("id", None)
            conn.execute(update(records).where(records.c.id == identifier, records.c.version == row["version"])
                         .values(payload=self._encode(changed, row["private"]), version=row["version"] + 1, updated=now()))
            return changed | {"id": identifier, "_version": row["version"] + 1, "_created": row["created"]}

    def event(self, workspace: str, campaign: str, kind: str, payload: dict):
        with self.transaction() as conn:
            result = conn.execute(insert(events).values(workspace=workspace, campaign=campaign, kind=kind,
                                 payload=payload, created=now()))
            return result.inserted_primary_key[0]

    def event_history(self, workspace: str, campaign: str | None = None, after=0, limit=100):
        stmt = select(events).where(events.c.workspace == workspace, events.c.seq > after)
        if campaign:
            stmt = stmt.where(events.c.campaign == campaign)
        with self.engine.connect() as conn:
            return [dict(row) for row in conn.execute(stmt.order_by(events.c.seq).limit(min(limit, 1000))).mappings().all()]

    def once(self, workspace: str, operation: str, key: str, request: dict, create: Callable[[], dict]) -> dict:
        if not key or len(key) > 100:
            raise ValueError("An Idempotency-Key with 1–100 characters is required.")
        identifier = workspace + ":" + operation + ":" + key
        request_hash = digest(request)
        try:
            with self.transaction() as conn:
                conn.execute(insert(idempotency).values(id=identifier, request_hash=request_hash,
                             result={"_pending": True}, created=now()))
        except IntegrityError:
            with self.engine.connect() as conn:
                row = conn.execute(select(idempotency).where(idempotency.c.id == identifier)).mappings().one()
            if row["request_hash"] != request_hash:
                raise Conflict("The idempotency key belongs to a different request.")
            if row["result"].get("_pending"):
                raise Conflict("This operation is already in progress; retry the same key.")
            return row["result"]
        try:
            result = create()
        except BaseException:
            with self.transaction() as conn:
                conn.execute(delete(idempotency).where(idempotency.c.id == identifier))
            raise
        with self.transaction() as conn:
            conn.execute(update(idempotency).where(idempotency.c.id == identifier).values(result=result))
        return result

    def close(self):
        self.engine.dispose()

