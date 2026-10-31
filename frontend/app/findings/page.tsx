"use client";

import { useEffect, useState } from "react";
import { api, type FindingRow } from "@/lib/api";
import { useActiveCampaign } from "@/lib/store";
import { Badge, Card, Empty } from "@/components/ui";
import Link from "next/link";

export default function FindingsPage() {
  const [campaignId] = useActiveCampaign();
  const [findings, setFindings] = useState<FindingRow[]>([]);
  const [q, setQ] = useState("");

  useEffect(() => {
    if (!campaignId) return;
    api.findings(campaignId).then(setFindings).catch(() => {});
  }, [campaignId]);

  if (!campaignId) return <Empty>Aktif kampanya yok.</Empty>;

  const filtered = findings.filter(
    (f) =>
      !q ||
      f.violated_property.includes(q) ||
      f.component.includes(q) ||
      f.finding_id.includes(q)
  );

  const groups = new Map<string, FindingRow[]>();
  for (const f of filtered) {
    groups.set(f.group_id || f.finding_id, [...(groups.get(f.group_id || f.finding_id) || []), f]);
  }

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-slate-100">Findings</h1>
          <p className="text-xs text-slate-500">
            {findings.length} doğrulanmış bulgu · {groups.size} grup — metin varyasyonları farklı
            açık sayılmaz
          </p>
        </div>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="ara: özellik / bileşen / kimlik"
          className="w-64 rounded-lg border border-base-600 bg-base-800 px-3 py-1.5 text-xs placeholder:text-slate-600"
        />
      </header>

      {filtered.length === 0 ? (
        <Empty>Doğrulanmış bulgu yok (tanımlı kapsamda).</Empty>
      ) : (
        <div className="space-y-4">
          {[...groups.entries()].map(([gid, fs]) => (
            <Card
              key={gid}
              title={`${fs[0].violated_property} — ${fs[0].component}`}
              subtitle={`grup ${gid.slice(0, 18)} · ${fs.length} bulgu · sınır: ${fs[0].boundary}`}
            >
              <table className="grid">
                <thead>
                  <tr>
                    <th>Bulgu</th>
                    <th>Önem</th>
                    <th>Tekrar üretim</th>
                    <th>Teşhis</th>
                    <th>ATLAS</th>
                    <th>Gözlenen etki</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {fs.map((f) => (
                    <tr key={f.finding_id}>
                      <td className="font-mono text-[11px] text-accent-300">
                        {f.finding_id.slice(0, 16)}
                      </td>
                      <td>
                        <Badge status={f.severity}>{f.severity}</Badge>
                      </td>
                      <td className="tabular-nums">
                        {Math.round(f.reproduction_rate * 100)}%
                      </td>
                      <td className="text-slate-400">{f.diagnosis}</td>
                      <td className="font-mono text-[11px]">
                        {f.atlas.map((a) => a.technique_id).join(", ")}
                      </td>
                      <td className="max-w-[260px] truncate text-slate-400">
                        {f.observed_effect}
                      </td>
                      <td className="text-right">
                        <Link
                          href={`/findings/${f.finding_id}`}
                          className="text-xs text-accent-300 hover:underline"
                        >
                          detay →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
