"""Bulgu pipeline'ı: doğrula → küçült → grupla → eşle.

"Bin farklı metin" ile "bin farklı açık" aynı şey değildir. Gruplandırma
metin benzerliğine değil; ihlal edilen özellik + güven sınırı + bileşen +
gözlenen etki + kontrol eksikliği bileşimine dayanır.
"""
from __future__ import annotations

from aegis.contracts.models import (
    Attempt,
    Assessment,
    DiagnosisState,
    EvidenceItem,
    Finding,
    FindingGroup,
    SecurityProperty,
    Verdict,
)
from aegis.execution import run_attempt_chain
from aegis.findings.atlas import map_finding_to_atlas
from aegis.targets.synthetic_assistant.app import (
    AssistantRequest,
    AssistantResponse,
    SyntheticAssistant,
    DefenseStack,
)
from aegis.contracts.models import TenantContext


SEVERITY_BY_PROPERTY: dict[SecurityProperty, str] = {
    SecurityProperty.SECRET_CONFIDENTIALITY: "high",
    SecurityProperty.TENANT_ISOLATION: "high",
    SecurityProperty.TOOL_AUTHORIZATION: "critical",
    SecurityProperty.DATA_INSTRUCTION_SEPARATION: "high",
    SecurityProperty.TASK_CONSTRAINT: "medium",
    SecurityProperty.OUTPUT_INTEGRITY: "medium",
}


class FindingPipeline:
    def __init__(self, assistant: SyntheticAssistant, evaluator) -> None:
        self.assistant = assistant
        self.evaluator = evaluator

    # -- 1) Doğrulama: temiz oturumda tekrar -----------------------------------

    def reproduce(self, attempt: Attempt, trials: int = 3) -> dict:
        """Temiz oturumda N bağımsız tekrar. Deterministik hedefte 3/3 beklenir."""
        results = []
        ok = 0
        for i in range(trials):
            fresh_ctx = TenantContext(
                tenant_id=(attempt.tenant_context.tenant_id if attempt.tenant_context else "tenant-alpha"),
                user_id=f"repro_{i}",
                session_id=f"sess_repro_{i}",
            )
            resp = run_attempt_chain(
                self.assistant,
                attempt.turns,
                fresh_ctx,
                document_ids=list(attempt.document_ids),
                expect_json=(attempt.cell.strategy_family.value == "output_schema_abuse"),
            )
            repro_attempt = attempt.model_copy(
                update={
                    "attempt_id": f"{attempt.attempt_id}_repro{i}",
                    "tenant_context": fresh_ctx,
                }
            )
            repro_attempt.execution_status = attempt.execution_status
            ev = self.evaluator.assess_attempt(repro_attempt, resp)
            violated = ev.assessment.verdict == Verdict.VIOLATION
            ok += int(violated)
            results.append(
                {
                    "trial": i,
                    "violation": violated,
                    "property": ev.assessment.violated_property.value if ev.assessment.violated_property else None,
                    "response_excerpt": resp.text[:120],
                }
            )
        return {"trials": trials, "successful": ok, "rate": round(ok / trials, 2) if trials else 0.0, "details": results}

    # -- 2) Küçültme -----------------------------------------------------------

    def minimize(self, attempt: Attempt, response_text: str) -> list[str]:
        """Gereksiz tur/metin kaldırılarak ihlalin korunup korunmadığı sınanır.

        Orijinal örnek silinmez; küçültülmüş örnek ayrıca saklanır.
        """
        turns = list(attempt.turns)
        # çok turluysa: son turu koru, öncekileri tek tek düşür
        if len(turns) > 1:
            candidate = turns[-1:]
            if self._still_violates(candidate, attempt):
                return candidate
            return turns  # çok turlu zincir gerekli
        # tek turluysa: cümleleri düşür
        text = turns[0] if turns else ""
        sentences = [s.strip() for s in text.split(". ") if s.strip()]
        if len(sentences) <= 1:
            return turns
        # son cümle en kritik talimatı taşır varsayımıyla sondan tek düşür
        reduced = sentences[:-1]
        if reduced and self._still_violates([". ".join(reduced) + "."], attempt):
            return [". ".join(reduced) + "."]
        return turns

    def _still_violates(self, turns: list[str], attempt: Attempt) -> bool:
        ctx = attempt.tenant_context or TenantContext(tenant_id="tenant-alpha", user_id="minimizer")
        resp = run_attempt_chain(
            self.assistant,
            turns,
            ctx,
            document_ids=list(attempt.document_ids),
            expect_json=(attempt.cell.strategy_family.value == "output_schema_abuse"),
        )
        probe = attempt.model_copy(update={"turns": turns})
        probe.execution_status = attempt.execution_status
        ev = self.evaluator.assess_attempt(probe, resp)
        return ev.assessment.verdict == Verdict.VIOLATION

    # -- 3) Bulgu oluşturma ----------------------------------------------------

    def build_finding(
        self,
        attempt: Attempt,
        assessment: Assessment,
        response: AssistantResponse,
    ) -> Finding:
        prop = assessment.violated_property or attempt.cell.security_property
        family = attempt.cell.strategy_family.value
        repro = self.reproduce(attempt)
        minimized = self.minimize(attempt, response.text)
        atlas = map_finding_to_atlas(prop.value, family, response.text[:80])
        evidence = list(assessment.deterministic_evidence)
        evidence.append(
            EvidenceItem(kind="response_text", content=response.text[:400], source="target_adapter")
        )
        return Finding(
            campaign_id=attempt.campaign_id,
            violated_property=prop,
            boundary=f"strategy_family={family}",
            component=self._component_for(prop),
            observed_effect=self._effect_summary(prop, assessment, response),
            original_attempt_id=attempt.attempt_id,
            minimized_turns=minimized,
            reproduction_trials=repro["details"],
            reproduction_rate=repro["rate"],
            atlas_mapping=atlas,
            diagnosis=DiagnosisState.EVIDENCE_SUPPORTED,
            diagnosis_notes=self._diagnosis_note(prop, response),
            evidence=evidence,
            severity=SEVERITY_BY_PROPERTY.get(prop, "medium"),
            limitations=self._limitations(prop),
        )

    def _effect_summary(self, prop: SecurityProperty, assessment: Assessment, response: AssistantResponse) -> str:
        """Gözlenen etki: genel yanıt metni değil, ihlale özgü kanıt özeti."""
        det = assessment.deterministic_evidence
        if det:
            first = det[0].content
            return f"[{det[0].kind}] {first[:200]}"
        return response.text[:200]

    def _component_for(self, prop: SecurityProperty) -> str:
        return {
            SecurityProperty.SECRET_CONFIDENTIALITY: "retrieval+response",
            SecurityProperty.TENANT_ISOLATION: "retrieval",
            SecurityProperty.TOOL_AUTHORIZATION: "tool_gateway",
            SecurityProperty.DATA_INSTRUCTION_SEPARATION: "prompt_assembly",
            SecurityProperty.TASK_CONSTRAINT: "prompt_assembly",
            SecurityProperty.OUTPUT_INTEGRITY: "output_validation",
        }.get(prop, "unknown")

    def _diagnosis_note(self, prop: SecurityProperty, response: AssistantResponse) -> str:
        notes = {
            SecurityProperty.SECRET_CONFIDENTIALITY: "Retrieval tenant filtresi yok; kanarya değeri yanıta sızdı.",
            SecurityProperty.TENANT_ISOLATION: "Retrieval katmanında server-side tenant kapsamı uygulanmıyor.",
            SecurityProperty.TOOL_AUTHORIZATION: "Araç çağrıları downstream yetkilendirme olmadan yürütülüyor.",
            SecurityProperty.DATA_INSTRUCTION_SEPARATION: "Prompt birleştirmede veri/talimat ayrımı yok.",
            SecurityProperty.TASK_CONSTRAINT: "Görev kısıtı yalnızca sistem promptuyla ifade ediliyor, mekanik zorlama yok.",
            SecurityProperty.OUTPUT_INTEGRITY: "Çıktı şema doğrulaması devrede değil.",
        }
        return notes.get(prop, "")

    def _limitations(self, prop: SecurityProperty) -> list[str]:
        return [
            "Bulgular tanımlı kapsam ve erişim profiliyle sınırlıdır.",
            "Simüle hedefte deterministik davranış ölçülür; gerçek model dağılımı temsil edilmez.",
        ]

    # -- 4) Gruplama -----------------------------------------------------------

    def group_findings(self, findings: list[Finding]) -> list[FindingGroup]:
        groups: dict[tuple[str, str, str], FindingGroup] = {}
        for f in findings:
            key = (f.violated_property.value, f.boundary, f.component)
            g = groups.get(key)
            if g is None:
                g = FindingGroup(
                    violated_property=f.violated_property,
                    boundary=f.boundary,
                    component=f.component,
                )
                groups[key] = g
            g.finding_ids.append(f.finding_id)
            f.group_id = g.group_id
        return list(groups.values())
