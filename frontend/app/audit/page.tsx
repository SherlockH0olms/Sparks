"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Badge, Button, Card, Empty } from "@/components/ui";

interface AuditEntry {
  ts: string;
  action: string;
  detail: Record<string, unknown>;
}

export default function AuditPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [confirmKill, setConfirmKill] = useState(false);

  useEffect(() => {
    api.audit().then(setEntries).catch(() => {});
    const t = setInterval(() => api.audit().then(setEntries).catch(() => {}), 4000);
    return () => clearInterval(t);
  }, []);

  const kill = async () => {
    try {
      await api.killSwitch();
      setConfirmKill(false);
      const rows = await api.audit();
      setEntries(rows);
    } catch {
      /* hata audit'te görünür */
    }
  };

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-slate-100">Audit</h1>
          <p className="text-xs text-slate-500">
            Tüm kontrol eylemleri denetlenebilir kayıtlara bağlanır
          </p>
        </div>
        {confirmKill ? (
          <div className="flex items-center gap-2">
            <span className="text-xs text-warn">Tüm kampanyalar iptal edilecek. Emin misiniz?</span>
            <Button tone="danger" onClick={kill}>
              Evet, kill switch
            </Button>
            <Button tone="ghost" onClick={() => setConfirmKill(false)}>
              Vazgeç
            </Button>
          </div>
        ) : (
          <Button tone="danger" onClick={() => setConfirmKill(true)}>
            Kill Switch
          </Button>
        )}
      </header>

      <Card title="Denetim kaydı" subtitle={`${entries.length} kayıt`}>
        {entries.length === 0 ? (
          <Empty>Kayıt yok.</Empty>
        ) : (
          <table className="grid">
            <thead>
              <tr>
                <th>Zaman (UTC)</th>
                <th>Eylem</th>
                <th>Detay</th>
              </tr>
            </thead>
            <tbody>
              {entries
                .slice()
                .reverse()
                .map((e, i) => (
                  <tr key={i}>
                    <td className="whitespace-nowrap font-mono text-[11px] text-slate-500">
                      {e.ts}
                    </td>
                    <td>
                      <Badge status={e.action.includes("kill") ? "fail" : "completed"}>
                        {e.action}
                      </Badge>
                    </td>
                    <td className="font-mono text-[11px] text-slate-400">
                      {JSON.stringify(e.detail).slice(0, 120)}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
