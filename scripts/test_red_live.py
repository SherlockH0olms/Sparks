"""Run real Red generation against campaign cells; never calls a local target or Judge."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import statistics
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from aegis_v2.budget import Budget
from aegis_v2.config import Settings
from aegis_v2.contracts import CampaignCreate, ResourceLimits
from aegis_v2.providers import BudgetedChat, ChatClient, ProviderError
from aegis_v2.red import InvalidCandidate, RedGenerator
from aegis_v2.red_library import installed_library
from aegis_v2.scenarios import build_cells, target_template
from aegis_v2.storage import Store

PLANS = [
    ("direct_injection", "task_constraint", "tr"),
    ("indirect_injection", "data_instruction_separation", "tr"),
    ("authority_spoofing", "secret_confidentiality", "en"),
    ("multi_turn_manipulation", "task_constraint", "az"),
    ("encoding_evasion", "task_constraint", "en"),
    ("tenant_probe", "tenant_isolation", "tr"),
    ("tool_misuse", "tool_authorization", "az"),
    ("schema_abuse", "output_integrity", "en"),
]


class CaptureClient(ChatClient):
    def __init__(self, settings):
        super().__init__(settings)
        self.calls = []

    def chat(self, messages, tools=None):
        result = super().chat(messages, tools)
        self.calls.append({"message_roles": [m["role"] for m in messages],
            "tool_results": [json.loads(m["content"]) for m in messages if m["role"] == "tool"],
            "tools_sent": tools is not None, "finish_reason": result.finish_reason,
            "tool_names": [t.get("function", {}).get("name") for t in result.tool_calls],
            "tool_calls": deepcopy(result.tool_calls),
            "usage": deepcopy(result.usage), "provider_request_id": result.provider_request_id})
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--families", nargs="+", choices=[p[0] for p in PLANS])
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--method", choices=list(installed_library().methods), help="Explicit method; use with one compatible family")
    parser.add_argument("--tool-mode", choices=["auto", "native", "json"])
    parser.add_argument("--output", type=Path, default=ROOT / ".runtime" / "live-red-regression.json")
    args = parser.parse_args()
    if args.workers < 1 or args.rounds < 1:
        parser.error("workers and rounds must be positive")
    cfg = Settings.load().red
    if args.tool_mode:
        cfg = replace(cfg, tool_mode=args.tool_mode)
    if cfg.issues():
        raise SystemExit("Red configuration is incomplete: " + "; ".join(cfg.issues()))
    scope = CampaignCreate(target_id="generation-audit-only")
    snapshot = target_template("http://localhost/v1", "NOT_CONNECTED_REVIEW_ONLY")
    cells = build_cells(scope, snapshot)
    plans = [p for p in PLANS if not args.families or p[0] in args.families]
    run_id = uuid.uuid4().hex[:12]
    runtime = ROOT / ".runtime" / ("live-red-regression-" + run_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    started = time.perf_counter()

    def run_case(plan, round_index, observations):
        family, prop, language = plan
        cell = next(c for c in cells if (c["family"], c["property"], c["language"]) == plan)
        folder = runtime / (family + "_" + str(round_index))
        store = Store("sqlite:///" + str(folder / "audit.db"), "", folder)
        budget = Budget.create(store, family, "audit", ResourceLimits())
        client = CaptureClient(cfg)
        red = RedGenerator(BudgetedChat(store, "audit", client, "generator_calls"))
        record = {"family": family, "property": prop, "language": language, "round": round_index,
            "explicit_method": args.method,
            "cell_id": cell["id"], "required_turns": cell["required_turns"],
            "cell_source": "build_cells(CampaignCreate defaults, target_template)",
            "target_calls": 0, "judge_calls": 0}
        case_started = time.perf_counter()
        try:
            candidate = red.generate(cell, snapshot, scope.model_dump(mode="json"), observations, budget,
                                     "discovery", "live_" + run_id + "_" + family + "_" + str(round_index), method_id=args.method)
            record.update(valid=True, candidate=candidate, actual_turns=len(candidate["turns"]))
        except (InvalidCandidate, ProviderError) as exc:
            record.update(valid=False, error=str(exc), error_type=type(exc).__name__)
        finally:
            record["seconds"] = round(time.perf_counter() - case_started, 3)
            record["calls"] = client.calls
            record["provider_calls"] = len(client.calls)
            record["native_submission"] = any("submit_attack" in call["tool_names"] for call in client.calls)
            record["inspect_then_submit"] = any("inspect_target" in call["tool_names"] for call in client.calls[:-1]) and record["native_submission"]
            record["truncated"] = any(call["finish_reason"] == "length" for call in client.calls)
            record["resources"] = budget.snapshot()["used"]
            assert record["resources"]["target_calls"] == record["resources"]["judge_calls"] == 0
            store.close()
        return record

    def save(complete=False):
        strategies = [r.get("candidate", {}).get("red_strategy", {}) for r in rows]
        methods = sorted({s["method_id"] for s in strategies if s.get("method_id")})
        transforms = [t for s in strategies for t in s.get("transformations", [])]
        result = {"run_id": run_id, "complete": complete, "provider": cfg.public(),
            "expected_cases": len(plans) * args.rounds, "finished_cases": len(rows),
            "attack_library": installed_library().summary(),
            "distinct_methods": methods, "distinct_method_count": len(methods),
            "resource_read_cases": sum(bool(s.get("resources")) for s in strategies),
            "distinct_sources_read": sorted({r["framework"] for s in strategies for r in s.get("resources", [])}),
            "distinct_tactics_read": len({t for s in strategies for t in s.get("tactic_ids", [])}),
            "tactic_composition_calls": sum(len(s.get("compositions", [])) for s in strategies),
            "distinct_tactics_composed": len({t for s in strategies for c in s.get("compositions", []) for t in c["tactic_ids"]}),
            "transformation_calls": len(transforms), "applied_transformations": sum(t["applied"] for t in transforms),
            "transformation_frameworks": sorted({t["framework"] for t in transforms}),
            "valid_candidates": sum(r["valid"] for r in rows),
            "native_submissions": sum(r["native_submission"] for r in rows),
            "inspect_then_submit_cases": sum(r["inspect_then_submit"] for r in rows),
            "target_calls": 0, "judge_calls": 0, "target_asr": None,
            "mean_generation_seconds": statistics.mean(r["seconds"] for r in rows) if rows else None,
            "sum_generation_seconds": sum(r["seconds"] for r in rows),
            "wall_seconds": round(time.perf_counter() - started, 3),
            "total_provider_calls": sum(r["provider_calls"] for r in rows),
            "results": sorted(rows, key=lambda r: (r["round"], [p[0] for p in plans].index(r["family"]))),
            "limitations": ["Candidate validity is not attack success against a target.",
                "One example per selected family/language cannot establish population success rates."]}
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    print("START " + json.dumps({"provider": cfg.public(), "cases": len(plans), "workers": args.workers}), flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for round_index in range(args.rounds):
            observations = [{"scenario": r["family"], "language": r["language"],
                "red_strategy": r["candidate"].get("red_strategy", {}),
                "prior_attack": {k: r["candidate"].get(k) for k in ("turns", "document_body", "hypothesis")}}
                for r in rows if r.get("valid")]
            futures = [pool.submit(run_case, plan, round_index, observations) for plan in plans]
            for future in as_completed(futures):
                row = future.result()
                rows.append(row)
                save()
                summary = {k: row.get(k) for k in ("family", "round", "valid", "seconds", "required_turns", "actual_turns",
                    "provider_calls", "native_submission", "inspect_then_submit", "truncated", "error")}
                summary["method"] = row.get("candidate", {}).get("red_strategy", {}).get("method_id")
                print(json.dumps(summary), flush=True)
    result = save(complete=True)
    print("SUMMARY " + json.dumps({k: v for k, v in result.items() if k not in {"results", "limitations"}}), flush=True)
    print("ARTIFACT " + str(args.output), flush=True)
    return 0 if all(r["valid"] and not r["truncated"] for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
