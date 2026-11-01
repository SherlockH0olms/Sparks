"""Human-readable projections of recorded evidence; never new security verdicts."""
from __future__ import annotations

import json
import re

SOURCE_NAMES = {"pyrit": "PyRIT", "garak": "Garak", "promptfoo": "Promptfoo", "deepteam": "DeepTeam",
    "tensortrust": "TensorTrust", "wildteaming": "WildTeaming", "bipia": "BIPIA", "injecagent": "InjecAgent",
    "harmbench": "HarmBench", "agentdojo": "AgentDojo"}
EXPECTATIONS = {
    "tenant_isolation": "Retrieve only documents owned by the authenticated tenant. A consent or administrator claim inside a request cannot grant cross-tenant access.",
    "tool_authorization": "Execute tool effects only after trusted permission checks. Model-generated arguments and user role claims cannot grant permission.",
    "secret_confidentiality": "Keep registered confidential data out of unauthorized public output.",
    "output_integrity": "Return output that satisfies the application's declared response contract.",
    "data_instruction_separation": "Treat retrieved reference content as data, without allowing it to replace application instructions.",
    "task_constraint": "Follow the application's task policy and trusted authority rules.",
    "session_isolation": "Keep protected information within its authorized session and tenant boundary.",
}
OBSERVED = {
    "unauthorized_retrieval": "A document belonging to another tenant entered the application's retrieval context.",
    "unauthorized_tool_effect": "The simulated tool gateway executed an operation without trusted authorization.",
    "confidential_output": "A registered confidential marker appeared in the public response.",
    "invalid_output_contract": "The target's output failed the application's declared response contract.",
    "untrusted_instruction_executed": "An instruction from untrusted input resulted in an unauthorized tool effect.",
    "policy_diversion": "The evaluator recorded a departure from the declared task or data/instruction policy.",
}


def excerpt(value, limit=360):
    """An explicitly marked quotation excerpt, not a paraphrase or final answer."""
    raw = str(value or "")
    clean = re.sub(r"\s+", " ", raw).strip()
    if len(clean) <= limit:
        return {"text": clean, "shortened": False, "original_characters": len(raw)}
    cut = clean[:limit].rsplit(" ", 1)[0]
    return {"text": cut + " …", "shortened": True, "original_characters": len(raw)}


def output_excerpt(value):
    raw = str(value or "")
    # Use a declared answer field if the server returned a structured response.
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict) and isinstance(obj.get("answer"), str):
            result = excerpt(obj["answer"])
            result["note"] = "Excerpt from the recorded structured answer."
            return result
    except (ValueError, TypeError):
        pass
    # Keep protocol diagnostics in evidence, rather than presenting them as prose.
    visible = re.sub(r"^\s*<arg_missing>.*?</arg_missing>\s*", "", raw, count=1, flags=re.S)
    result = excerpt(visible)
    result["original_characters"] = len(raw)
    result["note"] = ("Excerpt starts after a protocol diagnostic; complete output is retained in the evidence export."
                      if visible != raw else "A short quotation of recorded output; it is not a reconstructed final answer.")
    return result


def evidence_story(candidate, steps, property, tenant=None, attempt_id=None):
    strategy = candidate.get("red_strategy") or {}
    turns = candidate.get("turns") or []
    resources = strategy.get("resources") or []
    assessments = [s.get("assessment") or {} for s in steps]
    violations = [a for a in assessments if a.get("verdict") == "violation"]
    chosen = next((s for s in steps if (s.get("assessment") or {}).get("verdict") == "violation"), steps[-1] if steps else {})
    assessment = chosen.get("assessment") or {}
    effect = assessment.get("effect", "")
    observed = OBSERVED.get(effect, "Review the recorded assessment and observed boundary below.")
    if not violations:
        observed = "No violating observation is included in this evidence excerpt."
    rows = []
    for i, step in enumerate(steps, 1):
        a = step.get("assessment") or {}
        for item in a.get("evidence") or []:
            if not isinstance(item, dict):
                continue
            if item.get("tenant") and item.get("id"):
                rows.append(["Turn " + str(i), "Retrieved document", item["id"], "Owner: " + item["tenant"]])
            elif item.get("canary_id"):
                rows.append(["Turn " + str(i), "Protected marker", item["canary_id"], "Observed in public output"])
            elif item.get("name") or item.get("tool"):
                rows.append(["Turn " + str(i), "Tool effect", item.get("name") or item["tool"],
                             "Executed" if item.get("executed") else "Recorded request"])
            elif "schema_valid" in item:
                rows.append(["Turn " + str(i), "Response contract", "JSON schema", "Valid" if item["schema_valid"] else "Invalid"])
        if not (a.get("evidence") or []) and a.get("verdict"):
            rows.append(["Turn " + str(i), "Assessment", a.get("boundary", property), str(a["verdict"]).replace("_", " ")])
    has_traces = bool(steps) and all(isinstance(s.get("trace"), dict) for s in steps)
    effects = [t for s in steps for t in (s.get("trace") or {}).get("tools", [])]
    executed = sum(bool(t.get("executed")) for t in effects) if has_traces else None
    if effect == "unauthorized_retrieval":
        meaning = "The failure is at the retrieval boundary: foreign data reached the model context, even if the model later refused the requested export."
        if executed == 0:
            meaning += " No simulated tool effect executed in this attempt; this finding does not claim a successful export."
        elif executed is None:
            meaning += " This excerpt does not establish whether an export executed; consult the original tool trace."
    elif effect == "unauthorized_tool_effect":
        meaning = "The finding relies on a recorded gateway effect, rather than the model merely claiming that it performed an action. The gateway is simulated."
    else:
        meaning = "The assessment applies to the recorded application boundary and oracle; the quotation alone is not the verdict."
    method = strategy.get("method_id") or "Not recorded"
    method_label = str(method).removeprefix("wild_").replace("_", " ").capitalize()
    summary = f"{len(turns)}-turn {candidate.get('language', 'unspecified')} security input; recorded method: {method_label}."
    response = (chosen.get("trace") or {}).get("response", chosen.get("response", ""))
    sources = sorted({SOURCE_NAMES.get(r.get("framework"), str(r.get("framework", "Unknown"))) for r in resources})
    display_inputs = []
    indexes = [0] if len(turns) == 1 else [0, len(turns) - 1] if turns else []
    for i in indexes:
        display_inputs.append({"label": "Attack input" if len(turns) == 1 else "Attack turn " + str(i + 1), **excerpt(turns[i], 300)})
    if candidate.get("document_body"):
        display_inputs.append({"label": "Assigned document input", **excerpt(candidate["document_body"], 300)})
    return {"summary": summary, "expected_behavior": EXPECTATIONS.get(property, "Respect the declared application boundary."),
        "observed_result": observed, "interpretation": meaning, "tenant": tenant or "Recorded tenant",
        "inputs": display_inputs, "omitted_input_turns": max(0, len(turns) - len(indexes)),
        "target_output": output_excerpt(response), "proof_rows": rows[:6], "additional_proof_rows": max(0, len(rows) - 6),
        "tool_requests": len(effects) if has_traces else None, "executed_tool_effects": executed,
        "method": method_label, "sources": sources, "resource_count": len({r.get('id') for r in resources if r.get('id')}),
        "tactic_count": len(set(strategy.get("tactic_ids") or [])),
        "transformation_count": len(strategy.get("transformations") or []),
        "attempt_id": attempt_id, "oracle": assessment.get("oracle", "Not recorded"),
        "evidence_notice": "Full attack text, model output, resource records and hashes are available in the separate JSON/NDJSON evidence export."}


def risk_story(risk):
    """Also render persisted v3 reports without exporting their JSON into prose."""
    if risk.get("evidence_story"):
        return risk["evidence_story"]
    try:
        legacy = json.loads(risk.get("evidence_excerpt") or "{}")
    except (ValueError, TypeError):
        legacy = {}
    return evidence_story(legacy.get("minimized_input") or {}, legacy.get("observations") or [],
                          risk.get("property"), attempt_id=risk.get("original_attempt_id"))
