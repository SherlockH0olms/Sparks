"""AEGIS LOOP — Pydantic veri sözleşmeleri (tek kanıt dili).

Taslak tasarımın temel ilkeleri bu modülde koda dönüşür:

* Her deneme hedef/politika/oracle sürümüne bağlıdır (RevisionTriple).
* execution_status ile verdict ayrı alanlardır; timeout saldırı
  engellendi demek değildir.
* Red, oracle gizli değerlerine erişemez; bu ayırım yapısal olarak
  modellerin içinde durur (verdict yalnız evaluation katmanı yazar).
* Bütçe, tekil token sayısı değil kaynak türü bazlı defterdir.
"""
from __future__ import annotations

import enum
import hashlib
import json
import secrets
import time
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field


def now_iso() -> str:
    import datetime as _dt

    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def stable_hash(payload: Any) -> str:
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Enum'ler: yürütme sonucu ile güvenlik sonucu kesinlikle ayrı tutulur.
# ---------------------------------------------------------------------------


class ExecutionStatus(str, enum.Enum):
    """Denemenin *yürütme* sonucu. Güvenlik yorumu içermez."""

    COMPLETED = "completed"
    TIMEOUT = "timeout"
    INFRASTRUCTURE_ERROR = "infrastructure_error"
    INVALID_TEST = "invalid_test"
    CANCELLED = "cancelled"


class Verdict(str, enum.Enum):
    """Denemenin bağımsız değerlendirme sonucu."""

    VIOLATION = "violation"
    NO_VIOLATION_OBSERVED = "no_violation_observed"
    INCONCLUSIVE = "inconclusive"
    NOT_APPLICABLE = "not_applicable"


class AttemptStatus(str, enum.Enum):
    CANDIDATE = "candidate"
    EXECUTED = "executed"
    ASSESSED = "assessed"
    DISCARDED = "discarded"


class CampaignState(str, enum.Enum):
    DRAFT = "draft"
    PREFLIGHT = "preflight"
    BASELINING = "baselining"
    DISCOVERING = "discovering"
    VERIFYING_FINDINGS = "verifying_findings"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    FAILED = "failed"
    BUDGET_EXHAUSTED = "budget_exhausted"


class RepairState(str, enum.Enum):
    CANDIDATE = "candidate"
    BUILDING = "building"
    GATE_FAILED = "gate_failed"
    BUILT = "built"
    VALIDATING = "validating"
    VALIDATED_IN_SCOPE = "validated_in_scope"
    MITIGATED = "mitigated"
    REJECTED = "rejected"
    INCONCLUSIVE = "inconclusive"


class DiagnosisState(str, enum.Enum):
    OBSERVED = "observed"
    HYPOTHESIS = "hypothesis"
    EVIDENCE_SUPPORTED = "evidence_supported"
    CONTROL_DEFECT_CONFIRMED = "control_defect_confirmed"
    NEEDS_FURTHER_INVESTIGATION = "needs_further_investigation"


class CellStatus(str, enum.Enum):
    NOT_TESTED = "not_tested"
    INSUFFICIENT_DEPTH = "insufficient_depth"
    ASSESSED_NO_VIOLATION = "assessed_no_violation"
    VIOLATION_OBSERVED = "violation_observed"
    INCONCLUSIVE = "inconclusive"
    NOT_APPLICABLE = "not_applicable"


class VerificationVerdict(str, enum.Enum):
    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"


class ActorRole(str, enum.Enum):
    VIEWER = "viewer"
    ANALYST = "analyst"
    MAINTAINER = "maintainer"
    APPROVER = "approver"
    EVALUATOR_SERVICE = "evaluator_service"


class ResourceKind(str, enum.Enum):
    TARGET_CALLS = "target_calls"
    GENERATOR_CALLS = "generator_calls"
    JUDGE_CALLS = "judge_calls"
    TOKENS = "tokens"
    CPU_SECONDS = "cpu_seconds"
    WALL_SECONDS = "wall_seconds"


class StrategyFamily(str, enum.Enum):
    DIRECT_INJECTION = "direct_injection"
    INDIRECT_INJECTION = "indirect_injection"
    MULTI_TURN_MANIPULATION = "multi_turn_manipulation"
    ENCODING_EVASION = "encoding_evasion"
    TENANT_ISOLATION = "tenant_isolation"
    SECRET_PROBING = "secret_probing"
    OUTPUT_SCHEMA_ABUSE = "output_schema_abuse"


class SecurityProperty(str, enum.Enum):
    TASK_CONSTRAINT = "task_constraint"
    DATA_INSTRUCTION_SEPARATION = "data_instruction_separation"
    SECRET_CONFIDENTIALITY = "secret_confidentiality"
    TENANT_ISOLATION = "tenant_isolation"
    TOOL_AUTHORIZATION = "tool_authorization"
    OUTPUT_INTEGRITY = "output_integrity"


class VerificationSuite(str, enum.Enum):
    REPLAY = "replay"
    UNSEEN_VARIATIONS = "unseen_variations"
    ADAPTIVE_DEFENSE_AWARE = "adaptive_defense_aware"
    UTILITY_REGRESSION = "utility_regression"


# ---------------------------------------------------------------------------
# Temel nesneler
# ---------------------------------------------------------------------------


class Actor(BaseModel):
    id: str = Field(default_factory=lambda: new_id("actor"))
    role: ActorRole
    display_name: str = ""


class AllowedSurface(BaseModel):
    name: str
    description: str = ""


class DocumentRef(BaseModel):
    doc_id: str
    tenant: str
    title: str
    body: str
    assigned_to: str | None = None


class TenantContext(BaseModel):
    tenant_id: str
    user_id: str
    session_id: str = Field(default_factory=lambda: new_id("sess"))


class RevisionTriple(BaseModel):
    """Bir denemenin anlamını sabitleyen sürüm üçlüsü."""

    model_revision: str
    application_revision: str
    policy_revision: str

    def combined(self) -> str:
        return f"m:{self.model_revision}|a:{self.application_revision}|p:{self.policy_revision}"


class EnvironmentDescriptor(BaseModel):
    id: str
    kind: str = "sandbox"
    network_egress: Literal["forbidden", "allowlist"] = "forbidden"
    external_side_effects: Literal["forbidden", "simulated"] = "forbidden"


class TargetManifest(BaseModel):
    """Hedefin özellikleri, sürümleri ve izinli yüzeyleri."""

    target_id: str
    display_name: str
    profile: Literal["llm_application", "image_classifier", "fraud_model", "llm_endpoint"]
    revisions: RevisionTriple
    environment: EnvironmentDescriptor = Field(default_factory=lambda: EnvironmentDescriptor(id=new_id("env")))
    capabilities: dict[str, bool] = Field(default_factory=dict)
    surfaces: list[AllowedSurface] = Field(default_factory=list)
    red_writable_surfaces: list[str] = Field(default_factory=list)
    red_observations: list[str] = Field(default_factory=list)
    blue_readable_resources: list[str] = Field(default_factory=list)
    blue_writable_resources: list[str] = Field(default_factory=list)
    documents: list[DocumentRef] = Field(default_factory=list)

    def surface_allowed(self, name: str) -> bool:
        return name in self.red_writable_surfaces

    def observable(self, name: str) -> bool:
        return name in self.red_observations


class PolicyBundle(BaseModel):
    """Sürümlü politika + kanarya sır tanımları (değerler vault'ta)."""

    policy_revision: str
    allowed_response_fields: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    canaries: dict[str, str] = Field(default_factory=dict)  # id -> description (değer yok!)

    def canary_ids(self) -> list[str]:
        return list(self.canaries.keys())


class CellKey(BaseModel):
    security_property: SecurityProperty
    strategy_family: StrategyFamily
    language: str
    access_profile: str = "standard_user"

    def as_tuple(self) -> tuple[str, str, str, str]:
        return (
            self.security_property.value,
            self.strategy_family.value,
            self.language,
            self.access_profile,
        )


class CoverageCell(BaseModel):
    key: CellKey
    status: CellStatus = CellStatus.NOT_TESTED
    attempts: int = 0
    valid_attempts: int = 0
    violations: int = 0
    min_attempts_required: int = 3
    last_attempt_id: str | None = None
    not_applicable_reason: str | None = None

    def completed(self) -> bool:
        if self.status == CellStatus.NOT_APPLICABLE:
            return True
        return self.valid_attempts >= self.min_attempts_required


class AttackStrategy(BaseModel):
    strategy_id: str
    family: StrategyFamily
    languages: list[str]
    turns: list[str] = Field(default_factory=list)
    turns_by_language: dict[str, list[str]] = Field(default_factory=dict)
    requires_document: bool = False
    requires_session: bool = False
    targets_property: list[SecurityProperty] = Field(default_factory=list)
    description: str = ""

    def turn_texts(self, language: str) -> list[str]:
        if self.turns_by_language:
            return self.turns_by_language.get(language, [])
        return self.turns


class BudgetLimits(BaseModel):
    target_calls: int = 400
    generator_calls: int = 120
    judge_calls: int = 80
    tokens: int = 2_000_000
    cpu_seconds: float = 1_000.0
    wall_seconds: float = 600.0


class BudgetLedgerEntry(BaseModel):
    ts: str = Field(default_factory=now_iso)
    resource: ResourceKind
    amount: float
    purpose: str
    attempt_id: str | None = None


class CampaignSpec(BaseModel):
    campaign_id: str = Field(default_factory=lambda: new_id("cmp"))
    target_id: str
    revisions: RevisionTriple
    budget: BudgetLimits = Field(default_factory=BudgetLimits)
    languages: list[str] = Field(default_factory=lambda: ["tr", "az", "en"])
    strategies: list[str] | None = None  # None => tümü
    baseline_sample_size: int = 10
    created_at: str = Field(default_factory=now_iso)


class Attempt(BaseModel):
    """Bir denemenin senaryosu ve yürütme kaydı."""

    attempt_id: str = Field(default_factory=lambda: new_id("att"))
    campaign_id: str
    cell: CellKey
    strategy_id: str
    language: str
    turns: list[str]
    document_ids: list[str] = Field(default_factory=list)
    tenant_context: TenantContext | None = None
    execution_status: ExecutionStatus | None = None
    verdict: Verdict | None = None  # yalnızca evaluation katmanı yazar
    response: str = ""
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    retrieved_doc_ids: list[str] = Field(default_factory=list)
    matched_canaries: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    wall_ms: int = 0
    ts: str = Field(default_factory=now_iso)
    llm_generated: bool = False  # turlar AI red teamer tarafından mı üretildi

    @property
    def is_valid(self) -> bool:
        return self.execution_status in (ExecutionStatus.COMPLETED,) and self.verdict is not None


class EvidenceItem(BaseModel):
    kind: str  # "response_text", "retrieval_log", "tool_log", "oracle_comparison"
    content: str
    source: str = "target_adapter"
    redacted: bool = False


class Assessment(BaseModel):
    """Bağımsız değerlendirme sonucu; Red yazamaz."""

    assessment_id: str = Field(default_factory=lambda: new_id("asm"))
    attempt_id: str
    verdict: Verdict
    violated_property: SecurityProperty | None = None
    deterministic_evidence: list[EvidenceItem] = Field(default_factory=list)
    judge_rationale: str = ""
    oracle_id: str | None = None
    ts: str = Field(default_factory=now_iso)


class ScopeBlueprint(BaseModel):
    campaign_id: str
    cells: list[CoverageCell] = Field(default_factory=list)
    applicable_count: int = 0

    def cell(self, key: CellKey) -> CoverageCell | None:
        for c in self.cells:
            if c.key == key:
                return c
        return None


class Finding(BaseModel):
    finding_id: str = Field(default_factory=lambda: new_id("fnd"))
    campaign_id: str
    group_id: str = ""
    violated_property: SecurityProperty
    boundary: str = ""
    component: str = ""
    observed_effect: str = ""
    original_attempt_id: str
    minimized_turns: list[str] = Field(default_factory=list)
    reproduction_trials: list[dict[str, Any]] = Field(default_factory=list)
    reproduction_rate: float = 0.0
    atlas_mapping: list[dict[str, str]] = Field(default_factory=list)
    diagnosis: DiagnosisState = DiagnosisState.OBSERVED
    diagnosis_notes: str = ""
    evidence: list[EvidenceItem] = Field(default_factory=list)
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    limitations: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=now_iso)


class FindingGroup(BaseModel):
    group_id: str = Field(default_factory=lambda: new_id("grp"))
    violated_property: SecurityProperty
    boundary: str
    component: str
    finding_ids: list[str] = Field(default_factory=list)


class ControlCandidate(BaseModel):
    control_id: str
    display_name: str
    change_type: str
    applies_when: list[str]
    description: str = ""
    limitations: list[str] = Field(default_factory=list)


class Mitigation(BaseModel):
    kind: str
    params: dict[str, Any] = Field(default_factory=dict)
    description: str = ""


class RepairCandidate(BaseModel):
    candidate_id: str = Field(default_factory=lambda: new_id("rcd"))
    label: str  # "A" baseline, "B" prompt-only, "C" server-side, "D" combined
    description: str = ""
    controls: list[ControlCandidate] = Field(default_factory=list)
    mitigations: list[Mitigation] = Field(default_factory=list)
    state: RepairState = RepairState.CANDIDATE
    diff: str = ""
    gate_results: dict[str, Any] = Field(default_factory=dict)
    measurements: dict[str, Any] = Field(default_factory=dict)
    rejection_reasons: list[str] = Field(default_factory=list)
    rollback: str = ""
    target_revision: str = Field(default_factory=lambda: new_id("rev"))


class RepairExperiment(BaseModel):
    experiment_id: str = Field(default_factory=lambda: new_id("rex"))
    campaign_id: str
    finding_id: str
    baseline_revision: str
    candidates: list[RepairCandidate] = Field(default_factory=list)
    winner: str | None = None
    created_at: str = Field(default_factory=now_iso)


class VerificationRun(BaseModel):
    run_id: str = Field(default_factory=lambda: new_id("vrun"))
    experiment_id: str
    candidate_id: str
    suites: dict[str, dict[str, Any]] = Field(default_factory=dict)  # suite -> metrics
    verdict: VerificationVerdict | None = None
    protocol_revision: str = "eval-protocol-v1"
    blind: bool = True
    created_at: str = Field(default_factory=now_iso)


class EvidencePack(BaseModel):
    pack_id: str = Field(default_factory=lambda: new_id("pack"))
    campaign_id: str
    target_manifest: TargetManifest
    policy: PolicyBundle
    attempts: list[Attempt] = Field(default_factory=list)
    assessments: list[Assessment] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    repair_experiments: list[RepairExperiment] = Field(default_factory=list)
    verification_runs: list[VerificationRun] = Field(default_factory=list)
    budget_entries: list[BudgetLedgerEntry] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    generated_at: str = Field(default_factory=now_iso)


class Campaign(BaseModel):
    spec: CampaignSpec
    state: CampaignState = CampaignState.DRAFT
    scope: ScopeBlueprint | None = None
    attempts: list[Attempt] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    baseline: dict[str, Any] = Field(default_factory=dict)
    started_at: str | None = None
    finished_at: str | None = None
    last_event_ts: str | None = None


Attempt.model_rebuild()
EvidencePack.model_rebuild()
