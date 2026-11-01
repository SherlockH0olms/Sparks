"use client";
import { useState } from "react";
import { RedLibraryResponse, RedResource, RedResourcePage, RedSourceInventory } from "@/lib/api";
import { Panel, QueryError, Stat, useAuth, useData } from "./platform";

export function RedLibrary() {
  const { health } = useAuth();
  const [expanded, setExpanded] = useState(false);
  const [draft, setDraft] = useState("");
  const [query, setQuery] = useState("");
  const [source, setSource] = useState("");
  const [offset, setOffset] = useState(0);
  const [resourceId, setResourceId] = useState<string | null>(null);
  const [inventoryFilter, setInventoryFilter] = useState("");
  const methods = useData<RedLibraryResponse>(expanded ? "/red/library" : null);
  const sources = useData<RedSourceInventory>(expanded ? "/red/library/sources" : null);
  const page = useData<RedResourcePage>(expanded ? `/red/library/resources?query=${encodeURIComponent(query)}${source ? `&framework=${encodeURIComponent(source)}` : ""}&offset=${offset}&limit=10` : null);
  const resource = useData<RedResource>(expanded && resourceId ? `/red/library/resource/${encodeURIComponent(resourceId)}` : null);
  const library = methods.data?.summary ?? health?.red_attack_library;
  if (!library) return null;
  const names = [...new Set([...library.frameworks.map(f => f.id), ...Object.keys(library.resources_per_framework ?? {})])];
  const inventory = sources.data?.research_inventory.filter(r => `${r.name} ${r.category} ${r.capability}`.toLocaleLowerCase("en-US").includes(inventoryFilter.toLocaleLowerCase("en-US"))) ?? [];
  const status: Record<string,string> = {installed_components:"Local components connected", indexed_attacker_inputs:"Attack inputs indexed", indexed_attack_templates:"Templates indexed", indexed_template_fragments:"Template fragments indexed", indexed_tactics_and_composition:"Tactics and composition connected", gated_unconnected:"Dataset terms need acceptance", not_connected:"Researched; not connected", reference_only:"Reference or defense"};
  return <Panel title="Red attack library" subtitle={names.join(" · ")}>
    {library.available ? <>
      <div className="stats">
        <Stat title="Unique resources" value={library.unique_resources.toLocaleString("en-US")} hint="Seeds, tactics, and guidance with duplicate text removed" />
        <Stat title="Mechanism groups" value={library.mechanism_groups} hint="Source-based groups for choosing different approaches" tone="red" />
        <Stat title="Available transformations" value={library.executable_transforms} hint="Verified local framework components" tone="cyan" />
        <Stat title="Tactic records" value={(library.tactic_records ?? 0).toLocaleString("en-US")} hint="Mined ideas can overlap; this count is not a count of independent algorithms" tone="blue" />
      </div>
      <p className="small muted">Red recommends less-used approaches, reads real source examples, and combines selected tactics. Each candidate records the sources and transformations used. Resource counts describe the library; target tests measure attack success.</p>
      <details className="library-details" onToggle={event => setExpanded(event.currentTarget.open)}>
        <summary className="small link">Browse methods, sources, and research</summary>
        <QueryError error={methods.error} />
        <div className="table-wrap"><table><thead><tr><th>Method</th><th>Source examples</th><th>Transformations</th></tr></thead><tbody>
          {methods.data?.methods.map(method => <tr key={method.id}><td>{method.id.replaceAll("_", " ")}</td><td>{method.resource_count}</td><td>{method.transforms.join(", ") || "Template adaptation"}</td></tr>)}
        </tbody></table></div>
        <p className="small muted">{library.frameworks.map((framework, i) => <span key={framework.id}>{i > 0 ? " · " : ""}<a className="link" href={framework.url} target="_blank" rel="noreferrer">{framework.id} {framework.version}</a></span>)}</p>
        <div className="table-wrap"><table><thead><tr><th>Indexed source</th><th>Unique records</th></tr></thead><tbody>{Object.entries(library.resources_per_framework ?? {}).map(([name,count]) => <tr key={name}><td>{name}</td><td>{count.toLocaleString("en-US")}</td></tr>)}</tbody></table></div>
        <form className="resource-search" onSubmit={event => {event.preventDefault(); setQuery(draft); setOffset(0); setResourceId(null);}}>
          <label className="small">Search the library <input aria-label="Attack resource search" value={draft} onChange={event => setDraft(event.target.value)} placeholder="Try translation, dialogue, or metadata" /></label>
          <select aria-label="Source filter" value={source} onChange={event => {setSource(event.target.value); setOffset(0); setResourceId(null);}}><option value="">All sources</option>{Object.keys(library.resources_per_framework ?? {}).map(name => <option key={name} value={name}>{name}</option>)}</select>
          <button className="button" type="submit">Search</button>
        </form>
        <QueryError error={page.error ?? resource.error} />
        <p className="small muted">{page.data?.total.toLocaleString("en-US") ?? "—"} matches</p>
        <div className="table-wrap"><table><thead><tr><th>Source</th><th>Kind</th><th>Record</th></tr></thead><tbody>{page.data?.results.map(r => <tr key={r.id}><td>{r.framework}</td><td>{r.kind ?? "seed"}</td><td><button type="button" className="link" onClick={() => setResourceId(r.id)}>{r.title}</button></td></tr>)}</tbody></table></div>
        <button className="button" type="button" disabled={offset === 0} onClick={() => setOffset(Math.max(0,offset-10))}>Previous</button>{" "}<button className="button" type="button" disabled={page.data?.next_offset == null} onClick={() => setOffset(page.data?.next_offset ?? offset)}>Next</button>
        {resource.data && <div className="library-resource"><p className="small">{resource.data.id} · {resource.data.license} · {resource.data.path}</p><pre className="code" style={{whiteSpace:"pre-wrap",maxHeight:320,overflow:"auto"}}>{resource.data.text}</pre></div>}
        <h3>Research inventory ({library.research_inventory_count ?? sources.data?.research_inventory.length ?? 0})</h3>
        <p className="small muted">Frameworks, datasets, algorithms, evaluation tools, and defenses. The integration status shows which parts are connected to AEGIS.</p>
        <input aria-label="Research inventory filter" value={inventoryFilter} onChange={event => setInventoryFilter(event.target.value)} placeholder="Search by source name or category" />
        <QueryError error={sources.error} />
        <div className="table-wrap"><table><thead><tr><th>Source</th><th>Category / capability</th><th>AEGIS integration</th></tr></thead><tbody>{inventory.map(r => <tr key={r.id}><td><a className="link" href={r.url} target="_blank" rel="noreferrer">{r.name}</a></td><td>{r.category}<p className="small muted">{r.capability}</p></td><td>{status[r.integration_status] ?? r.integration_status}{!r.link_verified && <p className="small muted">Link could not be verified</p>}</td></tr>)}</tbody></table></div>
      </details>
    </> : <p className="small muted">The attack library is not installed yet. Follow the setup instructions in How to use.</p>}
  </Panel>;
}
