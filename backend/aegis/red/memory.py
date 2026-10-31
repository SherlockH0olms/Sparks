"""Red hafızası: sadece başarılı metinler değil, koşullar da saklanır.

Hafıza kaydı şunları içerir: uygulanma koşulları, hedef/politika sürümü,
izinli gözlemler, başarılı ve başarısız sonuçlar, kaynak maliyeti,
tekrar üretilebilirlik, bilinen sınırlar.

**Bağımsız değerlendirme verileri bu hafızaya yazılmaz** (yapısal kural).
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field

from aegis.contracts.models import Attempt, CellKey, ExecutionStatus, Verdict


@dataclass
class MemoryRecord:
    cell_key: tuple[str, str, str, str]
    strategy_id: str
    language: str
    succeeded: bool
    verdict: Verdict | None
    execution_status: ExecutionStatus | None
    turns_digest: str
    observations: list[str] = field(default_factory=list)
    cost: dict[str, float] = field(default_factory=dict)
    reproduction_ok: bool | None = None
    known_limits: list[str] = field(default_factory=list)


def _digest(turns: list[str]) -> str:
    import hashlib

    blob = "|".join(turns).encode()
    return hashlib.sha256(blob).hexdigest()[:12]


class RedMemory:
    def __init__(self) -> None:
        self._records: list[MemoryRecord] = []
        self._seen_turn_digests: set[str] = set()
        self._lock = threading.RLock()

    def record(self, attempt: Attempt, observations: list[str], cost: dict[str, float]) -> None:
        with self._lock:
            succeeded = attempt.verdict == Verdict.VIOLATION
            rec = MemoryRecord(
                cell_key=attempt.cell.as_tuple(),
                strategy_id=attempt.strategy_id,
                language=attempt.language,
                succeeded=succeeded,
                verdict=attempt.verdict,
                execution_status=attempt.execution_status,
                turns_digest=_digest(attempt.turns),
                observations=observations,
                cost=cost,
            )
            self._records.append(rec)
            self._seen_turn_digests.add(rec.turns_digest)

    def seen(self, turns: list[str]) -> bool:
        with self._lock:
            return _digest(turns) in self._seen_turn_digests

    def cell_stats(self, cell_key: tuple[str, str, str, str]) -> dict[str, float]:
        with self._lock:
            recs = [r for r in self._records if r.cell_key == cell_key]
            if not recs:
                return {"attempts": 0, "violations": 0, "success_rate": 0.0}
            violations = sum(1 for r in recs if r.succeeded)
            return {
                "attempts": len(recs),
                "violations": violations,
                "success_rate": violations / len(recs),
            }

    def successful_in_family(self, family_value: str) -> list[MemoryRecord]:
        with self._lock:
            return [r for r in self._records if r.cell_key[1] == family_value and r.succeeded]

    def all_records(self) -> list[MemoryRecord]:
        with self._lock:
            return list(self._records)
