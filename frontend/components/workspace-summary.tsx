"use client";

import Link from "next/link";
import type { CampaignRow, Health, Target } from "@/lib/api";
import { percent } from "@/lib/api";
import { campaignName } from "@/lib/registration-names";
import { Icon } from "./platform";
import "./workspace-summary.css";

const inactive = new Set(["completed", "failed", "cancelled", "budget_exhausted", "draft", "paused"]);

export function WorkspaceSummary({ health, targets, campaigns, canCreate, onCreate }: {
  health: Health | null; targets: Target[] | null; campaigns: CampaignRow[] | null; canCreate: boolean; onCreate: () => void;
}) {
  const rows = campaigns ?? [];
  const inventory = targets ?? [];
  const latest = rows[0];
  const active = rows.filter(c => !inactive.has(c.state)).length;
  const findings = rows.reduce((n, c) => n + c.findings, 0);
  const fixture = !!health?.fixture_environment;
  const configured = fixture || !!(health?.red.configured && health?.judge.configured);
  const connected = inventory.some(t => t.preflight?.connected);
  const next = !configured
    ? { step:"01", href:"/guide?step=setup", label:"Review model setup", text:"Connect Red and Judge to prepare your security experiments." }
    : !inventory.length
    ? { step:"02", href:"/target", label:"Register your target", text:"Connect the AI application you want to evaluate and define its expected behavior." }
    : !connected
    ? { step:"02", href:"/target", label:"Check your target connection", text:"Verify that the registered application responds before starting a security campaign." }
    : !rows.length
    ? { step:"03", href:"/campaign", label:"Create your first campaign", text:"Choose the security behaviors, languages and test depth for your experiment." }
    : { step:"03", href: latest ? "/campaign?campaign="+encodeURIComponent(latest.id) : "/campaign", label:"Open campaign console", text:active ? `${active} campaign${active===1?" is":"s are"} running. Follow attacks, independent reproduction and emerging evidence.` : "Review an existing test or create a new campaign to begin attack discovery." };
  const checks = [
    { name:"Red settings", ready:fixture || !!health?.red.configured },
    { name:"Judge settings", ready:fixture || !!health?.judge.configured },
    { name:"Target registered", ready:inventory.length>0 },
    { name:"Target connection", ready:connected },
    { name:"Campaign created", ready:rows.length>0 },
  ];
  const coverage = latest?.coverage.coverage_pct;
  const ready = checks.every(c=>c.ready);

  return <div className="workspace-overview">
    <header className="workspace-heading">
      <div className="workspace-heading-copy"><span className="workspace-eyebrow">SECURITY CONTROL PLANE</span><h1>Your AI security workspace</h1><p>Discover weaknesses. Reproduce the evidence. Verify the improvement.</p></div>
      <div className="workspace-heading-actions"><Link href="/guide" className="workspace-guide-link">How to use<Icon name="arrow" size={15}/></Link><button type="button" className="workspace-create" disabled={!canCreate||!inventory.length} onClick={onCreate}><Icon name="plus" size={17}/>New campaign</button></div>
    </header>

    <section className="workspace-next" aria-label="Getting started">
      <div className="workspace-next-top"><span className="workspace-eyebrow">YOUR NEXT STEP / {next.step}</span><span className={"workspace-setup-status "+(ready?"is-ready":"")}><i/>{ready?"Setup ready":"Setup in progress"}</span></div>
      <div className="workspace-next-content"><div className="workspace-next-copy"><h2>{next.label}</h2><p>{next.text}</p></div><Link href={next.href} className="workspace-next-action" aria-label={next.label}><span>{next.label}</span><Icon name="arrow" size={21}/></Link></div>
      <ol className="workspace-readiness" aria-label="Setup checklist">{checks.map((check,index)=><li key={check.name} className={check.ready?"is-ready":""}><span className="workspace-check-mark" aria-hidden="true">{check.ready?<Icon name="check" size={13}/>:String(index+1).padStart(2,"0")}</span><span>{check.name}</span><small>{check.ready?"Ready":"Pending"}</small></li>)}</ol>
    </section>

    <section className="workspace-metrics" aria-label="Workspace metrics">
      <Link href="/target" className="workspace-metric metric-targets"><div className="workspace-metric-label"><span>Registered targets</span><Icon name="target" size={15}/></div><strong>{targets===null?"—":inventory.length.toLocaleString("en-US")}</strong><p>Reusable application snapshots</p><span className="workspace-metric-foot">Explore target registry<Icon name="arrow" size={13}/></span></Link>
      <Link href="/campaign" className="workspace-metric metric-active"><div className="workspace-metric-label"><span>Active campaigns</span><Icon name="activity" size={15}/></div><strong>{campaigns===null?"—":active.toLocaleString("en-US")}<span className={"workspace-metric-state "+(active?"is-live":"")}><i/>{active?"LIVE":"IDLE"}</span></strong><p>{rows.length.toLocaleString("en-US")} saved campaigns</p><span className="workspace-metric-foot">Follow campaign activity<Icon name="arrow" size={13}/></span></Link>
      <Link href="/findings" className="workspace-metric metric-findings"><div className="workspace-metric-label"><span>Confirmed findings</span><Icon name="shield" size={15}/></div><strong>{campaigns===null?"—":findings.toLocaleString("en-US")}</strong><p>Reproduced in fresh sessions</p><span className="workspace-metric-foot">Review the evidence<Icon name="arrow" size={13}/></span></Link>
      <Link href={latest?"/coverage?campaign="+encodeURIComponent(latest.id):"/coverage"} className="workspace-metric metric-coverage"><div className="workspace-metric-label"><span>Latest campaign coverage</span><Icon name="layers" size={15}/></div><strong>{percent(coverage==null?null:coverage/100)}</strong><p>{latest?`${latest.coverage.completed} / ${latest.coverage.applicable} applicable cells`:"No measurements yet"}</p><div className="workspace-coverage-meter" aria-hidden="true"><span style={{width:Math.max(0,Math.min(100,coverage??0))+"%"}}/></div><span className="workspace-metric-foot">{latest?campaignName(latest):"Explore test coverage"}<Icon name="arrow" size={13}/></span></Link>
    </section>
  </div>;
}
