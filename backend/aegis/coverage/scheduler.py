"""Scheduler: açıklanabilir seçim politikası.

Öncelik =
    kapsam eksikliği
    + güvenlik özelliğinin önemi
    + yeni davranış araştırma değeri
    + kanıtla desteklenen ilerleme
    - tekrar maliyeti
    - tahmini kaynak maliyeti

Bu başlangıç sezgisidir; optimum olduğu iddia edilmez. Her seçim için
kısa bir karar kaydı (gerekçe) üretilir; bu gizli muhakeme dökümü değil,
yapılandırılmış açıklamadır.
"""
from __future__ import annotations

from dataclasses import dataclass

from aegis.contracts.models import (
    CellKey,
    CellStatus,
    CoverageCell,
    SecurityProperty,
)
from aegis.red.memory import RedMemory


PROPERTY_WEIGHT: dict[SecurityProperty, float] = {
    SecurityProperty.SECRET_CONFIDENTIALITY: 3.0,
    SecurityProperty.TENANT_ISOLATION: 3.0,
    SecurityProperty.TOOL_AUTHORIZATION: 2.5,
    SecurityProperty.DATA_INSTRUCTION_SEPARATION: 2.0,
    SecurityProperty.TASK_CONSTRAINT: 1.5,
    SecurityProperty.OUTPUT_INTEGRITY: 1.0,
}


@dataclass
class SchedulerDecision:
    cell_key: CellKey
    strategy_id: str
    language: str
    reason: str
    priority_score: float


class Scheduler:
    def __init__(self, grid, memory: RedMemory) -> None:
        self.grid = grid
        self.memory = memory

    def next_choice(self, strategy_for_cell) -> SchedulerDecision | None:
        """En yüksek öncelikli hücreyi ve stratejiyi seçer.

        strategy_for_cell: (CoverageCell) -> (strategy_id, language) seçici.
        """
        best: tuple[float, CoverageCell, str, str, str] | None = None
        for cell in self.grid.cells.values():
            if cell.status == CellStatus.NOT_APPLICABLE:
                continue
            if cell.completed():
                continue
            key = cell.key

            # 1) kapsam eksikliği
            deficit = max(0, cell.min_attempts_required - cell.valid_attempts) / max(
                1, cell.min_attempts_required
            )

            # 2) özellik önemi
            importance = PROPERTY_WEIGHT.get(key.security_property, 1.0)

            # 3) araştırma değeri: hiç dokunulmamış hücre ekstra değerli
            stats = self.memory.cell_stats(key.as_tuple())
            exploration = 1.0 if stats["attempts"] == 0 else 0.2

            # 4) kanıtla desteklenen ilerleme: ihlal gören hücrede derinleş
            progress = 0.8 if stats["violations"] > 0 else 0.0

            # 5) tekrar maliyeti: çok denenmiş hücrede azal
            repetition_penalty = min(1.0, stats["attempts"] / 6.0)

            score = (
                deficit * 3.0
                + importance * 0.5
                + exploration * 1.5
                + progress * 0.8
                - repetition_penalty * 0.6
                - 0.1  # tahmini kaynak maliyeti sabit terimi
            )

            pick = strategy_for_cell(cell)
            if pick is None:
                continue
            strategy_id, language = pick
            reason = self._reason(cell, stats, deficit, score)
            if best is None or score > best[0]:
                best = (score, cell, strategy_id, language, reason)

        if best is None:
            return None
        score, cell, strategy_id, language, reason = best
        return SchedulerDecision(
            cell_key=cell.key,
            strategy_id=strategy_id,
            language=language,
            reason=reason,
            priority_score=round(score, 3),
        )

    def _reason(self, cell: CoverageCell, stats: dict, deficit: float, score: float) -> str:
        bits = []
        if stats["attempts"] == 0:
            bits.append("hücre hiç test edilmedi (kapsam açığı)")
        else:
            bits.append(
                f"geçerli deneme {cell.valid_attempts}/{cell.min_attempts_required} (eksik {deficit:.0%})"
            )
        if stats["violations"] > 0:
            bits.append(f"hücrede {int(stats['violations'])} ihlal gözlendi, derinleştirme değerli")
        if stats["attempts"] >= 5:
            bits.append("tekrar maliyeti artıyor, öncelik düşürüldü")
        bits.append(f"özellik ağırlığı: {PROPERTY_WEIGHT.get(cell.key.security_property, 1.0)}")
        return "; ".join(bits) + f" → skor {score:.2f}"
