"""Kaynak türü bazlı bütçe defteri.

Tek bir token sayısına indirgemek yerine kaynak türleri ayrı izlenir;
maliyet yapılandırılmış katsayılarla hesaplanır. Final doğrulama rezervi,
daha fazla keşif için sessizce tüketilemez (reserve mekanizması).
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field

from aegis.contracts.models import (
    BudgetLedgerEntry,
    BudgetLimits,
    ResourceKind,
)


@dataclass
class _Reserve:
    """Bir amaca önceden ayrılmış kaynak rezervi."""

    purpose: str
    amounts: dict[ResourceKind, float]


class BudgetLedger:
    """Kampanya bütçesi; iş başlamadan rezerve edilir, bitince mutabakat yapılır."""

    def __init__(self, limits: BudgetLimits) -> None:
        self.limits = limits
        self._used: dict[ResourceKind, float] = {k: 0.0 for k in ResourceKind}
        self._reserved: dict[ResourceKind, float] = {k: 0.0 for k in ResourceKind}
        self._entries: list[BudgetLedgerEntry] = []
        self._lock = threading.RLock()

    # -- ham API ---------------------------------------------------------------

    def _limit_of(self, kind: ResourceKind) -> float:
        return float(getattr(self.limits, kind.value))

    def used(self, kind: ResourceKind) -> float:
        with self._lock:
            return self._used[kind]

    def reserved(self, kind: ResourceKind) -> float:
        with self._lock:
            return self._reserved[kind]

    def remaining(self, kind: ResourceKind) -> float:
        with self._lock:
            return max(0.0, self._limit_of(kind) - self._used[kind] - self._reserved[kind])

    def entries(self) -> list[BudgetLedgerEntry]:
        with self._lock:
            return list(self._entries)

    def snapshot(self) -> dict[str, dict[str, float]]:
        with self._lock:
            out: dict[str, dict[str, float]] = {}
            for kind in ResourceKind:
                limit = self._limit_of(kind)
                out[kind.value] = {
                    "limit": limit,
                    "used": round(self._used[kind], 3),
                    "reserved": round(self._reserved[kind], 3),
                    "remaining": round(max(0.0, limit - self._used[kind] - self._reserved[kind]), 3),
                }
            return out

    # -- rezervasyon -----------------------------------------------------------

    def reserve(self, purpose: str, amounts: dict[ResourceKind, float]) -> bool:
        """İş başlamadan bütçe ayırır. Yetersizse False döner; iş başlamaz."""
        with self._lock:
            for kind, amount in amounts.items():
                if self._used[kind] + self._reserved[kind] + amount > self._limit_of(kind):
                    return False
            for kind, amount in amounts.items():
                self._reserved[kind] += amount
            return True

    def release(self, purpose: str, amounts: dict[ResourceKind, float] | None = None) -> None:
        with self._lock:
            if amounts is None:
                for kind in ResourceKind:
                    self._reserved[kind] = 0.0
                return
            for kind, amount in amounts.items():
                self._reserved[kind] = max(0.0, self._reserved[kind] - amount)

    def spend(
        self,
        purpose: str,
        amounts: dict[ResourceKind, float],
        attempt_id: str | None = None,
        from_reserve: bool = False,
    ) -> bool:
        """Harcanan kaynağı işler. Limit aşılırsa False döner ve işlemez."""
        with self._lock:
            for kind, amount in amounts.items():
                if self._used[kind] + amount > self._limit_of(kind):
                    return False
            for kind, amount in amounts.items():
                self._used[kind] += amount
                if from_reserve:
                    self._reserved[kind] = max(0.0, self._reserved[kind] - amount)
            for kind, amount in amounts.items():
                self._entries.append(
                    BudgetLedgerEntry(
                        resource=kind,
                        amount=amount,
                        purpose=purpose,
                        attempt_id=attempt_id,
                    )
                )
            return True

    def exhausted(self) -> bool:
        """Tüm kaynak türlerinden en az biri tükendi mi?"""
        return any(self.remaining(k) <= 0 for k in ResourceKind)

    def summary(self) -> dict[str, float]:
        snap = self.snapshot()
        total_limit = sum(v["limit"] for v in snap.values())
        total_used = sum(v["used"] for v in snap.values())
        return {
            "total_limit": round(total_limit, 3),
            "total_used": round(total_used, 3),
            "percent_used": round(100.0 * total_used / total_limit, 2) if total_limit else 0.0,
        }
