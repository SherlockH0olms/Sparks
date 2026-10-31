"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, type FindingDetail } from "@/lib/api";
import { useActiveCampaign } from "@/lib/store";
import { Badge, Card, Empty } from "@/components/ui";
import Link from "next/link";

const TABS = ["Summary", "Evidence", "Reproduction", "Diagnosis", "Mapping", "Repairs"] as const;

export default function FindingDetailPage() {
  const params = useParams<{ finding_id: string }>();
  const [campaignId] = useActiveCampaign();
  const [finding, setFinding] = useState<FindingDetail | null>(null);
  const [tab, setTab] = useState<(typeof TABS)[number]>("Summary");
  const [repairs, setRepairs] = useState<
    { experiment_id: string; finding_id: string; rows: { label: string; state: string; rejection_reasons: string[] }[] }[]
  >([]);

  useEffect(() => {
    if (!campaignId || !params?.finding_id) return;
    api.finding(campaignId, params.finding_id).then(setFinding).catch(() => {});
    api.repair(campaignId).then(setRepairs).catch(() => {});
  }, [campaignId, params?.finding_id]);

  if (!campaignId) return <Empty>Aktif kampanya yok.</Empty>;
  if (!finding) return <Empty>Bulgu yükleniyor…</Empty>;

  const relatedExperiments = repairs.filter(
    (r) => r.finding_id === finding.finding_id || repairs.length <= 3
  );

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-mono text-sm text-slate-100">{finding.finding_id}</h1>
          <div className="mt-1 flex items-center gap-2">
            <Badge status={finding.severity}>{finding.severity}</Badge>
            <Badge>{finding.violated_property}</Badge>
            <span className="text-xs text-slate-500">{finding.component}</span>
          </div>
        </div>
        <Link href="/findings" className="text-xs text-accent-300 hover:underline">
          ← bulgu listesi
        </Link>
      </header>

      <nav className="flex gap-1 rounded-xl border border-base-700/50 bg-base-900/60 p-1">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-lg px-3 py-1.5 text-xs transition-colors ${
              tab === t ? "bg-accent-500/20 text-accent-300" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {t}
          </button>
        ))}
      </nav>

      {tab === "Summary" && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card title="Ne ihlal edildi?">
            <dl className="space-y-2 text-xs">
              <Row k="İhlal edilen özellik" v={finding.violated_property} />
              <Row k="Güven sınırı" v={finding.boundary} />
              <Row k="Bileşen" v={finding.component} />
              <Row k="Önem" v={finding.severity} />
              <Row k="Teşhis" v={finding.diagnosis} />
              <Row
                k="Tekrar üretim oranı"
                v={`${Math.round(finding.reproduction_rate * 100)}% (temiz oturum)`}
              />
            </dl>
          </Card>
          <Card title="Gözlenen etki" subtitle="yanıt kırpılmış — güvenilmeyen veri">
            <pre className="max-h-48 overflow-y-auto whitespace-pre-wrap rounded-lg bg-base-900/70 p-3 font-mono text-[11px] text-slate-300">
              {finding.observed_effect}
            </pre>
          </Card>
          <Card title="Orijinal senaryo" subtitle="kırpılmış">
            <pre className="max-h-40 overflow-y-auto whitespace-pre-wrap rounded-lg bg-base-900/70 p-3 font-mono text-[11px] text-slate-300">
              {finding.original_attempt?.turns?.join("\n---\n") || "—"}
            </pre>
            {finding.original_attempt && (
              <div className="mt-2 flex items-center gap-2">
                <Badge status={finding.original_attempt.execution_status || ""}>
                  {finding.original_attempt.execution_status}
                </Badge>
                <Badge status={finding.original_attempt.verdict || ""}>
                  {finding.original_attempt.verdict}
                </Badge>
              </div>
            )}
          </Card>
          <Card title="Küçültülmüş senaryo" subtitle="gereksiz kısımlar bütçe içinde çıkarıldı">
            {finding.minimized_turns.length ? (
              <pre className="max-h-40 overflow-y-auto whitespace-pre-wrap rounded-lg bg-base-900/70 p-3 font-mono text-[11px] text-ok/90">
                {finding.minimized_turns.join("\n---\n")}
              </pre>
            ) : (
              <Empty>Küçültme uygulanmadı.</Empty>
            )}
          </Card>
        </div>
      )}

      {tab === "Evidence" && (
        <Card title="Kanıt zinciri" subtitle="deterministik kanıtlar — modelin iddiası kanıt değildir">
          {finding.evidence.length === 0 ? (
            <Empty>Kanıt kaydı yok.</Empty>
          ) : (
            <div className="space-y-2">
              {finding.evidence.map((e, i) => (
                <div key={i} className="rounded-lg border border-base-700/50 bg-base-900/60 p-3">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[11px] text-accent-300">{e.kind}</span>
                    <span className="text-[11px] text-slate-500">{e.source}</span>
                  </div>
                  <pre className="mt-2 max-h-32 overflow-y-auto whitespace-pre-wrap font-mono text-[11px] text-slate-300">
                    {e.content}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {tab === "Reproduction" && (
        <Card title="Temiz oturumda tekrar denemeleri" subtitle="bağımsız değerlendirici tekrar üretir">
          <table className="grid">
            <thead>
              <tr>
                <th>Deneme</th>
                <th>Sonuç</th>
                <th>Yanıt (kırpılmış)</th>
              </tr>
            </thead>
            <tbody>
              {finding.reproduction_trials.map((t) => (
                <tr key={t.trial}>
                  <td className="tabular-nums">#{t.trial + 1}</td>
                  <td>
                    <Badge status={t.violation ? "violation" : "no_violation_observed"}>
                      {t.violation ? "ihlal tekrarlandı" : "ihlal gözlenmedi"}
                    </Badge>
                  </td>
                  <td className="max-w-[420px] truncate text-slate-400">{t.response_excerpt}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {tab === "Diagnosis" && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card title="Teşhip durumu" subtitle="kanıt türleri — LLM'in 'eminim' ifadesi değil">
            <dl className="space-y-2 text-xs">
              <Row k="Durum" v={finding.diagnosis} />
              <Row k="Not" v={finding.diagnosis_notes || "—"} />
            </dl>
          </Card>
          <Card title="Bilinen sınırlamalar">
            <ul className="list-disc space-y-1 pl-5 text-xs text-slate-400">
              {finding.limitations.map((l, i) => (
                <li key={i}>{l}</li>
              ))}
            </ul>
          </Card>
        </div>
      )}

      {tab === "Mapping" && (
        <Card title="MITRE ATLAS eşleştirmesi" subtitle="her eşleme gerekçelidir; zorla eşleme yok">
          {finding.atlas.length === 0 ? (
            <Empty>Eşleme yok.</Empty>
          ) : (
            <div className="space-y-2">
              {finding.atlas.map((a, i) => (
                <div key={i} className="rounded-lg border border-base-700/50 bg-base-900/60 p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded bg-accent-500/15 px-2 py-0.5 font-mono text-[11px] text-accent-300">
                      {a.technique_id}
                    </span>
                    <span className="text-xs font-semibold text-slate-200">{a.name}</span>
                  </div>
                  <p className="mt-2 text-xs leading-5 text-slate-400">{a.justification}</p>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {tab === "Repairs" && (
        <Card title="İlgili düzeltme deneyleri" subtitle="aday karşılaştırması Repair Lab'da">
          {relatedExperiments.length === 0 ? (
            <Empty>Bu bulgu için deney yok.</Empty>
          ) : (
            <table className="grid">
              <thead>
                <tr>
                  <th>Deney</th>
                  <th>Aday</th>
                  <th>Durum</th>
                  <th>Ret gerekçesi</th>
                </tr>
              </thead>
              <tbody>
                {relatedExperiments.flatMap((exp) =>
                  exp.rows.map((r) => (
                    <tr key={`${exp.experiment_id}-${r.label}`}>
                      <td className="font-mono text-[11px] text-slate-500">
                        {exp.experiment_id.slice(0, 14)}
                      </td>
                      <td>{r.label}</td>
                      <td>
                        <Badge status={r.state}>{r.state}</Badge>
                      </td>
                      <td className="text-slate-400">
                        {r.rejection_reasons[0] || "—"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}
        </Card>
      )}
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-base-700/30 pb-1.5">
      <dt className="text-slate-500">{k}</dt>
      <dd className="text-right text-slate-200">{v}</dd>
    </div>
  );
}
