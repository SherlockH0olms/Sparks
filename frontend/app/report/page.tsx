"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useActiveCampaign } from "@/lib/store";
import { Button, Card, Empty } from "@/components/ui";

export default function ReportPage() {
  const [campaignId] = useActiveCampaign();
  const [report, setReport] = useState<{ markdown: string; html: string } | null>(null);
  const [mode, setMode] = useState<"rendered" | "markdown">("rendered");

  useEffect(() => {
    if (!campaignId) return;
    api.report(campaignId).then(setReport).catch(() => {});
  }, [campaignId]);

  const download = () => {
    if (!report || !campaignId) return;
    const blob = new Blob([report.html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `aegis-report-${campaignId}.html`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!campaignId) return <Empty>Aktif kampanya yok.</Empty>;
  if (!report) return <Empty>Rapor yok — kampanya tamamlanmadan rapor üretilmez.</Empty>;

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-slate-100">Report</h1>
          <p className="text-xs text-slate-500">
            Kanıtlardan üretilen önce/sonra raporu — ATLAS eşlemeleri, sınırlamalar ve kalan risk
            dahil
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button tone="ghost" onClick={() => setMode(mode === "rendered" ? "markdown" : "rendered")}>
            {mode === "rendered" ? "markdown göster" : "rendered göster"}
          </Button>
          <Button tone="primary" onClick={download}>
            HTML indir
          </Button>
        </div>
      </header>

      <Card title={`Rapor · ${campaignId}`} subtitle="yönetici özeti → teknik bulgular → ATLAS → düzeltme → doğrulama → kalan risk">
        {mode === "rendered" ? (
          <div
            className="report-body max-h-[70vh] overflow-y-auto text-sm leading-6 [&_h1]:mt-2 [&_h1]:text-lg [&_h1]:font-semibold [&_h1]:text-accent-300 [&_h2]:mt-6 [&_h2]:border-b [&_h2]:border-base-700 [&_h2]:pb-1 [&_h2]:text-base [&_h2]:font-semibold [&_h2]:text-slate-100 [&_h3]:mt-3 [&_h3]:text-sm [&_h3]:font-semibold [&_h3]:text-slate-200 [&_p]:mt-2 [&_ul]:mt-2 [&_ul]:list-disc [&_ul]:pl-5 [&_li]:mt-1 [&_table]:my-3 [&_table]:w-full [&_td]:border [&_td]:border-base-700 [&_td]:px-2 [&_td]:py-1 [&_th]:border [&_th]:border-base-700 [&_th]:bg-base-800 [&_th]:px-2 [&_th]:py-1 [&_th]:text-left [&_th]:text-accent-300"
            dangerouslySetInnerHTML={{ __html: sanitizeReportHtml(report.html) }}
          />
        ) : (
          <pre className="max-h-[70vh] overflow-y-auto whitespace-pre-wrap font-mono text-[11px] leading-4 text-slate-300">
            {report.markdown}
          </pre>
        )}
      </Card>
    </div>
  );
}

/**
 * Rapor HTML'i backend'den geliyor; yine de saldırı içerikleri güvenilmeyen
 * veri olduğu için script/iframe/link temizliği uygulanır (defense in depth).
 */
function sanitizeReportHtml(html: string): string {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, "")
    .replace(/<iframe[\s\S]*?<\/iframe>/gi, "")
    .replace(/ on\w+="[^"]*"/gi, "")
    .replace(/ href="(?!#)[^"]*"/gi, ' href="#"');
}
