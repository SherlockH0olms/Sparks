"""Demo pipeline: hakaton sunumu için uçtan uca akışı CLI'dan çalıştırır.

Kullanım:
    python scripts/demo_pipeline.py            # tam akış + rapor
    python scripts/demo_pipeline.py --quiet    # yalnızca özet
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aegis.contracts.models import BudgetLimits, CampaignSpec  # noqa: E402
from aegis.core.events import EventBus  # noqa: E402
from aegis.engine import CampaignEngine  # noqa: E402
from aegis.evaluation.evaluator import IndependentEvaluator  # noqa: E402
from aegis.evaluation.oracle_vault import OracleVault  # noqa: E402
from aegis.reporting.report import ReportGenerator  # noqa: E402
from aegis.targets.synthetic_assistant import build_manifest  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="AEGIS LOOP demo pipeline")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--budget", type=int, default=300)
    parser.add_argument("--languages", nargs="*", default=["tr", "az", "en"])
    parser.add_argument("--out", default=None, help="rapor markdown çıktı dosyası")
    args = parser.parse_args()

    manifest = build_manifest()
    vault = OracleVault()
    evaluator = IndependentEvaluator(vault)
    bus = EventBus()
    spec = CampaignSpec(
        target_id=manifest.target_id,
        revisions=manifest.revisions,
        budget=BudgetLimits(target_calls=args.budget),
        languages=args.languages,
    )
    engine = CampaignEngine(spec, manifest, None, bus)
    engine.attach_evaluator(vault, evaluator)

    if not args.quiet:
        print("► Preflight + baseline + keşif + doğrulama + repair başlıyor…")
    engine.run()

    s = engine.summary()
    print("═══ AEGIS LOOP — Kampanya Özeti ═══")
    print(f"  Durum        : {s['state']}")
    print(f"  Kapsam       : {s['coverage']['coverage_pct']}% "
          f"({s['coverage']['completed']}/{s['coverage']['applicable']} hücre)")
    print(f"  Deneme       : {s['attempts']}")
    print(f"  Bulgu        : {s['findings']} (grup: {s['groups']})")
    print(f"  Deney        : {s['experiments']}")
    print(f"  Doğrulama    : {s['verification_runs']}")

    if not args.quiet:
        print("\n═══ Bulgular (özet) ═══")
        for f in engine.campaign.findings[:10]:
            atlas = ", ".join(m["technique_id"] for m in f.atlas_mapping)
            print(f"  {f.finding_id[:14]}  {f.violated_property.value:32} {f.severity:8} ATLAS: {atlas}")
        if len(engine.campaign.findings) > 10:
            print(f"  … ve {len(engine.campaign.findings) - 10} bulgu daha")

        print("\n═══ Repair Lab ═══")
        for exp in engine.experiments:
            winner = (exp.winner or "—")[:14]
            print(f"  Deney {exp.experiment_id[:14]} → kazanan: {winner}")
            for c in exp.candidates:
                pre = c.gate_results.get("security_pretest", {})
                if isinstance(pre, dict):
                    pre_s = f"{pre['violations_remaining']}/{pre['replayed']} ihlal"
                else:
                    pre_s = "—"
                rej = c.rejection_reasons[0] if c.rejection_reasons else ""
                print(f"    {c.label}: pretest={pre_s} utility={c.measurements.get('utility', '—')} "
                      f"durum={c.state.value} {('| RET: ' + rej) if rej else ''}")

        print("\n═══ Bağımsız Doğrulama ═══")
        for run in engine.verification_runs:
            bits = []
            for suite, m in run.suites.items():
                v = m.get("violations", m.get("utility"))
                bits.append(f"{suite}={v}")
            print(f"  {run.run_id[:14]} aday={run.candidate_id[:10]} → {run.verdict.value}  ({'; '.join(bits)})")

    reporter = ReportGenerator()
    atlas_rows: list[dict] = []
    for f in engine.campaign.findings:
        atlas_rows.extend(f.atlas_mapping)
    md = reporter.markdown(
        engine.campaign,
        engine.grid.coverage_metrics(),
        engine.groups,
        engine.experiments,
        engine.verification_runs,
        atlas_rows,
    )
    out = args.out or os.path.join(os.path.dirname(__file__), "..", "docs", "demo-report.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(f"\n► Rapor yazıldı: {out}")

    pack = reporter.build_evidence_pack(
        engine.campaign, manifest, None, engine.experiments, engine.verification_runs
    )
    pack_path = os.path.join(os.path.dirname(out), "demo-evidence-pack.json")
    with open(pack_path, "w", encoding="utf-8") as fh:
        json.dump(pack.model_dump(), fh, ensure_ascii=False, indent=2, default=str)
    print(f"► Kanıt paketi yazıldı: {pack_path}")


if __name__ == "__main__":
    main()
