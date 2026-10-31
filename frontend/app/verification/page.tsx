"use client";

import { useEffect, useState } from "react";
import { api, type VerificationRunView } from "@/lib/api";
import { useActiveCampaign } from "@/lib/store";
import { Badge, Card, Empty } from "@/components/ui";

const SUITE_LABEL: Record<string, string> = {
  replay: "Replay — bilinen ihlal örnekleri",
  unseen_variations: "Görülmemiş varyasyonlar (holdout)",
  adaptive_defense_aware: "Savunmaya uyarlanmış kampanya",
  utility_regression: "Normal kullanım regresyonu",
};

export default function VerificationPage() {
  const [campaignId] = useActiveCampaign();
  const [runs, setRuns] = useState<VerificationRunView[]>([]);

  useEffect(() => {
    if (!campaignId) return;
    api.verification(campaignId).then(setRuns).catch(() => {});
  }, [campaignId]);

  if (!campaignId) return <Empty>Aktif kampanya yok.</Empty>;
  if (runs.length === 0)
    return <Empty>Bağımsız doğrulama koşusu yok — Repair Lab adayının dondurulmasını bekleyin.</Empty>;

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-lg font-semibold text-slate-100">Verification Lab</h1>
        <p className="text-xs text-slate-500">
          Bağımsız final: aday dondurulur, geliştirme rolleri gizli set ayrıntılarını görmez.
          Önce/sonra aynı sabit protokolde karşılaştırılır.
        </p>
      </header>

      {runs.map((run) => (
        <Card
          key={run.run_id}
          title={`Koşu ${run.run_id.slice(0, 16)}`}
          subtitle={`aday ${run.candidate_id.slice(0, 12)} · deney ${run.experiment_id.slice(0, 14)}`}
          actions={
            <Badge status={run.verdict || ""}>
              {run.verdict === "pass"
                ? "geçti (tanımlı kapsamda)"
                : run.verdict === "fail"
                  ? "geçemedi"
                  : run.verdict === "inconclusive"
                    ? "belirsiz"
                    : "—"}
            </Badge>
          }
        >
          <table className="grid">
            <thead>
              <tr>
                <th>Süit</th>
                <th>Deneme</th>
                <th>İhlal</th>
                <th>ASR</th>
                <th>Utility</th>
                <th>Yanlış engelleme</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(run.suites).map(([suite, m]) => (
                <tr key={suite}>
                  <td>{SUITE_LABEL[suite] || suite}</td>
                  <td className="tabular-nums">{m.attempts ?? m.questions ?? "—"}</td>
                  <td className="tabular-nums">{m.violations ?? "—"}</td>
                  <td className="tabular-nums">
                    {m.asr !== undefined ? `${Math.round(m.asr * 100)}%` : "—"}
                  </td>
                  <td className="tabular-nums">
                    {m.utility !== undefined ? `${Math.round(m.utility * 100)}%` : "—"}
                  </td>
                  <td className="tabular-nums">{m.false_blocks ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-3 text-[11px] leading-4 text-slate-500">
            ASR = ihlal gözlenen geçerli deneme / geçerli deneme. Timeout ve altyapı hataları
            güvenlik sonucu sayılmaz. &quot;Geçti&quot; ifadesi tanımlı kapsam ve sürüme bağlıdır.
          </p>
        </Card>
      ))}
    </div>
  );
}
