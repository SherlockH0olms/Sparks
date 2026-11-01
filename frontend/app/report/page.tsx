"use client";
import { useState } from "react";
import { api, Campaign, download, terminal } from "@/lib/api";
import { Button, CampaignPicker, Empty, Heading, Loading, Notice, Panel, QueryError, useAuth, useCampaignId, useData } from "@/components/platform";
import { Markdown } from "@/components/markdown";
type ReportResponse={markdown:string;summary:Campaign;html:string;report:Record<string,unknown>};
export default function Report(){
 const [cid,setCid]=useCampaignId();const q=useData<ReportResponse>(cid?"/campaigns/"+cid+"/report":null,8000);const {user}=useAuth();const [busy,setBusy]=useState(false);const [error,setError]=useState<string|null>(null);const [view,setView]=useState("presentation");
 async function evidence(sensitive=false){setBusy(true);setError(null);try{const pack=await api.get("/campaigns/"+cid+"/evidence-pack?sensitive="+sensitive);download("aegis-evidence"+(sensitive?"-raw":"")+".json",JSON.stringify(pack,null,2));}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 return <><Heading eyebrow="EVIDENCE / EXPORT" title="Experiment report" description="Review findings, measured remediation, MITRE ATLAS and NIST supporting evidence, deployment plans, and uncertainty." action={<CampaignPicker value={cid} onChange={setCid}/>}/><QueryError error={q.error}/>{error&&<Notice error>{error}</Notice>}{!cid?<Panel><Empty title="Select a campaign to view its report"/></Panel>:q.isLoading?<Loading/>:q.data&&<>
 <Panel title="Presentation and evidence exports" subtitle="PDF for review, editable PowerPoint for presentation, and complete records for analysis">
  <div className="row wrap">
   <a className="button primary" href={"/api/campaigns/"+cid+"/report?format=pdf"} download>Download PDF</a>
   <a className="button" href={"/api/campaigns/"+cid+"/report?format=pptx"} download>Download PowerPoint</a>
   <a className="button" href={"/api/campaigns/"+cid+"/report?format=html"} download>Download HTML</a>
   <Button onClick={()=>download("aegis-report.md",q.data!.markdown,"text/markdown")}>Download Markdown</Button>
   <Button onClick={()=>download("aegis-report.json",JSON.stringify(q.data!.report,null,2))}>Download report JSON</Button>
  </div>
  {user?.role!=="viewer"&&<div className="row wrap gap-top">
   <Button disabled={busy} onClick={()=>evidence()}>Download evidence package</Button>
   <a className="button" href={"/api/campaigns/"+cid+"/evidence.ndjson"} download>Download evidence NDJSON</a>
   <a className="button" href={"/api/campaigns/"+cid+"/remediation-bundle"} download>Download remediation bundle</a>
   {user?.role==="admin"&&<Button disabled={busy||!terminal.has(q.data.summary.state)} onClick={()=>evidence(true)}>Download raw evidence (admin)</Button>}
   {user?.role==="admin"&&terminal.has(q.data.summary.state)&&<a className="button" href={"/api/campaigns/"+cid+"/evidence.ndjson?sensitive=true"} download>Download raw NDJSON (admin)</a>}
  </div>}
  <p className="small muted gap-top">The bundle includes tested configurations, deployment and rollback plans, and integrity hashes. Verify the selected candidate and implement controls in your application's actual boundaries. NIST crosswalks provide supporting evidence and identify unassessed domains.</p>
 </Panel>
 {!terminal.has(q.data.summary.state)&&<Notice>The campaign is still running. This report is a snapshot of the records available so far.</Notice>}
 <div className="row gap-top" style={{marginBottom:16}}><Button variant={view==="presentation"?"primary":"ghost"} onClick={()=>setView("presentation")}>Presentation preview</Button><Button variant={view==="markdown"?"primary":"ghost"} onClick={()=>setView("markdown")}>Text report</Button></div>
 {view==="presentation"?<iframe title="AI security and remediation report preview" sandbox="allow-same-origin" srcDoc={q.data.html} style={{width:"100%",height:"1100px",border:"1px solid var(--line)",borderRadius:12,background:"white"}}/>:<Panel><Markdown text={q.data.markdown}/></Panel>}
 </>}</>;
}
