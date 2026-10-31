"use client";

import { useEffect, useState } from "react";
import { api, type TargetInfo } from "@/lib/api";
import { Badge, Card, Empty, KV } from "@/components/ui";

export default function TargetPage() {
  const [targets, setTargets] = useState<TargetInfo[]>([]);
  const [canaries, setCanaries] = useState<
    { canary_id: string; description: string; pattern_hint: string; tenant: string }[]
  >([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.targets().then(setTargets).catch((e) => setErr(String(e)));
    api
      .canaries("analyst")
      .then(setCanaries)
      .catch(() => setCanaries([]));
  }, []);

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-lg font-semibold text-slate-100">Target Setup</h1>
        <p className="text-xs text-slate-500">
          Hedef tanımı, sürümler, izinli yüzeyler ve erişim profilleri
        </p>
      </header>

      {err && (
        <div className="rounded-lg border border-bad/40 bg-bad/10 px-4 py-2 text-xs text-bad">{err}</div>
      )}

      {targets.map((t) => (
        <Card key={t.target_id} title={t.display_name} subtitle={`${t.target_id} · ${t.profile}`}>
          <div className="grid gap-5 lg:grid-cols-2">
            <div>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
                Sürümler (RevisionTriple)
              </h3>
              <div className="rounded-lg border border-base-700/50 bg-base-900/60 px-4 py-2">
                <KV k="model_revision" v={<span className="font-mono text-[11px]">{t.revisions.model_revision}</span>} />
                <KV k="application_revision" v={<span className="font-mono text-[11px]">{t.revisions.application_revision}</span>} />
                <KV k="policy_revision" v={<span className="font-mono text-[11px]">{t.revisions.policy_revision}</span>} />
              </div>

              <h3 className="mb-2 mt-4 text-xs font-semibold uppercase tracking-wider text-slate-500">
                Yetenekler
              </h3>
              <div className="flex flex-wrap gap-2">
                {Object.entries(t.capabilities).map(([k, v]) => (
                  <Badge key={k} status={v ? "completed" : "not_applicable"}>
                    {k}
                  </Badge>
                ))}
              </div>

              <h3 className="mb-2 mt-4 text-xs font-semibold uppercase tracking-wider text-slate-500">
                Red erişim profili
              </h3>
              <div className="space-y-1 text-xs text-slate-300">
                <div>
                  yazılabilir yüzeyler:{" "}
                  {t.red_writable_surfaces.map((s) => (
                    <Badge key={s} className="mr-1">{s}</Badge>
                  ))}
                </div>
                <div>
                  izinli gözlemler:{" "}
                  {t.red_observations.map((s) => (
                    <Badge key={s} className="mr-1">{s}</Badge>
                  ))}
                </div>
              </div>
            </div>

            <div>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
                Belgeler (tenant envanteri)
              </h3>
              <table className="grid">
                <thead>
                  <tr>
                    <th>Belge</th>
                    <th>Tenant</th>
                    <th>Başlık</th>
                  </tr>
                </thead>
                <tbody>
                  {t.documents.map((d) => (
                    <tr key={d.doc_id}>
                      <td className="font-mono text-[11px] text-accent-300">{d.doc_id}</td>
                      <td>
                        <Badge status={d.tenant === "tenant-beta" ? "warn" : "completed"}>
                          {d.tenant}
                        </Badge>
                      </td>
                      <td>{d.title}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </Card>
      ))}

      <Card
        title="Kanarya oracle envanteri"
        subtitle="Analyst görünümü — gizli değerler yalnızca evaluator_service rolüne açılır"
      >
        {canaries.length === 0 ? (
          <Empty>Kanarya listesi alınamadı (rol yetkisi yok olabilir).</Empty>
        ) : (
          <table className="grid">
            <thead>
              <tr>
                <th>Kimlik</th>
                <th>Açıklama</th>
                <th>Yapı ipucu</th>
                <th>Tenant</th>
              </tr>
            </thead>
            <tbody>
              {canaries.map((c) => (
                <tr key={c.canary_id}>
                  <td className="font-mono text-[11px] text-accent-300">{c.canary_id}</td>
                  <td>{c.description}</td>
                  <td className="font-mono text-[11px] text-slate-400">{c.pattern_hint}</td>
                  <td>{c.tenant}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <p className="mt-3 text-[11px] leading-4 text-slate-500">
          Vault izolasyonu: Red ve Blue süreçleri yalnızca bu metadata'yı görür.
          Gerçek sırra yalnızca bağımsız değerlendirme servisi erişir; girdide
          zaten bulunan metin sızmazı sayılmaz.
        </p>
      </Card>
    </div>
  );
}
