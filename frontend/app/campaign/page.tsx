"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, type AttemptRow, type CampaignSummary } from "@/lib/api";
import { useActiveCampaign } from "@/lib/store";
import { Badge, Button, Card, Empty, Meter } from "@/components/ui";

interface LiveEvent {
  seq: number;
  kind: string;
  payload: Record<string, unknown>;
  ts: string;
}

const KIND_LABEL: Record<string, string> = {
  state_changed: "durum",
  attempt_started: "deneme başladı",
  attempt_finished: "deneme bitti",
  scheduler_decision: "scheduler kararı",
  finding_confirmed: "bulgu doğrulandı",
  finding_grouped: "bulgu gruplandı",
  repair_build: "repair deneyi",
  repair_rejected: "aday reddedildi",
  verification_done: "doğrulama bitti",
  verification_update: "doğrulama güncellendi",
  budget_update: "bütçe",
  baseline_update: "baseline",
  campaign_completed: "kampanya tamamlandı",
  worker_lost: "worker kaybı",
  kill_switch: "kill switch",
};

export default function CampaignPage() {
  const [campaignId] = useActiveCampaign();
  const [summary, setSummary] = useState<CampaignSummary | null>(null);
  const [attempts, setAttempts] = useState<AttemptRow[]>([]);
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [live, setLive] = useState(true);
  const [note, setNote] = useState<string | null>(null);
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    if (!campaignId) return;
    try {
      setSummary(await api.campaign(campaignId));
      setAttempts(await api.attempts(campaignId, 40));
    } catch {
      /* worker kaybı UI'da doğru gösterilir */
    }
  }, [campaignId]);

  useEffect(() => {
    refresh();
    pollTimer.current = setInterval(refresh, 2000);
    return () => {
      if (pollTimer.current) clearInterval(pollTimer.current);
    };
  }, [refresh]);

  // SSE canlı olay akışı
  useEffect(() => {
    if (!campaignId || !live) return;
    const es = new EventSource(`/api/campaigns/${campaignId}/events`);
    es.onmessage = (msg) => {
      try {
        const data = JSON.parse(msg.data) as LiveEvent;
        setEvents((prev) => [...prev.slice(-80), data]);
      } catch {
        /* keepalive */
      }
    };
    es.onerror = () => {
      setNote("Olay akışı koptu — yeniden bağlanılıyor…");
    };
    es.onopen = () => setNote(null);
    return () => es.close();
  }, [campaignId, live]);

  const act = async (fn: () => Promise<unknown>, label: string) => {
    try {
      await fn();
      setNote(`${label} isteği gönderildi`);
      await refresh();
    } catch (e) {
      setNote(`${label} hatası: ${String(e)}`);
    }
  };

  if (!campaignId) {
    return <Empty>Aktif kampanya yok — Overview'dan yeni kampanya başlatın.</Empty>;
  }

  const running = summary && ["discovering", "baselining", "verifying_findings", "preflight"].includes(summary.state);

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-slate-100">Campaign Console</h1>
          <p className="text-xs text-slate-500">
            {campaignId}
            {summary && (
              <>
                {" · "}
                <Badge status={summary.state}>{summary.state}</Badge>
              </>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            onClick={() => act(() => api.pauseCampaign(campaignId), "Pause")}
            disabled={!running}
          >
            Pause
          </Button>
          <Button
            onClick={() => act(() => api.resumeCampaign(campaignId), "Resume")}
            disabled={running || summary?.state !== "paused"}
          >
            Resume
          </Button>
          <Button
            tone="danger"
            onClick={() => act(() => api.cancelCampaign(campaignId), "Cancel")}
            disabled={!running && summary?.state !== "paused"}
          >
            Cancel
          </Button>
          <Button tone="ghost" onClick={() => setLive((v) => !v)}>
            {live ? "canlı akış: açık" : "canlı akış: kapalı"}
          </Button>
        </div>
      </header>

      {note && (
        <div className="rounded-lg border border-accent-500/40 bg-accent-500/10 px-4 py-2 text-xs text-accent-300">
          {note}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Sol: kapsam */}
        <Card title="Kapsam" subtitle="hücre durumları">
          {summary ? (
            <div className="space-y-3 text-xs">
              <div>
                <div className="mb-1 flex justify-between text-slate-400">
                  <span>tamamlanma</span>
                  <span className="tabular-nums">{summary.coverage_pct}%</span>
                </div>
                <Meter value={summary.coverage_pct} />
              </div>
              <div className="space-y-1 text-slate-400">
                <div className="flex justify-between">
                  <span>uygulanabilir hücre</span>
                  <span className="tabular-nums text-slate-200">{summary.applicable}</span>
                </div>
                <div className="flex justify-between">
                  <span>ihlal gözlenen</span>
                  <span className="tabular-nums text-bad">{summary.cells_with_violations}</span>
                </div>
                <div className="flex justify-between">
                  <span>uygulanamaz</span>
                  <span className="tabular-nums text-slate-500">{summary.not_applicable}</span>
                </div>
              </div>
            </div>
          ) : (
            <Empty>veri yok</Empty>
          )}
        </Card>

        {/* Orta: denemeler */}
        <Card
          title="Canlı denemeler"
          subtitle={`${attempts.length} kayıt · execution ve verdict ayrı gösterilir`}
          className="lg:col-span-2"
        >
          {attempts.length === 0 ? (
            <Empty>Deneme yok.</Empty>
          ) : (
            <div className="max-h-72 overflow-y-auto">
              <table className="grid">
                <thead>
                  <tr>
                    <th>Strateji</th>
                    <th>Dil</th>
                    <th>Yürütme</th>
                    <th>Verdict</th>
                    <th>Yanıt (kırpılmış)</th>
                    <th>ms</th>
                  </tr>
                </thead>
                <tbody>
                  {attempts
                    .slice()
                    .reverse()
                    .map((a) => (
                      <tr key={a.attempt_id}>
                        <td className="font-mono text-[11px]">{a.strategy}</td>
                        <td>{a.language}</td>
                        <td>
                          <Badge status={a.execution_status || ""}>{a.execution_status}</Badge>
                        </td>
                        <td>
                          <Badge status={a.verdict || ""}>{a.verdict}</Badge>
                        </td>
                        <td className="max-w-[280px] truncate text-slate-400">
                          {a.response_preview}
                        </td>
                        <td className="tabular-nums text-slate-500">{a.wall_ms}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Olay akışı (SSE)" subtitle="scheduler gerekçeleri ve sistem olayları">
          <div className="max-h-80 space-y-1.5 overflow-y-auto font-mono text-[11px] leading-4">
            {events.length === 0 && (
              <div className="text-slate-500">bağlanıyor / olay bekleniyor…</div>
            )}
            {events
              .slice()
              .reverse()
              .map((e) => (
                <div key={e.seq} className="rounded border border-base-700/40 bg-base-900/50 px-2.5 py-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-accent-300">{KIND_LABEL[e.kind] || e.kind}</span>
                    <span className="text-slate-600">{e.ts?.slice(11, 19)}</span>
                  </div>
                  <div className="mt-0.5 whitespace-pre-wrap text-slate-400">
                    {renderPayload(e)}
                  </div>
                </div>
              ))}
          </div>
        </Card>

        <Card title="Bütçe defteri" subtitle="kaynak türü bazlı tüketim ve rezerv">
          {summary?.budget ? (
            <table className="grid">
              <thead>
                <tr>
                  <th>Kaynak</th>
                  <th>Kullanılan</th>
                  <th>Rezerv</th>
                  <th>Limit</th>
                  <th>Kalan</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(summary.budget).map(([kind, b]) => (
                  <tr key={kind}>
                    <td className="font-mono text-[11px]">{kind}</td>
                    <td className="tabular-nums">{Math.round(b.used)}</td>
                    <td className="tabular-nums text-warn">{Math.round(b.reserved)}</td>
                    <td className="tabular-nums text-slate-500">{Math.round(b.limit)}</td>
                    <td className="tabular-nums text-ok">{Math.round(b.remaining)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <Empty>Bütçe verisi yok.</Empty>
          )}
        </Card>
      </div>
    </div>
  );
}

function renderPayload(e: LiveEvent): string {
  const p = e.payload;
  switch (e.kind) {
    case "scheduler_decision":
      return `${p.strategy} · ${p.language} · hücre [${(p.cell as string[])?.join(", ")}]
sebep: ${p.reason}`;
    case "attempt_finished":
      return `${p.attempt_id} → ${p.execution_status} / verdict=${p.verdict}`;
    case "finding_confirmed":
      return `${p.finding_id} · ${p.violated_property} · tekrar=${p.reproduction_rate} · atlas=${(p.atlas as string[])?.join(",")}`;
    case "repair_rejected":
      return `aday ${p.candidate}: ${(p.reasons as string[])?.[0]}`;
    case "verification_done":
      return `${p.candidate} → ${p.verdict}`;
    default:
      return JSON.stringify(p).slice(0, 220);
  }
}
