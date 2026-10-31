export type Role = "viewer" | "analyst" | "maintainer" | "admin";
export type Actor = { id: string; name: string; role: Role; workspace: string };
export type Health = { status: string; version: string; auth_configured: boolean; red: { configured: boolean; model: string | null; issues: string[]; provider: string }; judge: { configured: boolean; issues: string[] }; local_defaults: { endpoint: string; model: string }; workers: { configured_workers: number; active_jobs: number; controller_alive: boolean }; fixture_environment: boolean; configuration_notice: string | null };
export type Coverage = { total_cells: number; applicable: number; not_applicable: number; completed: number; coverage_pct: number | null; cells_with_violations: number; inconclusive: number };
export type Cell = { id: string; property: string; family: string; language: string; surface: string; required_turns: number; access_profile: string; applicable: boolean; reason: string; minimum: number; attempts: number; valid: number; violations: number; inconclusive: number; digests: string[] };
export type Target = { id: string; name: string; revision: string; endpoint: string; model: string; model_revision: string; application_revision: string; capabilities: Record<string, boolean>; documents: { id: string; tenant: string; title: string; assigned_to_red: boolean; confidential: boolean }[]; utility_count: number; preflight: { connected: boolean; issues: string[] } | null };
export type TargetSpec = { name: string; endpoint: string; model: string; model_revision: string; application_revision: string; tenant: string; task_policy: string; capabilities: Record<string, boolean>; documents: { id: string; tenant: string; title: string; body: string; assigned_to_red: boolean; confidential: boolean }[]; utility_cases: { id: string; language: string; tenant: string; message: string; expected_terms: string[]; expected_tool: string | null; expect_json: boolean; forbid_refusal: boolean }[]; defenses: Record<string, boolean>; red_observations: string[]; writable_surfaces: string[] };
export type Limits = { target_calls: number; generator_calls: number; judge_calls: number; tokens: number; wall_seconds: number };
export type CampaignSpec = { target_id: string; languages: string[]; properties: string[]; families: string[]; minimum_tests_per_cell: number; max_discovery_attempts: number; max_turns: number; max_candidate_chars: number; reproduction_trials: number; minimum_reproduction_rate: number; max_repair_groups: number; final_cases_per_property: number; adaptive_attempts: number; utility_floor: number; limits: Limits };
export type Operation = { operation_id: string; bucket: string; purpose: string; reserved: Record<string, number>; actual: Record<string, number>; status: string; started: number; finished: number | null };
export type Budget = { limits: Record<string, number>; allocations: Record<string, Record<string, number>>; used: Record<string, number>; reserved: Record<string, number>; remaining: Record<string, number>; operations?: Operation[]; total_operations?: number; overrun: boolean };
export type CampaignRow = { id: string; state: string; phase: string; target_id: string; target_revision: string; created_at: number; attempts: number; findings: number; coverage: Coverage };
export type Campaign = { id: string; state: string; phase: string; target_id: string; target_revision: string; spec: CampaignSpec; progress: Record<string, number>; baseline: { questions: number; valid: number; answered: number; utility: number | null; false_blocks: number } | null; error: { type: string; message: string } | null; started_at: number | null; finished_at: number | null; checkpoint: Record<string, unknown> | null; coverage: Coverage; attempts: number; findings: number; groups: number; experiments: number; verification_runs: number; budget: Budget; worker: { state: string; heartbeat: number | null; owner: string | null; lease_until: number } };
export type EventRecord = { seq: number; workspace: string; campaign: string; kind: string; payload: Record<string, unknown>; created: number };
export type Assessment = { property?: string; verdict?: string; boundary?: string; effect?: string; oracle?: string; rationale?: string; evidence?: Record<string, unknown>[] };
export type Candidate = { language: string; turns: string[]; document_body: string | null; hypothesis: string; expected_signal: string };
export type Step = { index: number; message: string; trace: { status: string; response: string; raw_response?: string; retrieval: Record<string, unknown>[]; tools: Record<string, unknown>[]; refused?: boolean; schema_valid?: boolean; error?: string; provenance?: string }; assessment: Assessment };
export type Attempt = { id: string; phase: string; cell: Cell; candidate_digest: string; execution_status: string; verdict: string | null; turns: number; response_preview: string; created_at: number };
export type AttemptDetail = { id: string; candidate: Candidate; injected_document: Record<string, unknown> | null; session_id: string; steps: Step[]; execution_status: string; assessment: Assessment; target_revision: string };
export type Finding = { id: string; property: string; boundary: string; effect: string; severity: string; reproduction_rate: number; diagnosis: string; atlas: { technique_id: string | null; name: string; url?: string; reason: string; catalog_commit: string }; status: string; diagnosis_note?: string; minimized_candidate?: Candidate; reproduction?: { attempt_id: string; valid: boolean; same_violation: boolean }[]; original_attempt?: AttemptDetail; assessment?: Assessment; limitations?: string[] };
export type Metric = { attempts?: number; valid: number; violations?: number; asr?: number | null; status: string; questions?: number; answered?: number; utility?: number | null; false_blocks?: number; minimum?: number; inconclusive?: number; timeouts?: number; infrastructure_errors?: number };
export type RepairCandidate = { id: string; label: string; patch: Record<string, boolean>; configuration: Record<string, boolean>; diff: string; artifact: { hash: string }; state: string; gates: { build?: { status: string; runner: string; attempt_id: string }; security?: Metric; utility?: { questions: number; answered: number; utility: number | null; false_blocks: number } }; rejection_reasons: string[]; limitations: string[]; rollback: Record<string, unknown> };
export type Experiment = { id: string; finding_id: string; property: string; target_revision: string; candidates: RepairCandidate[]; winner: string | null; winner_hash: string | null; frozen_at: number | null; state: string };
export type Verification = { id: string; experiment_id: string; candidate_id: string; candidate_hash: string; target_revision: string; protocol_revision: string; set_revision: string; verdict: string; suites: { baseline: Record<string, Metric>; candidate: Record<string, Metric> }; utility_delta: number | null; independent: boolean; limitations: string[]; closed_at: number };

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch("/api" + path, { credentials: "include", ...init, headers: { "Content-Type": "application/json", ...init?.headers } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    if (response.status === 401 && typeof window !== "undefined") window.dispatchEvent(new Event("aegis-auth-expired"));
    const detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? response.statusText);
    throw new ApiError(response.status, detail);
  }
  return response.json();
}
export const api = {
  get: <T,>(path: string, signal?: AbortSignal) => request<T>(path, { signal }),
  post: <T,>(path: string, body?: unknown, key?: string) => request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body), headers: { "Idempotency-Key": key ?? crypto.randomUUID() } }),
};
export const terminal = new Set(["completed", "cancelled", "failed", "budget_exhausted"]);
export const labels: Record<string, string> = {
  draft: "Taslak", queued: "Sırada", preflight: "Ön kontrol", baselining: "Normal kullanım", discovering: "Keşif", reproducing: "Yeniden üretim", repairing: "Düzeltme", verifying: "Bağımsız doğrulama", reporting: "Rapor", paused: "Duraklatıldı", completed: "Tamamlandı", cancelled: "İptal edildi", failed: "Başarısız", budget_exhausted: "Bütçe tükendi",
  violation: "İhlal", no_violation_observed: "İhlal gözlenmedi", inconclusive: "Belirsiz", invalid_test: "Geçersiz test", timeout: "Zaman aşımı", infrastructure_error: "Altyapı hatası", interrupted: "Kesintiye uğradı",
  validated_in_scope: "Kapsamda doğrulandı", rejected: "Reddedildi", ready: "Ön testleri geçti", proposed: "Önerildi", reference: "Referans", frozen: "Donduruldu", pass: "Geçti", fail: "Geçemedi", confirmed: "Doğrulandı",
  task_constraint: "Görev sınırı", data_instruction_separation: "Veri / talimat sınırı", tenant_isolation: "Tenant izolasyonu", secret_confidentiality: "Gizli veri", tool_authorization: "Araç yetkisi", output_integrity: "Çıktı sözleşmesi", session_isolation: "Oturum izolasyonu",
  direct_injection: "Doğrudan injection", indirect_injection: "Belgeden injection", authority_spoofing: "Yetki taklidi", multi_turn_manipulation: "Çok turlu yönlendirme", encoding_evasion: "Kodlama varyasyonu", tenant_probe: "Tenant sınaması", tool_misuse: "Araç sınaması", schema_abuse: "Şema sınaması",
  baseline: "Baseline", discovery: "Keşif", reproduction: "Yeniden üretim", development: "Düzeltme geliştirme", final: "Final güvenlik", utility: "Normal kullanım", replay: "Bilinen ihlal", unseen: "Görülmemiş örnek", adaptive: "Adaptif yeniden saldırı",
  target_calls: "Hedef çağrıları", generator_calls: "Foundry çağrıları", judge_calls: "Judge çağrıları", tokens: "Token", wall_seconds: "Süre (sn)",
};
export const label = (value: string) => labels[value] ?? value;
export const percent = (value: number | null | undefined) => value == null ? "—" : (value * 100).toFixed(1).replace(/\.0$/, "") + "%";
export const dateTime = (value: number | null | undefined) => value ? new Date(value * 1000).toLocaleString("tr-TR") : "—";
export const short = (value: string | undefined, size = 12) => value ? value.slice(0, size) : "—";
export function download(filename: string, text: string, type = "application/json") { const url = URL.createObjectURL(new Blob([text], { type })); const a = document.createElement("a"); a.href = url; a.download = filename; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
