"""Ortak veri sözleşmeleri.

Bu modül, Red/Repair/Verification laboratuvarlarının ve UI'ın konuştuğu
tek kanıt ve deney dilini tanımlar. İlk geliştirme hedefi bu sözleşmelerdir;
her ekip farklı "bulgu" ve "başarı" tanımı geliştirmemeli.
"""
from aegis.contracts.models import (
    Actor,
    ActorRole,
    AllowedSurface,
    Assessment,
    Attempt,
    AttemptStatus,
    AttackStrategy,
    BudgetLedgerEntry,
    Campaign,
    CampaignSpec,
    CampaignState,
    CellKey,
    CellStatus,
    ControlCandidate,
    CoverageCell,
    DiagnosisState,
    DocumentRef,
    EnvironmentDescriptor,
    EvidenceItem,
    EvidencePack,
    ExecutionStatus,
    Finding,
    FindingGroup,
    Mitigation,
    PolicyBundle,
    RepairCandidate,
    RepairExperiment,
    RepairState,
    ResourceKind,
    RevisionTriple,
    ScopeBlueprint,
    SecurityProperty,
    StrategyFamily,
    TargetManifest,
    TenantContext,
    Verdict,
    VerificationRun,
    VerificationSuite,
    VerificationVerdict,
)

__all__ = [name for name in dir() if not name.startswith("_")]
