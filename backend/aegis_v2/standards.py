"""Standards crosswalks are supporting evidence, never compliance certifications."""
from __future__ import annotations

from .defenses import CONTROLS

AI_RMF = "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf"
GENAI = "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf"
REQUIREMENTS = {
    "GOVERN 1.6": ("AI system inventory", "The versioned target and campaign record identify the tested application.", "GOVERN"),
    "MAP 1.1": ("Deployment and intended-use context", "The target task policy, tenant, capabilities, and writable surfaces establish the experiment context.", "MAP"),
    "MAP 5.1": ("Characterize impact likelihood and magnitude", "Finding impact and measured reproduction are recorded; broader operational likelihood needs owner review.", "MAP"),
    "MEASURE 2.7": ("Security and resilience evaluation", "Recorded attacks, assessments, and paired verification provide scoped security evidence.", "MEASURE"),
    "MEASURE 2.10": ("Privacy risk evaluation", "Confidential marker disclosure and registered PII controls provide partial privacy evidence.", "MEASURE"),
    "MEASURE 2.13": ("Effectiveness of evaluation methods", "Valid denominators, inconclusive counts, diversity, and confidence intervals document evaluation limits.", "MEASURE"),
    "MANAGE 1.3": ("Develop and document risk responses", "Candidate configurations, rejected alternatives, deployment steps, and rollback records support a risk response.", "MANAGE"),
    "MANAGE 4.1": ("Post-deployment monitoring and response plans", "The remediation plan defines monitoring and rollback criteria; production monitoring remains an operator responsibility.", "MANAGE"),
}


def finding_crosswalk(finding):
    ids = ["MAP 5.1", "MEASURE 2.7", "MANAGE 1.3"]
    if finding["property"] in {"secret_confidentiality", "tenant_isolation", "session_isolation"}:
        ids.append("MEASURE 2.10")
    rows = [{"framework": "NIST AI RMF 1.0", "id": identifier, "name": REQUIREMENTS[identifier][0],
             "function": REQUIREMENTS[identifier][2], "rationale": REQUIREMENTS[identifier][1], "source": AI_RMF,
             "status": "supporting_evidence", "evidence_refs": [finding["id"], finding["original_attempt_id"]]} for identifier in ids]
    action = "MS-2.10-001" if finding["property"] in {"secret_confidentiality", "session_isolation"} else "MS-2.7-001"
    rows.append({"framework": "NIST Generative AI Profile (AI 600-1)", "id": action,
                 "name": "Confidential information red-teaming" if action == "MS-2.10-001" else "Security vulnerability assessment",
                 "function": "MEASURE", "rationale": "This finding contributes evidence for the declared security boundary; other risks in the action remain outside scope.",
                 "source": GENAI, "status": "supporting_evidence", "evidence_refs": [finding["id"]]})
    return rows


def campaign_crosswalk(campaign, findings, verification):
    rows = []
    for identifier, (name, rationale, function) in REQUIREMENTS.items():
        evidence = [campaign["id"]]
        status = "supporting_evidence"
        if identifier == "MEASURE 2.7":
            evidence += [v["id"] for v in verification]
            if not verification:
                status = "not_evaluated"
        if identifier == "MEASURE 2.10" and not any(f["property"] in {"secret_confidentiality", "tenant_isolation", "session_isolation"} for f in findings):
            status = "outside_tested_scope"
        if identifier == "MANAGE 4.1":
            status = "deployment_plan_required"
        rows.append({"framework": "NIST AI RMF 1.0", "id": identifier, "name": name, "function": function,
                     "rationale": rationale, "source": AI_RMF, "status": status, "evidence_refs": evidence})
    seen = {(r["framework"], r["id"]) for r in rows}
    for finding in findings:
        for row in finding_crosswalk(finding):
            if (row["framework"], row["id"]) not in seen:
                seen.add((row["framework"], row["id"]))
                rows.append(row)
    return {"disclaimer": "A scoped evidence crosswalk is not a NIST compliance audit or certification.", "rows": rows,
            "unassessed_domains": ["Organizational governance effectiveness", "Legal compliance", "Fairness and bias", "Environmental impact", "Production incident-response execution"]}


def remediation_plan(finding, changes):
    controls = [{"id": name, **CONTROLS[name]} for name, enabled in changes.items() if enabled]
    diagnoses = {
        "tool_authorization": "A model-requested tool effect reached the gateway without a trusted permission or tenant-owned destination. Model role claims and well-formed JSON do not grant authority.",
        "tenant_isolation": "The retrieval candidate set included documents owned by a different tenant. The access decision must precede ranking and context construction.",
        "secret_confidentiality": "A server-owned marker from protected data reached the public response. Review both data access and every response/effect disclosure boundary.",
        "output_integrity": "The target returned data outside the declared response contract. A downstream consumer must receive a validated contract or an explicit application rejection.",
        "data_instruction_separation": "Untrusted reference content crossed the instruction boundary. Prompt envelopes reduce confusion; production tool effects still require deterministic authorization.",
        "task_constraint": "The target followed instructions outside the declared task policy. Test prompt changes and input defenses together with legitimate-use regressions.",
        "session_isolation": "Protected information crossed the declared session boundary. Confirm persistence, identity binding, and data ownership in the actual application.",
    }
    return {"boundary": finding["boundary"], "observed_effect": finding["effect"],
            "diagnosis": diagnoses.get(finding["property"], "Insufficient enforcement was observed at " + finding["boundary"]),
            "diagnosis_status": "Evidence-based intervention hypothesis; verify the production root cause separately.",
            "evidence_refs": [finding["id"], finding["original_attempt_id"]], "controls": controls,
            "nist": finding_crosswalk(finding), "atlas": finding["atlas"],
            "deployment": {"scope": "Registered AEGIS application adapter", "owner": "Application owner",
                "steps": ["Review the frozen target revision and configuration diff.", "Apply the chosen controls to the corresponding application boundaries.",
                          "Repeat the same security and normal-use suites in the destination environment.", "Enable monitoring for blocked requests, tool denials, and utility regression."] +
                         [c["name"] + ": " + step for c in controls for step in c["deployment_steps"]],
                "rollback_triggers": ["Normal-use pass rate falls below the campaign floor.", "Legitimate requests exceed the false-block threshold.", "Target startup or connectivity fails."],
                "external_application_note": "This artifact does not automatically patch an unrelated remote application's internal retrieval or tools."},
            "residual_risks": sorted({lim for c in controls for lim in c["limitations"]})}
