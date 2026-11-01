"use client";
import { useState } from "react";
import { ConnectionKind, TargetConnection, TargetSpec } from "@/lib/api";
import { Field } from "./platform";

export const deployments: {id: ConnectionKind; name: string; example: string; help: string}[] = [
  {id:"local",name:"This computer / localhost",example:"http://127.0.0.1:11434/v1",help:"Ollama, LM Studio, vLLM, llama.cpp, or another model server on the API host."},
  {id:"lan",name:"LAN / private IP",example:"http://192.168.1.50:8000/v1",help:"A model server on another computer reachable from the platform backend."},
  {id:"tailscale",name:"Tailscale / private network",example:"http://100.64.0.20:8000/v1",help:"Use its Tailscale IP or .ts.net hostname. The backend must join the same tailnet."},
  {id:"cloudflare",name:"Cloudflare Tunnel",example:"https://model.example.com/v1",help:"Use the tunnel HTTPS address. Add Access service credentials below if Access protects it."},
  {id:"ngrok",name:"ngrok tunnel",example:"https://your-model.ngrok-free.app/v1",help:"Use the HTTPS forwarding address. The platform sends the ngrok browser-warning bypass header."},
  {id:"notebook",name:"Kaggle / Colab notebook tunnel",example:"https://your-model.ngrok-free.app/v1",help:"Run an API model server in the notebook and expose it through ngrok or Cloudflare. The notebook session must stay active."},
  {id:"custom",name:"Custom / other deployment",example:"https://model.example.com/v1",help:"Any reachable server implementing OpenAI-compatible chat or native Ollama. Other API protocols need an adapter."},
];

export function TargetConnectionForm({spec,onChange}:{spec:TargetSpec & TargetConnection;onChange:(next:TargetSpec & TargetConnection)=>void}){
  const [auth,setAuth]=useState(spec.api_key==null?"environment":spec.api_key?"key":"none");const [access,setAccess]=useState(spec.access_client_id==null?"environment":spec.access_client_id?"token":"none");
  const selected=deployments.find(d=>d.id===(spec.connection_kind??"local"))!;
  const ollama=spec.api_format==="ollama";
  return <>
    <div className="form-grid">
      <Field title="Deployment type"><select aria-label="Deployment type" value={spec.connection_kind??"local"} onChange={e=>{const kind=e.target.value as ConnectionKind;const d=deployments.find(d=>d.id===kind)!;onChange({...spec,connection_kind:kind,endpoint:ollama?d.example.replace(/\/v1$/,""):d.example});}}>{deployments.map(d=><option value={d.id} key={d.id}>{d.name}</option>)}</select></Field>
      <Field title="API format"><select aria-label="API format" value={spec.api_format??"openai_compatible"} onChange={e=>{const format=e.target.value as "ollama"|"openai_compatible";onChange({...spec,api_format:format,endpoint:format==="ollama"?spec.endpoint.replace(/\/v1\/?$/,""):spec.endpoint.replace(/\/$/,"")+(spec.endpoint.endsWith("/v1")?"":"/v1")});}}><option value="openai_compatible">OpenAI-compatible chat API</option><option value="ollama">Native Ollama API</option></select></Field>
    </div>
    <p className="small muted">{selected.help}</p>
    <div className="form-grid"><Field title="Maximum response tokens" hint="Blank removes the application token cap. Server context and generation settings still apply."><input aria-label="Maximum response tokens" type="number" min={1} placeholder="Unlimited" value={spec.max_output_tokens??""} onChange={e=>onChange({...spec,max_output_tokens:e.target.value===""?null:+e.target.value})}/></Field><Field title="Request timeout (seconds)" hint="Blank removes the application request timeout."><input aria-label="Request timeout (seconds)" type="number" min={1} placeholder="Unlimited" value={spec.timeout_seconds??""} onChange={e=>onChange({...spec,timeout_seconds:e.target.value===""?null:+e.target.value})}/></Field></div>
    <Field title="Tool request protocol" hint="Use the JSON adapter when your server ignores API tool schemas. It validates explicit model requests and sends them through the same application gateway; it does not claim native function calling."><select aria-label="Tool request protocol" value={spec.tool_mode??"native"} onChange={e=>onChange({...spec,tool_mode:e.target.value as "native"|"json"})}><option value="native">Native API tool_calls</option><option value="json">Validated JSON application adapter</option></select></Field>
    <Field title="API base URL" hint={ollama?"Enter the server root, such as http://127.0.0.1:11434. Requests use /api/chat.":"Enter the API base, usually ending in /v1. Requests use /chat/completions. Replace the sample address with your real URL."}><input aria-label="API base URL" type="url" value={spec.endpoint} placeholder={selected.example} onChange={e=>onChange({...spec,endpoint:e.target.value})}/></Field>
    <Field title="Model authentication"><select aria-label="Model authentication" value={auth} onChange={e=>{setAuth(e.target.value);onChange({...spec,api_key:e.target.value==="environment"?null:""});}}><option value="environment">Use AEGIS_LOCAL_API_KEY default</option><option value="none">No API key</option><option value="key">Enter a key for this target</option></select></Field>
    {auth==="key"&&<Field title="Target API key" hint="Stored in the encrypted target snapshot. The saved target returns only an authentication status."><input aria-label="Target API key" type="password" autoComplete="new-password" value={spec.api_key??""} onChange={e=>onChange({...spec,api_key:e.target.value})}/></Field>}
    <details open={spec.connection_kind==="cloudflare"}><summary className="small link">Cloudflare Access authentication</summary><div className="stack gap-top">
      <Field title="Access authentication"><select aria-label="Access authentication" value={access} onChange={e=>{setAccess(e.target.value);onChange({...spec,access_client_id:e.target.value==="environment"?null:"",access_client_secret:e.target.value==="environment"?null:""});}}><option value="none">No Cloudflare Access credentials</option><option value="environment">Use environment Access defaults</option><option value="token">Enter an Access service token</option></select></Field>
      {access==="token"&&<><Field title="Access client ID"><input aria-label="Access client ID" type="password" autoComplete="new-password" value={spec.access_client_id??""} onChange={e=>onChange({...spec,access_client_id:e.target.value})}/></Field><Field title="Access client secret"><input aria-label="Access client secret" type="password" autoComplete="new-password" value={spec.access_client_secret??""} onChange={e=>onChange({...spec,access_client_secret:e.target.value})}/></Field></>}
    </div></details>
    <p className="small muted">Connection checks run from the platform backend. A temporary tunnel outage pauses a campaign after recorded retries; reconnect the same target and select Resume. Register a new target if the URL changes.</p>
  </>;
}

export function targetReview(spec:TargetSpec & TargetConnection){
  const result={...spec};for(const key of ["api_key","access_client_id","access_client_secret"] as const){result[key]=spec[key]==null?"Environment default":spec[key]?"[Entered; hidden]":"No credential";}return result;
}
