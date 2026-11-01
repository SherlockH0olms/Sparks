"""Start or observe a real campaign and independently audit its exported evidence.

No attack payload, finding, remediation candidate or verdict is supplied by this
script. The campaign worker creates them through the normal application APIs.
Private evidence is held in memory; only aggregate audit results are written.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import sys
import time
import uuid
import zipfile

import httpx
from pypdf import PdfReader
from pptx import Presentation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from aegis_v2.config import Settings
from aegis_v2.contracts import CampaignCreate, attack_digest, digest


def audit(client, base, output, expected_model):
    response = client.get(base + "/evidence-pack?sensitive=true")
    response.raise_for_status()
    pack = response.json()
    campaign = pack["campaign"]
    calls = pack["calls"]
    attempts = pack["attempts"]
    experiments = pack["experiments"]
    verification = pack["verification"]
    discovery = [a for a in attempts if a["phase"] == "discovery"]
    target_calls = [c for c in calls if c["model"] == expected_model]
    red_calls = [c for c in calls if c.get("tools") and c["model"] != expected_model]
    red_tools = Counter(t["function"]["name"] for c in red_calls
                        for t in (c.get("response") or {}).get("tool_calls", []))
    manifests = []
    for call in red_calls:
        for message in call["messages"]:
            if message["role"] != "user":
                continue
            try:
                value = json.loads(message["content"])
            except (ValueError, TypeError):
                continue
            if isinstance(value, dict) and "target" in value and "scenario" in value:
                manifests.append(value["target"])
    protected = [c["value"] for c in pack["oracle"] if c["tenant"] != pack["target_snapshot"]["tenant"]]
    foreign_ids = {d["id"] for d in pack["target_snapshot"]["documents"]
                   if d["tenant"] != pack["target_snapshot"]["tenant"]}
    checks = {"campaign_completed": campaign["state"] == "completed",
              "no_fixture_provider_calls": bool(calls) and all(c["provenance"] != "fixture" for c in calls),
              "target_is_expected_model": bool(target_calls) and pack["target_snapshot"]["model"] == expected_model,
              "evidence_content_hash": digest({k: v for k, v in pack.items() if k != "content_hash"}) == pack["content_hash"],
              "all_discovery_candidates_have_source_provenance": bool(discovery) and all(a["candidate"].get("red_strategy", {}).get("method_id") for a in discovery)}
    checks["native_red_submission_observed"] = red_tools["submit_attack"] > 0
    checks["protected_data_excluded_from_red_manifest"] = bool(manifests) and all(
        not any(secret in json.dumps(m) for secret in protected)
        and not foreign_ids.intersection(d["id"] for d in m.get("own_documents", [])) for m in manifests)
    configs = []
    for experiment in experiments:
        for candidate in experiment["candidates"]:
            valid = digest({"target_revision": experiment["target_revision"],
                            "configuration": candidate["configuration"]}) == candidate["artifact"]["hash"]
            configs.append(valid)
    checks["configuration_artifacts_match_hashes"] = bool(configs) and all(configs)
    by_attempt = {a["id"]: a for a in attempts}
    checks["findings_reproduced_in_fresh_sessions"] = bool(pack["findings"]) and all(
        len({by_attempt[t["attempt_id"]]["session_id"] for t in f["reproduction"]}) == len(f["reproduction"])
        and all(t["valid"] and t["same_violation"] for t in f["reproduction"]) for f in pack["findings"])
    known = {a["candidate_digest"] for a in discovery}
    known.update(attack_digest(row["candidate"]) for e in experiments
                 for row in e.get("development_cases", []) if row.get("candidate"))
    final_cases = [row for protocol in pack.get("final_protocols", [])
                   for row in protocol["generated"] + protocol["adaptive_cases"] if row.get("candidate")]
    hashes = [attack_digest(row["candidate"]) for row in final_cases]
    strategies = [a["candidate"].get("red_strategy", {}) for a in discovery]
    strategies += [row["candidate"].get("red_strategy", {}) for e in experiments
                   for row in e.get("development_cases", []) if row.get("candidate")]
    strategies += [row["candidate"].get("red_strategy", {}) for row in final_cases]
    transformations = [t for strategy in strategies for t in strategy.get("transformations", [])]
    checks["final_cases_distinct_from_discovery_and_development"] = bool(hashes) and not known.intersection(hashes)
    checks["final_cases_are_unique_per_experiment"] = bool(final_cases) and all(
        len(values := [attack_digest(r["candidate"]) for r in p["generated"] + p["adaptive_cases"] if r.get("candidate")]) == len(set(values))
        for p in pack.get("final_protocols", []))
    checks["independent_verification_ran"] = bool(verification) and all(v["independent"] for v in verification)
    checks["remediation_validated_in_scope"] = bool(verification) and any(v["verdict"] == "validated_in_scope" for v in verification)
    by_experiment = {e["id"]: e for e in experiments}
    checks["final_verification_used_frozen_candidate"] = bool(verification) and all(
        v["candidate_id"] == by_experiment[v["experiment_id"]]["winner"]
        and v["candidate_hash"] == by_experiment[v["experiment_id"]]["winner_hash"]
        and by_experiment[v["experiment_id"]]["frozen_at"] < v["closed_at"] for v in verification)

    downloads = [("report?format=html", "aegis-report.html"),
                 ("report?format=markdown", "aegis-report.md"),
                 ("report?format=pdf", "aegis-report.pdf"),
                 ("report?format=pptx", "aegis-report.pptx"),
                 ("evidence.ndjson", "aegis-evidence.ndjson"),
                 ("remediation-bundle", "aegis-remediation.zip")]
    for route, name in downloads:
        value = client.get(base + "/" + route)
        value.raise_for_status()
        (output / name).write_bytes(value.content)
    result = client.get(base + "/report")
    result.raise_for_status()
    (output / "report.json").write_text(json.dumps(result.json(), indent=2), encoding="utf-8")
    pdf = PdfReader(output / "aegis-report.pdf")
    pdf_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    deck = Presentation(output / "aegis-report.pptx")
    deck_text = "\n".join(shape.text for slide in deck.slides for shape in slide.shapes if shape.has_text_frame)
    checks["pdf_has_standards_and_rollback"] = all(x in pdf_text for x in ("NIST", "MITRE", "Rollback"))
    checks["powerpoint_has_standards_and_rollback"] = all(x in deck_text for x in ("NIST", "MITRE", "Rollback"))
    lines = (output / "aegis-evidence.ndjson").read_bytes().splitlines(keepends=True)
    trailer = json.loads(lines[-1])
    checks["ndjson_sha256"] = hashlib.sha256(b"".join(lines[:-1])).hexdigest() == trailer["sha256"]
    counts = Counter(json.loads(line)["kind"] for line in lines[1:-1])
    checks["ndjson_record_counts"] = dict(counts) == trailer["counts"]
    with zipfile.ZipFile(output / "aegis-remediation.zip") as archive:
        manifest = json.loads(archive.read("manifest.json"))
        checks["remediation_bundle_sha256"] = bool(manifest["files"]) and all(
            hashlib.sha256(archive.read(name)).hexdigest() == sha for name, sha in manifest["files"].items())
    events = client.get(base + "/events?once=true")
    events.raise_for_status()
    controls = [json.loads(line[6:])["payload"] for line in events.text.splitlines()
                if line.startswith("data: ") and json.loads(line[6:])["kind"] == "control_requested"]
    checks["no_operator_intervention_after_start"] = bool(controls) and all(x["action"] == "start" for x in controls)
    target_effects = [t for a in attempts for step in a["steps"] for t in step["trace"].get("tools", [])]
    protocol_events = [event for a in attempts for step in a["steps"]
                       for event in step["trace"].get("defense_events", []) if event["control"] == "tool_protocol"]
    results = {"campaign_id": campaign["id"], "target_model": expected_model, "state": campaign["state"],
               "baseline": campaign["baseline"], "coverage": campaign["coverage"],
               "red_diversity": campaign["red_diversity"], "checks": checks,
               "discovery_valid": sum(a["execution_status"] == "completed" and a["assessment"]["verdict"] in {"violation", "no_violation_observed"} for a in discovery),
               "discovery_violations": sum(a["assessment"]["verdict"] == "violation" for a in discovery),
               "native_red_tools": dict(red_tools), "real_target_calls": len(target_calls),
               "framework_sources_read": sorted({r["framework"] for strategy in strategies for r in strategy.get("resources", [])}),
               "framework_transforms_executed": {"frameworks": sorted({t["framework"] for t in transformations}),
                                                 "calls": len(transformations), "applied_to_payload": sum(t["applied"] for t in transformations)},
               "target_response_finish_reasons": dict(Counter((c.get("response") or {}).get("finish_reason", "incomplete") for c in target_calls)),
               "tool_protocol_observations": {"checked": len(protocol_events), "valid": sum(e["valid"] for e in protocol_events),
                                              "plain_text_or_invalid_envelope": sum(not e["valid"] for e in protocol_events)},
               "confirmed_findings": len(pack["findings"]), "configuration_artifacts": len(configs),
               "target_tool_effects": {"requested": len(target_effects), "executed": sum(bool(t.get("executed")) for t in target_effects),
                                       "unauthorized_executed": sum(bool(t.get("executed")) and not t.get("authorized") for t in target_effects)},
               "verification": verification, "resources": campaign["budget"]["used"],
               "pdf_pages": len(pdf.pages), "powerpoint_slides": len(deck.slides), "operator_controls": controls,
               "limitations": ["A scoped workflow test does not establish population-wide model security.",
                               "The model identifier is operator supplied; the model weight checksum is unverified.",
                               "JSON-adapter tool requests are simulated application effects, not native model-server tools.",
                               "Remediation changes the versioned AEGIS application adapter, not model weights."]}
    (output / "validated-results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps({"campaign_id": campaign["id"], "state": campaign["state"], "checks": checks,
                      "verification_verdicts": [v["verdict"] for v in verification],
                      "results": str(output / "validated-results.json")}, indent=2), flush=True)
    return 0 if all(checks.values()) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8008")
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--campaign")
    choice.add_argument("--start-tenant-test", metavar="TARGET_ID")
    parser.add_argument("--model", default="granite-4.2-8b")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    settings = Settings.load()
    args.output.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=90, headers={"Authorization": "Bearer " + settings.admin_token}, trust_env=False) as client:
        if args.start_tenant_test:
            spec = CampaignCreate(target_id=args.start_tenant_test, languages=["en"],
                properties=["tenant_isolation"], families=["tenant_probe"], minimum_tests_per_cell=1,
                max_discovery_attempts=3, reproduction_trials=3, development_fresh_cases=1,
                final_cases_per_property=2, adaptive_attempts=1, utility_repeats=1,
                remediation_profile="custom")
            headers = {"Idempotency-Key": "live-audit-" + uuid.uuid4().hex}
            created = client.post(args.api + "/api/campaigns", json=spec.model_dump(mode="json"), headers=headers)
            created.raise_for_status()
            args.campaign = created.json()["id"]
            started = client.post(args.api + "/api/campaigns/" + args.campaign + "/start", headers=headers)
            started.raise_for_status()
        base = args.api + "/api/campaigns/" + args.campaign
        (args.output / "run.json").write_text(json.dumps({"campaign_id": args.campaign, "api": args.api,
            "model": args.model, "created_by": "normal_campaign_api", "attack_payload_supplied": False}, indent=2), encoding="utf-8")
        last = None
        while True:
            response = client.get(base)
            response.raise_for_status()
            campaign = response.json()
            (args.output / "progress.json").write_text(json.dumps(campaign, indent=2), encoding="utf-8")
            current = (campaign["state"], campaign["progress"], campaign["budget"]["used"])
            if current != last:
                print(json.dumps({"campaign_id": args.campaign, "state": campaign["state"], "progress": campaign["progress"],
                                  "coverage": campaign["coverage"], "resources": campaign["budget"]["used"]}), flush=True)
                last = current
            if campaign["state"] in {"completed", "failed", "cancelled", "budget_exhausted"}:
                return audit(client, base, args.output, args.model)
            if campaign["state"] == "paused":
                print(json.dumps({"paused": campaign["error"], "checkpoint": campaign["checkpoint"]}), flush=True)
                return 2
            if args.once:
                return 2
            time.sleep(15)


if __name__ == "__main__":
    raise SystemExit(main())
