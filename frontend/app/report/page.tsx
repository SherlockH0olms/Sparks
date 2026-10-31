"use client";
import { useState } from "react";
import { api, Campaign, download, terminal } from "@/lib/api";
import { Button, CampaignPicker, Empty, Heading, Loading, Notice, Panel, QueryError, useAuth, useCampaignId, useData } from "@/components/platform";
import { Markdown } from "@/components/markdown";
export default function Report(){
 const [cid,setCid]=useCampaignId();const q=useData<{markdown:string;summary:Campaign}>(cid?"/campaigns/"+cid+"/report":null,8000);const {user}=useAuth();const [busy,setBusy]=useState(false);const [error,setError]=useState<string|null>(null);
 async function evidence(sensitive=false){setBusy(true);setError(null);try{const pack=await api.get("/campaigns/"+cid+"/evidence-pack?sensitive="+sensitive);download("aegis-evidence"+(sensitive?"-raw":"")+".json",JSON.stringify(pack,null,2));}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 return <><Heading eyebrow="EVIDENCE / EXPORT" title="Deney raporu" description="Gerçek kanıtlar, aynı suite ile önce/sonra ölçümü, bütçe ve tamamlanmamış kapsam." action={<CampaignPicker value={cid} onChange={setCid}/>}/><QueryError error={q.error}/>{error&&<Notice error>{error}</Notice>}{!cid?<Panel><Empty title="Rapor için kampanya seçin"/></Panel>:q.isLoading?<Loading/>:q.data&&<><div className="row wrap" style={{marginBottom:24}}><Button onClick={()=>download("aegis-report.md",q.data!.markdown,"text/markdown")}>Markdown indir</Button><a className="button" href={"/api/campaigns/"+cid+"/report?format=html"} download>HTML indir</a><Button disabled={busy||user?.role==="viewer"} onClick={()=>evidence()}>Kanıt paketi indir</Button>{user?.role==="admin"&&<Button disabled={busy||!terminal.has(q.data.summary.state)} onClick={()=>evidence(true)}>Admin raw kanıt paketi</Button>}</div>{!terminal.has(q.data.summary.state)&&<Notice>Kampanya sürüyor. Bu rapor mevcut kayıtların anlık görünümüdür.</Notice>}<Panel><Markdown text={q.data.markdown}/></Panel></>}</>;
}
