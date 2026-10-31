"use client";

import { useEffect, useMemo, useState } from "react";
import { api, type CoverageCell } from "@/lib/api";
import { useActiveCampaign } from "@/lib/store";
import { Badge, Card, Empty, Stat } from "@/components/ui";

const STATUS_LABEL: Record<string, string> = {
  not_tested: "test edilmedi",
  insufficient_depth: "yetersiz derinlik",
  assessed_no_violation: "ihlal gözlenmedi",
  violation_observed: "ihlal gözlendi",
  inconclusive: "belirsiz",
  not_applicable: "uygulanamaz",
};

export default function CoveragePage() {
  const [campaignId] = useActiveCampaign();
  const [cells, setCells] = useState<CoverageCell[]>([]);
  const [metrics, setMetrics] = useState<{
    total_cells: number;
    applicable: number;
    not_applicable: number;
    completed: number;
    coverage_pct: number;
    cells_with_violations: number;
  } | null>(null);
  const [fProp, setFProp] = useState("all");
  const [fLang, setFLang] = useState("all");
  const [fStatus, setFStatus] = useState("all");

  useEffect(() => {
    if (!campaignId) return;
    const load = () =>
      api
        .coverage(campaignId)
        .then((d) => {
          setCells(d.cells);
          setMetrics(d.metrics);
        })
        .catch(() => {});
    load();
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, [campaignId]);

  const props = useMemo(() => [...new Set(cells.map((c) => c.property))], [cells]);
  const langs = useMemo(() => [...new Set(cells.map((c) => c.language))], [cells]);
  const filtered = cells.filter(
    (c) =>
      (fProp === "all" || c.property === fProp) &&
      (fLang === "all" || c.language === fLang) &&
      (fStatus === "all" || c.status === fStatus)
  );

  if (!campaignId) return <Empty>Aktif kampanya yok.</Empty>;

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-lg font-semibold text-slate-100">Coverage Explorer</h1>
        <p className="text-xs text-slate-500">
          Kapsam = tamamlanan uygulanabilir hücre / kampanya başında sabitlenen uygulanabilir hücre
        </p>
      </header>

      {metrics && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
          <Stat label="Toplam hücre" value={metrics.total_cells} />
          <Stat label="Uygulanabilir" value={metrics.applicable} hint={`${metrics.not_applicable} uygulanamaz`} />
          <Stat label="Tamamlanan" value={metrics.completed} tone="accent" />
          <Stat label="Kapsam" value={`${metrics.coverage_pct}%`} tone={metrics.coverage_pct === 100 ? "ok" : "accent"} />
          <Stat label="İhlal gören hücre" value={metrics.cells_with_violations} tone="bad" />
        </div>
      )}

      <Card
        title="Kapsam hücreleri"
        subtitle={`${filtered.length} / ${cells.length} hücre görünür`}
        actions={
          <div className="flex gap-2">
            <select
              value={fProp}
              onChange={(e) => setFProp(e.target.value)}
              className="rounded-lg border border-base-600 bg-base-800 px-2 py-1 text-xs"
            >
              <option value="all">özellik: tümü</option>
              {props.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
            <select
              value={fLang}
              onChange={(e) => setFLang(e.target.value)}
              className="rounded-lg border border-base-600 bg-base-800 px-2 py-1 text-xs"
            >
              <option value="all">dil: tümü</option>
              {langs.map((l) => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
            <select
              value={fStatus}
              onChange={(e) => setFStatus(e.target.value)}
              className="rounded-lg border border-base-600 bg-base-800 px-2 py-1 text-xs"
            >
              <option value="all">durum: tümü</option>
              {Object.entries(STATUS_LABEL).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
        }
      >
        {filtered.length === 0 ? (
          <Empty>Hücre yok.</Empty>
        ) : (
          <table className="grid">
            <thead>
              <tr>
                <th>Güvenlik özelliği</th>
                <th>Strateji ailesi</th>
                <th>Dil</th>
                <th>Erişim</th>
                <th>Durum</th>
                <th>Deneme</th>
                <th>Geçerli</th>
                <th>İhlal</th>
                <th>Min</th>
                <th>Not</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c, i) => (
                <tr key={i}>
                  <td className="font-mono text-[11px]">{c.property}</td>
                  <td className="text-slate-400">{c.family}</td>
                  <td>{c.language}</td>
                  <td className="text-slate-500">{c.access_profile}</td>
                  <td>
                    <Badge status={c.status}>{STATUS_LABEL[c.status] || c.status}</Badge>
                  </td>
                  <td className="tabular-nums">{c.attempts}</td>
                  <td className="tabular-nums">{c.valid_attempts}</td>
                  <td className="tabular-nums text-bad">{c.violations || "—"}</td>
                  <td className="tabular-nums text-slate-500">{c.min_required}</td>
                  <td className="max-w-[220px] text-[11px] text-slate-500">
                    {c.not_applicable_reason || ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <p className="mt-3 text-[11px] leading-4 text-slate-500">
          &quot;%80 kapsam&quot; ifadesi dünyadaki saldırıların %80&apos;i anlamına gelmez;
          payda burada görünür. Uygulanamaz hücreler &quot;geçti&quot; olarak sayılmaz,
          nedenleriyle listelenir.
        </p>
      </Card>
    </div>
  );
}
