"use client";
import { useState } from "react";
import { TargetConnection, TargetSpec, label } from "@/lib/api";
import { Badge, Button, Field, Notice, Panel } from "./platform";
import { deployments } from "./target-connection";

type Document = TargetSpec["documents"][number];
type Task = TargetSpec["utility_cases"][number];
const newId = (prefix: string) => prefix + "_" + crypto.randomUUID().replaceAll("-", "").slice(0, 16);

export function validateTargetSetup(spec: TargetSpec, checkAccess = true) {
  if (!spec.documents.length || !spec.utility_cases.length) throw new Error("Add at least one document and one normal-use task.");
  for (const [i, d] of spec.documents.entries()) {
    if (!d.title.trim() || !d.tenant.trim() || !d.body.trim()) throw new Error(`Document ${i + 1}: enter a title, owner group, and document content.`);
  }
  for (const [i, task] of spec.utility_cases.entries()) {
    if (!task.message.trim() || !task.tenant.trim()) throw new Error(`Task ${i + 1}: enter a user question and user group.`);
    if (!spec.documents.some(d => d.tenant === task.tenant)) throw new Error(`Task ${i + 1}: its user group needs at least one document.`);
  }
  if (!checkAccess) return;
  if (!spec.documents.some(d => d.tenant === spec.tenant)) throw new Error("The Red user group needs at least one document. Update its group or add a document.");
  if (spec.capabilities.multi_tenant && new Set(spec.documents.map(d => d.tenant)).size < 2) throw new Error("Multiple-tenant tests need documents from two owner groups. Add another group or disable Multiple tenants.");
  if (spec.writable_surfaces.includes("assigned_document") && !spec.documents.some(d => d.assigned_to_red && d.tenant === spec.tenant)) throw new Error("Allow Red to edit a document in its own group, or disable the Assigned document attack surface.");
}

export function DocumentEditor({documents, tenant, onChange}: {documents: Document[]; tenant: string; onChange: (documents: Document[]) => void}) {
  const [addedId, setAddedId] = useState<string|null>(null);
  const update = (index: number, patch: Partial<Document>) => onChange(documents.map((d, i) => i === index ? {...d, ...patch} : d));
  return <section className="stack" aria-label="Document editor">
    <div className="row between wrap"><div><h3>Documents</h3><p className="small muted">These documents form the test workspace supplied to your model. Each owner group has its own access boundary.</p></div><Button onClick={() => {const id=newId("doc");setAddedId(id);onChange([...documents, {id, title: "", tenant, body: "", assigned_to_red: false, confidential: false}]);}}>Add document</Button></div>
    {documents.map((d, i) => <details key={d.id} className="target-editor" open={i === 0 || d.id === addedId}>
      <summary><strong>{d.title || `New document ${i + 1}`}</strong><span>{d.tenant || "Choose an owner"}{d.confidential ? " · Confidential" : ""}{d.assigned_to_red ? " · Red may edit" : ""}</span></summary>
      <div className="stack target-editor-body"><div className="form-grid">
        <Field title="Document title"><input aria-label="Document title" maxLength={300} value={d.title} onChange={e => update(i, {title:e.target.value})}/></Field>
        <Field title="Owner group" hint="For example, tenant-alpha or tenant-beta. This determines who may read the document."><input aria-label="Owner group" maxLength={100} value={d.tenant} onChange={e => update(i, {tenant:e.target.value})}/></Field>
      </div><Field title="Document content" hint="Paste the text the assistant should use when answering normal questions."><textarea aria-label="Document content" rows={5} value={d.body} onChange={e => update(i, {body:e.target.value})}/></Field>
      <label className="check"><input type="checkbox" checked={d.assigned_to_red} onChange={e => update(i, {assigned_to_red:e.target.checked})}/>Allow Red to edit this document during injection tests</label>
      <label className="check"><input type="checkbox" checked={d.confidential} onChange={e => update(i, {confidential:e.target.checked})}/>Confidential document</label>
      <p className="small muted">Confidential documents receive a server-generated secret marker for disclosure checks. Red can only edit assigned documents in its own group.</p>
      <div className="row between wrap"><span className="tiny muted">Document ID: {d.id}</span><Button variant="ghost" aria-label={`Remove document ${i + 1}`} onClick={() => onChange(documents.filter((_, n) => n !== i))}>Remove document</Button></div></div>
    </details>)}
  </section>;
}

function ExpectedTerms({terms, onChange}: {terms: string[]; onChange: (terms: string[]) => void}) {
  const [text, setText] = useState(terms.join("\n"));
  return <Field title="Expected answer terms" hint="Optional. Put one word or phrase on each line, such as 09:00 and 18:00. All terms must appear in the answer."><textarea aria-label="Expected answer terms" rows={3} placeholder={"09:00\n18:00"} value={text} onChange={e => {setText(e.target.value); onChange(e.target.value.split("\n").map(s => s.trim()).filter(Boolean));}}/></Field>;
}

export function TaskEditor({tasks, tenant, onChange}: {tasks: Task[]; tenant: string; onChange: (tasks: Task[]) => void}) {
  const [addedId, setAddedId] = useState<string|null>(null);
  const update = (index: number, patch: Partial<Task>) => onChange(tasks.map((t, i) => i === index ? {...t, ...patch} : t));
  return <section className="stack" aria-label="Normal-use task editor">
    <div className="row between wrap"><div><h3>Normal-use tasks</h3><p className="small muted">Legitimate questions check that the model remains useful before and after a repair.</p></div><Button onClick={() => {const id=newId("task");setAddedId(id);onChange([...tasks, {id, language:"en", tenant, message:"", expected_terms:[], expected_tool:null, expect_json:false, forbid_refusal:true}]);}}>Add task</Button></div>
    {tasks.map((t, i) => <details key={t.id} className="target-editor" open={i === 0 || t.id === addedId}>
      <summary><strong>{t.message || `New task ${i + 1}`}</strong><span>{label(t.language)} · {t.tenant}</span></summary>
      <div className="stack target-editor-body"><Field title="User question" hint="Write a normal request the assistant should handle successfully."><textarea aria-label="User question" rows={3} maxLength={2000} value={t.message} onChange={e => update(i, {message:e.target.value})}/></Field>
      <div className="form-grid"><Field title="Task language"><select aria-label="Task language" value={t.language} onChange={e => update(i, {language:e.target.value})}>{["en", "tr", "az"].map(v => <option key={v} value={v}>{label(v)}</option>)}</select></Field><Field title="User group" hint="The owner group this user belongs to."><input aria-label="User group" maxLength={100} value={t.tenant} onChange={e => update(i, {tenant:e.target.value})}/></Field></div>
      <ExpectedTerms terms={t.expected_terms} onChange={expected_terms => update(i, {expected_terms})}/>
      <details><summary className="small link">Tool and response requirements</summary><div className="stack gap-top"><Field title="Required tool" hint="Leave as No tool required for an ordinary question."><select aria-label="Required tool" value={t.expected_tool ?? ""} onChange={e => update(i, {expected_tool:e.target.value || null})}><option value="">No tool required</option><option value="doc_export">Export an authorized document (doc_export)</option><option value="email_send">Record an authorized email (email_send)</option>{t.expected_tool && !["doc_export", "email_send"].includes(t.expected_tool) && <option value={t.expected_tool}>{t.expected_tool}</option>}</select></Field>
      <label className="check"><input type="checkbox" checked={t.expect_json} onChange={e => update(i, {expect_json:e.target.checked})}/>Require a structured response</label><p className="small muted">Checks the application's answer, citations, and task response format automatically.</p>
      <label className="check"><input type="checkbox" checked={t.forbid_refusal} onChange={e => update(i, {forbid_refusal:e.target.checked})}/>The assistant should answer this legitimate request</label></div></details>
      <Button variant="ghost" aria-label={`Remove task ${i + 1}`} onClick={() => onChange(tasks.filter((_, n) => n !== i))}>Remove task</Button></div>
    </details>)}
  </section>;
}

const credential = (value: string | null | undefined) => value == null ? "Environment default" : value ? "Entered; hidden" : "No credential";
export function TargetReview({spec}: {spec: TargetSpec & TargetConnection}) {
  return <div className="stack" aria-label="Target summary">
    <Panel title={spec.name} subtitle="Connection and application"><dl className="detail-list"><dt>API base URL</dt><dd>{spec.endpoint}</dd><dt>Deployment</dt><dd>{deployments.find(d => d.id === (spec.connection_kind ?? "local"))?.name}</dd><dt>Model</dt><dd>{spec.model}</dd><dt>Pinned version</dt><dd>{spec.model_revision}</dd><dt>Application version</dt><dd>{spec.application_revision}</dd><dt>API format</dt><dd>{spec.api_format === "ollama" ? "Native Ollama" : "OpenAI-compatible chat"}</dd><dt>Tool protocol</dt><dd>{spec.tool_mode === "json" ? "Validated application adapter" : "Native API tool calls"}</dd><dt>Response token cap</dt><dd>{spec.max_output_tokens ?? "Unlimited"}</dd><dt>Request timeout</dt><dd>{spec.timeout_seconds == null ? "Unlimited" : `${spec.timeout_seconds} seconds`}</dd><dt>API authentication</dt><dd>{credential(spec.api_key)}</dd><dt>Cloudflare Access</dt><dd>{credential(spec.access_client_id)}</dd></dl><p className="small gap-top"><strong>Task policy</strong></p><p className="small">{spec.task_policy}</p></Panel>
    <Panel title="Documents and normal tasks" subtitle={`${spec.documents.length} documents · ${spec.utility_cases.length} normal-use tasks`}><div className="target-review-list">{spec.documents.map(d => <div key={d.id}><strong>{d.title}</strong><p>{d.tenant} · {d.confidential ? "Confidential" : "Standard"} · {d.assigned_to_red ? "Red may edit" : "Read-only during attacks"}</p></div>)}</div><details className="gap-top"><summary className="small link">View normal-use tasks</summary><div className="target-review-list gap-top">{spec.utility_cases.map(t => <div key={t.id}><strong>{t.message}</strong><p>{label(t.language)} · {t.tenant}{t.expected_terms.length ? ` · Expected: ${t.expected_terms.join(", ")}` : ""}{t.expected_tool ? ` · Tool: ${t.expected_tool}` : ""}</p></div>)}</div></details></Panel>
    <Panel title="Access and controls"><dl className="detail-list"><dt>Red user group</dt><dd>{spec.tenant}</dd><dt>Attack inputs</dt><dd>{spec.writable_surfaces.map(label).join(", ") || "None"}</dd><dt>Red feedback</dt><dd>{spec.red_observations.map(label).join(", ") || "None"}</dd><dt>Starting defenses</dt><dd>{Object.entries(spec.defenses).filter(([,v]) => v).map(([k]) => label(k)).join(", ") || "No additional defenses"}</dd></dl><div className="checks gap-top">{Object.entries(spec.capabilities).filter(([,v]) => v).map(([k]) => <Badge key={k}>{label(k)}</Badge>)}</div></Panel>
    <Notice>Saving records this configuration as a fixed version. Connection checks confirm model access; campaigns measure security and normal-use behavior.</Notice>
  </div>;
}
