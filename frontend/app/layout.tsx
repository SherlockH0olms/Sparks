import type { Metadata } from "next";
import { Suspense } from "react";
import { Providers, AppShell } from "@/components/platform";
import "./globals.css";
export const metadata: Metadata = { title: "AEGIS LOOP · Security experiments", description: "Foundry offensive AI, local model security testing and independently verified remediation." };
export default function RootLayout({ children }: { children: React.ReactNode }) { return <html lang="tr"><body><Providers><Suspense fallback={<div className="boot">AEGIS LOOP yükleniyor…</div>}><AppShell>{children}</AppShell></Suspense></Providers></body></html>; }
