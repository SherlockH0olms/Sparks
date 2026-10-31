"""Olay veriyolu: SSE ile UI'a akan tek olay akışı.

Her olay; kampanya, kaynak ve zaman damgasıyla etiketlenir. UI bu akıştan
worker kaybını, pause davranışını ve son olayı doğru göstermek zorundadır.
"""
from __future__ import annotations

import enum
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Deque

from aegis.contracts.models import now_iso


class EventKind(str, enum.Enum):
    CAMPAIGN_CREATED = "campaign_created"
    STATE_CHANGED = "state_changed"
    ATTEMPT_STARTED = "attempt_started"
    ATTEMPT_FINISHED = "attempt_finished"
    VERDICT_DECIDED = "verdict_decided"
    FINDING_CANDIDATE = "finding_candidate"
    FINDING_CONFIRMED = "finding_confirmed"
    FINDING_GROUPED = "finding_grouped"
    BUDGET_UPDATE = "budget_update"
    SCHEDULER_DECISION = "scheduler_decision"
    REPAIR_BUILD = "repair_build"
    REPAIR_GATE = "repair_gate"
    REPAIR_REJECTED = "repair_rejected"
    VERIFICATION_UPDATE = "verification_update"
    VERIFICATION_DONE = "verification_done"
    CAMPAIGN_COMPLETED = "campaign_completed"
    WORKER_LOST = "worker_lost"
    AUDIT = "audit"
    KILL_SWITCH = "kill_switch"
    SNAPSHOT = "snapshot"
    PREFLIGHT = "preflight"
    BASELINE_UPDATE = "baseline_update"


@dataclass
class EventRecord:
    seq: int
    kind: EventKind
    campaign_id: str
    payload: dict
    ts: str = field(default_factory=now_iso)

    def to_json(self) -> dict:
        return {
            "seq": self.seq,
            "kind": self.kind.value,
            "campaign_id": self.campaign_id,
            "payload": self.payload,
            "ts": self.ts,
        }


class EventBus:
    """Bellek içi olay veriyolu; sıralı cursor ile yeniden oynatma destekler."""

    def __init__(self, maxlen: int = 5000) -> None:
        self._events: Deque[EventRecord] = deque(maxlen=maxlen)
        self._subscribers: dict[str, list[Callable[[EventRecord], None]]] = {}
        self._lock = threading.RLock()
        self._seq = 0

    def publish(self, kind: EventKind, campaign_id: str, payload: dict | None = None) -> EventRecord:
        with self._lock:
            self._seq += 1
            rec = EventRecord(seq=self._seq, kind=kind, campaign_id=campaign_id, payload=payload or {})
            self._events.append(rec)
            subs = list(self._subscribers.get(campaign_id, []))
        for cb in subs:
            try:
                cb(rec)
            except Exception:  # abone hatası veriyolunu düşürmez
                pass
        return rec

    def subscribe(self, campaign_id: str, callback: Callable[[EventRecord], None]) -> Callable[[], None]:
        with self._lock:
            self._subscribers.setdefault(campaign_id, []).append(callback)

        def _unsub() -> None:
            with self._lock:
                lst = self._subscribers.get(campaign_id, [])
                if callback in lst:
                    lst.remove(callback)

        return _unsub

    def history(self, campaign_id: str, after_seq: int = 0) -> list[EventRecord]:
        with self._lock:
            return [e for e in self._events if e.campaign_id == campaign_id and e.seq > after_seq]

    def all_history(self) -> list[EventRecord]:
        with self._lock:
            return list(self._events)
