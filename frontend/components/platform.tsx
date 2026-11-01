"use client";
import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { QueryClient, QueryClientProvider, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, Actor, CampaignRow, Health, label, dateTime } from "@/lib/api";
import { PageHelp } from "./page-help";
import { campaignOption } from "@/lib/registration-names";

type AuthState = { user: Actor | null; health: Health | null; loading: boolean; login: (key: string) => Promise<void>; logout: () => Promise<void> };
const AuthContext = createContext<AuthState | null>(null);
export function useAuth() { const context = useContext(AuthContext); if (!context) throw new Error("Auth provider missing"); return context; }
export function useData<T>(path: string | null, interval = 0) {
  return useQuery<T>({ queryKey: [path], queryFn: ({ signal }) => api.get<T>(path!, signal), enabled: !!path, refetchInterval: interval || false, retry: 1, staleTime: 1000 });
}
export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(() => new QueryClient({ defaultOptions: { queries: { refetchOnWindowFocus: false } } }));
  return <QueryClientProvider client={client}><AuthProvider>{children}</AuthProvider></QueryClientProvider>;
}
function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<Actor | null>(null); const [health, setHealth] = useState<Health | null>(null); const [loading, setLoading] = useState(true);
  const client = useQueryClient();
  useEffect(() => {
    let alive = true;
    api.get<Actor>("/auth/me").then(u => alive && setUser(u)).catch(() => {}).finally(() => alive && setLoading(false));
    const refresh = () => api.get<Health>("/health").then(h => alive && setHealth(h)).catch(() => {});
    refresh(); const timer = setInterval(refresh, 10000); const expired = () => { setUser(null); client.clear(); };
    window.addEventListener("aegis-auth-expired", expired);
    return () => { alive = false; clearInterval(timer); window.removeEventListener("aegis-auth-expired", expired); };
  }, [client]);
  const value = { user, health, loading, login: async (key: string) => { const u = await api.post<Actor>("/auth/login", { key }); setUser(u); client.clear(); }, logout: async () => { await api.post("/auth/logout"); setUser(null); client.clear(); } };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
const nav = [{ href: "/", title: "Overview", icon: "grid" }, { href: "/guide", title: "How to use", icon: "file" }, { href: "/target", title: "Targets", icon: "target" }, { href: "/campaign", title: "Campaign", icon: "activity" }, { href: "/coverage", title: "Coverage", icon: "layers" }, { href: "/findings", title: "Findings", icon: "shield" }, { href: "/repair", title: "Repair Lab", icon: "tool" }, { href: "/verification", title: "Verification", icon: "check" }, { href: "/report", title: "Report", icon: "file" }, { href: "/audit", title: "Audit and access", icon: "lock" }];
export function Icon({ name, size = 18 }: { name: string; size?: number }) {
  const paths: Record<string, React.ReactNode> = {
    shield: <path d="M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6l-8-3Z" />, target: <><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="4" /><path d="m12 12 7-7" /></>,
    grid: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
    activity: <path d="M2 12h5l3-8 4 16 3-8h5" />, layers: <><path d="m3 8 9-5 9 5-9 5-9-5Zm0 5 9 5 9-5m-18 5 9 5 9-5" /></>,
    tool: <path d="M14 6a5 5 0 0 0-6 6L3 17a3 3 0 0 0 4 4l5-5a5 5 0 0 0 6-6l-3 3-4-4 3-3Z" />, check: <><circle cx="12" cy="12" r="9" /><path d="m7 12 3 3 7-7" /></>,
    file: <><path d="M6 3h8l4 4v14H6V3Zm8 0v5h4M9 12h6m-6 4h6" /></>, lock: <><rect x="5" y="10" width="14" height="11" rx="2" /><path d="M8 10V6a4 4 0 0 1 8 0v4m-4 5v2" /></>,
    arrow: <path d="M4 12h16m-6-6 6 6-6 6" />, plus: <path d="M12 4v16M4 12h16" />, close: <path d="m6 6 12 12M6 18 18 6" />, download: <path d="M12 3v12m-5-5 5 5 5-5M5 17v4h14v-4" />,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name] ?? paths.shield}</svg>;
}
export function Badge({ value, children }: { value?: string; children?: React.ReactNode }) {
  const tone = ["violation", "failed", "rejected", "fail", "budget_exhausted", "critical"].includes(value ?? "") ? "red" : ["pass", "validated_in_scope", "ready", "confirmed"].includes(value ?? "") ? "green" : ["inconclusive", "paused", "timeout", "invalid_test", "high", "interrupted"].includes(value ?? "") ? "amber" : ["discovering", "baselining", "repairing", "verifying", "queued"].includes(value ?? "") ? "cyan" : "neutral";
  return <span className={"badge " + tone}>{children ?? label(value ?? "")}</span>;
}
export function Button({ children, variant = "default", ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "default" | "primary" | "danger" | "ghost" }) { return <button className={"button " + variant} {...props}>{children}</button>; }
export function Panel({ title, subtitle, action, children, className = "" }: { title?: React.ReactNode; subtitle?: React.ReactNode; action?: React.ReactNode; children: React.ReactNode; className?: string }) { return <section className={"panel " + className}>{title && <div className="panel-head"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{action}</div>}<div className="panel-body">{children}</div></section>; }
export function Heading({ eyebrow, title, description, action }: { eyebrow?: string; title: string; description: string; action?: React.ReactNode }) { return <header className="page-heading"><div>{eyebrow && <span className="eyebrow">{eyebrow}</span>}<h1>{title}</h1><p>{description}</p></div>{action}</header>; }
export function Empty({ title = "No records yet", children, action }: { title?: string; children?: React.ReactNode; action?: React.ReactNode }) { return <div className="empty"><div className="empty-icon"><Icon name="layers" size={26} /></div><h3>{title}</h3><p>{children}</p>{action}</div>; }
export function Notice({ children, error = false }: { children: React.ReactNode; error?: boolean }) { return <div className={"notice " + (error ? "error" : "")} role={error ? "alert" : "status"}>{children}</div>; }
export function Loading() { return <div className="loading" aria-label="Loading"><span /><span /><span /></div>; }
export function QueryError({ error }: { error: Error | null }) { return error ? <Notice error>{error.message}. Check the connection and your access permissions.</Notice> : null; }
export function Stat({ title, value, hint, tone = "" }: { title: string; value: React.ReactNode; hint: string; tone?: string }) { return <div className={"stat " + tone}><span>{title}</span><strong>{value}</strong><small>{hint}</small></div>; }
export function Meter({ value, tone = "cyan" }: { value: number | null | undefined; tone?: string }) { return <div className={"meter " + tone}><div style={{ width: Math.max(0, Math.min(100, value ?? 0)) + "%" }} /></div>; }
export function Modal({ title, children, onClose }: { title: string; children: React.ReactNode; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null); useEffect(() => { ref.current?.showModal(); }, []);
  return <dialog ref={ref} className="modal" onCancel={onClose} onClick={e => e.target === e.currentTarget && onClose()}><div className="modal-header"><h2>{title}</h2><Button variant="ghost" aria-label="Close" onClick={onClose}><Icon name="close" /></Button></div>{children}</dialog>;
}
export function Field({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) { return <label className="field"><span>{title}</span>{children}{hint && <small>{hint}</small>}</label>; }
export function JsonBlock({ value }: { value: unknown }) { return <pre className="code">{typeof value === "string" ? value : JSON.stringify(value, null, 2)}</pre>; }
export function useCampaignId(): [string | null, (id: string) => void] {
  const search = useSearchParams(); const router = useRouter(); const pathname = usePathname();
  const fromUrl = search.get("campaign"); const [stored, setStored] = useState<string | null>(null);
  useEffect(() => { try { setStored(localStorage.getItem("aegis-campaign")); } catch {} }, []);
  const set = (id: string) => { try { localStorage.setItem("aegis-campaign", id); } catch {} setStored(id); const next = new URLSearchParams(search); next.set("campaign", id); router.replace(pathname + "?" + next.toString()); };
  useEffect(() => { if (fromUrl) { try { localStorage.setItem("aegis-campaign", fromUrl); } catch {} } }, [fromUrl]);
  return [fromUrl || stored, set];
}
export function CampaignPicker({ value, onChange }: { value: string | null; onChange: (id: string) => void }) {
  const rows = useData<CampaignRow[]>("/campaigns", 5000);
  return <select aria-label="Active campaigns" className="campaign-picker" value={value ?? ""} onChange={e => onChange(e.target.value)}><option value="">Select a campaign</option>{rows.data?.map(c => <option key={c.id} value={c.id}>{campaignOption(c)} · {label(c.state)}{c.is_latest ? " · Latest test" : ""}</option>)}</select>;
}
export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, health, loading, logout } = useAuth(); const pathname = usePathname(); const [cid, setCid] = useCampaignId();
  if (loading) return <div className="boot"><Icon name="shield" size={36} /><span>AEGIS LOOP</span><Loading /></div>;
  if (!user) return <LoginScreen />;
  return <div className="app-shell"><aside className="sidebar"><Link className="brand" href="/"><span className="brand-mark"><Icon name="shield" size={27} /></span><span>AEGIS <b>LOOP</b><small>AI SECURITY EXPERIMENTS</small></span></Link><div className="workspace"><span className="workspace-symbol">{user.workspace.slice(0, 1).toUpperCase()}</span><div><strong>{user.workspace}</strong><small>Security workspace</small></div><Badge>{label(user.role)}</Badge></div><span className="nav-label">WORKSPACE</span><nav>{nav.map(n => <Link key={n.href} aria-label={n.title} title={n.title} href={n.href + (cid ? "?campaign=" + cid : "")} className={(n.href === "/" ? pathname === "/" : pathname.startsWith(n.href)) ? "active" : ""}><Icon name={n.icon} /><span>{n.title}</span>{n.href === "/campaign" && <span className="nav-dot" />}</Link>)}</nav><div className="sidebar-bottom"><div className="boundary"><Icon name="lock" /><span>Registered targets<br /><small>Isolated local tools</small></span></div><small>AEGIS LOOP v2.0</small></div></aside><div className="main-column"><header className="topbar"><div className="breadcrumb">Workspace <span>/</span> <strong>{nav.find(n => n.href === pathname)?.title ?? "Finding details"}</strong></div><div className="topbar-actions"><span className={"connection " + (health?.red.configured ? "configured" : "")}><i />Red {health?.red.configured ? "configured" : "needs configuration"}</span><span className="user-avatar">{user.name.slice(0, 1)}</span><Button variant="ghost" onClick={logout}>Sign out</Button></div></header><main className="content">{health?.fixture_environment && <Notice>TEST FIXTURE — this demo uses simulated models and does not make live provider calls.</Notice>}<PageHelp path={pathname} campaignId={cid}/>{children}</main><footer className="footer"><span>Evidence-based decisions · Versioned targets · Measured budgets</span><span>Red / Local target / Judge</span></footer></div></div>;
}
function LoginScreen() {
  const { login, health } = useAuth(); const [key, setKey] = useState(""); const [busy, setBusy] = useState(false); const [error, setError] = useState<string | null>(null);
  return <div className="login-screen"><div className="login-visual"><div className="eyebrow">AEGIS LOOP / V2</div><h1>Test.<br />Verify.<br /><span>Improve.</span></h1><p>Test your local AI application with Red, inspect the evidence, and verify defense improvements.</p><div className="login-flow"><span>RED LAB</span><Icon name="arrow" /><span>REPAIR LAB</span><Icon name="arrow" /><span>VERIFICATION</span></div><div className="orb"><Icon name="shield" size={130} /></div></div><form className="login-card" onSubmit={async e => { e.preventDefault(); setBusy(true); setError(null); try { await login(key); } catch (err) { setError((err as Error).message); } finally { setBusy(false); } }}><span className="brand-mark"><Icon name="shield" size={30} /></span><h2>Sign in to your workspace</h2><p>Enter your platform access key. Your model provider keys are configured separately.</p>{health?.configuration_notice && <Notice>{health.configuration_notice}</Notice>}<Field title="Access key" hint="Use AEGIS_ADMIN_TOKEN from .env for the first administrator login. Red and Judge API keys go in .env, in their own provider settings."><input aria-label="Access key" type="password" autoComplete="current-password" value={key} onChange={e => setKey(e.target.value)} required /></Field>{error && <Notice error>{error}</Notice>}<Button variant="primary" type="submit" disabled={busy}>{busy ? "Signing in…" : "Open workspace"}<Icon name="arrow" /></Button><details className="login-help"><summary>First time using AEGIS?</summary><p>Use AEGIS_ADMIN_TOKEN from the project's .env file to sign in as the first administrator. Configure AEGIS_RED_* and AEGIS_JUDGE_* in that file for the two model services. After signing in, open How to use for the complete walkthrough.</p></details><small>Your access key determines your workspace and permissions.</small></form></div>;
}

