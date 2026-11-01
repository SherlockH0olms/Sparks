"use client";
import Link from "next/link";
import { CampaignRow, Target } from "@/lib/api";
import { useAuth,useData } from "./platform";

export function GettingStarted() {
  const {health}=useAuth();
  const targets=useData<Target[]>("/targets");
  const campaigns=useData<CampaignRow[]>("/campaigns");
  const hasTarget=!!targets.data?.length;
  const connected=targets.data?.some(t=>t.preflight?.connected);
  const hasCampaign=!!campaigns.data?.length;
  const fixture=!!health?.fixture_environment;
  const checks=[{name:fixture?"Simulated Red":"Red settings",done:fixture||health?.red.configured},{name:fixture?"Fixture evaluation":"Judge settings",done:fixture||health?.judge.configured},{name:"Target registered",done:hasTarget},{name:"Target connection",done:connected},{name:"Campaign created",done:hasCampaign}];
  const configured=fixture||(health?.red.configured&&health?.judge.configured);
  const next=!configured?{href:"/guide?step=setup",label:"Review model setup",text:"Configure the Red and Judge models in .env to prepare live experiments."}:!hasTarget?{href:"/target",label:"Register a target",text:"Your provider settings are present. Next, register the AI application you want to test."}:!connected?{href:"/target",label:"Test target connection",text:"A target is registered. Check that its target model responds before starting a campaign."}:!hasCampaign?{href:"/campaign",label:"Create a campaign",text:"Choose the behaviors to test, languages, and budget for your first experiment."}:fixture?{href:"/campaign",label:"Explore demo campaign",text:"A completed example is ready. Review its findings, repairs, verification, and report."}:{href:"/campaign",label:"Open campaign console",text:"Select a campaign to start a draft or inspect an existing run."};
  return <section className="start-card" aria-label="Getting started">
    <div><span className="eyebrow">YOUR NEXT STEP</span><h2>{next.label}</h2><p>{next.text}</p></div>
    <div className="setup-checks">{checks.map(c=><span className={c.done?"setup-check done":"setup-check"} key={c.name}><span aria-hidden="true">{c.done?"✓":"○"}</span>{c.name}</span>)}</div>
    <div className="row wrap"><Link className="button primary" href={next.href}>{next.label} →</Link><Link className="link" href="/guide">How to use AEGIS from start to finish →</Link></div>
  </section>;
}
