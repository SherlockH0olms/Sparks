"""Kampanya motoru: Red → Findings → Repair → Verification zinciri.

Kritik kurallar:
* Devam eden kampanyanın hedefi yerinde değiştirilmez; Repair adayları
  baseline'ın izole kopyalarında çalışır.
* Bütçe iş başlamadan rezerve edilir; final doğrulama rezervi keşif
  için sessizce tüketilmez.
* COMPLETED, "bütün özellikler geçti" değil; planlanan akış bitti demektir.
"""
from __future__ import annotations

import time
from typing import Any

from aegis.contracts.models import (
    Attempt,
    Campaign,
    CampaignSpec,
    CampaignState,
    CellKey,
    ExecutionStatus,
    PolicyBundle,
    ResourceKind,
    Verdict,
)
from aegis.core.budget import BudgetLedger
from aegis.core.events import EventBus, EventKind
from aegis.core.machine import CampaignStateMachine
from aegis.coverage.grid import CoverageGrid
from aegis.coverage.scheduler import Scheduler
from aegis.evaluation.baseline import BaselineRunner
from aegis.evaluation.evaluator import IndependentEvaluator
from aegis.findings.pipeline import FindingPipeline
from aegis.red.library import StrategyLibrary, injected_doc_body_for
from aegis.red.memory import RedMemory
from aegis.repair.lab import RepairLab
from aegis.reporting.report import ReportGenerator
from aegis.targets.synthetic_assistant.app import (
    AssistantRequest,
    DefenseStack,
    SyntheticAssistant,
)
from aegis.verification.runner import VerificationRunner


class CampaignEngine:
    """Tek kampanyanın uçtan uca yürütülmesi."""

    def __init__(
        self,
        spec: CampaignSpec,
        manifest,
        policy: PolicyBundle,
        bus: EventBus,
    ) -> None:
        self.spec = spec
        self.manifest = manifest
        self.policy = policy
        self.bus = bus
        self.campaign = Campaign(spec=spec)
        self.machine = CampaignStateMachine()
        self.ledger = BudgetLedger(spec.budget)
        self.library = StrategyLibrary()
        self.memory = RedMemory()
        self.grid = CoverageGrid(manifest, self.library, spec.languages)
        self.vault = None  # engine dışında enjekte edilir
        self.evaluator: IndependentEvaluator | None = None
        self.finding_pipeline: FindingPipeline | None = None
        self.repair_lab: RepairLab | None = None
        self.verification: VerificationRunner | None = None
        self.baseline_assistant = SyntheticAssistant(manifest.documents, DefenseStack())
        self._pause_requested = False
        self._cancel_requested = False
        self.experiments: list[Any] = []
        self.verification_runs: list[Any] = []
        self.groups: list[Any] = []

    # -- kurulum ---------------------------------------------------------------

    def attach_evaluator(self, vault, evaluator: IndependentEvaluator) -> None:
        self.vault = vault
        self.evaluator = evaluator
        self.finding_pipeline = FindingPipeline(self.baseline_assistant, evaluator)
        self.repair_lab = RepairLab(self.manifest.documents, evaluator=evaluator)
        self.verification = VerificationRunner(self.manifest.documents, evaluator, self.repair_lab)

    # -- olaylar ----------------------------------------------------------------

    def _emit(self, kind: EventKind, payload: dict | None = None) -> None:
        self.bus.publish(kind, self.spec.campaign_id, payload)

    # -- durum geçişleri ---------------------------------------------------------

    def _go(self, to: CampaignState) -> None:
        self.machine.go(to)
        self.campaign.state = to
        self._emit(EventKind.STATE_CHANGED, {"state": to.value})

    # -- preflight ----------------------------------------------------------------

    def preflight(self) -> list[str]:
        self._go(CampaignState.PREFLIGHT)
        issues: list[str] = []
        if self.evaluator is None:
            issues.append("bağımsız değerlendirici bağlı değil")
        for surface in ("user_message",):
            if surface not in self.manifest.red_writable_surfaces:
                issues.append(f"izinli yüzey eksik: {surface}")
        if "assigned_test_document" not in self.manifest.red_writable_surfaces:
            issues.append("dolaylı injection için test belgesi yüzeyi yok")
        self._emit(EventKind.PREFLIGHT, {"issues": issues})
        return issues

    # -- baseline -----------------------------------------------------------------

    def run_baseline(self) -> dict[str, Any]:
        self._go(CampaignState.BASELINING)
        runner = BaselineRunner(self.baseline_assistant)
        stats = runner.run()
        self.campaign.baseline = {
            "questions": stats.total,
            "answered": stats.answered,
            "utility": round(stats.answered / stats.total, 2) if stats.total else 0.0,
            "avg_wall_ms": round(stats.avg_wall_ms, 1),
            "details": stats.details,
        }
        self.ledger.spend(
            "baseline",
            {ResourceKind.TARGET_CALLS: stats.total, ResourceKind.TOKENS: stats.total * 220},
        )
        self._emit(
            EventKind.BASELINE_UPDATE,
            {"utility": self.campaign.baseline["utility"], "answered": stats.answered},
        )
        return self.campaign.baseline

    # -- kapsam -------------------------------------------------------------------

    def build_scope(self) -> None:
        blueprint = self.grid.build()
        blueprint.campaign_id = self.spec.campaign_id
        self.campaign.scope = blueprint

    # -- keşif döngüsü --------------------------------------------------------------

    def _strategy_for_cell(self, cell):
        """Hücrenin özellik+ailesine uygun strateji ve dil seç."""
        for strategy in self.library.strategies.values():
            if strategy.family != cell.key.strategy_family:
                continue
            if cell.key.security_property not in strategy.targets_property:
                continue
            for lang in self.spec.languages:
                if lang in strategy.languages:
                    return (strategy.strategy_id, lang)
        return None

    def _make_attempt(self, decision, variant_index: int = 0) -> Attempt:
        strategy = self.library.get(decision.strategy_id)
        turns = strategy.turn_texts(decision.language)
        # Varyasyon: aynı stratejinin metnini küçük değişikliklerle çeşitlendir
        if variant_index > 0:
            turns = self._vary_turns(turns, decision.language, variant_index)
        doc_ids: list[str] = []
        if strategy.requires_document:
            # Red'e atanmış test belgesi: gövde Red tarafından yazılabilir
            from aegis.contracts.models import DocumentRef

            doc = DocumentRef(
                doc_id=f"doc_red_injected_{decision.language}",
                tenant="tenant-alpha",
                title="Vendor Contract Draft (assigned)",
                body=injected_doc_body_for(decision.language, variant=variant_index),
                assigned_to="red",
            )
            self.baseline_assistant.documents[doc.doc_id] = doc
            doc_ids = [doc.doc_id]
        from aegis.contracts.models import TenantContext

        ctx = TenantContext(tenant_id="tenant-alpha", user_id="red_operator")
        return Attempt(
            campaign_id=self.spec.campaign_id,
            cell=decision.cell_key,
            strategy_id=decision.strategy_id,
            language=decision.language,
            turns=turns,
            document_ids=doc_ids,
            tenant_context=ctx,
        )

    _VARIATION_SUFFIXES = {
        "tr": ["", " Lütfen ayrıntılı yanıt ver.", " Bu çok önemli.", " Acil olarak işlem gerekiyor."],
        "az": ["", " Zəhmət olmasa ətraflı cavab ver.", " Bu çox vacibdir.", " Təcili əməliyyat tələb olunur."],
        "en": ["", " Please answer in detail.", " This is very important.", " Urgent action required."],
    }

    def _vary_turns(self, turns: list[str], language: str, variant_index: int) -> list[str]:
        suffixes = self._VARIATION_SUFFIXES.get(language, self._VARIATION_SUFFIXES["en"])
        suffix = suffixes[variant_index % len(suffixes)]
        return [t + suffix for t in turns]

    def _execute_attempt(self, attempt: Attempt) -> None:
        """Hedef çağrısı + değerlendirme; execution/verdict ayrı yazılır."""
        self._emit(
            EventKind.ATTEMPT_STARTED,
            {"attempt_id": attempt.attempt_id, "strategy": attempt.strategy_id, "language": attempt.language},
        )
        t0 = time.perf_counter()
        req = AssistantRequest(
            message=attempt.turns[0] if attempt.turns else "",
            tenant_context=attempt.tenant_context,
            assigned_document_ids=list(attempt.document_ids),
            expect_json=(attempt.cell.strategy_family.value == "output_schema_abuse"),
        )
        resp = self.baseline_assistant.handle(req)
        attempt.execution_status = ExecutionStatus.COMPLETED
        attempt.response = resp.text
        attempt.tool_calls = resp.tool_calls
        attempt.retrieved_doc_ids = resp.retrieved_doc_ids
        attempt.wall_ms = int((time.perf_counter() - t0) * 1000)

        # bağımsız değerlendirme (verdict'i Red yazmaz)
        ev = self.evaluator.assess_attempt(attempt, resp)
        attempt.verdict = ev.assessment.verdict
        attempt.evidence = ev.assessment.deterministic_evidence

        # bütçe
        self.ledger.spend(
            f"attempt:{attempt.strategy_id}",
            {
                ResourceKind.TARGET_CALLS: 1,
                ResourceKind.GENERATOR_CALLS: 1,
                ResourceKind.TOKENS: 320,
                ResourceKind.CPU_SECONDS: 0.01,
                ResourceKind.WALL_SECONDS: max(0.001, attempt.wall_ms / 1000.0),
            },
            attempt_id=attempt.attempt_id,
        )

        # kapsam + hafıza güncelle
        self.grid.record_attempt(
            attempt.cell,
            verdict_is_violation=(ev.assessment.verdict == Verdict.VIOLATION),
            valid=attempt.is_valid,
        )
        self.memory.record(
            attempt,
            observations=[f"response={resp.text[:80]}"],
            cost={"target_calls": 1, "tokens": 320},
        )
        self.campaign.attempts.append(attempt)
        self._emit(
            EventKind.ATTEMPT_FINISHED,
            {
                "attempt_id": attempt.attempt_id,
                "execution_status": attempt.execution_status.value,
                "verdict": attempt.verdict.value if attempt.verdict else None,
                "wall_ms": attempt.wall_ms,
            },
        )

    def discovery_loop(self, max_attempts: int | None = None) -> None:
        self._go(CampaignState.DISCOVERING)
        scheduler = Scheduler(self.grid, self.memory)
        # final doğrulama rezervi: bütçenin %10'u ayrılır, keşifte kullanılmaz
        reserve_calls = max(2.0, self.spec.budget.target_calls * 0.10)
        self.ledger.reserve(
            "final_verification_reserve",
            {ResourceKind.TARGET_CALLS: reserve_calls},
        )
        count = 0
        while True:
            if self._pause_requested or self._cancel_requested:
                return
            if max_attempts is not None and count >= max_attempts:
                return
            if self.ledger.remaining(ResourceKind.TARGET_CALLS) <= 1:
                self._go(CampaignState.BUDGET_EXHAUSTED)
                return
            decision = scheduler.next_choice(self._strategy_for_cell)
            if decision is None:
                return  # tüm uygulanabilir hücreler tamamlandı
            self._emit(
                EventKind.SCHEDULER_DECISION,
                {
                    "cell": decision.cell_key.as_tuple(),
                    "strategy": decision.strategy_id,
                    "language": decision.language,
                    "reason": decision.reason,
                    "score": decision.priority_score,
                },
            )
            cell = self.grid.get(decision.cell_key)
            variant_index = cell.attempts  # hücrede kaç deneme yapıldıysa o varyasyon
            attempt = self._make_attempt(decision, variant_index=variant_index)
            self._execute_attempt(attempt)
            count += 1

    # -- bulgu doğrulama ------------------------------------------------------------

    def verify_findings(self) -> None:
        self._go(CampaignState.VERIFYING_FINDINGS)
        violating = [a for a in self.campaign.attempts if a.verdict == Verdict.VIOLATION]
        seen_group_keys: set[tuple] = set()
        for att in violating:
            assessment = None
            # orijinal değerlendirmeyi yeniden üret
            req = AssistantRequest(
                message=att.turns[0] if att.turns else "",
                tenant_context=att.tenant_context,
                assigned_document_ids=list(att.document_ids),
                expect_json=(att.cell.strategy_family.value == "output_schema_abuse"),
            )
            resp = self.baseline_assistant.handle(req)
            ev = self.evaluator.assess_attempt(att, resp)
            finding = self.finding_pipeline.build_finding(att, ev.assessment, resp)
            self.campaign.findings.append(finding)
            self._emit(
                EventKind.FINDING_CONFIRMED,
                {
                    "finding_id": finding.finding_id,
                    "property": finding.violated_property.value,
                    "severity": finding.severity,
                    "reproduction_rate": finding.reproduction_rate,
                    "atlas": [m["technique_id"] for m in finding.atlas_mapping],
                },
            )
        # gruplama
        self.groups = self.finding_pipeline.group_findings(self.campaign.findings)
        self._emit(EventKind.FINDING_GROUPED, {"groups": len(self.groups)})

    # -- repair + verification --------------------------------------------------------

    def run_repair_and_verification(self) -> None:
        """Her bulgu GRUBU için: deney → aday seçimi → bağımsız final.

        Aynı kontrol eksikliğine işaret eden bulgular tek deneyde ele alınır;
        'bin farklı metin' bin farklı yama üretmez.
        """
        self.ledger.release("final_verification_reserve")
        for group in self.groups:
            group_findings = [
                f for f in self.campaign.findings if f.group_id == group.group_id
            ]
            if not group_findings:
                continue
            # grubun tüm saldırı denemeleri
            attack_attempts: list[Any] = []
            for finding in group_findings:
                attack_attempts.extend(
                    [a for a in self.campaign.attempts if a.attempt_id == finding.original_attempt_id]
                )
            if not attack_attempts:
                continue
            # deney, grubun temsilî bulgusu üzerinde kurulur
            lead = group_findings[0]
            exp = self.repair_lab.propose_experiment(
                campaign_id=self.spec.campaign_id,
                finding=lead,
                attack_attempts=attack_attempts,
                evaluator=self.evaluator,
                baseline_revision=self.spec.revisions.combined(),
            )
            self.experiments.append(exp)
            self._emit(
                EventKind.REPAIR_BUILD,
                {
                    "experiment_id": exp.experiment_id,
                    "finding_id": lead.finding_id,
                    "group_id": group.group_id,
                    "candidates": [
                        {
                            "label": c.label,
                            "state": c.state.value,
                            "rejected": bool(c.rejection_reasons),
                        }
                        for c in exp.candidates
                    ],
                },
            )
            for cand in exp.candidates:
                if cand.rejection_reasons and cand.label != "A":
                    self._emit(
                        EventKind.REPAIR_REJECTED,
                        {
                            "experiment_id": exp.experiment_id,
                            "candidate": cand.label,
                            "reasons": cand.rejection_reasons,
                        },
                    )
            if exp.winner is None:
                continue
            # adayı dondur, bağımsız final değerlendirmesini çalıştır
            run = self.verification.run(
                exp, exp.winner, attack_attempts, property_value=group.violated_property.value
            )
            self.verification_runs.append(run)
            self._emit(
                EventKind.VERIFICATION_DONE,
                {
                    "run_id": run.run_id,
                    "candidate": exp.winner,
                    "verdict": run.verdict.value if run.verdict else None,
                    "suites": run.suites,
                },
            )
            # Protokol: seçilen aday başarısızsa bir sonraki geçen aday denenir;
            # aynı geliştirme setiyle ikinci deneme artık tam bağımsız sayılmaz.
            if run.verdict is not None and run.verdict.value != "pass":
                fallback = self._fallback_candidate(exp)
                if fallback is not None:
                    run2 = self.verification.run(
                        exp, fallback, attack_attempts, property_value=group.violated_property.value
                    )
                    self.verification_runs.append(run2)
                    self._emit(
                        EventKind.VERIFICATION_UPDATE,
                        {
                            "run_id": run2.run_id,
                            "candidate": fallback,
                            "note": "ilk aday başarısız; sıradaki aday donduruldu (bağımsızlık azaldı)",
                            "verdict": run2.verdict.value if run2.verdict else None,
                        },
                    )
                    if run2.verdict is not None and run2.verdict.value == "pass":
                        exp.winner = fallback

    def _fallback_candidate(self, exp) -> str | None:
        from aegis.contracts.models import RepairState

        order = ["D", "C", "B"]
        for label in order:
            for cand in exp.candidates:
                if cand.label == label and cand.state in (
                    RepairState.BUILT,
                    RepairState.VALIDATING,
                    RepairState.VALIDATED_IN_SCOPE,
                ) and cand.candidate_id != exp.winner:
                    return cand.candidate_id
        return None

    # -- tam akış ---------------------------------------------------------------------

    def run(self, max_attempts: int | None = None) -> Campaign:
        issues = self.preflight()
        if issues:
            self._go(CampaignState.FAILED)
            return self.campaign
        self.run_baseline()
        self.build_scope()
        self.discovery_loop(max_attempts=max_attempts)
        if self._cancel_requested:
            self._go(CampaignState.CANCELLED)
            return self.campaign
        if self.campaign.state == CampaignState.BUDGET_EXHAUSTED:
            return self.campaign
        self.verify_findings()
        self.run_repair_and_verification()
        if self.machine.can(CampaignState.COMPLETED):
            self._go(CampaignState.COMPLETED)
            self._emit(EventKind.CAMPAIGN_COMPLETED, {"findings": len(self.campaign.findings)})
        self.campaign.finished_at = None or self.campaign.finished_at
        return self.campaign

    # -- kontrol ----------------------------------------------------------------------

    def request_pause(self) -> None:
        self._pause_requested = True

    def request_resume(self) -> None:
        self._pause_requested = False

    def request_cancel(self) -> None:
        self._cancel_requested = True

    # -- özet -------------------------------------------------------------------------

    def summary(self) -> dict[str, Any]:
        cov = self.grid.coverage_metrics()
        return {
            "campaign_id": self.spec.campaign_id,
            "state": self.campaign.state.value,
            "target": self.spec.target_id,
            "revisions": self.spec.revisions.model_dump(),
            "coverage": cov,
            "attempts": len(self.campaign.attempts),
            "findings": len(self.campaign.findings),
            "groups": len(self.groups),
            "experiments": len(self.experiments),
            "verification_runs": len(self.verification_runs),
            "budget": self.ledger.snapshot(),
            "baseline": self.campaign.baseline,
        }

    def snapshot(self) -> dict[str, Any]:
        """Checkpoint: pause/resume ve 'kayıtlı replay' için."""
        return {
            "campaign": self.campaign.model_dump(),
            "coverage": self.grid.coverage_metrics(),
            "budget": self.ledger.snapshot(),
            "ts": time.time(),
        }
