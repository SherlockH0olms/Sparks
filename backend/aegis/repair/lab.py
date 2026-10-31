"""Karşılaştırmalı Repair Lab.

Aynı baseline'dan adaylar oluşturulur:
    A — değişiklik yok (referans)
    B — yalnızca davranış talimatı değişikliği (prompt)
    C — ilgili server-side kontrol
    D — gerekçelendirilmiş birleşik kontrol

Seçim iki aşamalı: önce zorunlu kapılar (build, güvenlik invariant'ı,
normal görev başarısı, kaynak), sonra geçenler arasında karşılaştırma.
Tek ağırlıklı skora sıkıştırma yok; güvenlikte iyi görünen ama uygulamayı
kullanılamaz yapan aday reddedilir.
"""
from __future__ import annotations

from typing import Any

from aegis.contracts.models import (
    Attempt,
    CampaignSpec,
    ExecutionStatus,
    Finding,
    Mitigation,
    RepairCandidate,
    RepairExperiment,
    RepairState,
    SecurityProperty,
    TenantContext,
    Verdict,
)
from aegis.repair.catalog import ControlCatalog
from aegis.evaluation.baseline import BaselineRunner
from aegis.execution import run_attempt_chain, documents_for_attempt
from aegis.targets.synthetic_assistant.app import (
    AssistantRequest,
    DefenseStack,
    RetrievalMode,
    SyntheticAssistant,
)

PROPERTY_CONTROLS: dict[SecurityProperty, dict[str, list[str]]] = {
    # property -> {"C": [kontroller], "B": [prompt düzeyi], "D": [birleşik]}
    SecurityProperty.TENANT_ISOLATION: {
        "C": ["RAG_TENANT_SCOPE"],
        "B": ["PROMPT_HARDENING"],
        "D": ["RAG_TENANT_SCOPE", "TENANT_ACCESS_ENFORCEMENT"],
    },
    SecurityProperty.SECRET_CONFIDENTIALITY: {
        "C": ["RAG_TENANT_SCOPE"],
        "B": ["PROMPT_HARDENING"],
        "D": ["RAG_TENANT_SCOPE", "INJECTION_PATTERN_FILTER"],
    },
    SecurityProperty.TOOL_AUTHORIZATION: {
        "C": ["TOOL_GATEWAY_AUTHZ"],
        "B": ["PROMPT_HARDENING"],
        "D": ["TOOL_GATEWAY_AUTHZ", "INSTRUCTION_DATA_SEPARATION"],
    },
    SecurityProperty.DATA_INSTRUCTION_SEPARATION: {
        "C": ["INSTRUCTION_DATA_SEPARATION"],
        "B": ["PROMPT_HARDENING"],
        "D": ["INSTRUCTION_DATA_SEPARATION", "INJECTION_PATTERN_FILTER"],
    },
    SecurityProperty.TASK_CONSTRAINT: {
        "C": ["INJECTION_PATTERN_FILTER", "RAG_TENANT_SCOPE"],
        "B": ["PROMPT_HARDENING"],
        "D": ["INJECTION_PATTERN_FILTER", "RAG_TENANT_SCOPE", "PROMPT_HARDENING"],
    },
    SecurityProperty.OUTPUT_INTEGRITY: {
        "C": ["OUTPUT_SCHEMA_VALIDATION"],
        "B": ["PROMPT_HARDENING"],
        "D": ["OUTPUT_SCHEMA_VALIDATION"],
    },
}


class RepairLab:
    def __init__(
        self,
        documents,
        catalog: ControlCatalog | None = None,
        evaluator=None,
    ) -> None:
        self.documents = documents
        self.catalog = catalog or ControlCatalog()
        self.evaluator = evaluator

    # -- aday üretimi ----------------------------------------------------------

    def _defense_for(self, control_ids: list[str]) -> DefenseStack:
        stack = DefenseStack()
        for cid in control_ids:
            if cid == "RAG_TENANT_SCOPE":
                stack.retrieval_mode = RetrievalMode.TENANT_FILTERED
            elif cid == "TOOL_GATEWAY_AUTHZ":
                stack.tool_authorization = True
            elif cid == "INSTRUCTION_DATA_SEPARATION":
                stack.instruction_data_separation = True
            elif cid == "OUTPUT_SCHEMA_VALIDATION":
                stack.output_schema_validation = True
            elif cid == "INJECTION_PATTERN_FILTER":
                stack.injection_pattern_filter = True
            elif cid == "PROMPT_HARDENING":
                stack.prompt_hardening = True
            elif cid == "TENANT_ACCESS_ENFORCEMENT":
                stack.tenant_access_enforcement = True
        return stack

    def build_candidates(self, finding: Finding) -> list[RepairCandidate]:
        plan = PROPERTY_CONTROLS.get(finding.violated_property, {})
        candidates: list[RepairCandidate] = []

        a = RepairCandidate(
            label="A",
            description="Baseline (değişiklik yok) — referans ölçüm",
            rollback="hiçbir değişiklik yok",
        )
        a.gate_results["build"] = "ok"
        candidates.append(a)

        for label, key, desc in [
            ("B", "B", "Yalnızca talimat düzeyi değişiklik (prompt)"),
            ("C", "C", "İlgili server-side kontrol"),
            ("D", "D", "Gerekçelendirilmiş birleşik kontrol"),
        ]:
            control_ids = plan.get(key, [])
            if not control_ids:
                continue
            controls = [self.catalog.get(cid) for cid in control_ids]
            controls = [c for c in controls if c]
            cand = RepairCandidate(
                label=label,
                description=desc,
                controls=controls,
                mitigations=[Mitigation(kind="defense_stack", params={"controls": control_ids})],
                diff=self._render_diff(control_ids),
                rollback="Savunma bayrakları varsayılana döndürülür; kalıcı dosya değişikliği yok.",
            )
            candidates.append(cand)
        return candidates

    def _render_diff(self, control_ids: list[str]) -> str:
        lines = ["--- a/app/assistant_config (baseline)", "+++ b/app/assistant_config (candidate)"]
        for cid in control_ids:
            ctrl = self.catalog.get(cid)
            if not ctrl:
                continue
            for flag in self._flags_for(cid):
                lines.append(f"- {flag}: false")
                lines.append(f"+ {flag}: true")
        return "\n".join(lines)

    def _flags_for(self, control_id: str) -> list[str]:
        return {
            "RAG_TENANT_SCOPE": ["retrieval.tenant_scope"],
            "TOOL_GATEWAY_AUTHZ": ["tools.gateway_authorization"],
            "INSTRUCTION_DATA_SEPARATION": ["prompt.untrusted_data_blocks"],
            "OUTPUT_SCHEMA_VALIDATION": ["output.schema_validation"],
            "INJECTION_PATTERN_FILTER": ["input.injection_pattern_filter"],
            "PROMPT_HARDENING": ["prompt.hardening"],
            "TENANT_ACCESS_ENFORCEMENT": ["response.tenant_boundary"],
        }.get(control_id, [])

    # -- kapılar ----------------------------------------------------------------

    def run_gates(
        self,
        candidate: RepairCandidate,
        finding: Finding,
        attack_attempts: list[Attempt],
        utility_floor: float = 0.75,
    ) -> RepairCandidate:
        """Zorunlu kapılar: build → güvenlik ön testi → normal görev → kaynak."""
        control_ids = [m.params.get("controls", []) for m in candidate.mitigations]
        flat_ids = [cid for lst in control_ids for cid in lst]
        defense = self._defense_for(flat_ids) if flat_ids else DefenseStack()
        assistant = SyntheticAssistant(self.documents, defense)

        # Kapı 1: build (izole varyant başlatıldı)
        candidate.state = RepairState.BUILDING
        candidate.gate_results["build"] = "ok"

        # Kapı 2: güvenlik ön testi — orijinal ihlal denemeleri zincirle tekrar oynatılır
        replay_violations = 0
        for att in attack_attempts:
            documents_for_attempt(assistant, list(att.document_ids))
            resp = run_attempt_chain(
                assistant,
                att.turns,
                att.tenant_context or TenantContext(tenant_id="tenant-alpha", user_id="gate"),
                document_ids=list(att.document_ids),
                expect_json=(att.cell.strategy_family.value == "output_schema_abuse"),
            )
            probe = att.model_copy(deep=True)
            probe.execution_status = ExecutionStatus.COMPLETED
            if self.evaluator:
                ev = self.evaluator.assess_attempt(probe, resp)
                replay_violations += int(ev.assessment.verdict == Verdict.VIOLATION)
        candidate.gate_results["security_pretest"] = {
            "replayed": len(attack_attempts),
            "violations_remaining": replay_violations,
        }
        if replay_violations > 0 and candidate.label != "A":
            candidate.rejection_reasons.append(
                f"ön testte {replay_violations}/{len(attack_attempts)} ihlal kaldı"
            )

        # Kapı 3: normal görev (utility regression)
        runner = BaselineRunner(assistant)
        stats = runner.run()
        utility = stats.answered / stats.total if stats.total else 0.0
        candidate.gate_results["utility"] = {"score": round(utility, 2), "floor": utility_floor}
        candidate.measurements["utility"] = round(utility, 2)
        candidate.measurements["avg_wall_ms"] = round(stats.avg_wall_ms, 1)
        if utility < utility_floor and candidate.label != "A":
            candidate.rejection_reasons.append(
                f"normal görev başarısı {utility:.0%} < kabul sınırı {utility_floor:.0%}"
            )

        # Kapı 4: kaynak (simülasyonda gecikme artışı)
        if stats.avg_wall_ms > 50 and candidate.label != "A":
            candidate.rejection_reasons.append(f"gecikme eşiği aşıldı ({stats.avg_wall_ms:.0f}ms)")

        # durum geçişi
        if candidate.rejection_reasons and candidate.label != "A":
            candidate.state = RepairState.GATE_FAILED
        else:
            candidate.state = RepairState.BUILT
        return candidate

    # -- karşılaştırma ----------------------------------------------------------

    def compare(self, experiment: RepairExperiment) -> dict[str, Any]:
        rows = []
        for cand in experiment.candidates:
            rows.append(
                {
                    "candidate_id": cand.candidate_id,
                    "label": cand.label,
                    "description": cand.description,
                    "diff": cand.diff,
                    "controls": [c.display_name for c in cand.controls],
                    "build": cand.gate_results.get("build", "—"),
                    "security_pretest": cand.gate_results.get("security_pretest", "—"),
                    "utility": cand.measurements.get("utility", "—"),
                    "avg_wall_ms": cand.measurements.get("avg_wall_ms", "—"),
                    "state": cand.state.value,
                    "rejection_reasons": cand.rejection_reasons,
                    "rollback": cand.rollback,
                }
            )
        return {
            "experiment_id": experiment.experiment_id,
            "finding_id": experiment.finding_id,
            "baseline_revision": experiment.baseline_revision,
            "rows": rows,
        }

    def propose_experiment(
        self,
        campaign_id: str,
        finding: Finding,
        attack_attempts: list[Attempt],
        evaluator,
        baseline_revision: str,
    ) -> RepairExperiment:
        self.evaluator = evaluator
        exp = RepairExperiment(
            campaign_id=campaign_id,
            finding_id=finding.finding_id,
            baseline_revision=baseline_revision,
        )
        cands = self.build_candidates(finding)
        for cand in cands:
            self.run_gates(cand, finding, attack_attempts)
        exp.candidates = cands
        exp.winner = self._select_winner(cands)
        return exp

    def _select_winner(self, candidates: list[RepairCandidate]) -> str | None:
        """Kapıları geçen adaylar arasından en az değişiklikli olanı seçer.

        Sıra: C (server-side, mekanik) → D (birleşik) → B (yalnızca prompt).
        A referans ölçüm olduğu için asla kazanan olmaz. B, C ve D'nin hepsi
        geçse bile mekanik olmayan B son sırada kalır.
        """
        passing = [
            c
            for c in candidates
            if c.state in (RepairState.BUILT, RepairState.VALIDATING, RepairState.VALIDATED_IN_SCOPE)
            and c.label != "A"
        ]
        if not passing:
            return None
        order = {"C": 0, "D": 1, "B": 2}
        passing.sort(key=lambda c: order.get(c.label, 9))
        return passing[0].candidate_id

    def fallback_candidate(self, exp: "RepairExperiment", exclude_id: str | None = None) -> str | None:
        """Kazanan başarısızsa sıradaki aday: D → C → B (A hariç).

        Not: Bu yöntem aday seçim kurallarını bilir; deneyi yürüten motor
        (engine) bunu çağırır ve bağımsızlık azalmasını olayla işaretler.
        """
        order = ["D", "C", "B"]
        for label in order:
            for cand in exp.candidates:
                if (
                    cand.label == label
                    and cand.state
                    in (
                        RepairState.BUILT,
                        RepairState.VALIDATING,
                        RepairState.VALIDATED_IN_SCOPE,
                    )
                    and cand.candidate_id != (exclude_id or exp.winner)
                ):
                    return cand.candidate_id
        return None
