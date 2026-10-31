"""Kodla tanımlanmış durum makineleri.

Geçişler tabloda sabittir; veritabanında atomik geçiş yapılacak yer burasıdır.
COMPLETED, "bütün güvenlik özellikleri geçti" değil; planlanan akış bitti
anlamına gelir.
"""
from __future__ import annotations

from aegis.contracts.models import CampaignState, RepairState

CAMPAIGN_TRANSITIONS: dict[CampaignState, set[CampaignState]] = {
    CampaignState.DRAFT: {CampaignState.PREFLIGHT},
    CampaignState.PREFLIGHT: {CampaignState.BASELINING, CampaignState.FAILED, CampaignState.CANCELLED},
    CampaignState.BASELINING: {
        CampaignState.DISCOVERING,
        CampaignState.FAILED,
        CampaignState.CANCELLED,
        CampaignState.BUDGET_EXHAUSTED,
    },
    CampaignState.DISCOVERING: {
        CampaignState.VERIFYING_FINDINGS,
        CampaignState.PAUSED,
        CampaignState.CANCELLED,
        CampaignState.FAILED,
        CampaignState.BUDGET_EXHAUSTED,
    },
    CampaignState.VERIFYING_FINDINGS: {
        CampaignState.COMPLETED,
        CampaignState.PAUSED,
        CampaignState.CANCELLED,
        CampaignState.FAILED,
        CampaignState.BUDGET_EXHAUSTED,
    },
    CampaignState.PAUSED: {CampaignState.DISCOVERING, CampaignState.VERIFYING_FINDINGS, CampaignState.CANCELLED},
    CampaignState.COMPLETED: set(),
    CampaignState.CANCELLED: set(),
    CampaignState.FAILED: set(),
    CampaignState.BUDGET_EXHAUSTED: set(),
}

REPAIR_TRANSITIONS: dict[RepairState, set[RepairState]] = {
    RepairState.CANDIDATE: {RepairState.BUILDING},
    RepairState.BUILDING: {RepairState.GATE_FAILED, RepairState.BUILT},
    RepairState.GATE_FAILED: {RepairState.REJECTED},
    RepairState.BUILT: {RepairState.VALIDATING},
    RepairState.VALIDATING: {
        RepairState.VALIDATED_IN_SCOPE,
        RepairState.MITIGATED,
        RepairState.REJECTED,
        RepairState.INCONCLUSIVE,
    },
    RepairState.VALIDATED_IN_SCOPE: set(),
    RepairState.MITIGATED: set(),
    RepairState.REJECTED: set(),
    RepairState.INCONCLUSIVE: set(),
}


class TransitionError(RuntimeError):
    pass


class CampaignStateMachine:
    def __init__(self, state: CampaignState = CampaignState.DRAFT) -> None:
        self.state = state

    def can(self, to: CampaignState) -> bool:
        return to in CAMPAIGN_TRANSITIONS[self.state]

    def go(self, to: CampaignState) -> CampaignState:
        if not self.can(to):
            raise TransitionError(f"illegal transition {self.state.value} -> {to.value}")
        self.state = to
        return self.state

    def is_terminal(self) -> bool:
        return not CAMPAIGN_TRANSITIONS[self.state]


class RepairStateMachine:
    def __init__(self, state: RepairState = RepairState.CANDIDATE) -> None:
        self.state = state

    def can(self, to: RepairState) -> bool:
        return to in REPAIR_TRANSITIONS[self.state]

    def go(self, to: RepairState) -> RepairState:
        if not self.can(to):
            raise TransitionError(f"illegal transition {self.state.value} -> {to.value}")
        self.state = to
        return self.state

    def is_terminal(self) -> bool:
        return not REPAIR_TRANSITIONS[self.state]
