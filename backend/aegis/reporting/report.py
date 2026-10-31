"""Kanıtlardan rapor üretimi: önce/sonra, ATLAS, sınırlamalar, kalan risk.

Rapor; yönetici özeti, teknik bulgular, ATLAS eşlemeleri, düzeltme
deneyleri, önce/sonra metrikleri, test edilmeyen alanlar ve kalan risk
bölümlerini içerir. Ölçüm olmayan alan için uydurma değer kullanılmaz.
"""
from __future__ import annotations

import html as _html
from typing import Any

from aegis.contracts.models import (
    Attempt,
    EvidencePack,
    Finding,
    RepairExperiment,
    VerificationRun,
)


class ReportGenerator:
    def build_evidence_pack(
        self,
        campaign,
        manifest,
        policy,
        experiments: list[RepairExperiment],
        verification_runs: list[VerificationRun],
    ) -> EvidencePack:
        assessments = []
        for att in campaign.attempts:
            # verdict'ler assessment üzerinden üretilmişti; burada özet paketlenir
            assessments.append(
                {
                    "attempt_id": att.attempt_id,
                    "verdict": att.verdict.value if att.verdict else None,
                }
            )
        return EvidencePack(
            campaign_id=campaign.spec.campaign_id,
            target_manifest=manifest,
            policy=policy,
            attempts=campaign.attempts,
            findings=campaign.findings,
            repair_experiments=experiments,
            verification_runs=verification_runs,
            limitations=[
                "Bulgular tanımlı kapsam, erişim profili ve sabit sürümlerle sınırlıdır.",
                "Hedef simüle bir LLM uygulamasıdır; gerçek model dağılımı temsil edilmez.",
                "Kapsam metriği, kampanya başında sabitlenen uygulanabilir hücrelere göredir.",
            ],
        )

    # -- Markdown --------------------------------------------------------------

    def markdown(
        self,
        campaign,
        coverage_metrics: dict[str, Any],
        groups: list[Any],
        experiments: list[RepairExperiment],
        verification_runs: list[VerificationRun],
        atlas_rows: list[dict[str, str]],
    ) -> str:
        findings = campaign.findings
        distinct_props = sorted({f.violated_property.value for f in findings})
        lines: list[str] = []
        lines.append(f"# AEGIS LOOP — Güvenlik Değerlendirme Raporu")
        lines.append("")
        lines.append(f"**Kampanya:** `{campaign.spec.campaign_id}`")
        lines.append(f"**Durum:** {campaign.state.value}")
        lines.append(f"**Hedef:** {campaign.spec.target_id} @ {campaign.spec.revisions.combined()}")
        lines.append("")

        lines.append("## 1. Yönetici Özeti")
        lines.append("")
        lines.append(f"- Uygulanabilir kapsam hücresi: **{coverage_metrics['applicable']}** "
                     f"(toplam {coverage_metrics['total_cells']}, uygulanamaz {coverage_metrics['not_applicable']})")
        lines.append(f"- Tamamlanan kapsam: **{coverage_metrics['coverage_pct']}%** "
                     f"({coverage_metrics['completed']}/{coverage_metrics['applicable']} hücre)")
        lines.append(f"- Farklı doğrulanmış bulgu grubu: **{len(groups)}**")
        lines.append(f"- Farklı ihlal edilen güvenlik özelliği: **{len(distinct_props)}**")
        if verification_runs:
            passed = [v for v in verification_runs if v.verdict and v.verdict.value == "pass"]
            lines.append(f"- Doğrulanan düzeltme: **{len(passed)}/{len(verification_runs)}** aday bağımsız süitten geçti")
        lines.append("")

        lines.append("## 2. Kapsam")
        lines.append("")
        lines.append("| Metrik | Değer |")
        lines.append("|---|---|")
        for k, v in coverage_metrics.items():
            lines.append(f"| {k} | {v} |")
        lines.append("")

        lines.append("## 3. Teknik Bulgular")
        lines.append("")
        for f in findings:
            lines.append(f"### {f.finding_id} — {f.violated_property.value} ({f.severity})")
            lines.append("")
            lines.append(f"- **Bileşen:** {f.component}")
            lines.append(f"- **Gözlenen etki:** {f.observed_effect[:160]}")
            lines.append(f"- **Tekrar üretim:** {f.reproduction_rate:.0%} (temiz oturum)")
            lines.append(f"- **Teşhis:** {f.diagnosis.value}")
            lines.append(f"- **ATLAS:** " + (", ".join(m["technique_id"] for m in f.atlas_mapping) or "yok"))
            lines.append("")
        if not findings:
            lines.append("_Doğrulanmış bulgu yok (tanımlı kapsamda)._")
            lines.append("")

        lines.append("## 4. MITRE ATLAS Eşlemeleri")
        lines.append("")
        lines.append("| Teknik | Ad | Gerekçe |")
        lines.append("|---|---|---|")
        for row in atlas_rows:
            just = row.get("justification", "")[:120]
            lines.append(f"| {row['technique_id']} | {row['name']} | {_escape_md(just)} |")
        lines.append("")

        lines.append("## 5. Düzeltme Deneyleri")
        lines.append("")
        for exp in experiments:
            lines.append(f"### Deney {exp.experiment_id} (bulgu {exp.finding_id})")
            lines.append("")
            lines.append("| Aday | Değişiklik | Ön test | Utility | Durum | Karar |")
            lines.append("|---|---|---|---|---|---|")
            for cand in exp.candidates:
                pre = cand.gate_results.get("security_pretest", "—")
                if isinstance(pre, dict):
                    pre = f"{pre['violations_remaining']}/{pre['replayed']} ihlal"
                util = cand.measurements.get("utility", "—")
                decision = "REDDEDİLDİ: " + "; ".join(cand.rejection_reasons) if cand.rejection_reasons else ("aday" if cand.state.value in ("built", "validating", "validated_in_scope") else cand.state.value)
                lines.append(f"| {cand.label} | {cand.controls[0].display_name if cand.controls else 'yok'} | {pre} | {util} | {cand.state.value} | {decision} |")
            lines.append("")

        lines.append("## 6. Bağımsız Doğrulama (önce/sonra)")
        lines.append("")
        for run in verification_runs:
            lines.append(f"### {run.run_id} — aday {run.candidate_id} → **{run.verdict.value if run.verdict else '—'}**")
            lines.append("")
            lines.append("| Süit | Deneme | İhlal | ASR | Utility |")
            lines.append("|---|---|---|---|---|")
            for suite, m in run.suites.items():
                lines.append(f"| {suite} | {m.get('attempts', m.get('questions', '—'))} | {m.get('violations', '—')} | {m.get('asr', '—')} | {m.get('utility', '—')} |")
            lines.append("")

        lines.append("## 7. Test Edilmeyen Alanlar ve Kalan Risk")
        lines.append("")
        lines.append("- Kapsamı tamamlanmayan hücreler raporun kapsam bölümünde görünür.")
        lines.append("- Simüle hedef; gerçek model davranış dağılımını temsil etmez.")
        lines.append("- Kodlama kaçırma (encoding evasion) ailesi varsayılan filtrelerle sınırlıdır.")
        lines.append("")

        lines.append("## 8. Sınırlamalar")
        lines.append("")
        lines.append("- Bulgular sürüm kümesine bağlıdır: " + campaign.spec.revisions.combined())
        lines.append("- Bu rapor 'tanımlı kapsamda doğrulandı' ifadesiyle okunmalıdır.")
        lines.append("")
        return "\n".join(lines)

    # -- HTML ------------------------------------------------------------------

    def html(self, markdown_text: str, title: str = "AEGIS LOOP Report") -> str:
        # hafif, bağımlılıksız Markdown → HTML (başlık, tablo, liste, kalın)
        lines = markdown_text.split("\n")
        out: list[str] = []
        in_table = False
        in_list = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("|"):
                cells = [c.strip() for c in stripped.strip("|").split("|")]
                if all(set(c) <= set("-: ") for c in cells):
                    continue
                if not in_table:
                    out.append("<table class='rpt'>")
                    in_table = True
                    out.append("<tr>" + "".join(f"<th>{_h(c)}</th>" for c in cells) + "</tr>")
                else:
                    out.append("<tr>" + "".join(f"<td>{_h(c)}</td>" for c in cells) + "</tr>")
                continue
            if in_table:
                out.append("</table>")
                in_table = False
            if stripped.startswith("### "):
                out.append(f"<h3>{_h(stripped[4:])}</h3>")
            elif stripped.startswith("## "):
                out.append(f"<h2>{_h(stripped[3:])}</h2>")
            elif stripped.startswith("# "):
                out.append(f"<h1>{_h(stripped[2:])}</h1>")
            elif stripped.startswith("- "):
                if not in_list:
                    out.append("<ul>")
                    in_list = True
                out.append(f"<li>{_inline(_h(stripped[2:]))}</li>")
            elif not stripped:
                if in_list:
                    out.append("</ul>")
                    in_list = False
            else:
                if in_list:
                    out.append("</ul>")
                    in_list = False
                out.append(f"<p>{_inline(_h(stripped))}</p>")
        if in_table:
            out.append("</table>")
        if in_list:
            out.append("</ul>")
        return HTML_SHELL.format(title=_h(title), body="\n".join(out))


def _h(s: str) -> str:
    return _html.escape(s, quote=False)


def _escape_md(s: str) -> str:
    return s.replace("|", "\\|")


def _inline(s: str) -> str:
    # **kalın** desteği
    parts = s.split("**")
    if len(parts) >= 3:
        return parts[0] + "".join(
            f"<strong>{parts[i]}</strong>{parts[i+1]}" for i in range(1, len(parts) - 1, 2)
        ) + parts[-1] if len(parts) % 2 == 1 else s
    return s


HTML_SHELL = """<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  body {{ font-family: ui-sans-serif, system-ui, sans-serif; background: #0b1220; color: #dbe4f0; margin: 0; padding: 32px; }}
  h1 {{ color: #7dd3fc; font-size: 22px; }}
  h2 {{ color: #a5f3fc; font-size: 17px; border-bottom: 1px solid #1e293b; padding-bottom: 6px; margin-top: 28px; }}
  h3 {{ color: #e2e8f0; font-size: 15px; }}
  table.rpt {{ border-collapse: collapse; margin: 12px 0; font-size: 13px; width: 100%; }}
  th, td {{ border: 1px solid #1e293b; padding: 6px 10px; text-align: left; }}
  th {{ background: #0f1b2d; color: #93c5fd; }}
  code {{ font-family: ui-monospace, monospace; background: #0f1b2d; padding: 2px 6px; border-radius: 4px; color: #7dd3fc; }}
  ul {{ padding-left: 20px; }} li {{ margin: 4px 0; }}
</style>
</head>
<body>
{body}
</body>
</html>
"""
