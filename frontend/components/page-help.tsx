"use client";
import Link from "next/link";
import { pageHelp } from "@/lib/guide";

export function PageHelp({path,campaignId}:{path:string;campaignId:string|null}) {
  const key=path.startsWith("/findings/")?"/findings":path;
  const help=pageHelp[key];
  if(!help)return null;
  const next=help.next+(campaignId?"?campaign="+encodeURIComponent(campaignId):"");
  return <details className="page-help">
    <summary><span className="help-mark" aria-hidden="true">?</span><span>How to use this page <small>{help.title}</small></span><span className="help-expand">Show instructions</span></summary>
    <div className="help-content"><p>{help.description}</p><ol>{help.steps.map(step=><li key={step}>{step}</li>)}</ol>
      <div className="row wrap"><Link className="link" href={"/guide?step="+help.guideId+(campaignId?"&campaign="+encodeURIComponent(campaignId):"")}>Detailed walkthrough →</Link><Link className="link" href={next}>{help.nextLabel} →</Link></div>
    </div>
  </details>;
}
