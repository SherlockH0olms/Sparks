import clsx from "clsx";
import type { ReactNode } from "react";

export function Card({
  children,
  className,
  title,
  subtitle,
  actions,
}: {
  children: ReactNode;
  className?: string;
  title?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <section
      className={clsx(
        "rounded-xl border border-base-700/60 bg-base-850/70 shadow-[0_1px_0_rgba(255,255,255,0.03)_inset]",
        className
      )}
    >
      {(title || actions) && (
        <header className="flex items-center justify-between gap-3 border-b border-base-700/50 px-4 py-3">
          <div>
            <h2 className="text-sm font-semibold tracking-wide text-slate-100">{title}</h2>
            {subtitle && <p className="mt-0.5 text-xs text-slate-400">{subtitle}</p>}
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

export function Stat({
  label,
  value,
  hint,
  tone = "default",
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: "default" | "ok" | "bad" | "warn" | "accent";
}) {
  const toneCls = {
    default: "text-slate-100",
    ok: "text-ok",
    bad: "text-bad",
    warn: "text-warn",
    accent: "text-accent-300",
  }[tone];
  return (
    <div className="rounded-lg border border-base-700/50 bg-base-900/60 px-4 py-3">
      <div className="text-[11px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className={clsx("mt-1 text-2xl font-semibold tabular-nums", toneCls)}>{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
    </div>
  );
}

const STATUS_TONES: Record<string, string> = {
  violation: "bg-bad/15 text-bad border-bad/40",
  violation_observed: "bg-bad/15 text-bad border-bad/40",
  fail: "bg-bad/15 text-bad border-bad/40",
  gate_failed: "bg-bad/15 text-bad border-bad/40",
  rejected: "bg-bad/15 text-bad border-bad/40",
  critical: "bg-bad/15 text-bad border-bad/40",
  high: "bg-bad/15 text-bad border-bad/40",
  no_violation_observed: "bg-ok/10 text-ok border-ok/40",
  pass: "bg-ok/10 text-ok border-ok/40",
  validated_in_scope: "bg-ok/10 text-ok border-ok/40",
  assessed_no_violation: "bg-ok/10 text-ok border-ok/40",
  low: "bg-ok/10 text-ok border-ok/40",
  inconclusive: "bg-warn/10 text-warn border-warn/40",
  insufficient_depth: "bg-warn/10 text-warn border-warn/40",
  medium: "bg-warn/10 text-warn border-warn/40",
  paused: "bg-warn/10 text-warn border-warn/40",
  budget_exhausted: "bg-warn/10 text-warn border-warn/40",
  not_applicable: "bg-slate-500/10 text-slate-400 border-slate-500/40",
  not_tested: "bg-slate-500/10 text-slate-400 border-slate-500/40",
  cancelled: "bg-slate-500/10 text-slate-400 border-slate-500/40",
  completed: "bg-accent-500/15 text-accent-300 border-accent-500/40",
  discovering: "bg-accent-500/15 text-accent-300 border-accent-500/40",
  baselineing: "bg-accent-500/15 text-accent-300 border-accent-500/40",
  baselining: "bg-accent-500/15 text-accent-300 border-accent-500/40",
  verifying_findings: "bg-accent-500/15 text-accent-300 border-accent-500/40",
  timeout: "bg-warn/10 text-warn border-warn/40",
  infrastructure_error: "bg-warn/10 text-warn border-warn/40",
  invalid_test: "bg-slate-500/10 text-slate-400 border-slate-500/40",
};

export function Badge({
  children,
  status,
  className,
}: {
  children: ReactNode;
  status?: string;
  className?: string;
}) {
  const tone = (status && STATUS_TONES[status.toLowerCase()]) || "bg-base-700/60 text-slate-300 border-base-600/60";
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-medium leading-4",
        tone,
        className
      )}
    >
      {children}
    </span>
  );
}

export function Button({
  children,
  onClick,
  tone = "default",
  disabled,
  className,
  title,
}: {
  children: ReactNode;
  onClick?: () => void;
  tone?: "default" | "primary" | "danger" | "ghost";
  disabled?: boolean;
  className?: string;
  title?: string;
}) {
  const tones = {
    default: "bg-base-700 hover:bg-base-600 text-slate-200 border-base-600",
    primary: "bg-accent-500 hover:bg-accent-400 text-base-950 border-accent-400 font-semibold",
    danger: "bg-bad/80 hover:bg-bad text-base-950 border-bad font-semibold",
    ghost: "bg-transparent hover:bg-base-800 text-slate-300 border-transparent",
  }[tone];
  return (
    <button
      type="button"
      title={title}
      onClick={onClick}
      disabled={disabled}
      className={clsx(
        "rounded-lg border px-3 py-1.5 text-xs transition-colors disabled:cursor-not-allowed disabled:opacity-40",
        tones,
        className
      )}
    >
      {children}
    </button>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-base-700/60 px-4 py-8 text-center text-sm text-slate-500">
      {children}
    </div>
  );
}

export function Mono({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <code className={clsx("rounded bg-base-900/80 px-1.5 py-0.5 font-mono text-[11px] text-accent-300", className)}>
      {children}
    </code>
  );
}

export function KV({ k, v }: { k: string; v: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-1 text-xs">
      <span className="text-slate-500">{k}</span>
      <span className="text-right text-slate-200">{v}</span>
    </div>
  );
}

export function Meter({ value, tone = "accent" }: { value: number; tone?: "accent" | "ok" | "bad" | "warn" }) {
  const pct = Math.max(0, Math.min(100, value));
  const bar = { accent: "bg-accent-500", ok: "bg-ok", bad: "bg-bad", warn: "bg-warn" }[tone];
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-base-800">
      <div className={clsx("h-full rounded-full transition-all", bar)} style={{ width: `${pct}%` }} />
    </div>
  );
}
