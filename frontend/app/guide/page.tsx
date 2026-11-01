"use client";
import Link from "next/link";
import { useEffect,useRef,useState } from "react";
import { useRouter,useSearchParams } from "next/navigation";
import { glossary,guideSteps } from "@/lib/guide";
import { Button,Heading,Panel,useCampaignId } from "@/components/platform";
import { GettingStarted } from "@/components/getting-started";

export default function Guide() {
  const search=useSearchParams();const router=useRouter();const [cid]=useCampaignId();
  const active=Math.max(0,guideSteps.findIndex(s=>s.id===search.get("step")));
  const step=guideSteps[active];const [filter,setFilter]=useState("");
  const previousStep=useRef(active);
  useEffect(()=>{
    if(previousStep.current===active)return;
    previousStep.current=active;
    const title=document.getElementById("guide-current-title");
    title?.scrollIntoView({block:"start"});
    title?.focus({preventScroll:true});
  },[active]);
  const go=(index:number)=>router.replace("/guide?step="+guideSteps[index].id+(cid?"&campaign="+encodeURIComponent(cid):""),{scroll:false});
  const terms=glossary.filter(t=>(t.name+" "+t.explanation).toLowerCase().includes(filter.toLowerCase()));
  return <><Heading eyebrow="START HERE / PLATFORM GUIDE" title="How to use AEGIS Loop" description="Follow the experiment from model setup to a reviewable report. Learn what each page does, what to click, and how to interpret the results."/>
    <GettingStarted/>
    <section className="role-explainer" aria-label="Model roles">{guideSteps[0].terms.map(role=><div key={role.name}><h3>{role.name}</h3><p>{role.explanation}</p></div>)}</section>
    <div className="guide-layout"><nav className="guide-steps" aria-label="Walkthrough steps">{guideSteps.map((s,index)=><button type="button" key={s.id} aria-current={index===active?"step":undefined} className={index===active?"active":""} onClick={()=>go(index)}><span>{String(index+1).padStart(2,"0")}</span><strong>{s.title}</strong></button>)}</nav>
      <Panel className="guide-current" title={<span id="guide-current-title" tabIndex={-1}>{active+1}. {step.title}</span>} subtitle={"Page: "+step.pageName}>
        <p className="guide-purpose">{step.purpose}</p><h3>What to do</h3><ol className="guide-actions">{step.actions.map(action=><li key={action}>{action}</li>)}</ol>
        <div className="guide-outcome"><strong>What you should see</strong><p>{step.expected}</p></div>
        <h3>Terms used in this step</h3><dl className="guide-terms">{step.terms.map(term=><div key={term.name}><dt>{term.name}</dt><dd>{term.explanation}</dd></div>)}</dl>
        {step.id==="setup"&&<details className="guide-config"><summary>Where to enter your keys and endpoints</summary><p>Edit .env in the project folder. The administrator access key must contain at least 32 random characters. Each model has its own provider configuration. Use the platform access key to sign in; provider keys are loaded by the backend.</p><pre className="code">{`AEGIS_ADMIN_TOKEN=replace-with-at-least-32-random-characters\n\nAEGIS_RED_PROVIDER=foundry\nAEGIS_RED_ENDPOINT=https://your-provider-endpoint\nAEGIS_RED_API_KEY=your-red-provider-key\nAEGIS_RED_MODEL=your-red-model\n\nAEGIS_JUDGE_PROVIDER=foundry\nAEGIS_JUDGE_ENDPOINT=https://your-judge-endpoint\nAEGIS_JUDGE_API_KEY=your-judge-provider-key\nAEGIS_JUDGE_MODEL=your-judge-model`}</pre><p>Use the provider type required by your service. Azure OpenAI also uses the corresponding deployment and API version settings. AEGIS_API is the backend address used by the web app.</p></details>}
        <div className="guide-nav"><Button disabled={active===0} onClick={()=>go(active-1)}>Previous step</Button><Link className="button" href={step.page+(cid?"?campaign="+encodeURIComponent(cid):"")}>Open {step.pageName} →</Link><Button variant="primary" disabled={active===guideSteps.length-1} onClick={()=>go(active+1)}>Next step</Button></div>
      </Panel>
    </div>
    <Panel title="Using the Red attack library" subtitle="Find source material and understand how it contributes to a test.">
      <ol className="guide-actions"><li>On Overview, expand <strong>Browse methods, sources, and research</strong>. Review mechanism groups and available local transformations.</li><li>Use the source filter and search box to find an example. Select its title to read the complete resource; use Previous and Next to browse more results.</li><li>Search the research inventory to see a project's purpose and integration status. Indexed inputs provide examples; connected components run transformations. A researched reference may have no executable integration.</li><li>Red reads sources, composes tactics, and applies registered transformations through its tools. Inspect an attempt to see the actual source records and transformation use. Check Coverage for the variety used during your campaign.</li></ol>
      <p className="small">Library size describes available material. The target's recorded responses and assessments determine attack success.</p>
      <details className="guide-config"><summary>Install or rebuild the local library</summary><p>Run these commands from the project folder after the application dependencies are installed. The setup script installs framework components in separate environments, and the expansion script downloads and indexes the supported datasets.</p><pre className="code">{`.\\.venv-win\\Scripts\\python.exe scripts\\setup_redteam_tools.py --with-deepteam\n.\\.venv-win\\Scripts\\python.exe scripts\\expand_redteam_library.py`}</pre><p>Use --index-only with the setup script to preserve an existing corpus. Use --offline with the expansion script to rebuild from files already downloaded. Restart the backend after changing the installed library.</p></details>
      <div className="gap-top"><Link className="link" href={"/"+(cid?"?campaign="+encodeURIComponent(cid):"")}>Browse the library on Overview →</Link></div>
    </Panel>
    <Panel className="gap-top" title="When something does not work" subtitle="Use the recorded message to choose your next action.">
      <dl className="guide-terms"><div><dt>I cannot sign in</dt><dd>Use the platform access key for AEGIS. For the first administrator, read AEGIS_ADMIN_TOKEN in .env. Ask an administrator for a role-scoped key when joining an existing workspace.</dd></div><div><dt>A model needs configuration</dt><dd>Check that provider, endpoint, key, and model belong to the same service. Save .env and restart the application. A configured status checks settings; campaign preflight tests connectivity.</dd></div><div><dt>The target connection failed</dt><dd>Start the local model server, check its /v1 URL and exact model identifier, and select Test connection on Targets. A target registration does not install model weights.</dd></div><div><dt>A campaign stays queued</dt><dd>On Audit and access, check Controller and Active jobs. Review the execution lock and campaign events. The background controller must be active to process jobs.</dd></div><div><dt>A result is incomplete or inconclusive</dt><dd>Open the attempt assessment and recorded error. Check valid test counts and exhausted phase budgets. Increase the relevant capacity or fix the connection before creating another campaign.</dd></div><div><dt>A button is unavailable</dt><dd>Your role and the campaign state determine which actions are available. Viewers read results; analysts manage campaigns; maintainers register targets; administrators manage access and execution controls.</dd></div></dl>
    </Panel>
    <Panel className="guide-glossary" title="Plain-English glossary" subtitle="Search the terms used in the console, evidence, and reports."><label className="field"><span>Find a term</span><input value={filter} onChange={event=>setFilter(event.target.value)} placeholder="Try ASR, tenant, canary, or budget"/></label><dl className="guide-terms">{terms.map(term=><div key={term.name}><dt>{term.name}</dt><dd>{term.explanation}</dd></div>)}</dl>{!terms.length&&<p>No terms match your search.</p>}</Panel>
  </>;
}
