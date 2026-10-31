export const API_BASE = "/api";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json();
}

export function idem(): string {
  return `idem-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export interface TargetInfo {
  target_id: string;
  display_name: string;
  profile: string;
  revisions: { model_revision: string; application_revision: string; policy_revision: string };
  capabilities: Record<string, boolean>;
  red_writable_surfaces: string[];
  red_observations: string[];
  documents: { doc_id: string; tenant: string; title: string }[];
}

export interface CampaignRow {
  campaign_id: string;
  state: string;
  target: string;
  attempts: number;
  findings: number;
  created: string;
}

export interface CoverageMetrics {
  total_cells: number;
  applicable: number;
  not_applicable: number;
  completed: number;
  coverage_pct: number;
  cells_with_violations: number;
}

export interface CampaignSummary extends CoverageMetrics {
  campaign_id: string;
  state: string;
  target: string;
  attempts: number;
  findings: number;
  groups: number;
  experiments: number;
  verification_runs: number;
  baseline?: { utility?: number; answered?: number; questions?: number };
  budget?: Record<string, { limit: number; used: number; reserved: number; remaining: number }>;
}

export const api = {
  health: () => req<{ status: string; campaigns: number; kill_switch: boolean }>("/health"),
  targets: () => req<TargetInfo[]>("/targets"),
  campaigns: () => req<CampaignRow[]>("/campaigns"),
  campaign: (id: string) => req<CampaignSummary>(`/campaigns/${id}`),
  createCampaign: (body: { target_id: string; languages?: string[] }) =>
    req<{ campaign_id: string; state: string }>("/campaigns", {
      method: "POST",
      body: JSON.stringify(body),
      headers: { "Idempotency-Key": idem() },
    }),
  startCampaign: (id: string) =>
    req<{ ok: boolean; message: string }>(`/campaigns/${id}/start?background=true`, {
      method: "POST",
      headers: { "Idempotency-Key": idem() },
    }),
  pauseCampaign: (id: string) =>
    req<{ ok: boolean }>(`/campaigns/${id}/pause`, { method: "POST" }),
  resumeCampaign: (id: string) =>
    req<{ ok: boolean }>(`/campaigns/${id}/resume`, { method: "POST" }),
  cancelCampaign: (id: string) =>
    req<{ ok: boolean }>(`/campaigns/${id}/cancel`, { method: "POST" }),
  coverage: (id: string) =>
    req<{ metrics: CoverageMetrics; cells: CoverageCell[] }>(`/campaigns/${id}/coverage`),
  attempts: (id: string, limit = 60) =>
    req<AttemptRow[]>(`/campaigns/${id}/attempts?limit=${limit}`),
  findings: (id: string) => req<FindingRow[]>(`/campaigns/${id}/findings`),
  finding: (id: string, fid: string) => req<FindingDetail>(`/campaigns/${id}/findings/${fid}`),
  repair: (id: string) => req<RepairExperimentView[]>(`/campaigns/${id}/repair`),
  verification: (id: string) => req<VerificationRunView[]>(`/campaigns/${id}/verification`),
  budget: (id: string) =>
    req<Record<string, { limit: number; used: number; reserved: number; remaining: number }>>(
      `/campaigns/${id}/budget`
    ),
  report: (id: string) => req<{ markdown: string; html: string }>(`/campaigns/${id}/report`),
  audit: () => req<{ ts: string; action: string; detail: Record<string, unknown> }[]>("/audit"),
  canaries: (role = "analyst") =>
    req<{ canary_id: string; description: string; pattern_hint: string; tenant: string }[]>(
      `/vault/canaries?role=${role}`
    ),
  killSwitch: () => req<{ ok: boolean }>("/system/kill-switch", { method: "POST" }),
};

export interface CoverageCell {
  property: string;
  family: string;
  language: string;
  access_profile: string;
  status: string;
  attempts: number;
  valid_attempts: number;
  violations: number;
  min_required: number;
  not_applicable_reason: string;
}

export interface AttemptRow {
  attempt_id: string;
  strategy: string;
  language: string;
  cell: string[];
  execution_status: string | null;
  verdict: string | null;
  turns_preview: string[];
  response_preview: string;
  wall_ms: number;
  ts: string;
}

export interface FindingRow {
  finding_id: string;
  group_id: string;
  violated_property: string;
  boundary: string;
  component: string;
  observed_effect: string;
  severity: string;
  reproduction_rate: number;
  diagnosis: string;
  atlas: { technique_id: string; name: string; justification: string }[];
  minimized_turns: string[];
  original_attempt_id: string;
}

export interface FindingDetail extends FindingRow {
  evidence: { kind: string; content: string; source: string }[];
  diagnosis_notes: string;
  reproduction_trials: { trial: number; violation: boolean; response_excerpt: string }[];
  original_attempt: { turns: string[]; response: string; execution_status: string | null; verdict: string | null } | null;
  limitations: string[];
}

export interface RepairExperimentView {
  experiment_id: string;
  finding_id: string;
  baseline_revision: string;
  rows: {
    candidate_id: string;
    label: string;
    description: string;
    diff: string;
    controls: string[];
    build: string;
    security_pretest: { replayed: number; violations_remaining: number } | string;
    utility: number | string;
    avg_wall_ms: number | string;
    state: string;
    rejection_reasons: string[];
    rollback: string;
  }[];
}

export interface VerificationRunView {
  run_id: string;
  experiment_id: string;
  candidate_id: string;
  suites: Record<string, Record<string, number>>;
  verdict: string | null;
}
