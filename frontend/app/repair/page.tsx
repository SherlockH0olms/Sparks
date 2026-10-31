"use client";

import { useEffect, useState } from "react";
import { api, type RepairExperimentView } from "@/lib/api";
import { useActiveCampaign } from "@/lib/store";
import { Badge, Card, Empty } from "@/components/ui";

export default function RepairPage() {
  const [campaignId] = useActiveCampaign();
  const [experiments, setExperiments] = useState<RepairExperimentView[]>([]);
  const [openDiff, setOpenDiff] = useState<string | null>(null);

  useEffect(() => {
    if (!campaignId) return;
    api.repair(campaignId).then(setExperiments).catch(() => {});
  }, [campaignId]);

  if (!campaignId) return <Empty>Aktif kampanya yok.</Empty>;
  if (experiments.length === 0)
    return <Empty>Düzeltme deneyi yok — kampanyanın bulgu doğrulama aşamasını bekleyin.</Empty>;

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-lg font-semibold text-slate-100">Repair Lab</h1>
        <p className="text-xs text-slate-500">
          Aynı baseline&apos;dan A/B/C/D adayları: kapılar (build → güvenlik ön testi → normal
          görev → kaynak), sonra karşılaştırma. Tek ağırlıklı skor yok; işlevi bozan aday reddedilir.
        </p>
      </header>

      {experiments.map((exp) => (
        <Card
          key={exp.experiment_id}
          title={`Deney ${exp.experiment_id.slice(0, 16)}`}
          subtitle={`bulgu ${exp.finding_id.slice(0, 16)} · baseline ${exp.baseline_revision.slice(0, 24)}`}
        >
          <table className="grid">
            <thead>
              <tr>
                <th>Aday</th>
                <th>Değişiklik</th>
                <th>Build</th>
                <th>Güvenlik ön testi</th>
                <th>Utility</th>
                <th>Gecikme</th>
                <th>Durum</th>
                <th>Karar</th>
              </tr>
            </thead>
            <tbody>
              {exp.rows.map((r) => {
                const pre =
                  typeof r.security_pretest === "object"
                    ? `${r.security_pretest.violations_remaining}/${r.security_pretest.replayed} ihlal`
                    : "—";
                const rejected = r.state === "gate_failed" || r.rejection_reasons.length > 0;
                return (
                  <tr key={r.candidate_id}>
                    <td>
                      <Badge status={rejected ? "gate_failed" : "built"}>{r.label}</Badge>
                    </td>
                    <td className="max-w-[220px]">
                      <div className="truncate">{r.controls.join(", ") || "değişiklik yok"}</div>
                      {r.diff && (
                        <button
                          onClick={() => setOpenDiff(openDiff === r.candidate_id ? null : r.candidate_id)}
                          className="mt-0.5 text-[11px] text-accent-300 hover:underline"
                        >
                          {openDiff === r.candidate_id ? "diff'i kapat" : "diff'i göster"}
                        </button>
                      )}
                    </td>
                    <td>
                      <Badge status={r.build === "ok" ? "pass" : "fail"}>{r.build}</Badge>
                    </td>
                    <td className="tabular-nums">{pre}</td>
                    <td className="tabular-nums">
                      {typeof r.utility === "number" ? `${Math.round(r.utility * 100)}%` : "—"}
                    </td>
                    <td className="tabular-nums text-slate-500">{r.avg_wall_ms}ms</td>
                    <td>
                      <Badge status={r.state}>{r.state}</Badge>
                    </td>
                    <td className="max-w-[240px] text-[11px]">
                      {r.rejection_reasons.length ? (
                        <span className="text-bad">REDDEDİLDİ: {r.rejection_reasons[0]}</span>
                      ) : r.label === "A" ? (
                        <span className="text-slate-500">referans ölçüm</span>
                      ) : (
                        <span className="text-ok">kapıları geçti</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {openDiff && (
            <pre className="mt-3 max-h-56 overflow-y-auto whitespace-pre rounded-lg border border-base-700/50 bg-base-900/70 p-3 font-mono text-[11px] leading-4 text-slate-300">
              {exp.rows.find((r) => r.candidate_id === openDiff)?.diff}
            </pre>
          )}

          <div className="mt-3 rounded-lg border border-base-700/40 bg-base-900/40 p-3 text-[11px] leading-4 text-slate-500">
            <div>
              <span className="text-slate-400">Geri alma:</span>{" "}
              {exp.rows.find((r) => r.label !== "A")?.rollback || "—"}
            </div>
            <div className="mt-1">
              Adaylar baseline&apos;ın izole kopyalarında çalışır; devam eden kampanyanın hedefi
              yerinde değiştirilmez. Ölçüm olmayan hücrede &quot;—&quot; gösterilir, uydurma
              değer kullanılmaz.
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}
