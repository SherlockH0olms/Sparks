"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, type CampaignRow, type CampaignSummary } from "@/lib/api";
import { useActiveCampaign } from "@/lib/store";
import { Badge, Button, Card, Empty, Meter, Stat } from "@/components/ui";
import Link from "next/link";

export default function OverviewPage() {
  const [campaigns, setCampaigns] = useState<CampaignRow[]>([]);
  const [selected, setSelected] = useActiveCampaign();
  const [summary, setSummary] = useState<CampaignSummary | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [health, setHealth] = useState<{ campaigns: number; kill_switch: boolean } | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    try {
      setErr(null);
      const rows = await api.campaigns();
      setCampaigns(rows);
      setHealth(await api.health());
      const active = selected || rows[rows.length - 1]?.campaign_id || null;
      if (active && active !== selected) setSelected(active);
      if (active) setSummary(await api.campaign(active));
    } catch (e) {
      setErr(String(e));
    }
  }, [selected, setSelected]);

  useEffect(() => {
    refresh();
    timer.current = setInterval(refresh, 2500);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [refresh]);

  const newCampaign = async () => {
    setBusy(true);
    try {
      const targets = await api.targets();
      const created = await api.createCampaign({
        target_id: targets[0].target_id,
        languages: ["tr", "az", "en"],
      });
      setSelected(created.campaign_id);
      await api.startCampaign(created.campaign_id);
      await refresh();
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  };

  const cov = summary;
  const budgetUsed = (() => {
    if (!cov?.budget) return 0;
    const entries = Object.values(cov.budget);
    if (!entries.length) return 0;
    const used = entries.reduce((a, b) => a + b.used / Math.max(1, b.limit), 0);
    return Math.round((used / entries.length) * 100);
  })();

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-slate-100">Overview</h1>
          <p className="text-xs text-slate-500">
            Kampanyalar, kapsam, bulgular, bütçe ve çalışma durumu — tek bakışta
          </p>
        </div>
        <div className="flex items-center gap-2">
          {health?.kill_switch && <Badge status="fail">KILL SWITCH AKTİF</Badge>}
          <Button tone="primary" onClick={newCampaign} disabled={busy}>
            {busy ? "başlatılıyor…" : "+ Yeni Kampanya"}
          </Button>
        </div>
      </header>

      {err && (
        <div className="rounded-lg border border-bad/40 bg-bad/10 px-4 py-2 text-xs text-bad">
          API hatası: {err}
        </div>
      )}

      {cov ? (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
            <Stat
              label="Kapsam"
              value={`${cov.coverage_pct}%`}
              hint={`${cov.completed}/${cov.applicable} hücre`}
              tone={cov.coverage_pct === 100 ? "ok" : "accent"}
            />
            <Stat
              label="Bulgu grubu"
              value={cov.groups}
              hint={`${cov.findings} doğrulanmış bulgu`}
              tone={cov.groups > 0 ? "bad" : "default"}
            />
            <Stat label="Deneme" value={cov.attempts} hint="yürütülen denemeler" />
            <Stat label="Düzeltme deneyi" value={cov.experiments} hint="Repair Lab" />
            <Stat
              label="Doğrulama"
              value={cov.verification_runs}
              hint="bağımsız final koşusu"
              tone={cov.verification_runs > 0 ? "accent" : "default"}
            />
            <Stat
              label="Bütçe"
              value={`${budgetUsed}%`}
              hint="tüm kaynak türleri"
              tone={budgetUsed > 90 ? "warn" : "default"}
            />
          </div>

          <Card
            title={`Aktif kampanya: ${cov.campaign_id}`}
            subtitle={`durum · ${cov.state}`}
            actions={
              <>
                <Badge status={cov.state}>{cov.state}</Badge>
                <Link href="/campaign" className="text-xs text-accent-300 hover:underline">
                  konsolu aç →
                </Link>
              </>
            }
          >
            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <div className="mb-1 flex justify-between text-xs text-slate-400">
                  <span>Kapsam tamamlanması</span>
                  <span className="tabular-nums">{cov.coverage_pct}%</span>
                </div>
                <Meter value={cov.coverage_pct} tone="accent" />
                <div className="mt-1 text-[11px] text-slate-500">
                  payda: kampanya başında sabitlenen {cov.applicable} uygulanabilir hücre
                  {cov.not_applicable > 0 && ` · ${cov.not_applicable} uygulanamaz`}
                </div>
              </div>
              <div>
                <div className="mb-1 flex justify-between text-xs text-slate-400">
                  <span>İhlal gözlenen hücreler</span>
                  <span className="tabular-nums">{cov.cells_with_violations}</span>
                </div>
                <Meter
                  value={cov.applicable ? (cov.cells_with_violations / cov.applicable) * 100 : 0}
                  tone="bad"
                />
                <div className="mt-1 text-[11px] text-slate-500">
                  kapsam içi hücrelerin ihlal oranı
                </div>
              </div>
              <div>
                <div className="mb-1 flex justify-between text-xs text-slate-400">
                  <span>Normal görev başarısı (baseline)</span>
                  <span className="tabular-nums">
                    {cov.baseline ? `${Math.round((cov.baseline.utility ?? 0) * 100)}%` : "—"}
                  </span>
                </div>
                <Meter value={(cov.baseline?.utility ?? 0) * 100} tone="ok" />
                <div className="mt-1 text-[11px] text-slate-500">
                  {cov.baseline
                    ? `${cov.baseline.answered}/${cov.baseline.questions} soru yanıtlandı`
                    : "baseline henüz yok"}
                </div>
              </div>
            </div>
          </Card>
        </>
      ) : (
        <Empty>Kampanya verisi yok — yeni kampanya başlatın.</Empty>
      )}

      <Card title="Kampanyalar" subtitle={`${campaigns.length} kayıt`}>
        {campaigns.length === 0 ? (
          <Empty>Henüz kampanya yok.</Empty>
        ) : (
          <table className="grid">
            <thead>
              <tr>
                <th>Kampanya</th>
                <th>Durum</th>
                <th>Deneme</th>
                <th>Bulgu</th>
                <th>Oluşturma</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {campaigns.map((c) => (
                <tr key={c.campaign_id}>
                  <td className="font-mono text-[11px] text-accent-300">{c.campaign_id}</td>
                  <td>
                    <Badge status={c.state}>{c.state}</Badge>
                  </td>
                  <td className="tabular-nums">{c.attempts}</td>
                  <td className="tabular-nums">{c.findings}</td>
                  <td className="text-slate-500">{c.created?.slice(0, 19)}</td>
                  <td className="text-right">
                    <Button tone="ghost" onClick={() => setSelected(c.campaign_id)}>
                      {selected === c.campaign_id ? "seçili" : "seç"}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Card title="Risk–kontrol görünümü" subtitle="grup bazında ihlal ve düzeltme durumu">
        <RiskControlGrid />
      </Card>
    </div>
  );
}

function RiskControlGrid() {
  const [campaignId] = useActiveCampaign();
  const [findings, setFindings] = useState<import("@/lib/api").FindingRow[]>([]);
  const [verifs, setVerifs] = useState<import("@/lib/api").VerificationRunView[]>([]);

  useEffect(() => {
    if (!campaignId) return;
    api.findings(campaignId).then(setFindings).catch(() => {});
    api.verification(campaignId).then(setVerifs).catch(() => {});
  }, [campaignId]);

  if (!campaignId) return <Empty>Aktif kampanya seçilmedi.</Empty>;
  if (findings.length === 0) return <Empty>Bulgu yok.</Empty>;

  const groups = new Map<string, import("@/lib/api").FindingRow[]>();
  for (const f of findings) {
    const key = f.group_id || f.finding_id;
    groups.set(key, [...(groups.get(key) || []), f]);
  }

  return (
    <table className="grid">
      <thead>
        <tr>
          <th>Grup</th>
          <th>İhlal edilen özellik</th>
          <th>Bileşen</th>
          <th>Bulgu</th>
          <th>En yüksek önem</th>
          <th>Doğrulama</th>
        </tr>
      </thead>
      <tbody>
        {[...groups.entries()].map(([gid, fs]) => {
          const sevRank: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1 };
          const top = fs.reduce((a, b) => (sevRank[a.severity] >= sevRank[b.severity] ? a : b));
          const passed = verifs.filter((v) => v.verdict === "pass").length;
          return (
            <tr key={gid}>
              <td className="font-mono text-[11px] text-slate-500">{gid.slice(0, 16)}</td>
              <td>{fs[0].violated_property}</td>
              <td className="text-slate-400">{fs[0].component}</td>
              <td className="tabular-nums">{fs.length}</td>
              <td>
                <Badge status={top.severity}>{top.severity}</Badge>
              </td>
              <td>
                {verifs.length === 0 ? (
                  <span className="text-slate-500">—</span>
                ) : (
                  <Badge status={passed > 0 ? "pass" : "fail"}>
                    {passed}/{verifs.length} geçti
                  </Badge>
                )}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
