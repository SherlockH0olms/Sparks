import "./globals.css";
import type { ReactNode } from "react";
import Link from "next/link";

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/target", label: "Target" },
  { href: "/campaign", label: "Campaign" },
  { href: "/coverage", label: "Coverage" },
  { href: "/findings", label: "Findings" },
  { href: "/repair", label: "Repair Lab" },
  { href: "/verification", label: "Verification" },
  { href: "/report", label: "Report" },
  { href: "/audit", label: "Audit" },
];

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="tr">
      <body className="min-h-screen bg-base-950 font-sans text-slate-200 antialiased">
        <div className="flex min-h-screen">
          <aside className="sticky top-0 hidden h-screen w-56 shrink-0 flex-col border-r border-base-700/50 bg-base-900/80 md:flex">
            <div className="flex items-center gap-2.5 border-b border-base-700/50 px-4 py-4">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-accent-500/50 bg-accent-500/10 text-accent-300">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 2l8 4v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6l8-4z" />
                  <path d="M9 12l2 2 4-4" />
                </svg>
              </div>
              <div>
                <div className="text-sm font-bold tracking-wide text-slate-100">AEGIS LOOP</div>
                <div className="text-[10px] uppercase tracking-widest text-slate-500">
                  AI Red Teaming
                </div>
              </div>
            </div>
            <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 py-3">
              {NAV.map((n) => (
                <Link
                  key={n.href}
                  href={n.href}
                  className="block rounded-lg px-3 py-2 text-[13px] text-slate-400 transition-colors hover:bg-base-800 hover:text-slate-100"
                >
                  {n.label}
                </Link>
              ))}
            </nav>
            <div className="border-t border-base-700/50 px-4 py-3 text-[10px] leading-4 text-slate-600">
              Tek platform: kapsam güdümlü keşif, yeniden üretilebilir bulgu,
              kontrollü düzeltme deneyi ve bağımsız doğrulama.
            </div>
          </aside>
          <main className="min-w-0 flex-1">
            <div className="mx-auto max-w-6xl px-4 py-6 md:px-8">{children}</div>
          </main>
        </div>
      </body>
    </html>
  );
}
